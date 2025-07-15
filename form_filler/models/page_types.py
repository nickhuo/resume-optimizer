"""
页面类型定义和相关数据模型
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


class ActionType(Enum):
    """推荐的动作类型"""
    FILL_FORM = "fill_form"  # 填写表单
    CLICK_CTA = "click_cta"  # 点击CTA按钮
    LOGIN_REQUIRED = "login_required"  # 需要登录
    WAIT_FOR_HUMAN = "wait_for_human"  # 等待人工干预
    NO_ACTION = "no_action"  # 不采取任何动作


class PageType(Enum):
    """页面类型枚举"""
    JOB_DETAIL = "job_detail"  # 职位详情页（仅详情，无表单）
    JOB_DETAIL_WITH_FORM = "job_detail_with_form"  # 职位详情页（带申请表单）
    FORM_PAGE = "form_page"    # 独立表单页
    LOGIN_PAGE = "login_page"  # 登录页
    EXTERNAL_REDIRECT = "external_redirect"  # 外部跳转
    UNKNOWN = "unknown"        # 未知类型


@dataclass
class PageAnalysisResult:
    """页面分析结果"""
    page_type: PageType
    confidence: float  # 0.0 - 1.0
    title: str
    url: str
    form_count: int
    has_apply_button: bool
    cta_candidates: List['CTACandidate']
    reasoning: str  # LLM的判断理由
    raw_content: Optional[str] = None  # 原始内容，用于调试


@dataclass
class CTACandidate:
    """CTA（Call-to-Action）候选按钮"""
    text: str
    selector: str
    confidence: float  # 0.0 - 1.0
    element_type: str  # button, a, input等
    attributes: Dict[str, Any]  # 元素属性
    priority_score: int  # 基于PRD定义的优先级得分
    
    def __lt__(self, other):
        """用于排序，优先级高的排前面"""
        if self.confidence != other.confidence:
            return self.confidence > other.confidence
        return self.priority_score > other.priority_score


@dataclass
class RecommendedAction:
    """推荐的动作"""
    action_type: ActionType
    confidence: float  # 0.0 - 1.0
    reasoning: str  # 推荐理由
    target_element: Optional[str] = None  # 目标元素选择器（对于CTA按钮）
    form_selector: Optional[str] = None  # 表单选择器（对于表单填写）
    priority: int = 1  # 优先级（1-10）
    

@dataclass
class NavigationResult:
    """导航操作结果"""
    success: bool
    navigation_type: str  # same_page, new_tab, iframe, external
    new_url: Optional[str] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    time_elapsed: float = 0.0
