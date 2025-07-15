"""
动作执行器 - 基于Playwright的确定性动作执行层
处理各种复杂控件：文本、单/多选、下拉、日期、文件上传、富文本等
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from playwright.async_api import Page, ElementHandle
from difflib import SequenceMatcher
import asyncio
import re

logger = logging.getLogger(__name__)


class ActionExecutor:
    """动作执行器 - 确保每个动作的可靠执行"""
    
    def __init__(self, page: Page):
        """
        初始化动作执行器
        
        Args:
            page: Playwright页面对象
        """
        self.page = page
        self.max_retries = 3
        
    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个动作
        
        Args:
            action: 动作描述，包含：
                - selector: CSS选择器
                - control: 控件类型（text/select/radio/checkbox/file等）
                - value: 要填充的值
                - options: 可选的额外参数
                
        Returns:
            执行结果
        """
        result = {
            'success': False,
            'selector': action['selector'],
            'control': action['control'],
            'expected_value': action['value'],
            'actual_value': None,
            'error': None,
            'retries': 0
        }
        
        try:
            control_type = action['control'].lower()
            
            # 根据控件类型选择执行方法，每次输入后模拟延迟
            if control_type in ['text', 'email', 'tel', 'url', 'number']:
                await asyncio.sleep(0.5)  # 模拟自然输入延迟
                return await self._fill_text(action, result)
            elif control_type == 'select':
                return await self._select_option(action, result)
            elif control_type == 'radio':
                return await self._click_radio(action, result)
            elif control_type == 'checkbox':
                return await self._click_checkbox(action, result)
            elif control_type == 'file':
                return await self._upload_file(action, result)
            elif control_type in ['date', 'datetime-local']:
                return await self._fill_date(action, result)
            elif control_type == 'textarea':
                return await self._fill_textarea(action, result)
            elif control_type == 'custom-dropdown':
                return await self._handle_custom_dropdown(action, result)
            else:
                result['error'] = f"未知的控件类型: {control_type}"
                return result
                
        except Exception as e:
            logger.error(f"执行动作失败: {e}")
            result['error'] = str(e)
            return result
    
    async def _fill_text(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """填充文本字段"""
        selector = action['selector']
        value = str(action['value'])
        
        for retry in range(self.max_retries):
            try:
                # 首先尝试直接找到元素（不等待可见性）
                element = await self.page.query_selector(selector)
                if not element:
                    # 如果直接找不到，再等待元素出现
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if not element:
                        raise Exception(f"找不到元素: {selector}")
                
                # 检查元素是否隐藏
                is_hidden = await element.is_hidden()
                element_type = await element.get_attribute('type')
                
                if is_hidden and element_type == 'hidden':
                    # 对于隐藏字段，直接设置值并触发事件
                    await self._fill_hidden_field(element, value)
                    result['success'] = True
                    result['actual_value'] = value
                    logger.info(f"成功填充隐藏字段: {selector} = {value}")
                    return result
                else:
                    # 对于可见字段，使用原有逻辑
                    await element.scroll_into_view_if_needed()
                    
                    # 清空并填充
                    await element.fill('')
                    await element.fill(value)
                    
                    # 触发blur事件（重要：很多框架依赖blur事件）
                    await element.evaluate('el => el.blur()')
                    await self.page.keyboard.press('Tab')
                    
                    # 等待一下让框架处理
                    await self.page.wait_for_timeout(100)
                    
                    # 读回验证
                    actual_value = await element.evaluate('el => el.value')
                    
                    if actual_value == value:
                        result['success'] = True
                        result['actual_value'] = actual_value
                        return result
                    else:
                        logger.warning(f"值不匹配，期望: {value}, 实际: {actual_value}")
                        result['retries'] = retry + 1
                    
            except Exception as e:
                logger.error(f"填充文本失败 (尝试 {retry + 1}/{self.max_retries}): {e}")
                result['error'] = str(e)
                await self.page.wait_for_timeout(500)
        
        return result
    
    async def _select_option(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理下拉选择框"""
        selector = action['selector']
        target_value = str(action['value'])
        
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if not element:
                raise Exception(f"找不到元素: {selector}")
            
            # 检查是否是原生select
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            
            if tag_name == 'select':
                # 原生select元素
                # 先获取所有选项
                options = await element.evaluate("""
                    el => Array.from(el.options).map(opt => ({
                        value: opt.value,
                        text: opt.textContent.trim(),
                        index: opt.index
                    }))
                """)
                
                # 使用模糊匹配找到最佳选项
                best_match = self._fuzzy_match_option(target_value, options)
                
                if best_match:
                    # 尝试多种方式选择
                    try:
                        await element.select_option(value=best_match['value'])
                    except:
                        try:
                            await element.select_option(label=best_match['text'])
                        except:
                            await element.select_option(index=best_match['index'])
                    
                    # 验证
                    actual_value = await element.evaluate('el => el.options[el.selectedIndex].text')
                    result['success'] = True
                    result['actual_value'] = actual_value
                else:
                    result['error'] = f"找不到匹配的选项: {target_value}"
            else:
                # 自定义下拉框，转为custom-dropdown处理
                action['control'] = 'custom-dropdown'
                return await self._handle_custom_dropdown(action, result)
                
        except Exception as e:
            logger.error(f"选择下拉框失败: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _handle_custom_dropdown(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理自定义下拉框（React/Vue组件）"""
        selector = action['selector']
        target_value = str(action['value'])
        
        try:
            # 点击触发器打开下拉框
            trigger = await self.page.wait_for_selector(selector, timeout=5000)
            if not trigger:
                raise Exception(f"找不到元素: {selector}")
            
            await trigger.scroll_into_view_if_needed()
            await trigger.click()
            await self.page.wait_for_timeout(300)  # 等待动画
            
            # 查找选项
            option_selectors = [
                f'[role="option"]:has-text("{target_value}")',
                f'li:has-text("{target_value}")',
                f'[class*="option"]:has-text("{target_value}")',
                f'[class*="menu"] *:has-text("{target_value}")'
            ]
            
            option_found = False
            for option_selector in option_selectors:
                try:
                    option = await self.page.wait_for_selector(option_selector, timeout=1000)
                    if option:
                        await option.click()
                        option_found = True
                        break
                except:
                    continue
            
            if not option_found:
                # 尝试模糊匹配
                all_options = await self._get_visible_options()
                best_match = self._fuzzy_match_text(target_value, all_options)
                
                if best_match:
                    await self.page.click(f'text="{best_match}"')
                    option_found = True
            
            if option_found:
                await self.page.wait_for_timeout(200)
                # 读回实际值
                actual_value = await trigger.evaluate('el => el.textContent || el.value')
                result['success'] = True
                result['actual_value'] = actual_value.strip()
            else:
                # 关闭下拉框
                await self.page.keyboard.press('Escape')
                result['error'] = f"找不到匹配的选项: {target_value}"
                
        except Exception as e:
            logger.error(f"处理自定义下拉框失败: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _click_radio(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理单选框"""
        base_selector = action['selector']
        target_value = str(action['value'])
        
        try:
            # 获取name属性
            first_radio = await self.page.query_selector(base_selector)
            if not first_radio:
                raise Exception(f"找不到元素: {base_selector}")
                
            name = await first_radio.get_attribute('name')
            if not name:
                raise Exception("单选框没有name属性")
            
            # 获取所有同名的单选框
            radios = await self.page.query_selector_all(f'input[type="radio"][name="{name}"]')
            
            # 查找匹配的选项
            for radio in radios:
                # 获取value
                value = await radio.get_attribute('value') or ''
                
                # 获取关联的标签文本
                radio_id = await radio.get_attribute('id')
                label_text = ''
                if radio_id:
                    label = await self.page.query_selector(f'label[for="{radio_id}"]')
                    if label:
                        label_text = await label.text_content()
                
                # 如果没有找到label，尝试父级label
                if not label_text:
                    label_text = await radio.evaluate("""
                        el => {
                            const label = el.closest('label');
                            return label ? label.textContent.trim() : '';
                        }
                    """)
                
                # 匹配逻辑
                if self._match_radio_value(target_value, value, label_text):
                    await radio.click()
                    # 验证
                    is_checked = await radio.is_checked()
                    if is_checked:
                        result['success'] = True
                        result['actual_value'] = value or label_text
                        return result
            
            result['error'] = f"找不到匹配的单选框选项: {target_value}"
            
        except Exception as e:
            logger.error(f"处理单选框失败: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _click_checkbox(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理复选框"""
        selector = action['selector']
        should_check = self._parse_boolean_value(action['value'])
        
        try:
            checkbox = await self.page.wait_for_selector(selector, timeout=5000)
            if not checkbox:
                raise Exception(f"找不到元素: {selector}")
            
            await checkbox.scroll_into_view_if_needed()
            
            # 获取当前状态
            is_checked = await checkbox.is_checked()
            
            # 根据需要点击
            if should_check and not is_checked:
                await checkbox.click()
            elif not should_check and is_checked:
                await checkbox.click()
            
            # 验证
            final_state = await checkbox.is_checked()
            if final_state == should_check:
                result['success'] = True
                result['actual_value'] = final_state
            else:
                result['error'] = f"复选框状态不正确，期望: {should_check}, 实际: {final_state}"
                
        except Exception as e:
            logger.error(f"处理复选框失败: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _upload_file(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理文件上传"""
        selector = action['selector']
        file_path = action['value']
        
        try:
            # 查找文件输入框（可能是隐藏的）
            file_input = await self.page.query_selector(selector)
            
            # 如果直接找不到，尝试其他方法
            if not file_input:
                # 尝试点击上传按钮触发
                upload_triggers = [
                    'button:has-text("Upload")',
                    'button:has-text("Choose")',
                    'label:has-text("Upload")',
                    '[class*="upload"]'
                ]
                
                for trigger_selector in upload_triggers:
                    trigger = await self.page.query_selector(trigger_selector)
                    if trigger:
                        # 查找关联的file input
                        file_input = await self.page.query_selector('input[type="file"]')
                        break
            
            if not file_input:
                raise Exception("找不到文件输入框")
            
            # 设置文件
            await file_input.set_input_files(file_path)
            
            # 等待上传处理
            await self.page.wait_for_timeout(1000)
            
            # 验证（通过检查是否有文件名显示）
            # 这部分依赖于具体的UI实现
            result['success'] = True
            result['actual_value'] = file_path.split('/')[-1]  # 文件名
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _fill_date(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """处理日期输入"""
        selector = action['selector']
        date_value = action['value']
        
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if not element:
                raise Exception(f"找不到元素: {selector}")
            
            await element.scroll_into_view_if_needed()
            
            # 清空并填充
            await element.fill('')
            await element.fill(date_value)
            
            # 触发change事件
            await element.evaluate('el => el.dispatchEvent(new Event("change", { bubbles: true }))')
            
            # 验证
            actual_value = await element.evaluate('el => el.value')
            if actual_value:
                result['success'] = True
                result['actual_value'] = actual_value
            else:
                result['error'] = "日期填充失败"
                
        except Exception as e:
            logger.error(f"填充日期失败: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _fill_textarea(self, action: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """填充文本域"""
        # 与填充文本类似，但可能需要处理更长的内容
        return await self._fill_text(action, result)
    
    def _fuzzy_match_option(self, target: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """模糊匹配选项"""
        target_lower = target.lower().strip()
        best_match = None
        best_score = 0
        
        for option in options:
            # 检查value和text
            for field in ['value', 'text']:
                if field in option:
                    option_text = str(option[field]).lower().strip()
                    
                    # 精确匹配
                    if option_text == target_lower:
                        return option
                    
                    # 包含匹配
                    if target_lower in option_text or option_text in target_lower:
                        score = 0.8
                    else:
                        # 相似度匹配
                        score = SequenceMatcher(None, target_lower, option_text).ratio()
                    
                    if score > best_score:
                        best_score = score
                        best_match = option
        
        # 如果相似度超过阈值，返回最佳匹配
        if best_score > 0.6:
            return best_match
        
        return None
    
    def _fuzzy_match_text(self, target: str, texts: List[str]) -> Optional[str]:
        """模糊匹配文本列表"""
        target_lower = target.lower().strip()
        best_match = None
        best_score = 0
        
        for text in texts:
            text_lower = text.lower().strip()
            
            # 精确匹配
            if text_lower == target_lower:
                return text
            
            # 相似度匹配
            score = SequenceMatcher(None, target_lower, text_lower).ratio()
            if score > best_score:
                best_score = score
                best_match = text
        
        if best_score > 0.6:
            return best_match
        
        return None
    
    async def _get_visible_options(self) -> List[str]:
        """获取当前可见的选项"""
        try:
            options = await self.page.evaluate("""
                () => {
                    const selectors = ['[role="option"]', 'li', '[class*="option"]', '[class*="item"]'];
                    const texts = new Set();
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (el.offsetParent !== null) {  // 可见
                                const text = el.textContent.trim();
                                if (text) texts.add(text);
                            }
                        }
                    }
                    
                    return Array.from(texts);
                }
            """)
            return options
        except:
            return []
    
    def _match_radio_value(self, target: str, value: str, label: str) -> bool:
        """匹配单选框的值"""
        target_lower = target.lower().strip()
        value_lower = value.lower().strip()
        label_lower = label.lower().strip()
        
        # 直接匹配
        if target_lower == value_lower or target_lower == label_lower:
            return True
        
        # 特殊映射（Yes/No等）
        mappings = {
            'yes': ['yes', 'y', 'true', '1', 'authorized'],
            'no': ['no', 'n', 'false', '0', 'not authorized'],
            'male': ['male', 'm', 'man'],
            'female': ['female', 'f', 'woman']
        }
        
        for key, values in mappings.items():
            if target_lower in values:
                if value_lower in values or any(v in label_lower for v in values):
                    return True
        
        # 包含匹配
        if target_lower in label_lower or label_lower in target_lower:
            return True
        
        return False
    
    def _parse_boolean_value(self, value: Any) -> bool:
        """解析布尔值"""
        if isinstance(value, bool):
            return value
        
        value_str = str(value).lower().strip()
        return value_str in ['yes', 'true', '1', 'on', 'checked']
