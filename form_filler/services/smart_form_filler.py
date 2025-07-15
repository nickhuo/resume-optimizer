"""
智能表单填充服务
使用GPT分析表单字段并智能匹配个人信息
"""
import logging
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

from .gpt_service import GPTService
from .smart_field_handler import SmartFieldHandler

logger = logging.getLogger(__name__)


class SmartFormFiller:
    """智能表单填充器，使用GPT分析和匹配表单字段"""
    
    def __init__(self, gpt_service: GPTService = None):
        """
        初始化智能表单填充器
        
        Args:
            gpt_service: GPT服务实例
        """
        self.gpt_service = gpt_service or GPTService()
        
    def analyze_and_match_fields(self, form_fields: List[Dict[str, Any]], 
                                personal_data: Dict[str, Any],
                                resume_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        分析表单字段并智能匹配个人数据
        
        Args:
            form_fields: 表单字段信息列表
            personal_data: 从YAML文件加载的个人信息
            resume_data: 从JSON文件加载的简历信息
            
        Returns:
            字段匹配映射，key为字段选择器，value包含要填充的值和其他信息
        """
        # 如果字段太多，分批处理以避免token限制
        if len(form_fields) > 30:
            logger.info(f"Large form with {len(form_fields)} fields, processing in chunks")
            return self._analyze_fields_in_chunks(form_fields, personal_data, resume_data)
        
        return self._analyze_fields_batch(form_fields, personal_data, resume_data)
    
    def _analyze_fields_in_chunks(self, form_fields: List[Dict[str, Any]], 
                                 personal_data: Dict[str, Any],
                                 resume_data: Dict[str, Any], 
                                 chunk_size: int = 20) -> Dict[str, Dict[str, Any]]:
        """
        分批处理大量表单字段
        
        Args:
            form_fields: 表单字段信息列表
            personal_data: 个人信息
            resume_data: 简历信息
            chunk_size: 每批处理的字段数量
            
        Returns:
            合并后的字段匹配映射
        """
        all_mappings = {}
        
        for i in range(0, len(form_fields), chunk_size):
            chunk = form_fields[i:i + chunk_size]
            logger.info(f"Processing chunk {i//chunk_size + 1}/{(len(form_fields) + chunk_size - 1)//chunk_size}")
            
            chunk_mappings = self._analyze_fields_batch(chunk, personal_data, resume_data)
            all_mappings.update(chunk_mappings)
        
        return all_mappings
    
    def _analyze_fields_batch(self, form_fields: List[Dict[str, Any]], 
                             personal_data: Dict[str, Any],
                             resume_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        分析一批表单字段
        
        Args:
            form_fields: 表单字段信息列表
            personal_data: 个人信息
            resume_data: 简历信息
            
        Returns:
            字段匹配映射
        """
        system_prompt = """You are an intelligent form field analyzer for job applications.
        Given form fields and candidate data, create optimal field mappings.
        
        IMPORTANT: Return ONLY valid JSON without ellipsis (...), truncation, or markdown formatting.
        Keep values concise to avoid size limits.
        
        Return a JSON object with EXACTLY this structure:
        {
            "field_mappings": {
                "field_selector": {
                    "value": "actual value to fill",
                    "confidence": 0.9,
                    "source": "yaml",
                    "field_type": "text",
                    "reasoning": "brief reason"
                }
            },
            "unmatched_fields": [],
            "suggestions": []
        }
        
        Field matching rules:
        1. First/Last name: Split full name if needed
        2. Phone: Format consistently (e.g., +1 (xxx) xxx-xxxx)
        3. LinkedIn: Use full URL format
        4. GitHub: Convert username to full URL if needed
        5. Education: Match degree types (BS/Bachelor of Science, MS/Master of Science)
        6. Work experience: Use most recent position
        7. Skills: Match relevant skills from the skills list
        8. Cover letter: Generate if not provided, tailored to the position
        9. Work authorization: Map Yes/No to appropriate form values
        10. Expected salary: Use salary_expectation or suggest based on role
        
        For unmatched required fields, suggest reasonable defaults or mark for manual input.
        """
        
        # 合并所有可用数据
        all_data = self._merge_candidate_data(personal_data, resume_data)
        
        # Limit form fields data to prevent token overflow
        simplified_fields = []
        for field in form_fields:
            simplified_field = {
                "selector": field.get("selector"),
                "name": field.get("name"),
                "label": field.get("label"),
                "type": field.get("type"),
                "required": field.get("required", False),
                "placeholder": field.get("placeholder", "")
            }
            # Only include non-empty values
            simplified_fields.append({k: v for k, v in simplified_field.items() if v})
        
        # Simplify candidate data for the prompt
        simplified_data = {
            "basic_info": {
                "first_name": all_data.get("first_name"),
                "last_name": all_data.get("last_name"),
                "email": all_data.get("email"),
                "phone": all_data.get("phone"),
                "city": all_data.get("city"),
                "state": all_data.get("state")
            },
            "links": {
                "linkedin": all_data.get("linkedin"),
                "github": all_data.get("github"),
                "portfolio": all_data.get("portfolio")
            },
            "education": all_data.get("education"),
            "work": all_data.get("work"),
            "skills": all_data.get("skills", [])[:20],  # Limit skills
            "application_info": {
                "work_authorization": all_data.get("work_authorization"),
                "salary_expectation": all_data.get("salary_expectation"),
                "resume_path": all_data.get("resume_path")
            }
        }
        
        user_prompt = f"""Analyze these form fields and match with candidate data:

Form fields ({len(simplified_fields)} fields):
{json.dumps(simplified_fields, indent=2)}

Candidate data:
{json.dumps(simplified_data, indent=2)}

Create optimal field mappings. Return ONLY the JSON response.
"""
        
        try:
            response = self.gpt_service._make_request(system_prompt, user_prompt, response_format="json")
            # Validate response structure
            if not isinstance(response, dict):
                logger.error(f"GPT response is not a dict: {type(response)}")
                return self._fallback_field_mapping(form_fields, all_data)
            return self._process_field_mappings(response)
        except Exception as e:
            logger.error(f"Failed to analyze fields: {e}")
            return self._fallback_field_mapping(form_fields, all_data)
    
    def _merge_candidate_data(self, personal_data: Dict[str, Any], 
                             resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并YAML和JSON中的候选人数据
        
        Args:
            personal_data: YAML个人信息
            resume_data: JSON简历信息
            
        Returns:
            合并后的完整数据
        """
        # 从简历中提取结构化数据
        merged = {
            # 基本信息 - 优先使用YAML中的数据
            "first_name": personal_data.get("first_name", ""),
            "last_name": personal_data.get("last_name", ""),
            "full_name": resume_data.get("name", ""),
            "email": personal_data.get("email") or resume_data.get("email", ""),
            "phone": personal_data.get("phone") or resume_data.get("phone", ""),
            
            # 专业链接
            "linkedin": personal_data.get("linkedin", ""),
            "github": personal_data.get("github") or f"https://{resume_data.get('github', '')}",
            "portfolio": personal_data.get("portfolio") or f"https://{resume_data.get('website', '')}",
            
            # 地址信息
            "address": personal_data.get("address", ""),
            "city": personal_data.get("city", ""),
            "state": personal_data.get("state", ""),
            "zipcode": personal_data.get("zipcode", ""),
            "country": personal_data.get("country", ""),
            
            # 教育背景 - 合并两个来源
            "education": {
                "university": personal_data.get("university", ""),
                "degree": personal_data.get("degree", ""),
                "major": personal_data.get("major", ""),
                "graduation_year": personal_data.get("graduation_year", ""),
                "gpa": personal_data.get("gpa", ""),
                "education_list": resume_data.get("education", [])
            },
            
            # 工作经验 - 合并两个来源
            "work": {
                "current_company": personal_data.get("current_company", ""),
                "current_title": personal_data.get("current_title", ""),
                "years_experience": personal_data.get("years_experience", ""),
                "experience_list": resume_data.get("experience", [])
            },
            
            # 技能
            "skills": personal_data.get("skills", []) or self._extract_skills_from_resume(resume_data),
            
            # 申请相关
            "salary_expectation": personal_data.get("salary_expectation", ""),
            "work_authorization": personal_data.get("work_authorization", ""),
            "require_sponsorship": personal_data.get("require_sponsorship", ""),
            "start_date": personal_data.get("start_date", ""),
            
            # 其他
            "cover_letter": personal_data.get("cover_letter", ""),
            "resume_path": personal_data.get("resume_path", ""),
            "footnote": resume_data.get("footnote", "")
        }
        
        # 如果YAML中没有名字，从简历的full_name中提取
        if not merged["first_name"] and merged["full_name"]:
            parts = merged["full_name"].split()
            if len(parts) >= 2:
                merged["first_name"] = parts[0]
                merged["last_name"] = " ".join(parts[1:])
        
        return merged
    
    def _extract_skills_from_resume(self, resume_data: Dict[str, Any]) -> List[str]:
        """从简历数据中提取技能列表"""
        skills = []
        if "skills" in resume_data:
            for category, skill_list in resume_data["skills"].items():
                skills.extend(skill_list)
        return skills
    
    def _process_field_mappings(self, gpt_response: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        处理GPT返回的字段映射
        
        Args:
            gpt_response: GPT返回的原始响应
            
        Returns:
            处理后的字段映射
        """
        if "field_mappings" not in gpt_response:
            logger.error("No field_mappings in GPT response")
            return {}
        
        field_mappings = gpt_response["field_mappings"]
        
        # 记录未匹配的字段
        if "unmatched_fields" in gpt_response:
            for field in gpt_response["unmatched_fields"]:
                logger.warning(f"Unmatched field: {field.get('label')} - {field.get('reason')}")
        
        # 记录建议
        if "suggestions" in gpt_response:
            for suggestion in gpt_response["suggestions"]:
                logger.info(f"Suggestion: {suggestion}")
        
        return field_mappings
    
    def _fallback_field_mapping(self, form_fields: List[Dict[str, Any]], 
                               candidate_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        备用的基于规则的字段映射
        
        Args:
            form_fields: 表单字段列表
            candidate_data: 候选人数据
            
        Returns:
            基于规则的字段映射
        """
        mappings = {}
        
        # 定义字段名称到数据的映射规则
        rules = {
            # 名字
            ("firstname", "first_name", "fname"): candidate_data.get("first_name"),
            ("lastname", "last_name", "lname"): candidate_data.get("last_name"),
            ("fullname", "full_name", "name"): candidate_data.get("full_name") or 
                                               f"{candidate_data.get('first_name', '')} {candidate_data.get('last_name', '')}".strip(),
            
            # 联系方式
            ("email", "e-mail", "emailaddress"): candidate_data.get("email"),
            ("phone", "telephone", "mobile"): candidate_data.get("phone"),
            
            # 专业链接
            ("linkedin", "linkedin_url"): candidate_data.get("linkedin"),
            ("github", "github_url"): candidate_data.get("github"),
            ("portfolio", "website", "personal_website"): candidate_data.get("portfolio"),
            
            # 教育
            ("school", "university", "college"): candidate_data.get("education", {}).get("university"),
            ("degree", "education_level"): candidate_data.get("education", {}).get("degree"),
            ("major", "field_of_study"): candidate_data.get("education", {}).get("major"),
            
            # 工作
            ("company", "current_employer"): candidate_data.get("work", {}).get("current_company"),
            ("title", "position", "job_title"): candidate_data.get("work", {}).get("current_title"),
            
            # 其他
            ("cover_letter", "message", "why_interested"): candidate_data.get("cover_letter"),
            ("resume", "cv"): candidate_data.get("resume_path"),
        }
        
        # 遍历表单字段，应用规则
        for field in form_fields:
            field_name = field.get("name", "").lower()
            field_id = field.get("id", "").lower()
            field_placeholder = field.get("placeholder", "").lower()
            field_label = field.get("label", "").lower()
            
            # 构建选择器
            selector = field.get("selector") or f"[name='{field.get('name')}']" if field.get("name") else f"#{field.get('id')}"
            
            # 尝试匹配规则
            for rule_keys, rule_value in rules.items():
                if any(key in field_name or key in field_id or key in field_placeholder or key in field_label 
                      for key in rule_keys):
                    if rule_value:
                        mappings[selector] = {
                            "value": str(rule_value),
                            "confidence": 0.7,
                            "source": "rule_based",
                            "field_type": field.get("type", "text"),
                            "reasoning": f"Matched by rule for {rule_keys[0]}"
                        }
                        break
        
        return mappings
    
    def generate_cover_letter(self, job_title: str, company: str, 
                            job_description: str, candidate_data: Dict[str, Any]) -> str:
        """
        使用GPT生成定制化的求职信
        
        Args:
            job_title: 职位名称
            company: 公司名称
            job_description: 职位描述
            candidate_data: 候选人数据
            
        Returns:
            生成的求职信
        """
        system_prompt = """You are a professional cover letter writer.
        Create a compelling, concise cover letter (150-200 words) that:
        1. Shows enthusiasm for the specific role and company
        2. Highlights relevant experience and skills
        3. Demonstrates knowledge of the company
        4. Maintains professional tone
        5. Avoids generic phrases
        
        Return ONLY the cover letter text, no additional formatting or explanations."""
        
        user_prompt = f"""Write a cover letter for:
        
Position: {job_title} at {company}

Job Description highlights:
{job_description[:1000]}

Candidate Background:
- Name: {candidate_data.get('full_name')}
- Current Role: {candidate_data.get('work', {}).get('current_title')} at {candidate_data.get('work', {}).get('current_company')}
- Education: {candidate_data.get('education', {}).get('degree')} in {candidate_data.get('education', {}).get('major')}
- Key Skills: {', '.join(candidate_data.get('skills', [])[:10])}
- Notable: {candidate_data.get('footnote', '')}

Recent Experience Highlights:
{json.dumps(candidate_data.get('work', {}).get('experience_list', [])[:2], indent=2)}
"""
        
        try:
            cover_letter = self.gpt_service._make_request(system_prompt, user_prompt, response_format="text")
            return cover_letter.strip()
        except Exception as e:
            logger.error(f"Failed to generate cover letter: {e}")
            # 返回备用的通用求职信
            return candidate_data.get("cover_letter", f"""I am writing to express my strong interest in the {job_title} position at {company}. With my background in {candidate_data.get('education', {}).get('major', 'technology')} and experience as a {candidate_data.get('work', {}).get('current_title', 'software engineer')}, I am confident in my ability to contribute to your team.

I am particularly drawn to this opportunity because of {company}'s innovative approach and the chance to work on impactful projects. My technical skills and passion for problem-solving make me an ideal candidate for this role.

I look forward to discussing how my experience and enthusiasm can benefit your team. Thank you for your consideration.""")
    
    async def fill_form(self, page, fields: List[Dict[str, Any]], 
                       personal_data: Dict[str, Any] = None,
                       resume_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        填写表单
        
        Args:
            page: Playwright页面对象
            fields: 表单字段列表
            personal_data: 个人数据（可选）
            resume_data: 简历数据（可选）
            
        Returns:
            填写结果
        """
        result = {
            'success': False,
            'filled_fields': {},
            'errors': [],
            'field_results': []  # 详细的字段填充结果
        }
        
        try:
            # 加载数据文件（如果没有提供）
            if personal_data is None:
                personal_data = self._load_personal_data()
            if resume_data is None:
                resume_data = self._load_resume_data()
            
            # 分析字段并获取映射
            field_mappings = self.analyze_and_match_fields(fields, personal_data, resume_data)
            
            # 初始化智能字段处理器
            field_handler = SmartFieldHandler(page)
            
            # 统计信息
            total_fields = len(field_mappings)
            successful_fields = 0
            
            # 填充每个字段
            for selector, mapping in field_mappings.items():
                # 查找对应的字段信息
                field_info = None
                for field in fields:
                    if field.get('selector') == selector:
                        field_info = field
                        break
                
                if not field_info:
                    # 构造基本的字段信息
                    field_info = {
                        'selector': selector,
                        'type': mapping.get('field_type', 'text'),
                        'name': mapping.get('field_name', ''),
                        'label': mapping.get('field_label', '')
                    }
                
                # 使用智能字段处理器填充字段
                fill_result = await field_handler.analyze_and_fill_field(
                    field_info=field_info,
                    value_to_fill=mapping.get('value', ''),
                    personal_data=personal_data
                )
                
                # 记录结果
                result['field_results'].append(fill_result)
                
                if fill_result['success']:
                    successful_fields += 1
                    result['filled_fields'][selector] = {
                        'value': fill_result['actual_value'],
                        'type': fill_result['field_type'],
                        'confidence': fill_result['confidence'],
                        'attempted_value': fill_result['attempted_value']
                    }
                    logger.info(f"✓ 成功填充字段 {selector}: {fill_result['actual_value']} (置信度: {fill_result['confidence']:.2f})")
                else:
                    error_msg = fill_result['error'] or f"Failed to fill {selector}"
                    result['errors'].append(error_msg)
                    logger.warning(f"✗ 填充字段失败 {selector}: {error_msg}")
            
            # 计算成功率
            success_rate = successful_fields / total_fields if total_fields > 0 else 0
            result['success_rate'] = success_rate
            result['summary'] = {
                'total_fields': total_fields,
                'successful_fields': successful_fields,
                'failed_fields': total_fields - successful_fields,
                'success_rate': f"{success_rate * 100:.1f}%"
            }
            
            # 判断是否成功（超过70%的字段填充成功）
            result['success'] = success_rate >= 0.7
            
            logger.info(f"\n表单填充完成:")
            logger.info(f"  - 总字段数: {total_fields}")
            logger.info(f"  - 成功: {successful_fields}")
            logger.info(f"  - 失败: {total_fields - successful_fields}")
            logger.info(f"  - 成功率: {success_rate * 100:.1f}%")
            
        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            result['errors'].append(str(e))
        
        return result
    
    def _load_personal_data(self) -> Dict[str, Any]:
        """加载个人数据文件"""
        try:
            import yaml
            from pathlib import Path
            
            # 尝试多个可能的路径
            possible_paths = [
                Path('config/personal_info.yaml'),
                Path('data/personal_info.yaml'),
                Path('personal_info.yaml'),
                Path('../config/personal_info.yaml')
            ]
            
            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        # 展平嵌套结构为扁平字典
                        flat_data = {}
                        for section, values in data.items():
                            if isinstance(values, dict):
                                for key, value in values.items():
                                    flat_data[key] = value
                                # 保留原始嵌套结构以供需要
                                flat_data[section] = values
                            else:
                                flat_data[section] = values
                        return flat_data
            
            logger.warning("Personal info file not found")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to load personal data: {e}")
            return {}
    
    def _load_resume_data(self) -> Dict[str, Any]:
        """加载简历数据文件"""
        try:
            from pathlib import Path
            
            # 尝试多个可能的路径
            possible_paths = [
                Path('data/resume_example.json'),
                Path('data/resume.json'),
                Path('resume.json'),
                Path('../data/resume_example.json')
            ]
            
            for path in possible_paths:
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            logger.warning("Resume file not found")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to load resume data: {e}")
            return {}
