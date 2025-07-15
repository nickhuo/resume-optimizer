"""
DOM元素提取工具，用于从页面中提取所需的元素信息
"""
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)


class DOMExtractor:
    """DOM元素提取器，负责从页面中提取各种元素信息"""
    
    def __init__(self, page: Page):
        """
        初始化DOM提取器
        
        Args:
            page: Playwright页面对象
        """
        self.page = page
    
    async def extract_page_content(self, max_length: int = 5000) -> str:
        """
        提取页面的文本内容
        
        Args:
            max_length: 最大文本长度
            
        Returns:
            页面文本内容
        """
        try:
            # 移除不需要的元素
            await self._remove_unwanted_elements()
            
            # 获取主要内容区域的文本
            content = await self.page.evaluate("""
                () => {
                    // 尝试找到主要内容区域
                    const mainSelectors = ['main', 'article', '[role="main"]', '.job-description', '.content'];
                    for (const selector of mainSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.textContent.trim().length > 100) {
                            return element.textContent.trim();
                        }
                    }
                    // 如果没找到特定区域，返回body内容
                    return document.body.textContent.trim();
                }
            """)
            
            # 清理文本
            content = self._clean_text(content)
            
            # 截断到最大长度
            if len(content) > max_length:
                content = content[:max_length] + "..."
                
            return content
            
        except Exception as e:
            logger.error(f"Failed to extract page content: {e}")
            return ""
    
    async def extract_buttons(self) -> List[Dict[str, Any]]:
        """
        提取页面上所有可能的CTA按钮
        
        Returns:
            按钮信息列表
        """
        try:
            buttons = await self.page.evaluate("""
                () => {
                    const buttons = [];
                    
                    // 收集所有可能的按钮元素
                    const selectors = [
                        'button',
                        'a[href*="apply"]',
                        'a[href*="candidate"]',
                        'input[type="submit"]',
                        'input[type="button"]',
                        '[role="button"]',
                        '.btn',
                        '.button'
                    ];
                    
                    const elements = new Set();
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.offsetWidth > 0 && el.offsetHeight > 0) {  // 只收集可见元素
                                elements.add(el);
                            }
                        });
                    });
                    
                    elements.forEach(el => {
                        const text = el.textContent.trim() || el.value || '';
                        const href = el.href || '';
                        
                        // 过滤掉明显不是申请按钮的元素
                        const excludePatterns = ['cookie', 'privacy', 'terms', 'login', 'sign in', 'register'];
                        const textLower = text.toLowerCase();
                        if (excludePatterns.some(pattern => textLower.includes(pattern))) {
                            return;
                        }
                        
                        // 构建选择器
                        let selector = '';
                        if (el.id) {
                            selector = `#${el.id}`;
                        } else if (el.className) {
                            selector = el.tagName.toLowerCase() + '.' + el.className.split(' ').join('.');
                        } else {
                            selector = el.tagName.toLowerCase();
                            if (el.textContent) {
                                selector += `:text("${el.textContent.trim().substring(0, 30)}")`;
                            }
                        }
                        
                        buttons.push({
                            text: text,
                            selector: selector,
                            element_type: el.tagName.toLowerCase(),
                            attributes: {
                                href: href,
                                class: el.className,
                                id: el.id,
                                'aria-label': el.getAttribute('aria-label'),
                                'data-action': el.getAttribute('data-action'),
                                'data-test': el.getAttribute('data-test'),
                                style: {
                                    backgroundColor: window.getComputedStyle(el).backgroundColor,
                                    color: window.getComputedStyle(el).color,
                                    fontSize: window.getComputedStyle(el).fontSize
                                }
                            }
                        });
                    });
                    
                    return buttons;
                }
            """)
            
            logger.info(f"Extracted {len(buttons)} button candidates")
            return buttons
            
        except Exception as e:
            logger.error(f"Failed to extract buttons: {e}")
            return []
    
    async def extract_forms(self) -> List[Dict[str, Any]]:
        """
        提取页面上的表单信息
        
        Returns:
            表单信息列表
        """
        try:
            forms = await self.page.evaluate("""
                () => {
                    const forms = [];
                    document.querySelectorAll('form').forEach((form, index) => {
                        const fields = [];
                        
                        // 收集表单字段
                        form.querySelectorAll('input, select, textarea').forEach(field => {
                            if (field.type === 'hidden') return;
                            
                            // 尝试找到关联的label
                            let label = '';
                            if (field.id) {
                                const labelEl = document.querySelector(`label[for="${field.id}"]`);
                                if (labelEl) label = labelEl.textContent.trim();
                            }
                            
                            // 如果没有找到label，尝试其他方法
                            if (!label) {
                                // 检查是否在label内部
                                const parentLabel = field.closest('label');
                                if (parentLabel) {
                                    // 获取label文本，但排除field本身的内容
                                    const labelClone = parentLabel.cloneNode(true);
                                    const fieldClone = labelClone.querySelector(field.tagName.toLowerCase());
                                    if (fieldClone) fieldClone.remove();
                                    label = labelClone.textContent.trim();
                                }
                            }
                            
                            // 如果还是没有label，检查相邻元素
                            if (!label) {
                                const prev = field.previousElementSibling;
                                if (prev && (prev.tagName === 'LABEL' || prev.tagName === 'SPAN')) {
                                    label = prev.textContent.trim();
                                }
                            }
                            
                            // 收集更多属性用于调试
                            const fieldInfo = {
                                type: field.type || field.tagName.toLowerCase(),
                                name: field.name,
                                id: field.id,
                                label: label,
                                placeholder: field.placeholder,
                                required: field.required,
                                'aria-label': field.getAttribute('aria-label'),
                                'aria-required': field.getAttribute('aria-required'),
                                'data-required': field.getAttribute('data-required'),
                                className: field.className,
                                value: field.value,
                                // HTML5 验证属性
                                pattern: field.pattern,
                                minLength: field.minLength,
                                maxLength: field.maxLength,
                                min: field.min,
                                max: field.max,
                                // 计算选择器
                                selector: field.id ? `#${field.id}` : 
                                         field.name ? `[name="${field.name}"]` : 
                                         field.className ? `.${field.className.split(' ')[0]}` : 
                                         field.tagName.toLowerCase(),
                                // 父元素信息
                                parentTag: field.parentElement ? field.parentElement.tagName : null,
                                parentClass: field.parentElement ? field.parentElement.className : null
                            };
                            
                            fields.push(fieldInfo);
                        });
                        
                        forms.push({
                            index: index,
                            id: form.id,
                            className: form.className,
                            action: form.action,
                            method: form.method,
                            enctype: form.enctype,
                            autocomplete: form.autocomplete,
                            novalidate: form.novalidate,
                            fields: fields
                        });
                    });
                    
                    return forms;
                }
            """)
            
            logger.info(f"Extracted {len(forms)} forms")
            
            # 详细日志输出
            for i, form in enumerate(forms):
                logger.debug(f"Form {i}: id='{form.get('id')}', class='{form.get('className')}', action='{form.get('action')}'")
                for j, field in enumerate(form.get('fields', [])):
                    logger.debug(f"  Field {j}: name='{field.get('name')}', type='{field.get('type')}', "
                               f"required={field.get('required')}, aria-required='{field.get('aria-required')}', "
                               f"label='{field.get('label')}', placeholder='{field.get('placeholder')}'")
            
            return forms
            
        except Exception as e:
            logger.error(f"Failed to extract forms: {e}")
            return []
    
    async def check_for_captcha(self) -> bool:
        """
        检查页面是否包含验证码
        
        Returns:
            是否包含验证码
        """
        try:
            has_captcha = await self.page.evaluate("""
                () => {
                    // 检查常见的验证码标识
                    const captchaSelectors = [
                        'iframe[src*="recaptcha"]',
                        'iframe[src*="captcha"]',
                        'div[class*="captcha"]',
                        'div[id*="captcha"]',
                        '.g-recaptcha',
                        '[data-captcha]'
                    ];
                    
                    return captchaSelectors.some(selector => 
                        document.querySelector(selector) !== null
                    );
                }
            """)
            
            if has_captcha:
                logger.warning("Captcha detected on page")
                
            return has_captcha
            
        except Exception as e:
            logger.error(f"Failed to check for captcha: {e}")
            return False
    
    async def _remove_unwanted_elements(self):
        """移除页面中不需要的元素"""
        try:
            await self.page.evaluate("""
                () => {
                    // 移除干扰元素
                    const unwantedSelectors = [
                        'script',
                        'style',
                        'nav',
                        'header',
                        'footer',
                        '.cookie-banner',
                        '.privacy-notice',
                        '.advertisement',
                        '.social-share',
                        '[class*="popup"]',
                        '[class*="modal"]'
                    ];
                    
                    unwantedSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => el.remove());
                    });
                }
            """)
        except Exception as e:
            logger.debug(f"Failed to remove unwanted elements: {e}")
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本内容
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        import re
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # 移除连续的换行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
