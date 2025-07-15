"""
智能字段处理器 - 专门优化下拉框、单选框等复杂字段的处理
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
import re
from difflib import SequenceMatcher
from playwright.async_api import Page, ElementHandle
import asyncio

logger = logging.getLogger(__name__)


class SmartFieldHandler:
    """智能字段处理器，专门处理复杂的表单字段"""
    
    def __init__(self, page: Page):
        """
        初始化智能字段处理器
        
        Args:
            page: Playwright页面对象
        """
        self.page = page
        self.field_strategies = {
            'select': self._handle_select_field,
            'radio': self._handle_radio_field,
            'checkbox': self._handle_checkbox_field,
            'file': self._handle_file_field,
            'text': self._handle_text_field,
            'textarea': self._handle_textarea_field
        }
        
    async def analyze_and_fill_field(self, field_info: Dict[str, Any], 
                                   value_to_fill: Any,
                                   personal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析并填充单个字段
        
        Args:
            field_info: 字段信息
            value_to_fill: 要填充的值
            personal_data: 完整的个人数据
            
        Returns:
            填充结果
        """
        field_type = field_info.get('type', 'text')
        field_name = field_info.get('name', '')
        field_label = field_info.get('label', '')
        selector = field_info.get('selector')
        
        result = {
            'success': False,
            'field_name': field_name,
            'field_type': field_type,
            'attempted_value': value_to_fill,
            'actual_value': None,
            'error': None,
            'confidence': 0.0
        }
        
        try:
            # 根据字段类型选择处理策略
            handler = self.field_strategies.get(field_type, self._handle_text_field)
            
            # 执行字段填充
            success, actual_value, confidence = await handler(
                selector, field_info, value_to_fill, personal_data
            )
            
            result['success'] = success
            result['actual_value'] = actual_value
            result['confidence'] = confidence
            
            if success:
                logger.info(f"✓ 成功填充字段 {field_name} ({field_type}): {actual_value} (置信度: {confidence:.2f})")
            else:
                logger.warning(f"✗ 填充字段失败 {field_name} ({field_type})")
                
        except Exception as e:
            logger.error(f"处理字段 {field_name} 时出错: {e}")
            result['error'] = str(e)
            
        return result
    
    async def _handle_select_field(self, selector: str, field_info: Dict[str, Any], 
                                 value: Any, personal_data: Dict[str, Any]) -> Tuple[bool, Any, float]:
        """
        处理下拉框字段 - 使用智能匹配
        
        Returns:
            (成功, 实际填充值, 置信度)
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if not element:
                return False, None, 0.0
            
            # 获取所有选项
            options = await self._get_select_options(element)
            
            if not options:
                logger.warning(f"下拉框没有选项: {selector}")
                return False, None, 0.0
            
            # 智能匹配选项
            best_match = await self._find_best_option_match(
                value, options, field_info, personal_data
            )
            
            if best_match:
                # 尝试通过值选择
                try:
                    await element.select_option(value=best_match['value'])
                    logger.debug(f"通过值选择: {best_match['value']}")
                    return True, best_match['text'], best_match['confidence']
                except:
                    # 如果失败，尝试通过标签选择
                    try:
                        await element.select_option(label=best_match['text'])
                        logger.debug(f"通过标签选择: {best_match['text']}")
                        return True, best_match['text'], best_match['confidence']
                    except:
                        # 如果还是失败，尝试通过索引选择
                        try:
                            await element.select_option(index=best_match['index'])
                            logger.debug(f"通过索引选择: {best_match['index']}")
                            return True, best_match['text'], best_match['confidence']
                        except Exception as e:
                            logger.error(f"所有选择方法都失败了: {e}")
                            return False, None, 0.0
            else:
                logger.warning(f"找不到匹配的选项，期望值: {value}")
                return False, None, 0.0
                
        except Exception as e:
            logger.error(f"处理下拉框失败: {e}")
            return False, None, 0.0
    
    async def _get_select_options(self, element: ElementHandle) -> List[Dict[str, Any]]:
        """获取下拉框的所有选项"""
        options = await element.query_selector_all('option')
        option_list = []
        
        for i, option in enumerate(options):
            value = await option.get_attribute('value') or ''
            text = await option.text_content() or ''
            text = text.strip()
            
            # 跳过空选项或提示选项
            if not value and not text:
                continue
            if text.lower() in ['select', 'choose', 'please select', '--select--', 'select one']:
                continue
                
            option_list.append({
                'index': i,
                'value': value,
                'text': text,
                'text_lower': text.lower(),
                'value_lower': value.lower()
            })
            
        return option_list
    
    async def _find_best_option_match(self, target_value: str, options: List[Dict[str, Any]], 
                                    field_info: Dict[str, Any], 
                                    personal_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        智能查找最佳匹配的选项
        
        使用多种策略：
        1. 精确匹配
        2. 大小写不敏感匹配
        3. 包含匹配
        4. 缩写匹配
        5. 模糊匹配
        6. 语义匹配（基于字段类型）
        """
        if not target_value:
            return None
            
        target_lower = str(target_value).lower().strip()
        field_name = field_info.get('name', '').lower()
        field_label = field_info.get('label', '').lower()
        
        # 策略1: 精确匹配
        for option in options:
            if option['value'] == target_value or option['text'] == target_value:
                option['confidence'] = 1.0
                return option
        
        # 策略2: 大小写不敏感匹配
        for option in options:
            if option['value_lower'] == target_lower or option['text_lower'] == target_lower:
                option['confidence'] = 0.95
                return option
        
        # 策略3: 特殊字段的映射规则
        if 'country' in field_name or 'country' in field_label:
            country_match = self._match_country(target_value, options)
            if country_match:
                return country_match
                
        elif 'state' in field_name or 'state' in field_label or 'province' in field_name:
            state_match = self._match_state(target_value, options)
            if state_match:
                return state_match
                
        elif 'year' in field_name or 'graduation' in field_name:
            year_match = self._match_year(target_value, options)
            if year_match:
                return year_match
                
        elif 'degree' in field_name or 'education' in field_name:
            degree_match = self._match_degree(target_value, options)
            if degree_match:
                return degree_match
        
        # 策略4: 包含匹配
        for option in options:
            if target_lower in option['text_lower'] or option['text_lower'] in target_lower:
                option['confidence'] = 0.8
                return option
            if target_lower in option['value_lower'] or option['value_lower'] in target_lower:
                option['confidence'] = 0.75
                return option
        
        # 策略5: 缩写匹配
        target_abbr = self._get_abbreviation(target_value)
        for option in options:
            option_abbr = self._get_abbreviation(option['text'])
            if target_abbr == option_abbr:
                option['confidence'] = 0.7
                return option
        
        # 策略6: 模糊匹配（使用相似度）
        best_similarity = 0
        best_option = None
        
        for option in options:
            # 计算文本相似度
            text_similarity = SequenceMatcher(None, target_lower, option['text_lower']).ratio()
            value_similarity = SequenceMatcher(None, target_lower, option['value_lower']).ratio()
            
            similarity = max(text_similarity, value_similarity)
            
            if similarity > best_similarity and similarity > 0.6:  # 相似度阈值
                best_similarity = similarity
                best_option = option
        
        if best_option:
            best_option['confidence'] = best_similarity * 0.8  # 降低模糊匹配的置信度
            return best_option
        
        # 策略7: 默认选择第一个有效选项（非空）
        for option in options:
            if option['value'] and option['text']:
                option['confidence'] = 0.3
                logger.warning(f"无法找到匹配，使用默认选项: {option['text']}")
                return option
        
        return None
    
    def _match_country(self, target: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """匹配国家"""
        country_mappings = {
            'united states': ['usa', 'us', 'united states', 'united states of america', 'america'],
            'usa': ['usa', 'us', 'united states', 'united states of america'],
            'us': ['usa', 'us', 'united states', 'united states of america'],
            'uk': ['uk', 'united kingdom', 'great britain', 'gb', 'britain'],
            'china': ['china', 'cn', 'prc', "people's republic of china"],
            'canada': ['canada', 'ca', 'can'],
        }
        
        target_lower = target.lower()
        for option in options:
            # 检查直接匹配
            if target_lower in country_mappings:
                for variant in country_mappings[target_lower]:
                    if variant in option['text_lower'] or variant in option['value_lower']:
                        option['confidence'] = 0.9
                        return option
            
            # 检查反向匹配
            for country, variants in country_mappings.items():
                if target_lower in variants:
                    if country in option['text_lower'] or any(v in option['text_lower'] for v in variants):
                        option['confidence'] = 0.9
                        return option
        
        return None
    
    def _match_state(self, target: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """匹配州/省份"""
        # 美国州缩写映射
        state_mappings = {
            'ca': 'california',
            'ny': 'new york',
            'tx': 'texas',
            'fl': 'florida',
            'wa': 'washington',
            'ma': 'massachusetts',
            'il': 'illinois',
            'pa': 'pennsylvania',
            # 可以添加更多州...
        }
        
        target_lower = target.lower()
        
        for option in options:
            # 精确匹配缩写
            if len(target) == 2 and option['value_lower'] == target_lower:
                option['confidence'] = 0.95
                return option
            
            # 匹配全名
            if target_lower in state_mappings:
                full_name = state_mappings[target_lower]
                if full_name in option['text_lower']:
                    option['confidence'] = 0.9
                    return option
            
            # 反向匹配：全名到缩写
            for abbr, full_name in state_mappings.items():
                if target_lower == full_name and (abbr in option['value_lower'] or abbr in option['text_lower']):
                    option['confidence'] = 0.9
                    return option
        
        return None
    
    def _match_year(self, target: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """匹配年份"""
        target_str = str(target)
        
        for option in options:
            # 精确匹配年份
            if target_str in option['text'] or target_str in option['value']:
                option['confidence'] = 0.95
                return option
            
            # 匹配包含年份的文本（如 "2023 (expected)"）
            if target_str in option['text']:
                option['confidence'] = 0.9
                return option
        
        return None
    
    def _match_degree(self, target: str, options: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """匹配学位"""
        degree_mappings = {
            "bachelor's": ["bachelor", "bachelors", "bachelor's", "bs", "ba", "b.s.", "b.a."],
            "master's": ["master", "masters", "master's", "ms", "ma", "m.s.", "m.a.", "mba"],
            "phd": ["phd", "ph.d.", "doctor", "doctorate", "doctoral"],
            "associate": ["associate", "associates", "associate's", "aa", "as", "a.a.", "a.s."],
        }
        
        target_lower = target.lower()
        
        for option in options:
            # 直接匹配
            for degree_type, variants in degree_mappings.items():
                if target_lower in variants:
                    for variant in variants:
                        if variant in option['text_lower']:
                            option['confidence'] = 0.9
                            return option
        
        return None
    
    def _get_abbreviation(self, text: str) -> str:
        """获取文本的缩写"""
        words = text.split()
        if len(words) > 1:
            return ''.join(word[0].upper() for word in words if word)
        return text.upper()[:3]  # 单个词取前三个字母
    
    async def _handle_radio_field(self, selector: str, field_info: Dict[str, Any], 
                                value: Any, personal_data: Dict[str, Any]) -> Tuple[bool, Any, float]:
        """处理单选框字段"""
        try:
            field_name = field_info.get('name', '')
            
            # 获取所有相关的单选框
            if field_name:
                radio_selector = f'input[type="radio"][name="{field_name}"]'
            else:
                radio_selector = selector
            
            radios = await self.page.query_selector_all(radio_selector)
            
            if not radios:
                logger.warning(f"找不到单选框: {radio_selector}")
                return False, None, 0.0
            
            # 分析每个单选框选项
            best_match = None
            best_confidence = 0
            
            for radio in radios:
                radio_value = await radio.get_attribute('value') or ''
                radio_id = await radio.get_attribute('id') or ''
                
                # 获取关联的标签文本
                label_text = ''
                if radio_id:
                    label = await self.page.query_selector(f'label[for="{radio_id}"]')
                    if label:
                        label_text = await label.text_content() or ''
                
                # 尝试获取父级标签
                if not label_text:
                    parent_label = await radio.evaluate("el => el.closest('label')?.textContent || ''")
                    label_text = parent_label.strip()
                
                # 智能匹配
                confidence = self._calculate_radio_match_confidence(
                    value, radio_value, label_text, field_info
                )
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'element': radio,
                        'value': radio_value,
                        'label': label_text,
                        'confidence': confidence
                    }
            
            # 选择最佳匹配
            if best_match and best_confidence > 0.5:
                await best_match['element'].click()
                logger.debug(f"选中单选框: {best_match['label']} (置信度: {best_confidence:.2f})")
                return True, best_match['label'] or best_match['value'], best_confidence
            
            logger.warning(f"找不到匹配的单选框选项，期望值: {value}")
            return False, None, 0.0
            
        except Exception as e:
            logger.error(f"处理单选框失败: {e}")
            return False, None, 0.0
    
    def _calculate_radio_match_confidence(self, target_value: str, radio_value: str, 
                                        label_text: str, field_info: Dict[str, Any]) -> float:
        """计算单选框匹配的置信度"""
        target_lower = str(target_value).lower().strip()
        radio_value_lower = radio_value.lower().strip()
        label_lower = label_text.lower().strip()
        field_name = field_info.get('name', '').lower()
        
        # 工作授权相关的特殊处理
        if 'authorization' in field_name or 'authorized' in field_name or 'visa' in field_name:
            if target_lower in ['yes', 'true', '1']:
                if 'yes' in radio_value_lower or 'yes' in label_lower or 'authorized' in label_lower:
                    return 0.95
            elif target_lower in ['no', 'false', '0']:
                if 'no' in radio_value_lower or 'no' in label_lower or 'not authorized' in label_lower:
                    return 0.95
        
        # 性别相关
        if 'gender' in field_name:
            gender_map = {
                'male': ['male', 'm', 'man'],
                'female': ['female', 'f', 'woman'],
                'other': ['other', 'non-binary', 'prefer not to say']
            }
            for gender, variants in gender_map.items():
                if target_lower in variants:
                    if any(v in radio_value_lower or v in label_lower for v in variants):
                        return 0.9
        
        # 精确匹配
        if target_lower == radio_value_lower or target_lower == label_lower:
            return 1.0
        
        # 包含匹配
        if target_lower in radio_value_lower or target_lower in label_lower:
            return 0.8
        if radio_value_lower in target_lower or label_lower in target_lower:
            return 0.7
        
        # 相似度匹配
        value_similarity = SequenceMatcher(None, target_lower, radio_value_lower).ratio()
        label_similarity = SequenceMatcher(None, target_lower, label_lower).ratio()
        
        return max(value_similarity, label_similarity) * 0.8
    
    async def _handle_checkbox_field(self, selector: str, field_info: Dict[str, Any], 
                                   value: Any, personal_data: Dict[str, Any]) -> Tuple[bool, Any, float]:
        """处理复选框字段"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if not element:
                return False, None, 0.0
            
            # 检查是否应该勾选
            should_check = self._should_check_checkbox(value, field_info)
            
            if should_check:
                # 检查当前状态
                is_checked = await element.is_checked()
                if not is_checked:
                    await element.click()
                
                return True, "Checked", 0.9
            else:
                return True, "Not checked", 0.9
                
        except Exception as e:
            logger.error(f"处理复选框失败: {e}")
            return False, None, 0.0
    
    def _should_check_checkbox(self, value: Any, field_info: Dict[str, Any]) -> bool:
        """判断是否应该勾选复选框"""
        if not value:
            return False
        
        value_str = str(value).lower().strip()
        
        # 肯定的值
        positive_values = ['yes', 'true', '1', 'on', 'checked', 'agree', 'accept']
        if value_str in positive_values:
            return True
        
        # 否定的值
        negative_values = ['no', 'false', '0', 'off', 'unchecked', 'disagree', 'decline']
        if value_str in negative_values:
            return False
        
        # 根据字段名判断
        field_name = field_info.get('name', '').lower()
        field_label = field_info.get('label', '').lower()
        
        # 协议/条款类
        if any(keyword in field_name or keyword in field_label 
               for keyword in ['agree', 'accept', 'terms', 'policy', 'consent']):
            return True
        
        # 订阅类（通常不勾选）
        if any(keyword in field_name or keyword in field_label 
               for keyword in ['newsletter', 'marketing', 'email me', 'subscribe']):
            return False
        
        return False
    
    async def _handle_file_field(self, selector: str, field_info: Dict[str, Any], 
                               value: Any, personal_data: Dict[str, Any]) -> Tuple[bool, Any, float]:
        """处理文件上传字段"""
        try:
            from pathlib import Path
            
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if not element:
                return False, None, 0.0
            
            # 确定文件路径
            file_path = None
            field_name = field_info.get('name', '').lower()
            field_label = field_info.get('label', '').lower()
            
            # 如果value直接是路径
            if value and Path(str(value)).exists():
                file_path = Path(str(value))
            # 根据字段类型自动选择文件
            elif 'resume' in field_name or 'resume' in field_label or 'cv' in field_name:
                # 优先使用personal_data中的resume -> file_path
                resume_path = personal_data.get('resume', {}).get('file_path') or personal_data.get('resume_path')
                if resume_path and Path(resume_path).exists():
                    file_path = Path(resume_path)
                    logger.info(f"找到简历文件: {file_path}")
                else:
                    logger.warning(f"简历文件不存在或未配置: {resume_path}")
            elif 'cover' in field_name or 'cover' in field_label:
                cover_letter_path = personal_data.get('cover_letter_path')
                if cover_letter_path and Path(cover_letter_path).exists():
                    file_path = Path(cover_letter_path)
            
            if file_path:
                # 检查元素是否可见
                is_visible = await element.is_visible()
                
                if not is_visible:
                    # 尝试点击触发上传的元素
                    await self._trigger_file_upload(element, field_info)
                
                # 上传文件
                await element.set_input_files(str(file_path))
                logger.info(f"成功上传文件: {file_path.name}")
                return True, file_path.name, 0.95
            else:
                logger.warning(f"找不到要上传的文件")
                return False, None, 0.0
                
        except Exception as e:
            logger.error(f"处理文件上传失败: {e}")
            return False, None, 0.0
    
    async def _trigger_file_upload(self, file_input: ElementHandle, field_info: Dict[str, Any]):
        """触发文件上传（对于隐藏的input）"""
        field_id = field_info.get('id', '')
        
        # 查找可能的触发元素
        triggers = []
        if field_id:
            triggers.append(f'label[for="{field_id}"]')
        
        triggers.extend([
            'button:has-text("Upload")',
            'button:has-text("Choose")',
            'button:has-text("Browse")',
            'div:has-text("Drag and drop")',
            '[class*="upload"]',
            '[class*="file-input"]'
        ])
        
        for trigger_selector in triggers:
            try:
                trigger = await self.page.query_selector(trigger_selector)
                if trigger and await trigger.is_visible():
                    await trigger.click()
                    await self.page.wait_for_timeout(500)
                    return
            except:
                continue
    
    async def _handle_text_field(self, selector: str, field_info: Dict[str, Any], 
                               value: Any, personal_data: Dict[str, Any]) -> Tuple[bool, Any, float]:
        """处理文本字段"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if not element:
                return False, None, 0.0
            
            # 清空并填充
            await element.fill('')
            await element.fill(str(value))
            
            return True, str(value), 0.95
            
        except Exception as e:
            logger.error(f"处理文本字段失败: {e}")
            return False, None, 0.0
    
    async def _handle_textarea_field(self, selector: str, field_info: Dict[str, Any], 
                                   value: Any, personal_data: Dict[str, Any]) -> Tuple[bool, Any, float]:
        """处理文本域字段"""
        return await self._handle_text_field(selector, field_info, value, personal_data)
