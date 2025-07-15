"""
DOM快照生成器 - 生成轻量级的结构化DOM数据供LLM推理
基于Greenhouse、Workday、Lever等ATS系统的最佳实践
"""
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import Page, ElementHandle
import json

logger = logging.getLogger(__name__)


class DOMSnapshot:
    """DOM快照生成器"""
    
    def __init__(self, page: Page):
        """
        初始化DOM快照生成器
        
        Args:
            page: Playwright页面对象
        """
        self.page = page
        
    async def generate_snapshot(self, context_window_size: int = 50) -> List[Dict[str, Any]]:
        """
        生成轻量级DOM快照
        
        Args:
            context_window_size: 每个逻辑组的最大元素数
            
        Returns:
            结构化的DOM元素列表
        """
        try:
            # 使用JavaScript在浏览器中提取所有可交互元素
            elements_data = await self.page.evaluate("""
                () => {
                    const interactiveSelectors = [
                        'input', 'select', 'textarea', 'button',
                        '[role="combobox"]', '[role="listbox"]', '[role="radio"]', '[role="checkbox"]',
                        '[contenteditable="true"]', 'label'
                    ];
                    
                    const elements = [];
                    const processedIds = new Set();
                    
                    // 辅助函数：获取元素的文本内容
                    function getElementText(el) {
                        // 对于label，获取其文本但排除子元素的文本
                        if (el.tagName.toLowerCase() === 'label') {
                            return Array.from(el.childNodes)
                                .filter(node => node.nodeType === Node.TEXT_NODE)
                                .map(node => node.textContent.trim())
                                .join(' ');
                        }
                        return el.textContent ? el.textContent.trim().substring(0, 100) : '';
                    }
                    
                    // 辅助函数：获取select的选项
                    function getSelectOptions(selectEl) {
                        return Array.from(selectEl.options).map(opt => ({
                            value: opt.value,
                            text: opt.textContent.trim()
                        }));
                    }
                    
                    // 辅助函数：查找关联的label
                    function findAssociatedLabel(el) {
                        // 方法1: 通过for属性
                        if (el.id) {
                            const label = document.querySelector(`label[for="${el.id}"]`);
                            if (label) return getElementText(label);
                        }
                        
                        // 方法2: 父级是label
                        const parentLabel = el.closest('label');
                        if (parentLabel) return getElementText(parentLabel);
                        
                        // 方法3: 查找最近的前置label
                        let sibling = el.previousElementSibling;
                        while (sibling) {
                            if (sibling.tagName.toLowerCase() === 'label') {
                                return getElementText(sibling);
                            }
                            sibling = sibling.previousElementSibling;
                        }
                        
                        return '';
                    }
                    
                    // 辅助函数：获取元素的逻辑组
                    function getLogicalGroup(el) {
                        // 查找包含fieldset, form-group, 或其他逻辑分组
                        const groupSelectors = ['fieldset', '[role="group"]', '.form-group', '.field-group', '[class*="group"]'];
                        for (const selector of groupSelectors) {
                            const group = el.closest(selector);
                            if (group) {
                                return group.id || group.className || 'unnamed-group';
                            }
                        }
                        return 'default';
                    }
                    
                    // 辅助函数：检查元素是否在Shadow DOM中
                    function isInShadowDOM(el) {
                        while (el && el !== document) {
                            if (el.parentNode && el.parentNode.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                                return true;
                            }
                            el = el.parentNode || el.host;
                        }
                        return false;
                    }
                    
                    // 处理所有交互元素
                    for (const selector of interactiveSelectors) {
                        const els = document.querySelectorAll(selector);
                        
                        for (const el of els) {
                            // 跳过已处理的元素
                            const uniqueId = el.id || el.name || `${el.tagName}_${elements.length}`;
                            if (processedIds.has(uniqueId)) continue;
                            processedIds.add(uniqueId);
                            
                            // 跳过不可见元素（但保留file input，它们通常是隐藏的）
                            if (el.type !== 'file' && el.type !== 'hidden') {
                                const style = window.getComputedStyle(el);
                                if (style.display === 'none' || style.visibility === 'hidden') continue;
                            }
                            
                            const elementData = {
                                tag: el.tagName.toLowerCase(),
                                id: el.id || '',
                                name: el.name || '',
                                type: el.type || el.tagName.toLowerCase(),
                                className: el.className || '',
                                // ARIA属性
                                ariaLabel: el.getAttribute('aria-label') || '',
                                ariaLabelledBy: el.getAttribute('aria-labelledby') || '',
                                ariaDescribedBy: el.getAttribute('aria-describedby') || '',
                                role: el.getAttribute('role') || '',
                                // 数据属性
                                dataTestId: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || '',
                                dataQa: el.getAttribute('data-qa') || '',
                                // 基本属性
                                placeholder: el.placeholder || '',
                                value: el.value || '',
                                checked: el.checked || false,
                                required: el.required || false,
                                disabled: el.disabled || false,
                                readOnly: el.readOnly || false,
                                // 位置和可见性
                                visible: el.offsetParent !== null || el.type === 'file',
                                inShadowDOM: isInShadowDOM(el),
                                // 文本内容
                                innerText: getElementText(el),
                                label: findAssociatedLabel(el),
                                // 逻辑分组
                                logicalGroup: getLogicalGroup(el),
                                // 位置信息（用于排序）
                                rect: el.getBoundingClientRect()
                            };
                            
                            // 特殊处理：select元素的选项
                            if (el.tagName.toLowerCase() === 'select') {
                                elementData.options = getSelectOptions(el);
                            }
                            
                            // 特殊处理：radio/checkbox的值
                            if (el.type === 'radio' || el.type === 'checkbox') {
                                elementData.value = el.value || 'on';
                            }
                            
                            // 特殊处理：查找自定义下拉框的选项
                            if (el.getAttribute('role') === 'combobox' || el.getAttribute('aria-haspopup') === 'listbox') {
                                // 标记为自定义下拉框，需要特殊处理
                                elementData.isCustomDropdown = true;
                            }
                            
                            elements.push(elementData);
                        }
                    }
                    
                    // 按照页面位置排序（从上到下，从左到右）
                    elements.sort((a, b) => {
                        if (Math.abs(a.rect.top - b.rect.top) > 10) {
                            return a.rect.top - b.rect.top;
                        }
                        return a.rect.left - b.rect.left;
                    });
                    
                    // 移除rect信息（不需要传给LLM）
                    elements.forEach(el => delete el.rect);
                    
                    return elements;
                }
            """)
            
            # 按逻辑组分组
            grouped_elements = self._group_elements_by_logic(elements_data, context_window_size)
            
            logger.info(f"生成DOM快照：{len(elements_data)}个元素，{len(grouped_elements)}个逻辑组")
            
            return grouped_elements
            
        except Exception as e:
            logger.error(f"生成DOM快照失败: {e}")
            return []
    
    def _group_elements_by_logic(self, elements: List[Dict[str, Any]], 
                                 max_group_size: int = 50) -> List[Dict[str, Any]]:
        """
        将元素按逻辑组分组，避免单次发送给LLM的内容过多
        
        Args:
            elements: 元素列表
            max_group_size: 每组最大元素数
            
        Returns:
            分组后的元素列表
        """
        groups = {}
        
        # 按logicalGroup分组
        for element in elements:
            group_name = element.get('logicalGroup', 'default')
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(element)
        
        # 如果某个组太大，进一步拆分
        result = []
        for group_name, group_elements in groups.items():
            if len(group_elements) <= max_group_size:
                result.append({
                    'groupName': group_name,
                    'elements': group_elements
                })
            else:
                # 拆分大组
                for i in range(0, len(group_elements), max_group_size):
                    result.append({
                        'groupName': f"{group_name}_part{i//max_group_size + 1}",
                        'elements': group_elements[i:i + max_group_size]
                    })
        
        return result
    
    async def find_custom_dropdown_options(self, trigger_selector: str) -> List[Dict[str, Any]]:
        """
        查找自定义下拉框的选项（需要先点击触发器）
        
        Args:
            trigger_selector: 触发器的选择器
            
        Returns:
            选项列表
        """
        try:
            # 点击触发器
            trigger = await self.page.query_selector(trigger_selector)
            if not trigger:
                return []
                
            await trigger.click()
            await self.page.wait_for_timeout(500)  # 等待动画
            
            # 查找弹出的选项
            options = await self.page.evaluate("""
                () => {
                    const optionSelectors = [
                        '[role="option"]',
                        '[role="listbox"] li',
                        '[class*="option"]',
                        '[class*="menu"] li',
                        '[class*="dropdown"] li'
                    ];
                    
                    const options = [];
                    const processedTexts = new Set();
                    
                    for (const selector of optionSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            const text = el.textContent.trim();
                            if (text && !processedTexts.has(text)) {
                                processedTexts.add(text);
                                options.push({
                                    text: text,
                                    value: el.getAttribute('data-value') || el.getAttribute('value') || text,
                                    selector: selector
                                });
                            }
                        }
                    }
                    
                    return options;
                }
            """)
            
            # 关闭下拉框（按ESC）
            await self.page.keyboard.press('Escape')
            
            return options
            
        except Exception as e:
            logger.error(f"查找自定义下拉框选项失败: {e}")
            return []
    
    async def find_file_input_for_label(self, label_text: str) -> Optional[str]:
        """
        根据标签文本查找关联的文件输入框（可能是隐藏的）
        
        Args:
            label_text: 标签文本（如 "Upload Resume"）
            
        Returns:
            文件输入框的选择器
        """
        try:
            selector = await self.page.evaluate("""
                (labelText) => {
                    // 查找包含该文本的标签
                    const labels = Array.from(document.querySelectorAll('label, [class*="label"], [class*="upload"]'));
                    const targetLabel = labels.find(label => 
                        label.textContent.toLowerCase().includes(labelText.toLowerCase())
                    );
                    
                    if (!targetLabel) return null;
                    
                    // 方法1：通过for属性找到关联的input
                    const forAttr = targetLabel.getAttribute('for');
                    if (forAttr) {
                        const input = document.querySelector(`#${forAttr}`);
                        if (input && input.type === 'file') {
                            return `#${forAttr}`;
                        }
                    }
                    
                    // 方法2：在label内部查找input
                    const innerInput = targetLabel.querySelector('input[type="file"]');
                    if (innerInput) {
                        return innerInput.id ? `#${innerInput.id}` : 'label:has-text("' + labelText + '") input[type="file"]';
                    }
                    
                    // 方法3：在附近查找input[type="file"]
                    const parent = targetLabel.closest('div, section, form');
                    if (parent) {
                        const nearbyInput = parent.querySelector('input[type="file"]');
                        if (nearbyInput) {
                            return nearbyInput.id ? `#${nearbyInput.id}` : 'input[type="file"]';
                        }
                    }
                    
                    return null;
                }
            """, label_text)
            
            return selector
            
        except Exception as e:
            logger.error(f"查找文件输入框失败: {e}")
            return None
