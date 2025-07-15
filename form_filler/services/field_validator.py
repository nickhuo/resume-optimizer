"""
字段验证器，监听 change/blur 事件确保填充有效
"""
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import Page, TimeoutError

logger = logging.getLogger(__name__)


class FieldValidator:
    """
    验证器，监听字段事件并验证填充有效性
    """
    
    def __init__(self, page: Page, timeout: int = 5000):
        """
        初始化验证器
        
        Args:
            page: Playwright 页面对象
            timeout: 事件监听超时时间（毫秒）
        """
        self.page = page
        self.timeout = timeout
        self.validation_results = []
    
    async def validate_field(self, selector: str, expected_value: str, field_info: Dict[str, Any]) -> bool:
        """
        验证单个字段的填充
        
        Args:
            selector: 字段选择器
            expected_value: 期望的值
            field_info: 字段信息
            
        Returns:
            bool: 验证是否通过
        """
        try:
            # 监听 change 和 blur 事件
            event_fired = False
            
            def handle_event(event):
                nonlocal event_fired
                event_fired = True
            
            # 添加事件监听器
            await self.page.evaluate("""
                (selector) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        element.addEventListener('change', () => {
                            window.__fieldChanged = true;
                        });
                        element.addEventListener('blur', () => {
                            window.__fieldBlurred = true;
                        });
                    }
                }
            """, selector)
            
            # 触发 blur 事件
            await self.page.evaluate("""
                (selector) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        element.dispatchEvent(new Event('blur', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """, selector)
            
            # 等待事件触发
            await self.page.wait_for_function(
                "window.__fieldChanged || window.__fieldBlurred",
                timeout=self.timeout
            )
            
            # 获取当前值
            current_value = await self.page.evaluate("""
                (selector) => {
                    const element = document.querySelector(selector);
                    if (element) {
                        if (element.type === 'checkbox') {
                            return element.checked ? 'true' : 'false';
                        }
                        return element.value;
                    }
                    return null;
                }
            """, selector)
            
            # 验证值是否正确
            is_valid = current_value == expected_value
            
            # 记录验证结果
            self.validation_results.append({
                'selector': selector,
                'semantic_key': field_info.get('semantic_key'),
                'expected_value': expected_value,
                'actual_value': current_value,
                'is_valid': is_valid,
                'field_info': field_info
            })
            
            if not is_valid:
                logger.warning(f"Validation failed for field {selector}: expected '{expected_value}', got '{current_value}'")
            else:
                logger.info(f"Validation passed for field {selector}")
            
            # 清理事件标记
            await self.page.evaluate("() => { window.__fieldChanged = false; window.__fieldBlurred = false; }")
            
            return is_valid
            
        except TimeoutError:
            logger.error(f"Timeout waiting for events on field {selector}")
            self.validation_results.append({
                'selector': selector,
                'semantic_key': field_info.get('semantic_key'),
                'expected_value': expected_value,
                'actual_value': None,
                'is_valid': False,
                'error': 'Timeout waiting for events',
                'field_info': field_info
            })
            return False
        
        except Exception as e:
            logger.error(f"Error validating field {selector}: {str(e)}")
            self.validation_results.append({
                'selector': selector,
                'semantic_key': field_info.get('semantic_key'),
                'expected_value': expected_value,
                'actual_value': None,
                'is_valid': False,
                'error': str(e),
                'field_info': field_info
            })
            return False
    
    async def validate_all_fields(self, filled_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证所有填充的字段
        
        Args:
            filled_fields: 填充的字段列表，每个包含 selector, value, field_info
            
        Returns:
            Dict[str, Any]: 验证报告
        """
        total_fields = len(filled_fields)
        valid_fields = 0
        failed_fields = []
        
        for field in filled_fields:
            is_valid = await self.validate_field(
                selector=field['selector'],
                expected_value=field['value'],
                field_info=field.get('field_info', {})
            )
            
            if is_valid:
                valid_fields += 1
            else:
                failed_fields.append(field)
        
        validation_report = {
            'total_fields': total_fields,
            'valid_fields': valid_fields,
            'failed_fields': len(failed_fields),
            'validation_rate': valid_fields / total_fields if total_fields > 0 else 0,
            'failed_field_details': failed_fields,
            'all_results': self.validation_results
        }
        
        logger.info(f"Validation complete: {valid_fields}/{total_fields} fields valid ({validation_report['validation_rate']:.2%})")
        
        return validation_report
    
    async def check_form_errors(self) -> List[Dict[str, Any]]:
        """
        检查页面上的表单错误消息
        
        Returns:
            List[Dict[str, Any]]: 错误消息列表
        """
        errors = []
        
        # 查找常见的错误消息元素
        error_selectors = [
            '.error-message',
            '.field-error',
            '.validation-error',
            '[class*="error"]',
            '[role="alert"]',
            '.invalid-feedback'
        ]
        
        for selector in error_selectors:
            error_elements = await self.page.query_selector_all(selector)
            for element in error_elements:
                if await element.is_visible():
                    error_text = await element.text_content()
                    if error_text and error_text.strip():
                        errors.append({
                            'selector': selector,
                            'message': error_text.strip(),
                            'element': element
                        })
        
        if errors:
            logger.warning(f"Found {len(errors)} form errors on the page")
        
        return errors
    
    async def wait_for_validation_complete(self, max_wait: int = 3000) -> bool:
        """
        等待页面验证完成（例如 AJAX 验证）
        
        Args:
            max_wait: 最大等待时间（毫秒）
            
        Returns:
            bool: 是否成功等待
        """
        try:
            # 等待加载指示器消失
            await self.page.wait_for_function(
                """
                () => {
                    // 检查常见的加载指示器
                    const loadingIndicators = document.querySelectorAll(
                        '.loading, .spinner, [class*="loading"], [class*="spinner"]'
                    );
                    
                    // 检查所有指示器是否都不可见
                    return Array.from(loadingIndicators).every(el => {
                        const style = window.getComputedStyle(el);
                        return style.display === 'none' || style.visibility === 'hidden';
                    });
                }
                """,
                timeout=max_wait
            )
            
            # 额外等待一小段时间确保验证完成
            await self.page.wait_for_timeout(500)
            
            return True
            
        except TimeoutError:
            logger.warning("Timeout waiting for validation to complete")
            return False
    
    def get_validation_summary(self) -> str:
        """
        获取验证摘要
        
        Returns:
            str: 验证摘要文本
        """
        if not self.validation_results:
            return "No validation results available"
        
        valid_count = sum(1 for r in self.validation_results if r.get('is_valid'))
        total_count = len(self.validation_results)
        
        summary = f"Validation Summary:\n"
        summary += f"Total fields: {total_count}\n"
        summary += f"Valid fields: {valid_count}\n"
        summary += f"Failed fields: {total_count - valid_count}\n"
        summary += f"Success rate: {valid_count/total_count:.2%}\n"
        
        if total_count > valid_count:
            summary += "\nFailed fields:\n"
            for result in self.validation_results:
                if not result.get('is_valid'):
                    summary += f"  - {result.get('semantic_key', result.get('selector'))}: "
                    summary += f"expected '{result.get('expected_value')}', "
                    summary += f"got '{result.get('actual_value')}'\n"
                    if result.get('error'):
                        summary += f"    Error: {result.get('error')}\n"
        
        return summary
