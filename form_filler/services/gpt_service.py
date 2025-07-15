"""
GPT服务封装，用于与OpenAI API交互
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
import time
from pydantic import ValidationError

from ..models.llm_schemas import PageAnalysisSchema, FormFieldAnalysisSchema

logger = logging.getLogger(__name__)


class GPTService:
    """封装OpenAI GPT服务，提供统一的接口"""
    
    def __init__(self, model: str = "gpt-4o-mini", max_retries: int = 3):
        """
        初始化GPT服务
        
        Args:
            model: 使用的模型名称
            max_retries: 最大重试次数
        """
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        
    def analyze_page_content(self, url: str, title: str, content: str, 
                           buttons: List[Dict[str, Any]], forms: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析页面内容，判断页面类型和CTA按钮
        
        Args:
            url: 页面URL
            title: 页面标题
            content: 页面文本内容
            buttons: 页面上的按钮信息列表
            
        Returns:
            包含页面类型、CTA候选等信息的字典
        """
        # 构建系统提示
        system_prompt = """You are a web page analyzer specializing in job application flows. 
        Analyze the given page content and return ONLY a valid JSON response with the following structure. 
        Do not include any markdown formatting, code blocks, or comments.
        IMPORTANT: Return complete, valid JSON without ellipsis (...) or truncation.
        Keep responses concise to avoid size limits.
        {
            "page_type": "job_detail" | "job_detail_with_form" | "form_page" | "login_page" | "external_redirect" | "unknown",
            "confidence": 0.0-1.0,
            "form_count": number,
            "has_apply_button": boolean,
            "reasoning": "brief explanation",
            "cta_candidates": [
                {
                    "text": "button text",
                    "selector": "CSS selector",
                    "confidence": 0.0-1.0,
                    "element_type": "button" | "a" | "input",
                    "priority_score": 1-10
                }
            ],
            "recommended_action": {
                "action_type": "fill_form" | "click_cta" | "login_required" | "wait_for_human" | "no_action",
                "confidence": 0.0-1.0,
                "reasoning": "brief explanation",
                "target_element": "CSS selector or null",
                "form_selector": "CSS selector or null",
                "priority": 1-10
            }
        }
        
        Page type classification rules:
        - job_detail: Job posting with description, but NO application form on same page (only has navigation buttons like "Apply now" that link to other pages)
        - job_detail_with_form: Job posting with ACTUAL application form on same page (contains input fields like name, email, resume upload, etc.)
        - form_page: Standalone application form page (primarily form fields, minimal job description)
        - login_page: Login or authentication required
        - external_redirect: Page redirects to external site
        - unknown: Cannot determine page type
        
        IMPORTANT: Only classify as "job_detail_with_form" if the page contains ACTUAL FORM FIELDS (input, textarea, select, file upload, etc.) for job application. 
        If the page only has "Apply" buttons that are links to other pages, classify as "job_detail".
        
        Form counting rules:
        - Count only actual HTML forms or form-like structures with input fields
        - Do NOT count standalone buttons that are just navigation links
        - Look for elements like: input[type="text"], input[type="email"], textarea, select, input[type="file"]
        
        Action recommendation logic:
        - If form_count > 0 AND page contains job details: recommend "fill_form"
        - If form_count = 0 AND has good CTA candidates: recommend "click_cta"
        - If login is required: recommend "login_required"
        - If uncertain or low confidence: recommend "wait_for_human"
        - If no clear action: recommend "no_action"
        
        Priority scoring rules:
        - Text containing "Apply", "开始申请", "立即投递": 10
        - aria-label or data-action containing "apply": 9
        - URL containing /apply or /candidate: 8
        - Prominent button with high contrast: 7
        - Other relevant buttons: 1-6
        """
        
        # 构建用户提示
        forms_info = "No forms found on this page."
        if forms and len(forms) > 0:
            forms_info = f"Found {len(forms)} form(s) on this page:\n{json.dumps(forms[:5], indent=2)}"
        
        user_prompt = f"""Analyze this page:
        
URL: {url}
Title: {title}

Content (first 1500 chars):
{content[:1500]}

Buttons found on page:
{json.dumps(buttons[:20], indent=2)}

Forms found on page:
{forms_info}

Please provide your analysis in the specified JSON format. 
IMPORTANT: Base your form_count on the actual forms found above, not just the presence of Apply buttons."""
        
        raw_response = self._make_request(system_prompt, user_prompt, response_format="json")
        return self._validate_and_fix_page_analysis(raw_response)
    
    def analyze_form_fields(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析表单字段，识别每个字段的语义
        
        Args:
            fields: 表单字段信息列表
            
        Returns:
            包含字段映射的字典
        """
        system_prompt = """You are a form field analyzer. 
        For each form field, identify its semantic meaning and provide mapping information.
        Return a JSON response with field mappings."""
        
        user_prompt = f"""Analyze these form fields and identify their semantic meanings:
        
{json.dumps(fields, indent=2)}

Return a JSON object where keys are field selectors and values contain:
- semantic_key: standardized field name (e.g., 'first_name', 'email', 'phone')
- control_type: 'text' | 'select' | 'checkbox' | 'radio' | 'textarea' | 'file'
- required: boolean
- validation_hints: any validation rules detected"""
        
        return self._make_request(system_prompt, user_prompt, response_format="json")
    
    def _make_request(self, system_prompt: str, user_prompt: str, 
                     response_format: str = "text") -> Any:
        """
        向OpenAI API发送请求，带重试机制
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            response_format: 期望的响应格式 ("text" 或 "json")
            
        Returns:
            API响应内容
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,  # 低温度以获得更一致的结果
                    max_tokens=4000,  # 增加token限制以避免截断
                    response_format={"type": "json_object"} if response_format == "json" and self.model.startswith("gpt-4") else None
                )
                
                content = response.choices[0].message.content
                logger.debug(f"GPT Response: {content[:200]}...")
                
                if response_format == "json":
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON directly: {e}")
                        # 尝试清理和提取JSON部分
                        import re
                        
                        # 移除可能的markdown代码块标记
                        content = re.sub(r'```json\s*', '', content)
                        content = re.sub(r'```\s*$', '', content)
                        
                        # 尝试提取JSON对象
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            try:
                                # 尝试清理常见的JSON格式问题
                                json_str = re.sub(r'\s*//.*?\n', '\n', json_str)  # 移除单行注释
                                json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)  # 移除多行注释
                                json_str = re.sub(r',\s*}', '}', json_str)  # 移除末尾多余的逗号
                                json_str = re.sub(r',\s*]', ']', json_str)  # 移除数组末尾多余的逗号
                                
                                return json.loads(json_str)
                            except json.JSONDecodeError as e2:
                                logger.error(f"Failed to parse cleaned JSON: {e2}")
                                logger.error(f"Original content: {content[:500]}...")
                                logger.error(f"Cleaned JSON: {json_str[:500]}...")
                                # 返回一个默认的错误响应
                                return self._get_default_error_response(str(e2))
                        else:
                            logger.error(f"No JSON object found in response: {content[:500]}...")
                            return self._get_default_error_response("No JSON object found in response")
                
                return content
                
            except Exception as e:
                logger.warning(f"GPT request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise RuntimeError(f"Failed to get GPT response after {self.max_retries} attempts: {e}")
    
    def _get_default_error_response(self, error_message: str) -> Dict[str, Any]:
        """
        生成默认的错误响应
        
        Args:
            error_message: 错误消息
            
        Returns:
            Dict[str, Any]: 默认的错误响应
        """
        return {
            "page_type": "unknown",
            "confidence": 0.0,
            "form_count": 0,
            "has_apply_button": False,
            "reasoning": f"JSON parsing error: {error_message}",
            "cta_candidates": [],
            "recommended_action": {
                "action_type": "wait_for_human",
                "confidence": 0.0,
                "reasoning": f"Failed to parse GPT response: {error_message}",
                "target_element": None,
                "form_selector": None,
                "priority": 1
            }
        }
    
    def _validate_and_fix_page_analysis(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 Pydantic 验证和修复页面分析响应
        
        Args:
            raw_response: 原始GPT响应
            
        Returns:
            Dict[str, Any]: 验证和修复后的响应
        """
        try:
            # 尝试使用 Pydantic 验证
            validated_response = PageAnalysisSchema(**raw_response)
            logger.info("✓ Page analysis response passed Pydantic validation")
            return validated_response.model_dump()
            
        except ValidationError as e:
            logger.warning(f"Page analysis validation failed: {e}")
            
            # 尝试修复常见的验证错误
            fixed_response = self._fix_page_analysis_errors(raw_response, e)
            
            try:
                # 再次验证修复后的响应
                validated_response = PageAnalysisSchema(**fixed_response)
                logger.info("✓ Page analysis response passed validation after fixes")
                return validated_response.model_dump()
                
            except ValidationError as e2:
                logger.error(f"Failed to fix page analysis errors: {e2}")
                # 返回默认错误响应
                return self._get_default_error_response(f"Validation error: {str(e2)}")
    
    def _fix_page_analysis_errors(self, response: Dict[str, Any], error: ValidationError) -> Dict[str, Any]:
        """
        修复页面分析响应中的常见错误
        
        Args:
            response: 原始响应
            error: 验证错误
            
        Returns:
            Dict[str, Any]: 修复后的响应
        """
        fixed_response = response.copy()
        
        # 修复缺失的字段
        if 'page_type' not in fixed_response:
            fixed_response['page_type'] = 'unknown'
        if 'confidence' not in fixed_response:
            fixed_response['confidence'] = 0.0
        if 'form_count' not in fixed_response:
            fixed_response['form_count'] = 0
        if 'has_apply_button' not in fixed_response:
            fixed_response['has_apply_button'] = False
        if 'reasoning' not in fixed_response:
            fixed_response['reasoning'] = 'No reasoning provided'
        if 'cta_candidates' not in fixed_response:
            fixed_response['cta_candidates'] = []
        if 'recommended_action' not in fixed_response:
            fixed_response['recommended_action'] = {
                'action_type': 'wait_for_human',
                'confidence': 0.0,
                'reasoning': 'No action recommendation provided',
                'target_element': None,
                'form_selector': None,
                'priority': 1
            }
        
        # 修复页面类型
        valid_page_types = ['job_detail', 'job_detail_with_form', 'form_page', 'login_page', 'external_redirect', 'unknown']
        if fixed_response['page_type'] not in valid_page_types:
            fixed_response['page_type'] = 'unknown'
        
        # 修复置信度
        if not isinstance(fixed_response['confidence'], (int, float)) or not (0.0 <= fixed_response['confidence'] <= 1.0):
            fixed_response['confidence'] = 0.0
        
        # 修复表单数量
        if not isinstance(fixed_response['form_count'], int) or fixed_response['form_count'] < 0:
            fixed_response['form_count'] = 0
        
        # 修复CTA候选
        if not isinstance(fixed_response['cta_candidates'], list):
            fixed_response['cta_candidates'] = []
        else:
            # 修复每个CTA候选
            fixed_cta_candidates = []
            for cta in fixed_response['cta_candidates']:
                if isinstance(cta, dict):
                    fixed_cta = self._fix_cta_candidate(cta)
                    if fixed_cta:
                        fixed_cta_candidates.append(fixed_cta)
            fixed_response['cta_candidates'] = fixed_cta_candidates[:10]  # 限制数量
        
        # 修复推荐动作
        if not isinstance(fixed_response['recommended_action'], dict):
            fixed_response['recommended_action'] = {
                'action_type': 'wait_for_human',
                'confidence': 0.0,
                'reasoning': 'Invalid action recommendation',
                'target_element': None,
                'form_selector': None,
                'priority': 1
            }
        else:
            fixed_response['recommended_action'] = self._fix_recommended_action(fixed_response['recommended_action'])
        
        return fixed_response
    
    def _fix_cta_candidate(self, cta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        修复CTA候选按钮的错误
        
        Args:
            cta: CTA候选按钮数据
            
        Returns:
            Optional[Dict[str, Any]]: 修复后的CTA候选按钮，如果无法修复则返回None
        """
        try:
            fixed_cta = {
                'text': str(cta.get('text', '')).strip() or 'Unknown Button',
                'selector': str(cta.get('selector', '')).strip() or '.unknown',
                'confidence': float(cta.get('confidence', 0.0)),
                'element_type': str(cta.get('element_type', 'button')),
                'attributes': cta.get('attributes', {}),
                'priority_score': int(cta.get('priority_score', 1))
            }
            
            # 验证和修复置信度
            if not (0.0 <= fixed_cta['confidence'] <= 1.0):
                # 如果 confidence 值太大，可能是错误地使用了 priority_score
                if fixed_cta['confidence'] >= 1.0 and fixed_cta['confidence'] <= 10.0:
                    # 将 1-10 的范围转换为 0-1
                    fixed_cta['confidence'] = fixed_cta['confidence'] / 10.0
                else:
                    fixed_cta['confidence'] = 0.0
            
            # 验证和修复元素类型
            valid_element_types = ['button', 'a', 'input', 'submit', 'div', 'span']
            if fixed_cta['element_type'] not in valid_element_types:
                fixed_cta['element_type'] = 'button'
            
            # 验证和修复优先级得分
            if not (1 <= fixed_cta['priority_score'] <= 10):
                fixed_cta['priority_score'] = 1
            
            return fixed_cta
            
        except Exception as e:
            logger.warning(f"Failed to fix CTA candidate: {e}")
            return None
    
    def _fix_recommended_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        修复推荐动作的错误
        
        Args:
            action: 推荐动作数据
            
        Returns:
            Dict[str, Any]: 修复后的推荐动作
        """
        valid_action_types = ['fill_form', 'click_cta', 'login_required', 'wait_for_human', 'no_action']
        
        fixed_action = {
            'action_type': str(action.get('action_type', 'wait_for_human')),
            'confidence': float(action.get('confidence', 0.0)),
            'reasoning': str(action.get('reasoning', '')).strip() or 'No reasoning provided',
            'target_element': action.get('target_element'),
            'form_selector': action.get('form_selector'),
            'priority': int(action.get('priority', 1))
        }
        
        # 修复动作类型
        if fixed_action['action_type'] not in valid_action_types:
            fixed_action['action_type'] = 'wait_for_human'
        
        # 修复置信度
        if not (0.0 <= fixed_action['confidence'] <= 1.0):
            fixed_action['confidence'] = 0.0
        
        # 修复优先级
        if not (1 <= fixed_action['priority'] <= 10):
            fixed_action['priority'] = 1
        
        # 修复选择器
        if fixed_action['target_element'] is not None:
            fixed_action['target_element'] = str(fixed_action['target_element']).strip() or None
        
        if fixed_action['form_selector'] is not None:
            fixed_action['form_selector'] = str(fixed_action['form_selector']).strip() or None
        
        return fixed_action
    
    def _validate_and_fix_form_analysis(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 Pydantic 验证和修复表单字段分析响应
        
        Args:
            raw_response: 原始GPT响应
            
        Returns:
            Dict[str, Any]: 验证和修复后的响应
        """
        try:
            # 尝试使用 Pydantic 验证
            validated_response = FormFieldAnalysisSchema(**raw_response)
            logger.info("✓ Form analysis response passed Pydantic validation")
            return validated_response.model_dump()
            
        except ValidationError as e:
            logger.warning(f"Form analysis validation failed: {e}")
            
            # 如果验证失败，返回空的字段映射
            return {
                'fields': {}
            }
