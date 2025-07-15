"""
表单字段模型定义
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


class FieldType(Enum):
    """表单字段类型"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    FILE = "file"
    DATE = "date"
    NUMBER = "number"
    PASSWORD = "password"
    UNKNOWN = "unknown"


class SemanticFieldType(Enum):
    """字段语义类型"""
    # 个人信息
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    EMAIL = "email"
    PHONE = "phone"
    
    # 地址信息
    ADDRESS = "address"
    CITY = "city"
    STATE = "state"
    ZIP_CODE = "zip_code"
    COUNTRY = "country"
    
    # 工作相关
    CURRENT_COMPANY = "current_company"
    CURRENT_TITLE = "current_title"
    YEARS_OF_EXPERIENCE = "years_of_experience"
    SALARY_EXPECTATION = "salary_expectation"
    
    # 教育相关
    SCHOOL = "school"
    DEGREE = "degree"
    MAJOR = "major"
    GRADUATION_YEAR = "graduation_year"
    
    # 文档上传
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    PORTFOLIO = "portfolio"
    
    # 其他
    LINKEDIN_URL = "linkedin_url"
    GITHUB_URL = "github_url"
    WEBSITE = "website"
    REFERRAL = "referral"
    HOW_DID_YOU_HEAR = "how_did_you_hear"
    
    # 问答
    WHY_INTERESTED = "why_interested"
    AVAILABILITY = "availability"
    WORK_AUTHORIZATION = "work_authorization"
    REQUIRE_SPONSORSHIP = "require_sponsorship"
    
    UNKNOWN = "unknown"


@dataclass
class FormField:
    """表单字段信息"""
    # 基本信息
    field_type: FieldType
    semantic_type: SemanticFieldType
    selector: str
    name: Optional[str] = None
    id: Optional[str] = None
    
    # 标签和提示
    label: Optional[str] = None
    placeholder: Optional[str] = None
    aria_label: Optional[str] = None
    
    # 验证规则
    required: bool = False
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    pattern: Optional[str] = None
    
    # 选项（用于select/radio）
    options: Optional[List[Dict[str, str]]] = None
    
    # 填充值
    value: Optional[Any] = None
    confidence: float = 0.0  # 填充值的置信度


@dataclass
class FormAnalysisResult:
    """表单分析结果"""
    form_selector: Optional[str]  # 表单选择器
    fields: List[FormField]  # 字段列表
    submit_button_selector: Optional[str]  # 提交按钮选择器
    has_captcha: bool = False
    requires_login: bool = False
    total_fields: int = 0
    required_fields: int = 0
    recognized_fields: int = 0  # 成功识别语义的字段数
    
    @property
    def recognition_rate(self) -> float:
        """计算字段识别率"""
        if self.total_fields == 0:
            return 0.0
        return self.recognized_fields / self.total_fields
    
    def get_fields_by_semantic_type(self, semantic_type: SemanticFieldType) -> List[FormField]:
        """根据语义类型获取字段"""
        return [f for f in self.fields if f.semantic_type == semantic_type]
    
    def get_required_fields(self) -> List[FormField]:
        """获取所有必填字段"""
        return [f for f in self.fields if f.required]
    
    def get_unrecognized_fields(self) -> List[FormField]:
        """获取未识别的字段"""
        return [f for f in self.fields if f.semantic_type == SemanticFieldType.UNKNOWN]


@dataclass
class FieldMapping:
    """字段映射规则"""
    semantic_type: SemanticFieldType
    keywords: List[str]  # 用于匹配的关键词
    patterns: List[str]  # 正则表达式模式
    priority: int = 0  # 优先级，用于处理冲突


# 预定义的字段映射规则
FIELD_MAPPINGS = [
    # 姓名
    FieldMapping(SemanticFieldType.FIRST_NAME, 
                ["first name", "fname", "given name", "名"], 
                [r"first.*name", r"f_name"], 10),
    FieldMapping(SemanticFieldType.LAST_NAME, 
                ["last name", "lname", "surname", "family name", "姓"], 
                [r"last.*name", r"l_name"], 10),
    FieldMapping(SemanticFieldType.FULL_NAME, 
                ["full name", "name", "your name", "姓名"], 
                [r"full.*name", r"^name$"], 9),
    
    # 联系方式
    FieldMapping(SemanticFieldType.EMAIL, 
                ["email", "e-mail", "email address", "邮箱"], 
                [r"e.*mail"], 10),
    FieldMapping(SemanticFieldType.PHONE, 
                ["phone", "mobile", "cell", "telephone", "电话"], 
                [r"phone", r"mobile", r"cell"], 10),
    
    # 工作相关
    FieldMapping(SemanticFieldType.CURRENT_COMPANY, 
                ["current company", "employer", "organization", "当前公司"], 
                [r"current.*company", r"employer"], 8),
    FieldMapping(SemanticFieldType.CURRENT_TITLE, 
                ["current title", "job title", "position", "role", "职位"], 
                [r"title", r"position"], 8),
    
    # 文件上传
    FieldMapping(SemanticFieldType.RESUME, 
                ["resume", "cv", "curriculum vitae", "简历"], 
                [r"resume", r"cv"], 10),
    FieldMapping(SemanticFieldType.COVER_LETTER, 
                ["cover letter", "求职信"], 
                [r"cover.*letter"], 9),
    
    # 链接
    FieldMapping(SemanticFieldType.LINKEDIN_URL, 
                ["linkedin", "linkedin profile", "linkedin url"], 
                [r"linkedin"], 8),
    FieldMapping(SemanticFieldType.GITHUB_URL, 
                ["github", "github profile"], 
                [r"github"], 8),
    
    # 工作授权
    FieldMapping(SemanticFieldType.WORK_AUTHORIZATION, 
                ["work authorization", "authorized to work", "visa status"], 
                [r"work.*auth", r"visa.*status"], 9),
    FieldMapping(SemanticFieldType.REQUIRE_SPONSORSHIP, 
                ["sponsorship", "require sponsorship", "visa sponsorship"], 
                [r"sponsor"], 9),
]
