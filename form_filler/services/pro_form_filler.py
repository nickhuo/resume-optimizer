"""
专业版智能表单填充器
基于Greenhouse、Workday、Lever等ATS系统的最佳实践
核心原则：分离"字段理解"与"动作执行"，先"看"后"做"再"验"
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
import json
from pathlib import Path

from .gpt_service import GPTService
from .dom_snapshot import DOMSnapshot
from .action_executor import ActionExecutor
from .enhanced_data_manager import EnhancedDataManager
from .field_learning_system import FieldLearningSystem

logger = logging.getLogger(__name__)


class ProFormFiller:
    """专业版表单填充器 - 结合LLM语义理解和确定性执行"""
    
    def __init__(self, gpt_service: GPTService = None):
        """
        初始化表单填充器
        
        Args:
            gpt_service: GPT服务实例
        """
        self.gpt_service = gpt_service or GPTService()
        self.data_manager = EnhancedDataManager()
        self.learning_system = FieldLearningSystem(self.gpt_service)
        
    async def fill_form(self, page, personal_data: Dict[str, Any] = None,
                       resume_data: Dict[str, Any] = None,
                       url: str = None) -> Dict[str, Any]:
        """
        填写表单的主流程
        
        Args:
            page: Playwright页面对象
            personal_data: 个人数据
            resume_data: 简历数据
            
        Returns:
            填写结果
        """
        result = {
            'success': False,
            'filled_fields': {},
            'errors': [],
            'stats': {
                'total_fields': 0,
                'filled_fields': 0,
                'failed_fields': 0,
                'field_types': {}
            }
        }
        
        try:
            # 检测平台类型
            platform = None
            if url:
                platform = self.learning_system.detect_platform(url)
                logger.info(f"检测到平台: {platform or 'unknown'}")
            
            # 1. 加载数据并生成DOM快照
            logger.info("步骤1: 加载数据并生成DOM快照")
            personal_data = self.data_manager.personal_data
            resume_data = self.data_manager.resume_data
            dom_snapshot = DOMSnapshot(page)
            element_groups = await dom_snapshot.generate_snapshot()
            
            if not element_groups:
                result['errors'].append("无法生成DOM快照")
                return result
            
            # 2. 语义分析和字段映射
            logger.info("步骤2: 语义分析和字段映射")
            all_actions = []
            
            context = {
                'url': url,
                'platform': platform
            }
            
            for group in element_groups:
                actions = await self._analyze_element_group(
                    group, personal_data, resume_data, context
                )
                all_actions.extend(actions)
            
            logger.info(f"识别到 {len(all_actions)} 个待填充字段")
            result['stats']['total_fields'] = len(all_actions)
            
            # 3. 执行动作
            logger.info("步骤3: 执行动作")
            action_executor = ActionExecutor(page)
            
            for action in all_actions:
                # 记录字段类型统计
                field_type = action['control']
                if field_type not in result['stats']['field_types']:
                    result['stats']['field_types'][field_type] = {
                        'total': 0, 'success': 0, 'failed': 0
                    }
                result['stats']['field_types'][field_type]['total'] += 1
                
                # 执行动作
                exec_result = await action_executor.execute_action(action)
                
                if exec_result['success']:
                    result['filled_fields'][action['selector']] = {
                        'value': exec_result['actual_value'],
                        'type': action['control'],
                        'expected': action['value']
                    }
                    result['stats']['filled_fields'] += 1
                    result['stats']['field_types'][field_type]['success'] += 1
                    logger.info(f"✓ 成功填充 {action['selector']}: {exec_result['actual_value']}")
                else:
                    result['errors'].append({
                        'selector': action['selector'],
                        'error': exec_result['error'],
                        'type': action['control']
                    })
                    result['stats']['failed_fields'] += 1
                    result['stats']['field_types'][field_type]['failed'] += 1
                    logger.warning(f"✗ 填充失败 {action['selector']}: {exec_result['error']}")
            
            # 4. 计算成功率
            if result['stats']['total_fields'] > 0:
                success_rate = result['stats']['filled_fields'] / result['stats']['total_fields']
                result['stats']['success_rate'] = f"{success_rate * 100:.1f}%"
                result['success'] = success_rate >= 0.7  # 70%以上认为成功
            
            logger.info(f"\n填充完成:")
            logger.info(f"  总字段数: {result['stats']['total_fields']}")
            logger.info(f"  成功: {result['stats']['filled_fields']}")
            logger.info(f"  失败: {result['stats']['failed_fields']}")
            logger.info(f"  成功率: {result['stats'].get('success_rate', '0%')}")
            
        except Exception as e:
            logger.error(f"表单填充失败: {e}")
            result['errors'].append(str(e))
            
        return result
    
    async def _analyze_element_group(self, group: Dict[str, Any],
                                   personal_data: Dict[str, Any],
                                   resume_data: Dict[str, Any],
                                   context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        分析一组DOM元素并生成动作列表
        
        Args:
            group: DOM元素组
            personal_data: 个人数据
            resume_data: 简历数据
            
        Returns:
            动作列表
        """
        # 准备发送给LLM的数据
        system_prompt = """You are an expert form field analyzer for job application systems like Greenhouse, Workday, and Lever.

Given DOM elements and candidate data, create action mappings for form filling.

Rules:
1. Identify the semantic meaning of each field (first_name, email, work_authorization, etc.)
2. Match with appropriate candidate data
3. Determine the correct control type (text, select, radio, checkbox, file, custom-dropdown)
4. For custom dropdowns (React/Vue components), mark as "custom-dropdown"
5. For file uploads, provide the full file path

Return JSON array of actions:
[
  {
    "selector": "#field-id or [name='field-name']",
    "control": "text|select|radio|checkbox|file|custom-dropdown|date",
    "value": "value to fill",
    "semantic": "field semantic meaning",
    "confidence": 0.9
  }
]

Special mappings:
- "Are you authorized to work" -> work_authorization (Yes/No)
- "Upload Resume" -> file with resume_path
- Country/State dropdowns -> exact values from personal data
- Phone -> Format as provided in personal data"""

        # 简化元素数据以减少token使用
        simplified_elements = []
        for element in group['elements']:
            # 只保留关键信息
            simplified = {
                'tag': element['tag'],
                'type': element['type'],
                'id': element['id'],
                'name': element['name'],
                'label': element['label'],
                'placeholder': element['placeholder'],
                'ariaLabel': element['ariaLabel'],
                'visible': element['visible']
            }
            
            # 特殊处理
            if element['type'] == 'select' or element.get('isCustomDropdown'):
                simplified['isDropdown'] = True
            if element['type'] == 'file':
                simplified['isFileUpload'] = True
            if element['type'] in ['radio', 'checkbox']:
                simplified['value'] = element.get('value', '')
                
            simplified_elements.append(simplified)
        
        # 使用EnhancedDataManager的结构化数据
        basic_info = personal_data.get('basic_info', {})
        location = personal_data.get('location', {})
        education = personal_data.get('education', {})
        work_info = personal_data.get('work_info', {})
        legal_status = personal_data.get('legal_status', {})
        preferences = personal_data.get('preferences', {})
        files = personal_data.get('files', {})
        
        candidate_info = {
            'basic': {
                'first_name': basic_info.get('first_name', ''),
                'last_name': basic_info.get('last_name', ''),
                'email': basic_info.get('email', ''),
                'phone': self.data_manager._format_phone(basic_info.get('phone', ''))
            },
            'location': {
                'country': location.get('country', 'United States'),
                'state': location.get('state', ''),
                'city': location.get('city', '')
            },
            'professional': {
                'linkedin': basic_info.get('linkedin', ''),
                'github': basic_info.get('github', ''),
                'portfolio': basic_info.get('portfolio', '')
            },
            'work': {
                'current_company': work_info.get('current_company', ''),
                'current_title': work_info.get('current_title', ''),
                'years_experience': work_info.get('years_experience', '')
            },
            'education': {
                'university': education.get('university', ''),
                'degree': education.get('degree', ''),
                'major': education.get('major', ''),
                'graduation_year': education.get('graduation_year', '')
            },
            'application': {
                'work_authorization': legal_status.get('work_authorization', 'Yes'),
                'salary_expectation': self.data_manager._format_salary(preferences.get('salary_expectation', '')),
                'resume_path': files.get('resume', {}).get('file_path', '')
            }
        }
        
        user_prompt = f"""Analyze these form elements and create filling actions:

Elements in group "{group['groupName']}":
{json.dumps(simplified_elements, indent=2)}

Candidate data:
{json.dumps(candidate_info, indent=2)}

Generate actions array. Focus on high-confidence matches only."""

        try:
            # 调用LLM
            response = self.gpt_service._make_request(
                system_prompt, user_prompt, response_format="json"
            )
            
            # 验证并处理响应
            if isinstance(response, list):
                actions = response
            elif isinstance(response, dict) and 'actions' in response:
                actions = response['actions']
            else:
                logger.error(f"LLM返回格式错误: {type(response)}")
                return []
            
            # 后处理：添加缺失的字段，验证选择器等
            valid_actions = []
            for action in actions:
                if self._validate_action(action):
                    # 处理特殊情况
                    if action['control'] == 'file' and not action['value']:
                        action['value'] = candidate_info['application']['resume_path']
                    
                    valid_actions.append(action)
            
            return valid_actions
            
        except Exception as e:
            logger.error(f"LLM分析失败，使用规则回退: {e}")
            return self._fallback_analysis(group, personal_data)
    
    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """验证动作是否有效"""
        required_fields = ['selector', 'control', 'value']
        for field in required_fields:
            if field not in action:
                return False
        
        # 验证选择器格式
        selector = action['selector']
        if not selector or not isinstance(selector, str):
            return False
        
        # 验证控件类型
        valid_controls = [
            'text', 'email', 'tel', 'url', 'number',
            'select', 'radio', 'checkbox', 'file',
            'date', 'datetime-local', 'textarea',
            'custom-dropdown'
        ]
        if action['control'] not in valid_controls:
            return False
        
        return True
    
    def _fallback_analysis(self, group: Dict[str, Any],
                          personal_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于规则的回退分析"""
        actions = []
        
        # 定义规则映射
        rules = {
            # 基本信息
            ('first', 'name'): ('first_name', 'text'),
            ('last', 'name'): ('last_name', 'text'),
            ('email',): ('email', 'text'),
            ('phone',): ('phone', 'text'),
            
            # 链接
            ('linkedin',): ('linkedin', 'text'),
            ('github',): ('github', 'text'),
            ('portfolio', 'website'): ('portfolio', 'text'),
            
            # 工作授权
            ('authorized', 'work'): ('work_authorization', 'text'),
            
            # 文件上传
            ('resume', 'upload', 'cv'): ('resume_path', 'file'),
        }
        
        for element in group['elements']:
            # 获取所有可能的文本
            texts = [
                element.get('label', ''),
                element.get('placeholder', ''),
                element.get('ariaLabel', ''),
                element.get('name', ''),
                element.get('id', '')
            ]
            
            combined_text = ' '.join(texts).lower()
            
            # 尝试匹配规则
            for keywords, (data_key, control_type) in rules.items():
                if any(keyword in combined_text for keyword in keywords):
                    value = personal_data.get(data_key, '')
                    
                    # 特殊处理
                    if data_key == 'resume_path':
                        value = personal_data.get('resume', {}).get('file_path', '')
                    
                    if value:
                        # 构建选择器
                        if element['id']:
                            selector = f"#{element['id']}"
                        elif element['name']:
                            selector = f"[name='{element['name']}']"
                        else:
                            continue
                        
                        actions.append({
                            'selector': selector,
                            'control': control_type,
                            'value': value,
                            'semantic': data_key,
                            'confidence': 0.7
                        })
                        break
        
        return actions
