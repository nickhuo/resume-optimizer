"""
增强版数据管理器
基于 greenhouse_test.py 的经验，创建配置化和智能化的数据管理系统
"""
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import yaml
import json
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class EnhancedDataManager:
    """增强版数据管理器 - 智能处理各种数据格式和映射"""
    
    def __init__(self, personal_data_path: str = None, resume_data_path: str = None):
        """
        初始化数据管理器
        
        Args:
            personal_data_path: 个人数据文件路径
            resume_data_path: 简历数据文件路径
        """
        self.personal_data_path = personal_data_path or "personal_info.yaml"
        self.resume_data_path = resume_data_path or "data/sde_resume.json"
        
        # 加载数据
        self.personal_data = self._load_personal_data()
        self.resume_data = self._load_resume_data()
        
        # 智能字段映射
        self.field_mappings = self._create_field_mappings()
        
        # 常见值的标准化映射
        self.value_normalizer = self._create_value_normalizer()
        
    def _load_personal_data(self) -> Dict[str, Any]:
        """加载个人数据"""
        try:
            if Path(self.personal_data_path).exists():
                with open(self.personal_data_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"个人数据文件不存在: {self.personal_data_path}")
                return self._get_default_personal_data()
        except Exception as e:
            logger.error(f"加载个人数据失败: {e}")
            return self._get_default_personal_data()
    
    def _load_resume_data(self) -> Dict[str, Any]:
        """加载简历数据"""
        try:
            if Path(self.resume_data_path).exists():
                with open(self.resume_data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"简历数据文件不存在: {self.resume_data_path}")
                return {}
        except Exception as e:
            logger.error(f"加载简历数据失败: {e}")
            return {}
    
    def _get_default_personal_data(self) -> Dict[str, Any]:
        """获取默认个人数据结构"""
        return {
            'basic_info': {
                'first_name': '',
                'last_name': '',
                'full_name': '',
                'email': '',
                'phone': '',
                'linkedin': '',
                'github': '',
                'portfolio': '',
                'website': ''
            },
            'location': {
                'country': 'United States',
                'state': 'California',
                'city': 'San Francisco',
                'address': '',
                'zip_code': ''
            },
            'education': {
                'university': '',
                'degree': '',
                'major': '',
                'graduation_year': '',
                'graduation_month': '',
                'gpa': ''
            },
            'work_info': {
                'current_company': '',
                'current_title': '',
                'years_experience': '',
                'most_recent_employer': '',
                'willing_to_relocate': True,
                'remote_work_preference': True
            },
            'legal_status': {
                'work_authorization': 'Yes',
                'require_sponsorship': 'No',
                'visa_status': 'Authorized to work'
            },
            'preferences': {
                'salary_expectation': '70000',
                'start_date': 'Immediately',
                'job_type': 'Full-time',
                'remote_preference': 'Remote or Hybrid'
            },
            'files': {
                'resume': {
                    'file_path': '',
                    'file_name': 'resume.pdf'
                },
                'cover_letter': {
                    'file_path': '',
                    'file_name': 'cover_letter.pdf'
                }
            }
        }
    
    def _create_field_mappings(self) -> Dict[str, Dict[str, Any]]:
        """创建智能字段映射"""
        return {
            # 基本信息映射
            'first_name': {
                'patterns': ['first.name', 'firstName', 'fname', 'given.name'],
                'data_path': 'basic_info.first_name',
                'fallback_patterns': ['name', 'full.name']
            },
            'last_name': {
                'patterns': ['last.name', 'lastName', 'lname', 'family.name', 'surname'],
                'data_path': 'basic_info.last_name'
            },
            'full_name': {
                'patterns': ['full.name', 'fullName', 'legal.name', 'complete.name'],
                'data_path': 'basic_info.full_name',
                'computed': True,
                'compute_func': lambda data: f"{data.get('basic_info', {}).get('first_name', '')} {data.get('basic_info', {}).get('last_name', '')}".strip()
            },
            'email': {
                'patterns': ['email', 'e.mail', 'emailAddress', 'mail'],
                'data_path': 'basic_info.email',
                'validation': 'email'
            },
            'phone': {
                'patterns': ['phone', 'telephone', 'mobile', 'tel', 'phoneNumber'],
                'data_path': 'basic_info.phone',
                'format_func': self._format_phone
            },
            
            # 教育信息
            'university': {
                'patterns': ['university', 'college', 'school', 'institution', 'alma.mater'],
                'data_path': 'education.university'
            },
            'degree': {
                'patterns': ['degree', 'qualification', 'education.level'],
                'data_path': 'education.degree'
            },
            'major': {
                'patterns': ['major', 'field.of.study', 'specialization', 'subject'],
                'data_path': 'education.major'
            },
            'graduation_year': {
                'patterns': ['graduation.year', 'year.graduated', 'completion.year'],
                'data_path': 'education.graduation_year'
            },
            
            # 工作信息
            'current_company': {
                'patterns': ['current.company', 'employer', 'organization', 'workplace'],
                'data_path': 'work_info.current_company'
            },
            'current_title': {
                'patterns': ['current.title', 'position', 'role', 'job.title'],
                'data_path': 'work_info.current_title'
            },
            'years_experience': {
                'patterns': ['years.experience', 'experience.years', 'work.experience'],
                'data_path': 'work_info.years_experience'
            },
            
            # 法律状态
            'work_authorization': {
                'patterns': ['work.authorization', 'authorized.to.work', 'legal.to.work'],
                'data_path': 'legal_status.work_authorization',
                'value_map': {
                    'yes': ['Yes', 'Authorized', 'Eligible', 'Permitted'],
                    'no': ['No', 'Not Authorized', 'Not Eligible', 'Requires Sponsorship']
                }
            },
            'require_sponsorship': {
                'patterns': ['require.sponsorship', 'need.sponsorship', 'visa.sponsorship'],
                'data_path': 'legal_status.require_sponsorship',
                'value_map': {
                    'yes': ['Yes', 'Required', 'Needed'],
                    'no': ['No', 'Not Required', 'Not Needed']
                }
            },
            
            # 偏好设置
            'salary_expectation': {
                'patterns': ['salary.expectation', 'expected.salary', 'compensation'],
                'data_path': 'preferences.salary_expectation',
                'format_func': self._format_salary
            },
            'willing_to_relocate': {
                'patterns': ['willing.to.relocate', 'relocate', 'relocation'],
                'data_path': 'work_info.willing_to_relocate',
                'value_map': {
                    'yes': ['Yes', 'Willing', 'Open to'],
                    'no': ['No', 'Not Willing', 'Prefer Not To']
                }
            },
            
            # 文件上传
            'resume': {
                'patterns': ['resume', 'cv', 'curriculum.vitae', 'upload.resume'],
                'data_path': 'files.resume.file_path',
                'file_type': True
            }
        }
    
    def _create_value_normalizer(self) -> Dict[str, Dict[str, str]]:
        """创建值标准化映射"""
        return {
            'boolean_yes': {
                'yes': 'Yes',
                'y': 'Yes',
                '1': 'Yes',
                'true': 'Yes',
                'authorized': 'Yes',
                'eligible': 'Yes'
            },
            'boolean_no': {
                'no': 'No',
                'n': 'No',
                '0': 'No',
                'false': 'No',
                'not authorized': 'No',
                'not eligible': 'No'
            },
            'degree_levels': {
                'bachelor': "Bachelor's Degree",
                'bachelors': "Bachelor's Degree",
                'bs': "Bachelor's Degree",
                'ba': "Bachelor's Degree",
                'master': "Master's Degree",
                'masters': "Master's Degree",
                'ms': "Master's Degree",
                'ma': "Master's Degree",
                'phd': "PhD",
                'doctorate': "PhD"
            },
            'experience_levels': {
                '0': '0-1 years',
                '1': '1-2 years',
                '2': '2-3 years',
                '3': '3-5 years',
                '4': '3-5 years',
                '5': '5+ years'
            }
        }
    
    def get_field_value(self, field_identifier: str, context: Dict[str, Any] = None) -> Optional[str]:
        """
        根据字段标识符获取对应的值
        
        Args:
            field_identifier: 字段标识符（可能是标签文本、ID、name等）
            context: 额外的上下文信息
            
        Returns:
            字段值或None
        """
        # 标准化字段标识符
        normalized_id = self._normalize_field_identifier(field_identifier)
        
        # 查找匹配的字段映射
        for field_name, mapping in self.field_mappings.items():
            if self._matches_pattern(normalized_id, mapping.get('patterns', [])):
                # 获取值
                if mapping.get('computed'):
                    # 计算值
                    compute_func = mapping.get('compute_func')
                    if compute_func:
                        return compute_func(self.personal_data)
                else:
                    # 直接获取值
                    value = self._get_nested_value(self.personal_data, mapping['data_path'])
                    
                    # 格式化值
                    if mapping.get('format_func'):
                        value = mapping['format_func'](value)
                    
                    # 标准化值
                    if mapping.get('value_map'):
                        value = self._normalize_value(value, mapping['value_map'])
                    
                    return value
        
        # 如果没有找到标准映射，尝试模糊匹配
        return self._fuzzy_match_value(normalized_id)
    
    def _normalize_field_identifier(self, identifier: str) -> str:
        """标准化字段标识符"""
        if not identifier:
            return ""
        
        # 转换为小写
        normalized = identifier.lower()
        
        # 移除特殊字符，替换为点
        normalized = re.sub(r'[^a-z0-9]+', '.', normalized)
        
        # 移除首尾的点
        normalized = normalized.strip('.')
        
        return normalized
    
    def _matches_pattern(self, identifier: str, patterns: List[str]) -> bool:
        """检查标识符是否匹配模式"""
        for pattern in patterns:
            if pattern.lower() in identifier or identifier in pattern.lower():
                return True
        return False
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字典中的值"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _normalize_value(self, value: Any, value_map: Dict[str, List[str]]) -> str:
        """标准化值"""
        if not value:
            return ""
        
        value_str = str(value).lower()
        
        # 查找匹配的标准值
        for standard_value, variations in value_map.items():
            if value_str in [v.lower() for v in variations]:
                return variations[0]  # 返回第一个（标准）值
        
        return str(value)
    
    def _format_phone(self, phone: str) -> str:
        """格式化电话号码"""
        if not phone:
            return ""
        
        # 移除所有非数字字符
        digits = re.sub(r'[^\d]', '', phone)
        
        # 格式化为 (XXX) XXX-XXXX
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone  # 返回原始值
    
    def _format_salary(self, salary: str) -> str:
        """格式化薪资期望"""
        if not salary:
            return ""
        
        # 移除非数字字符
        digits = re.sub(r'[^\d]', '', salary)
        
        if digits:
            # 添加千位分隔符
            return f"{int(digits):,}"
        
        return salary
    
    def _fuzzy_match_value(self, identifier: str) -> Optional[str]:
        """模糊匹配值"""
        # 这里可以实现更复杂的模糊匹配逻辑
        # 例如基于Levenshtein距离的字符串相似度匹配
        
        # 简单的关键词匹配
        keyword_mappings = {
            'linkedin': self.personal_data.get('basic_info', {}).get('linkedin', ''),
            'github': self.personal_data.get('basic_info', {}).get('github', ''),
            'website': self.personal_data.get('basic_info', {}).get('website', ''),
            'portfolio': self.personal_data.get('basic_info', {}).get('portfolio', ''),
        }
        
        for keyword, value in keyword_mappings.items():
            if keyword in identifier and value:
                return value
        
        return None
    
    def get_all_available_data(self) -> Dict[str, Any]:
        """获取所有可用数据"""
        return {
            'personal_data': self.personal_data,
            'resume_data': self.resume_data,
            'field_mappings': list(self.field_mappings.keys())
        }
    
    def validate_required_fields(self, required_fields: List[str]) -> Dict[str, bool]:
        """验证必需字段是否可用"""
        validation_result = {}
        
        for field in required_fields:
            value = self.get_field_value(field)
            validation_result[field] = bool(value)
        
        return validation_result
