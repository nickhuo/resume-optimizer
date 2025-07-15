"""
字段自学习系统
基于 LLM 的智能字段识别和映射学习
"""
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class FieldLearningSystem:
    """字段自学习系统 - 持续学习和改进字段映射"""
    
    def __init__(self, gpt_service=None, knowledge_base_path: str = "data/field_knowledge_base.json"):
        """
        初始化学习系统
        
        Args:
            gpt_service: GPT服务实例
            knowledge_base_path: 知识库文件路径
        """
        self.gpt_service = gpt_service
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base = self._load_knowledge_base()
        
        # 平台特定的模式
        self.platform_patterns = {
            'greenhouse': {
                'url_pattern': r'greenhouse\.io',
                'specific_fields': {
                    'resume': ['resume', 'cv', 'upload resume'],
                    'cover_letter': ['cover letter', 'cover_letter'],
                    'linkedin': ['linkedin', 'linkedin profile'],
                    'github': ['github', 'github profile'],
                    'portfolio': ['portfolio', 'website', 'personal website'],
                    'referral': ['referral', 'how did you hear'],
                    'pronouns': ['pronouns', 'gender pronouns'],
                    'location': ['location', 'where are you located'],
                    'work_authorization': ['work authorization', 'authorized to work'],
                    'sponsorship': ['sponsorship', 'require sponsorship'],
                    'salary': ['salary', 'compensation', 'expected salary'],
                    'start_date': ['start date', 'when can you start']
                }
            },
            'lever': {
                'url_pattern': r'lever\.co',
                'specific_fields': {
                    'resume': ['resume', 'cv'],
                    'full_name': ['full name', 'name'],
                    'email': ['email', 'email address'],
                    'phone': ['phone', 'phone number'],
                    'current_company': ['current company', 'current employer'],
                    'linkedin': ['linkedin url', 'linkedin'],
                    'website': ['website', 'urls'],
                    'additional_info': ['additional information', 'comments']
                }
            },
            'workday': {
                'url_pattern': r'myworkdayjobs\.com',
                'specific_fields': {
                    'legal_name': ['legal name', 'full legal name'],
                    'preferred_name': ['preferred name', 'nickname'],
                    'country': ['country', 'country/region'],
                    'state': ['state', 'state/province'],
                    'city': ['city'],
                    'postal_code': ['postal code', 'zip code'],
                    'phone_type': ['phone type'],
                    'education_level': ['education level', 'highest degree'],
                    'field_of_study': ['field of study', 'major'],
                    'gpa': ['gpa', 'grade point average']
                }
            }
        }
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """加载知识库"""
        if self.knowledge_base_path.exists():
            try:
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载知识库失败: {e}")
        
        # 初始化空知识库
        return {
            'field_mappings': {},
            'platform_specific': {},
            'learning_history': [],
            'confidence_scores': {}
        }
    
    def _save_knowledge_base(self):
        """保存知识库"""
        try:
            self.knowledge_base_path.parent.mkdir(exist_ok=True)
            with open(self.knowledge_base_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
            logger.info("知识库已保存")
        except Exception as e:
            logger.error(f"保存知识库失败: {e}")
    
    def detect_platform(self, url: str) -> Optional[str]:
        """检测平台类型"""
        for platform, config in self.platform_patterns.items():
            if re.search(config['url_pattern'], url, re.I):
                return platform
        return None
    
    async def learn_field_mapping(self, field_info: Dict[str, Any], 
                                 user_value: str, 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """
        学习新的字段映射
        
        Args:
            field_info: 字段信息（包含label, id, name等）
            user_value: 用户填写的值
            context: 上下文信息（URL、平台等）
            
        Returns:
            学习结果
        """
        # 提取字段特征
        field_features = self._extract_field_features(field_info)
        
        # 使用 LLM 分析字段语义
        semantic_analysis = await self._analyze_field_semantics(
            field_features, user_value, context
        )
        
        # 更新知识库
        field_key = self._generate_field_key(field_features)
        
        if field_key not in self.knowledge_base['field_mappings']:
            self.knowledge_base['field_mappings'][field_key] = {
                'semantic_type': semantic_analysis['semantic_type'],
                'data_path': semantic_analysis['suggested_data_path'],
                'patterns': field_features['patterns'],
                'examples': [],
                'confidence': 0.5
            }
        
        # 添加示例
        self.knowledge_base['field_mappings'][field_key]['examples'].append({
            'value': user_value,
            'context': context,
            'timestamp': datetime.now().isoformat()
        })
        
        # 更新置信度
        self._update_confidence(field_key)
        
        # 记录学习历史
        self.knowledge_base['learning_history'].append({
            'field_key': field_key,
            'field_info': field_info,
            'value': user_value,
            'semantic_analysis': semantic_analysis,
            'timestamp': datetime.now().isoformat()
        })
        
        # 保存知识库
        self._save_knowledge_base()
        
        return {
            'field_key': field_key,
            'semantic_type': semantic_analysis['semantic_type'],
            'confidence': self.knowledge_base['field_mappings'][field_key]['confidence'],
            'learned': True
        }
    
    def _extract_field_features(self, field_info: Dict[str, Any]) -> Dict[str, Any]:
        """提取字段特征"""
        features = {
            'label': field_info.get('label', '').lower(),
            'id': field_info.get('id', '').lower(),
            'name': field_info.get('name', '').lower(),
            'placeholder': field_info.get('placeholder', '').lower(),
            'aria_label': field_info.get('ariaLabel', '').lower(),
            'type': field_info.get('type', ''),
            'patterns': []
        }
        
        # 提取所有文本模式
        for key in ['label', 'placeholder', 'aria_label']:
            if features[key]:
                # 分词和标准化
                words = re.findall(r'\w+', features[key])
                features['patterns'].extend(words)
        
        # 去重
        features['patterns'] = list(set(features['patterns']))
        
        return features
    
    async def _analyze_field_semantics(self, field_features: Dict[str, Any],
                                     user_value: str,
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 分析字段语义"""
        if not self.gpt_service:
            # 如果没有 GPT 服务，使用规则基础的分析
            return self._rule_based_analysis(field_features, user_value)
        
        system_prompt = """You are an expert at analyzing form fields and determining their semantic meaning.

Given field features and a user-provided value, determine:
1. The semantic type of the field (e.g., first_name, phone, custom_question, etc.)
2. The appropriate data path in a structured profile (e.g., basic_info.first_name)
3. Any validation rules or formatting requirements

Common semantic types:
- Personal: first_name, last_name, email, phone, address
- Professional: current_company, title, years_experience, salary_expectation
- Education: university, degree, major, graduation_year
- Links: linkedin, github, portfolio, website
- Legal: work_authorization, sponsorship_required, visa_status
- Custom: For company-specific questions

Return JSON with:
{
  "semantic_type": "field_type",
  "suggested_data_path": "category.field_name",
  "validation_type": "text|email|phone|url|number|date",
  "formatting_hint": "any special formatting",
  "confidence": 0.0-1.0
}"""

        user_prompt = f"""Analyze this form field:

Field features:
- Label: {field_features.get('label')}
- Placeholder: {field_features.get('placeholder')}
- Type: {field_features.get('type')}
- ID/Name: {field_features.get('id')} / {field_features.get('name')}

User provided value: {user_value}

Context:
- Platform: {context.get('platform', 'unknown')}
- URL: {context.get('url', '')}

What is the semantic meaning of this field?"""

        try:
            response = self.gpt_service._make_request(
                system_prompt, user_prompt, response_format="json"
            )
            return response
        except Exception as e:
            logger.error(f"LLM 分析失败: {e}")
            return self._rule_based_analysis(field_features, user_value)
    
    def _rule_based_analysis(self, field_features: Dict[str, Any],
                           user_value: str) -> Dict[str, Any]:
        """基于规则的字段分析（备用方案）"""
        patterns = ' '.join(field_features['patterns'])
        
        # 常见模式匹配
        if any(word in patterns for word in ['first', 'given']):
            return {
                'semantic_type': 'first_name',
                'suggested_data_path': 'basic_info.first_name',
                'validation_type': 'text',
                'confidence': 0.8
            }
        elif any(word in patterns for word in ['last', 'family', 'surname']):
            return {
                'semantic_type': 'last_name',
                'suggested_data_path': 'basic_info.last_name',
                'validation_type': 'text',
                'confidence': 0.8
            }
        elif 'email' in patterns:
            return {
                'semantic_type': 'email',
                'suggested_data_path': 'basic_info.email',
                'validation_type': 'email',
                'confidence': 0.9
            }
        elif any(word in patterns for word in ['phone', 'mobile', 'tel']):
            return {
                'semantic_type': 'phone',
                'suggested_data_path': 'basic_info.phone',
                'validation_type': 'phone',
                'confidence': 0.9
            }
        elif 'linkedin' in patterns:
            return {
                'semantic_type': 'linkedin',
                'suggested_data_path': 'basic_info.linkedin',
                'validation_type': 'url',
                'confidence': 0.9
            }
        elif 'github' in patterns:
            return {
                'semantic_type': 'github',
                'suggested_data_path': 'basic_info.github',
                'validation_type': 'url',
                'confidence': 0.9
            }
        else:
            # 未知字段
            return {
                'semantic_type': 'custom_field',
                'suggested_data_path': f'custom.{field_features.get("id", "unknown")}',
                'validation_type': 'text',
                'confidence': 0.3
            }
    
    def _generate_field_key(self, field_features: Dict[str, Any]) -> str:
        """生成字段的唯一键"""
        # 使用最有意义的标识符
        if field_features.get('label'):
            key = field_features['label']
        elif field_features.get('placeholder'):
            key = field_features['placeholder']
        elif field_features.get('id'):
            key = field_features['id']
        else:
            key = '_'.join(field_features['patterns'][:3])
        
        # 标准化
        key = re.sub(r'[^a-z0-9_]', '_', key.lower())
        key = re.sub(r'_+', '_', key).strip('_')
        
        return key
    
    def _update_confidence(self, field_key: str):
        """更新字段映射的置信度"""
        mapping = self.knowledge_base['field_mappings'][field_key]
        
        # 基于示例数量和一致性计算置信度
        example_count = len(mapping['examples'])
        
        # 检查值的一致性
        if example_count > 1:
            values = [ex['value'] for ex in mapping['examples']]
            unique_values = len(set(values))
            consistency = 1.0 - (unique_values - 1) / example_count
        else:
            consistency = 0.5
        
        # 计算置信度
        confidence = min(0.95, 0.5 + (example_count * 0.1) + (consistency * 0.3))
        mapping['confidence'] = round(confidence, 2)
    
    def get_learned_mapping(self, field_info: Dict[str, Any],
                          platform: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取已学习的字段映射"""
        field_features = self._extract_field_features(field_info)
        field_key = self._generate_field_key(field_features)
        
        # 首先检查精确匹配
        if field_key in self.knowledge_base['field_mappings']:
            mapping = self.knowledge_base['field_mappings'][field_key]
            if mapping['confidence'] > 0.6:
                return mapping
        
        # 检查平台特定的映射
        if platform and platform in self.knowledge_base.get('platform_specific', {}):
            platform_mappings = self.knowledge_base['platform_specific'][platform]
            if field_key in platform_mappings:
                return platform_mappings[field_key]
        
        # 模糊匹配
        for pattern in field_features['patterns']:
            for key, mapping in self.knowledge_base['field_mappings'].items():
                if pattern in mapping.get('patterns', []) and mapping['confidence'] > 0.7:
                    return mapping
        
        return None
    
    def get_platform_insights(self, platform: str) -> Dict[str, Any]:
        """获取平台特定的洞察"""
        insights = {
            'platform': platform,
            'known_fields': [],
            'common_patterns': [],
            'tips': []
        }
        
        if platform in self.platform_patterns:
            insights['known_fields'] = list(self.platform_patterns[platform]['specific_fields'].keys())
            
            # 从学习历史中提取模式
            platform_history = [
                h for h in self.knowledge_base['learning_history']
                if h.get('context', {}).get('platform') == platform
            ]
            
            if platform_history:
                # 提取常见模式
                field_types = defaultdict(int)
                for history in platform_history:
                    field_types[history['semantic_analysis']['semantic_type']] += 1
                
                insights['common_patterns'] = [
                    {'type': k, 'frequency': v}
                    for k, v in sorted(field_types.items(), key=lambda x: x[1], reverse=True)
                ]
            
            # 平台特定的提示
            if platform == 'greenhouse':
                insights['tips'] = [
                    "Greenhouse often uses custom question IDs like 'question_XXXXXXX'",
                    "Resume upload is usually required",
                    "Look for work authorization questions"
                ]
            elif platform == 'lever':
                insights['tips'] = [
                    "Lever typically groups fields by section",
                    "Additional information field is common",
                    "URLs section may include multiple links"
                ]
            elif platform == 'workday':
                insights['tips'] = [
                    "Workday has multi-step forms",
                    "Legal name vs preferred name distinction",
                    "Detailed address requirements"
                ]
        
        return insights
    
    def export_knowledge(self, output_path: Optional[str] = None) -> str:
        """导出知识库为可读格式"""
        if not output_path:
            output_path = f"field_knowledge_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_mappings': len(self.knowledge_base['field_mappings']),
            'total_examples': sum(
                len(m['examples']) 
                for m in self.knowledge_base['field_mappings'].values()
            ),
            'platforms': list(set(
                h.get('context', {}).get('platform', 'unknown')
                for h in self.knowledge_base['learning_history']
            )),
            'high_confidence_mappings': {
                k: v for k, v in self.knowledge_base['field_mappings'].items()
                if v['confidence'] > 0.8
            },
            'recent_learnings': self.knowledge_base['learning_history'][-20:]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"知识库已导出到: {output_path}")
        return output_path
