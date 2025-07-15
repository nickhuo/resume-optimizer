"""
页面类型分析器，使用GPT进行页面判定
"""
import logging
from typing import List, Dict, Any
from .gpt_service import GPTService
from ..models.page_types import PageType, PageAnalysisResult, CTACandidate, ActionType, RecommendedAction

logger = logging.getLogger(__name__)


class PageAnalyzer:
    """页面分析器，负责判断页面类型和识别CTA按钮"""
    
    def __init__(self, gpt_service: GPTService):
        """
        初始化页面分析器
        
        Args:
            gpt_service: GPT服务实例
        """
        self.gpt_service = gpt_service
    
    def analyze_page(self, url: str, title: str, content: str, 
                    buttons: List[Dict[str, Any]], forms: List[Dict[str, Any]] = None) -> PageAnalysisResult:
        """
        分析页面，判断页面类型并识别CTA按钮
        
        Args:
            url: 页面URL
            title: 页面标题
            content: 页面文本内容
            buttons: 页面上的按钮信息
            
        Returns:
            PageAnalysisResult: 分析结果
        """
        try:
            # 调用GPT服务分析页面
            gpt_response = self.gpt_service.analyze_page_content(
                url=url,
                title=title,
                content=content,
                buttons=buttons,
                forms=forms
            )
            
            # 解析CTA候选按钮
            cta_candidates = []
            for cta_data in gpt_response.get('cta_candidates', []):
                try:
                    cta = CTACandidate(
                        text=cta_data.get('text', ''),
                        selector=cta_data.get('selector', ''),
                        confidence=float(cta_data.get('confidence', 0.0)),
                        element_type=cta_data.get('element_type', 'unknown'),
                        attributes=cta_data.get('attributes', {}),
                        priority_score=int(cta_data.get('priority_score', 1))
                    )
                    cta_candidates.append(cta)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse CTA candidate: {e}")
            
            # 构建分析结果
            return PageAnalysisResult(
                page_type=PageType(gpt_response.get('page_type', 'unknown')),
                confidence=float(gpt_response.get('confidence', 0.0)),
                title=title,
                url=url,
                form_count=int(gpt_response.get('form_count', 0)),
                has_apply_button=bool(gpt_response.get('has_apply_button', False)),
                cta_candidates=sorted(cta_candidates),  # 按优先级排序
                reasoning=gpt_response.get('reasoning', ''),
                raw_content=content
            )
            
        except Exception as e:
            logger.error(f"Error analyzing page {url}: {str(e)}")
            # 返回默认结果
            return PageAnalysisResult(
                page_type=PageType.UNKNOWN,
                confidence=0.0,
                title=title,
                url=url,
                form_count=0,
                has_apply_button=False,
                cta_candidates=[],
                reasoning=f"Analysis failed: {str(e)}",
                raw_content=content
            )
    
    def get_recommended_action(self, url: str, title: str, content: str, 
                             buttons: List[Dict[str, Any]], 
                             forms: List[Dict[str, Any]] = None) -> RecommendedAction:
        """
        获取推荐的下一步动作
        
        Args:
            url: 页面URL
            title: 页面标题
            content: 页面文本内容
            buttons: 页面上的按钮信息
            forms: 页面上的表单信息（可选）
            
        Returns:
            RecommendedAction: 推荐的动作
        """
        try:
            # 调用GPT服务分析页面
            gpt_response = self.gpt_service.analyze_page_content(
                url=url,
                title=title,
                content=content,
                buttons=buttons,
                forms=forms
            )
            
            # 解析推荐动作
            action_data = gpt_response.get('recommended_action', {})
            
            return RecommendedAction(
                action_type=ActionType(action_data.get('action_type', 'no_action')),
                confidence=float(action_data.get('confidence', 0.0)),
                reasoning=action_data.get('reasoning', ''),
                target_element=action_data.get('target_element'),
                form_selector=action_data.get('form_selector'),
                priority=int(action_data.get('priority', 1))
            )
            
        except Exception as e:
            logger.error(f"Error getting recommended action for {url}: {str(e)}")
            return RecommendedAction(
                action_type=ActionType.WAIT_FOR_HUMAN,
                confidence=0.0,
                reasoning=f"Error analyzing page: {str(e)}",
                priority=1
            )
    
    def should_proceed_with_cta(self, analysis_result: PageAnalysisResult,
                               min_confidence: float = 0.6) -> bool:
        """
        判断是否应该继续执行CTA点击
        
        Args:
            analysis_result: 页面分析结果
            min_confidence: 最低置信度阈值
            
        Returns:
            bool: 是否应该继续
        """
        # 如果页面类型不是职位详情页，不继续
        if analysis_result.page_type != PageType.JOB_DETAIL:
            logger.info(f"Page type is {analysis_result.page_type.value}, not proceeding with CTA")
            return False
        
        # 如果没有CTA候选，不继续
        if not analysis_result.cta_candidates:
            logger.info("No CTA candidates found")
            return False
        
        # 检查最高置信度的CTA
        best_cta = analysis_result.cta_candidates[0]
        if best_cta.confidence < min_confidence:
            logger.info(f"Best CTA confidence {best_cta.confidence} is below threshold {min_confidence}")
            return False
        
        return True
    
    def should_proceed_with_action(self, analysis_result: PageAnalysisResult, 
                                  recommended_action: RecommendedAction,
                                  min_confidence: float = 0.6) -> bool:
        """
        新的智能决策方法：根据页面类型和推荐动作决定是否继续
        
        Args:
            analysis_result: 页面分析结果
            recommended_action: 推荐动作
            min_confidence: 最低置信度阈值
            
        Returns:
            bool: 是否应该继续
        """
        # 检查推荐动作的置信度
        if recommended_action.confidence < min_confidence:
            logger.info(f"Recommended action confidence {recommended_action.confidence} is below threshold {min_confidence}")
            return False
        
        # 根据动作类型做决定
        if recommended_action.action_type == ActionType.FILL_FORM:
            # 填写表单：检查页面是否有表单且与职位相关
            if analysis_result.form_count > 0:
                if analysis_result.page_type in [PageType.JOB_DETAIL_WITH_FORM, PageType.FORM_PAGE]:
                    logger.info(f"Proceeding with form filling on {analysis_result.page_type.value}")
                    return True
                else:
                    logger.info(f"Form found but page type is {analysis_result.page_type.value}, not proceeding")
                    return False
            else:
                logger.info("No forms found for fill_form action")
                return False
        
        elif recommended_action.action_type == ActionType.CLICK_CTA:
            # 点击CTA：检查是否有适合的CTA按钮且页面类型合适
            if analysis_result.page_type in [PageType.JOB_DETAIL, PageType.JOB_DETAIL_WITH_FORM]:
                if analysis_result.cta_candidates:
                    best_cta = analysis_result.cta_candidates[0]
                    if best_cta.confidence >= min_confidence:
                        logger.info(f"Proceeding with CTA click: {best_cta.text}")
                        return True
                    else:
                        logger.info(f"Best CTA confidence {best_cta.confidence} is below threshold")
                        return False
                else:
                    logger.info("No CTA candidates found")
                    return False
            else:
                logger.info(f"Page type {analysis_result.page_type.value} not suitable for CTA click")
                return False
        
        elif recommended_action.action_type == ActionType.LOGIN_REQUIRED:
            logger.info("Login required, human intervention needed")
            return False
        
        elif recommended_action.action_type == ActionType.WAIT_FOR_HUMAN:
            logger.info("Waiting for human intervention")
            return False
        
        elif recommended_action.action_type == ActionType.NO_ACTION:
            logger.info("No action recommended")
            return False
        
        else:
            logger.warning(f"Unknown action type: {recommended_action.action_type}")
            return False
    
    def get_action_description(self, recommended_action: RecommendedAction) -> str:
        """
        获取动作的中文描述
        
        Args:
            recommended_action: 推荐动作
            
        Returns:
            str: 中文描述
        """
        action_descriptions = {
            ActionType.FILL_FORM: "填写表单",
            ActionType.CLICK_CTA: "点击CTA按钮",
            ActionType.LOGIN_REQUIRED: "需要登录",
            ActionType.WAIT_FOR_HUMAN: "等待人工干预",
            ActionType.NO_ACTION: "无需操作"
        }
        
        return action_descriptions.get(recommended_action.action_type, "未知动作")
