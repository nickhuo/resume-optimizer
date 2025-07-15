"""
用于验证 LLM 输出的 Pydantic 模型
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from .page_types import PageType, ActionType


class CTACandidateSchema(BaseModel):
    """CTA候选按钮的验证模型"""
    text: str = Field(..., description="按钮文本", min_length=1, max_length=200)
    selector: str = Field(..., description="CSS选择器", min_length=1, max_length=500)
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    element_type: str = Field(..., description="元素类型", pattern=r"^(button|a|input|submit|div|span)$")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="元素属性")
    priority_score: int = Field(..., description="优先级得分", ge=1, le=10)
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        """验证按钮文本"""
        if not v.strip():
            raise ValueError('按钮文本不能为空')
        return v.strip()
    
    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v):
        """验证CSS选择器"""
        if not v.strip():
            raise ValueError('选择器不能为空')
        # 简单的CSS选择器验证
        forbidden_chars = ['{', '}', ';', ':', '(', ')']
        for char in forbidden_chars:
            if char in v:
                raise ValueError(f'选择器包含无效字符: {char}')
        return v.strip()
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """验证置信度"""
        if not 0.0 <= v <= 1.0:
            raise ValueError('置信度必须在0.0到1.0之间')
        return v


class RecommendedActionSchema(BaseModel):
    """推荐动作的验证模型"""
    action_type: str = Field(..., description="动作类型", pattern=r"^(fill_form|click_cta|login_required|wait_for_human|no_action)$")
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="推荐理由", min_length=1, max_length=1000)
    target_element: Optional[str] = Field(None, description="目标元素选择器", max_length=500)
    form_selector: Optional[str] = Field(None, description="表单选择器", max_length=500)
    priority: int = Field(..., description="优先级", ge=1, le=10)
    
    @field_validator('action_type')
    @classmethod
    def validate_action_type(cls, v):
        """验证动作类型"""
        valid_types = ['fill_form', 'click_cta', 'login_required', 'wait_for_human', 'no_action']
        if v not in valid_types:
            raise ValueError(f'无效的动作类型: {v}，必须是 {valid_types} 之一')
        return v
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v):
        """验证推荐理由"""
        if not v.strip():
            raise ValueError('推荐理由不能为空')
        return v.strip()
    
    @field_validator('target_element')
    @classmethod
    def validate_target_element(cls, v):
        """验证目标元素选择器"""
        if v is not None and not v.strip():
            return None
        return v.strip() if v else None
    
    @field_validator('form_selector')
    @classmethod
    def validate_form_selector(cls, v):
        """验证表单选择器"""
        if v is not None and not v.strip():
            return None
        return v.strip() if v else None
    
    @model_validator(mode='before')
    @classmethod
    def validate_action_consistency(cls, values):
        """验证动作的一致性"""
        action_type = values.get('action_type')
        target_element = values.get('target_element')
        form_selector = values.get('form_selector')
        
        # 如果是点击CTA，应该有目标元素
        if action_type == 'click_cta' and not target_element:
            raise ValueError('click_cta 动作必须指定 target_element')
        
        # 如果是填写表单，应该有表单选择器
        if action_type == 'fill_form' and not form_selector:
            # 允许为 None，但会在日志中记录警告
            pass
        
        # 如果不是点击CTA，不应该有目标元素
        if action_type != 'click_cta' and target_element:
            values['target_element'] = None
        
        # 如果不是填写表单，不应该有表单选择器
        if action_type != 'fill_form' and form_selector:
            values['form_selector'] = None
        
        return values


class PageAnalysisSchema(BaseModel):
    """页面分析结果的验证模型"""
    page_type: str = Field(..., description="页面类型", pattern=r"^(job_detail|job_detail_with_form|form_page|login_page|external_redirect|unknown)$")
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    form_count: int = Field(..., description="表单数量", ge=0)
    has_apply_button: bool = Field(..., description="是否有申请按钮")
    reasoning: str = Field(..., description="分析理由", min_length=1, max_length=2000)
    cta_candidates: List[CTACandidateSchema] = Field(default_factory=list, description="CTA候选按钮")
    recommended_action: RecommendedActionSchema = Field(..., description="推荐动作")
    
    @field_validator('page_type')
    @classmethod
    def validate_page_type(cls, v):
        """验证页面类型"""
        valid_types = ['job_detail', 'job_detail_with_form', 'form_page', 'login_page', 'external_redirect', 'unknown']
        if v not in valid_types:
            raise ValueError(f'无效的页面类型: {v}，必须是 {valid_types} 之一')
        return v
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v):
        """验证分析理由"""
        if not v.strip():
            raise ValueError('分析理由不能为空')
        return v.strip()
    
    @field_validator('cta_candidates')
    @classmethod
    def validate_cta_candidates(cls, v):
        """验证CTA候选按钮"""
        if len(v) > 10:
            raise ValueError('CTA候选按钮数量不能超过10个')
        return v
    
    @model_validator(mode='before')
    @classmethod
    def validate_page_consistency(cls, values):
        """验证页面分析的一致性"""
        page_type = values.get('page_type')
        form_count = values.get('form_count', 0)
        has_apply_button = values.get('has_apply_button', False)
        cta_candidates = values.get('cta_candidates', [])
        recommended_action = values.get('recommended_action')
        
        # 验证页面类型与表单数量的一致性
        if page_type == 'job_detail_with_form' and form_count == 0:
            raise ValueError('job_detail_with_form 类型的页面应该有表单 (form_count > 0)')
        
        if page_type == 'form_page' and form_count == 0:
            raise ValueError('form_page 类型的页面应该有表单 (form_count > 0)')
        
        # 验证Apply按钮与CTA候选的一致性
        if has_apply_button and not cta_candidates:
            raise ValueError('如果有Apply按钮，应该有CTA候选')
        
        # 验证推荐动作与页面类型的一致性
        if recommended_action:
            # 在 mode='before' 模式下，recommended_action 是字典而不是对象
            if isinstance(recommended_action, dict):
                action_type = recommended_action.get('action_type')
            else:
                action_type = recommended_action.action_type
            
            # 如果页面有表单，推荐动作应该是填写表单
            if form_count > 0 and page_type in ['job_detail_with_form', 'form_page']:
                if action_type not in ['fill_form', 'wait_for_human']:
                    raise ValueError(f'有表单的页面推荐动作应该是 fill_form 或 wait_for_human，而不是 {action_type}')
            
            # 如果页面没有表单但有CTA，推荐动作应该是点击CTA
            if form_count == 0 and cta_candidates and page_type == 'job_detail':
                if action_type not in ['click_cta', 'wait_for_human']:
                    raise ValueError(f'没有表单但有CTA的页面推荐动作应该是 click_cta 或 wait_for_human，而不是 {action_type}')
        
        return values


class FormFieldSchema(BaseModel):
    """表单字段的验证模型"""
    selector: str = Field(..., description="字段选择器", min_length=1, max_length=500)
    semantic_key: str = Field(..., description="语义键", min_length=1, max_length=100)
    control_type: str = Field(..., description="控件类型", pattern=r"^(text|select|checkbox|radio|textarea|file|email|password|tel|url|number|date|datetime-local|time|search)$")
    required: bool = Field(..., description="是否必填")
    validation_hints: List[str] = Field(default_factory=list, description="验证提示")
    
    @field_validator('semantic_key')
    @classmethod
    def validate_semantic_key(cls, v):
        """验证语义键"""
        if not v.strip():
            raise ValueError('语义键不能为空')
        # 语义键应该是snake_case格式
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('语义键应该是snake_case格式 (例如: first_name, email_address)')
        return v.strip()
    
    @field_validator('control_type')
    @classmethod
    def validate_control_type(cls, v):
        """验证控件类型"""
        valid_types = ['text', 'select', 'checkbox', 'radio', 'textarea', 'file', 'email', 'password', 'tel', 'url', 'number', 'date', 'datetime-local', 'time', 'search']
        if v not in valid_types:
            raise ValueError(f'无效的控件类型: {v}，必须是 {valid_types} 之一')
        return v
    
    @field_validator('validation_hints')
    @classmethod
    def validate_validation_hints(cls, v):
        """验证验证提示"""
        if len(v) > 5:
            raise ValueError('验证提示数量不能超过5个')
        return v


class FormFieldAnalysisSchema(BaseModel):
    """表单字段分析结果的验证模型"""
    fields: Dict[str, FormFieldSchema] = Field(..., description="字段映射")
    
    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v):
        """验证字段映射"""
        if not v:
            raise ValueError('字段映射不能为空')
        
        if len(v) > 50:
            raise ValueError('字段数量不能超过50个')
        
        # 检查语义键的唯一性
        semantic_keys = [field.semantic_key for field in v.values()]
        if len(semantic_keys) != len(set(semantic_keys)):
            raise ValueError('语义键必须唯一')
        
        return v
