import json
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class FieldParser:
    """
    字段解析器，提取和解析表单字段信息
    """

    def __init__(self):
        """初始化字段解析器"""
        pass

    async def extract_fields(self, page: Page) -> List[Dict[str, Any]]:
        """
        从页面提取表单字段信息
        
        Args:
            page: Playwright页面对象
            
        Returns:
            字段信息列表
        """
        try:
            # 提取所有表单输入元素（不使用:visible伪类）
            fields = await page.query_selector_all('input, select, textarea')
            field_info = []

            for field in fields:
                try:
                    # 获取元素标签名
                    tag_name = await field.evaluate('el => el.tagName.toLowerCase()')
                    
                    # 根据标签名确定字段类型
                    if tag_name == 'select':
                        field_type = 'select'
                    elif tag_name == 'textarea':
                        field_type = 'textarea'
                    else:
                        # input 元素，获取 type 属性
                        field_type = await field.get_attribute('type') or 'text'
                    
                    field_name = await field.get_attribute('name') or ''
                    field_id = await field.get_attribute('id') or ''
                    
                    # 检查元素是否可见
                    is_visible = await field.is_visible()
                    
                    # 获取字段标签
                    label = await self._get_field_label(page, field, field_id)
                    
                    # 获取占位符文本
                    placeholder = await field.get_attribute('placeholder') or ''
                    
                    # 检查是否必填
                    required = await field.get_attribute('required') is not None
                    
                    # 检查是否禁用
                    disabled = await field.get_attribute('disabled') is not None
                    
                    # 获取当前值
                    current_value = await field.get_attribute('value') or ''
                    
                    # 构建选择器
                    selector = await self._build_selector(field, field_id, field_name)
                    
                    # 对于select元素，获取选项
                    options = []
                    if field_type == 'select':
                        option_elements = await field.query_selector_all('option')
                        for option in option_elements:
                            option_value = await option.get_attribute('value') or ''
                            option_text = await option.inner_text()
                            options.append({
                                'value': option_value,
                                'text': option_text.strip()
                            })
                    
                    # 对于radio/checkbox，获取值
                    field_value = ''
                    if field_type in ['radio', 'checkbox']:
                        field_value = await field.get_attribute('value') or ''
                    
                    info = {
                        'type': field_type,
                        'name': field_name,
                        'id': field_id,
                        'label': label,
                        'placeholder': placeholder,
                        'selector': selector,
                        'required': required,
                        'disabled': disabled,
                        'visible': is_visible,
                        'current_value': current_value,
                        'value': field_value,  # 对于radio/checkbox
                        'options': options
                    }
                    
                    # 过滤掉隐藏的输入框（但保留文件输入，因为它们通常是隐藏的）
                    # 过滤掉禁用的字段
                    # 过滤掉隐藏的非file类型字段
                    if not disabled and (is_visible or field_type == 'file' or field_type == 'hidden'):
                        field_info.append(info)
                        
                except Exception as e:
                    logger.warning(f"Failed to extract field info: {e}")
                    continue

            logger.info(f"Extracted {len(field_info)} fields from page")
            return field_info
            
        except Exception as e:
            logger.error(f"Failed to extract fields: {e}")
            return []
    
    async def extract_all_forms(self, page: Page) -> List[Dict[str, Any]]:
        """
        提取页面上所有表单的信息
        
        Args:
            page: Playwright页面对象
            
        Returns:
            表单信息列表
        """
        try:
            forms = await page.query_selector_all('form')
            form_info = []
            
            for idx, form in enumerate(forms):
                form_id = await form.get_attribute('id') or f'form_{idx}'
                form_name = await form.get_attribute('name') or ''
                form_action = await form.get_attribute('action') or ''
                form_method = await form.get_attribute('method') or 'get'
                
                # 提取表单内的字段
                fields_in_form = await form.query_selector_all('input, select, textarea')
                
                form_data = {
                    'id': form_id,
                    'name': form_name,
                    'action': form_action,
                    'method': form_method,
                    'field_count': len(fields_in_form),
                    'selector': f'form#{form_id}' if form_id != f'form_{idx}' else f'form:nth-of-type({idx + 1})'
                }
                
                form_info.append(form_data)
            
            return form_info
            
        except Exception as e:
            logger.error(f"Failed to extract forms: {e}")
            return []
    
    async def _get_field_label(self, page: Page, field, field_id: str) -> str:
        """
        获取字段的标签文本
        
        Args:
            page: 页面对象
            field: 字段元素
            field_id: 字段ID
            
        Returns:
            标签文本
        """
        label = ''
        
        try:
            # 方法1: 通过aria-label属性
            aria_label = await field.get_attribute('aria-label')
            if aria_label:
                return aria_label.strip()
            
            # 方法2: 通过关联的label标签
            if field_id:
                label_element = await page.query_selector(f'label[for="{field_id}"]')
                if label_element:
                    label = await label_element.inner_text()
                    return label.strip()
            
            # 方法3: 查找包含该字段的label
            parent = await field.evaluate('el => el.parentElement')
            if parent:
                parent_tag = await page.evaluate('el => el.tagName.toLowerCase()', parent)
                if parent_tag == 'label':
                    label = await page.evaluate('el => el.textContent', parent)
                    return label.strip()
            
            # 方法4: 查找附近的文本节点
            label = await page.evaluate('''
                (field) => {
                    const parent = field.parentElement;
                    if (parent) {
                        const texts = [];
                        for (const node of parent.childNodes) {
                            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                                texts.push(node.textContent.trim());
                            }
                        }
                        return texts.join(' ');
                    }
                    return '';
                }
            ''', field)
            
            if label:
                return label.strip()
                
        except Exception as e:
            logger.debug(f"Failed to get field label: {e}")
        
        return label
    
    async def _build_selector(self, field, field_id: str, field_name: str) -> str:
        """
        构建字段的CSS选择器
        
        Args:
            field: 字段元素
            field_id: 字段ID
            field_name: 字段名称
            
        Returns:
            CSS选择器
        """
        try:
            # 优先使用ID选择器
            if field_id:
                return f'#{field_id}'
            
            # 其次使用name属性
            if field_name:
                field_type = await field.evaluate('el => el.tagName.toLowerCase()')
                return f'{field_type}[name="{field_name}"]'
            
            # 最后使用evaluate生成唯一选择器
            selector = await field.evaluate('''
                (el) => {
                    if (el.id) return '#' + CSS.escape(el.id);
                    if (el.className) {
                        const classes = el.className.split(' ').filter(c => c).map(c => '.' + CSS.escape(c)).join('');
                        if (classes) return el.tagName.toLowerCase() + classes;
                    }
                    // Generate nth-child selector
                    let child = el;
                    let n = 1;
                    while (child.previousElementSibling) {
                        child = child.previousElementSibling;
                        n++;
                    }
                    return el.tagName.toLowerCase() + ':nth-child(' + n + ')';
                }
            ''', field)
            
            return selector
            
        except Exception as e:
            logger.warning(f"Failed to build selector: {e}")
            return 'input'
