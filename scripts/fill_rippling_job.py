"""
Rippling 职位申请表自动填充脚本
使用 Playwright 自动化填充职位申请表单
"""
import logging
import asyncio
from typing import Dict, Any, List
from playwright.async_api import async_playwright, Page, Browser
from pathlib import Path
import json
import sys
import yaml
import os

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

from form_filler.services.page_analyzer import PageAnalyzer
from form_filler.services.gpt_service import GPTService
from form_filler.services.smart_form_filler import SmartFormFiller
from form_filler.utils.dom_extractor import DOMExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试数据
TEST_DATA = {
    # 基本信息
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1 (555) 123-4567",
    
    # 地址信息
    "address": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "zipcode": "94105",
    "country": "United States",
    
    # 工作信息
    "linkedin": "https://www.linkedin.com/in/johndoe",
    "portfolio": "https://johndoe.com",
    "github": "https://github.com/johndoe",
    
    # 教育背景
    "university": "Stanford University",
    "degree": "Bachelor of Science",
    "major": "Computer Science",
    "graduation_year": "2020",
    "gpa": "3.8",
    
    # 工作经验
    "current_company": "Tech Corp",
    "current_title": "Senior Software Engineer",
    "years_experience": "5",
    
    # 技能
    "skills": ["Python", "JavaScript", "React", "Node.js", "AWS"],
    
    # 其他常见字段
    "salary_expectation": "150000",
    "work_authorization": "Yes",
    "require_sponsorship": "No",
    "start_date": "2 weeks",
    "referral": "LinkedIn",
    "cover_letter": "I am excited to apply for this position at Rippling. With my strong background in software engineering and passion for building scalable systems, I believe I would be a great fit for your team.",
    
    # 多样性信息（通常是可选的）
    "gender": "Prefer not to say",
    "race": "Prefer not to say",
    "veteran_status": "I am not a veteran"
}


class RipplingJobFiller:
    def __init__(self, headless: bool = False, config_path: str = None, use_gpt: bool = True):
        self.headless = headless
        self.browser: Browser = None
        self.page: Page = None
        self.config_path = config_path
        self.data = self.load_config() if config_path else TEST_DATA
        self.use_gpt = use_gpt
        self.smart_filler = SmartFormFiller() if use_gpt else None
        self.resume_data = self.load_resume_data() if config_path else None
        
    async def setup(self):
        """初始化浏览器和页面"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
    def load_config(self) -> Dict[str, Any]:
        """从YAML文件加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 将嵌套的配置展平为扁平的字典
            data = {
                # 基本信息
                "first_name": config['basic_info']['first_name'],
                "last_name": config['basic_info']['last_name'],
                "email": config['basic_info']['email'],
                "phone": config['basic_info']['phone'],
                
                # 地址信息
                "address": config['location']['address'],
                "city": config['location']['city'],
                "state": config['location']['state'],
                "zipcode": config['location']['zipcode'],
                "country": config['location']['country'],
                
                # 专业链接
                "linkedin": config['professional']['linkedin'],
                "portfolio": config['professional']['portfolio'],
                "github": config['professional']['github'],
                
                # 教育背景
                "university": config['education']['university'],
                "degree": config['education']['degree'],
                "major": config['education']['major'],
                "graduation_year": config['education']['graduation_year'],
                "gpa": config['education']['gpa'],
                
                # 工作经验
                "current_company": config['work']['current_company'],
                "current_title": config['work']['current_title'],
                "years_experience": config['work']['years_experience'],
                
                # 技能 (optional, with fallback)
                "skills": config.get('skills', []),
                
                # 申请详情
                "salary_expectation": config['application']['salary_expectation'],
                "work_authorization": config['application']['work_authorization'],
                "require_sponsorship": config['application']['require_sponsorship'],
                "start_date": config['application']['start_date'],
                "referral": config['application']['referral'],
                
                # 求职信 (optional, generate a default one)
                "cover_letter": config.get('cover_letter', f"I am excited to apply for this position. With my background in {config['education']['major']} from {config['education']['university']}, I believe I would be a great fit for your team."),
                
                # 多样性信息
                "gender": config['diversity']['gender'],
                "race": config['diversity']['race'],
                "veteran_status": config['diversity']['veteran_status'],
                "disability_status": config['diversity'].get('disability_status', 'Prefer not to say'),
                
                # 简历路径
                "resume_path": config['resume']['file_path']
            }
            
            logger.info(f"成功加载配置文件: {self.config_path}")
            return data
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.info("使用默认测试数据")
            return TEST_DATA
    
    def load_resume_data(self) -> Dict[str, Any]:
        """加载简历JSON数据"""
        try:
            resume_path = Path("data/sde_resume.json")
            if resume_path.exists():
                with open(resume_path, 'r', encoding='utf-8') as f:
                    resume_data = json.load(f)
                logger.info(f"成功加载简历数据: {resume_path}")
                return resume_data
            else:
                logger.warning(f"简历文件不存在: {resume_path}")
                return {}
        except Exception as e:
            logger.error(f"加载简历数据失败: {e}")
            return {}
        
    async def goto_url(self, url: str):
        """访问目标URL"""
        logger.info(f"访问页面: {url}")
        try:
            logger.debug("尝试使用 networkidle 策略加载页面...")
            await self.page.goto(url, wait_until="networkidle", timeout=60000)
            logger.info("✓ 页面加载成功 (networkidle)")
        except Exception as e:
            if "Timeout" in str(e):
                logger.warning("网络空闲超时，尝试等待DOM加载完成...")
                try:
                    await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    logger.info("✓ 页面加载成功 (domcontentloaded)")
                    logger.debug("等待5秒确保页面渲染完成...")
                    await self.page.wait_for_timeout(5000)
                except Exception as e2:
                    logger.error(f"页面加载失败: {e2}")
                    raise
            else:
                logger.error(f"页面加载出错: {e}")
                raise
                
    async def fill_text_field(self, selector: str, value: str, field_name: str = ""):
        """填充文本字段"""
        try:
            # 检查元素是否存在
            element = await self.page.query_selector(selector)
            if not element:
                logger.debug(f"字段{field_name}不存在 ({selector})")
                return False
            
            # 等待元素出现
            await self.page.wait_for_selector(selector, timeout=2000)
            
            # 清空并填充
            await self.page.fill(selector, "")
            await self.page.fill(selector, value)
            
            logger.info(f"✓ 填充{field_name}: {value}")
            return True
        except Exception as e:
            if "Timeout" in str(e):
                logger.debug(f"字段{field_name}可能不存在 ({selector})")
            else:
                logger.warning(f"✗ 填充{field_name}失败: {str(e)[:100]}")
            return False
            
    async def select_dropdown(self, selector: str, value: str, field_name: str = ""):
        """选择下拉菜单"""
        try:
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.select_option(selector, value)
            logger.info(f"✓ 选择{field_name}: {value}")
            return True
        except Exception as e:
            logger.warning(f"✗ 无法选择{field_name} ({selector}): {e}")
            return False
            
    async def click_checkbox(self, selector: str, field_name: str = ""):
        """点击复选框"""
        try:
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.click(selector)
            logger.info(f"✓ 勾选{field_name}")
            return True
        except Exception as e:
            logger.warning(f"✗ 无法勾选{field_name} ({selector}): {e}")
            return False
            
    async def fill_rippling_form(self):
        """填充 Rippling 申请表"""
        logger.info("开始填充表单...")
        
        # 首先分析当前表单的字段
        field_info = await self.analyze_form_fields()
        
        if self.use_gpt and self.smart_filler and field_info:
            # 使用GPT智能填充
            logger.info("🤖 使用GPT智能分析和填充表单...")
            await self.smart_fill_form(field_info)
        else:
            # 使用传统规则填充
            logger.info("使用传统规则填充表单...")
            await self.rule_based_fill()
        
        # LinkedIn 和 Portfolio
        await self.fill_text_field('input[name*="linkedin"], input[placeholder*="LinkedIn"]', 
                                  self.data["linkedin"], "LinkedIn")
        await self.fill_text_field('input[name*="portfolio"], input[name*="website"], input[placeholder*="Portfolio"]', 
                                  self.data["portfolio"], "作品集")
        
        # 地址信息
        await self.fill_text_field('input[name*="address"], input[placeholder*="Address"]', 
                                  self.data["address"], "地址")
        await self.fill_text_field('input[name*="city"], input[placeholder*="City"]', 
                                  self.data["city"], "城市")
        
        # 工作授权
        work_auth_selectors = [
            'input[name*="authorization"][value*="yes" i], input[name*="authorized"][value*="yes" i]',
            'label:has-text("authorized to work"):has(input[type="radio"])'
        ]
        for selector in work_auth_selectors:
            try:
                await self.page.click(selector)
                logger.info("✓ 选择工作授权状态")
                break
            except:
                continue
        
        # 简历上传（如果有）
        await self.handle_resume_upload()
            
        # 等待一下让表单更新
        await self.page.wait_for_timeout(2000)
        
        # 处理下拉字段
        await self.handle_select_fields()
        
        # 查找并填充其他可能的字段
        await self.fill_additional_fields()
        
    async def fill_additional_fields(self):
        """填充其他可能出现的字段"""
        # 教育信息
        await self.fill_text_field('input[name*="school"], input[name*="university"], input[placeholder*="School"]', 
                                  self.data["university"], "学校")
        await self.fill_text_field('input[name*="degree"], input[placeholder*="Degree"]', 
                                  self.data["degree"], "学位")
        await self.fill_text_field('input[name*="major"], input[placeholder*="Major"]', 
                                  self.data["major"], "专业")
        
        # 工作经验
        await self.fill_text_field('input[name*="company"], input[placeholder*="Company"]', 
                                  self.data["current_company"], "当前公司")
        await self.fill_text_field('input[name*="title"], input[name*="position"], input[placeholder*="Title"]', 
                                  self.data["current_title"], "职位")
        
        # 薪资期望
        await self.fill_text_field('input[name*="salary"], input[placeholder*="Salary"]', 
                                  self.data["salary_expectation"], "薪资期望")
        
        # Cover Letter / 附加信息
        await self.fill_text_field('textarea[name*="cover"], textarea[name*="message"], textarea[placeholder*="Cover"]', 
                                  self.data["cover_letter"], "求职信")
                                  
    async def take_screenshot(self, filename: str = "rippling_form.png"):
        """截图保存"""
        await self.page.screenshot(path=filename, full_page=True)
        logger.info(f"截图已保存: {filename}")
        
    async def analyze_page(self):
        """分析当前页面"""
        try:
            # 获取页面标题和URL
            title = await self.page.title()
            url = self.page.url
            
            logger.info(f"\n===== 页面分析 =====")
            logger.info(f"页面标题: {title}")
            logger.info(f"当前URL: {url}")
            
            # 检查是否有表单
            forms = await self.page.query_selector_all('form')
            logger.info(f"\n找到 {len(forms)} 个表单")
            
            if len(forms) > 0:
                logger.info("✓ 页面包含表单，应该可以直接填写")
                # 查找所有表单字段
                form_fields = await self.page.query_selector_all('input, select, textarea')
                logger.info(f"找到 {len(form_fields)} 个表单字段")
                
                # 分析每个字段
                for i, field in enumerate(form_fields[:10]):  # 只显示前10个
                    field_type = await field.get_attribute('type') or 'text'
                    field_name = await field.get_attribute('name') or ''
                    field_placeholder = await field.get_attribute('placeholder') or ''
                    
                    logger.debug(f"  字段{i+1}: type={field_type}, name={field_name}, placeholder={field_placeholder}")
            else:
                logger.warning("✗ 页面没有表单，需要查找CTA按钮")
                await self.find_cta_buttons()
                
        except Exception as e:
            logger.error(f"分析页面时出错: {e}")
            
    async def analyze_form_fields(self):
        """分析表单中的所有字段"""
        logger.info("\n分析表单字段...")
        try:
            # 获取所有输入字段
            fields = await self.page.query_selector_all('input:not([type="hidden"]), select, textarea')
            logger.info(f"找到 {len(fields)} 个可见字段")
            
            field_info = []
            for field in fields:
                # 获取元素的标签名
                tag_name = await field.evaluate("el => el.tagName.toLowerCase()")
                
                # 根据标签名确定字段类型
                if tag_name == 'select':
                    field_type = 'select'
                elif tag_name == 'textarea':
                    field_type = 'textarea'
                else:
                    # 对于 input 元素，获取 type 属性
                    field_type = await field.get_attribute('type') or 'text'
                
                field_name = await field.get_attribute('name') or ''
                field_id = await field.get_attribute('id') or ''
                field_placeholder = await field.get_attribute('placeholder') or ''
                field_label = await self.get_field_label(field)
                
                info = {
                    'type': field_type,
                    'name': field_name,
                    'id': field_id,
                    'placeholder': field_placeholder,
                    'label': field_label
                }
                field_info.append(info)
                
                # 构建选择器
                if field_id:
                    info['selector'] = f"#{field_id}"
                elif field_name:
                    info['selector'] = f"[name='{field_name}']"
                else:
                    info['selector'] = None
                
                # 输出详细信息
                logger.debug(f"  字段: type={field_type}, name={field_name}, id={field_id}, "
                           f"placeholder={field_placeholder}, label={field_label}")
            
            # 分类字段
            text_fields = [f for f in field_info if f['type'] in ['text', 'email', 'tel', 'url']]
            file_fields = [f for f in field_info if f['type'].lower() == 'file']
            select_fields = [f for f in field_info if f['type'] == 'select']
            textarea_fields = [f for f in field_info if f['type'] == 'textarea']
            
            logger.info(f"\n字段统计:")
            logger.info(f"  - 文本字段: {len(text_fields)}")
            logger.info(f"  - 文件上传: {len(file_fields)}")
            logger.info(f"  - 下拉选择: {len(select_fields)}")
            logger.info(f"  - 文本域: {len(textarea_fields)}")
            
            # 显示识别到的字段详情
            if file_fields:
                logger.info("\n文件上传字段:")
                for f in file_fields:
                    logger.info(f"  - {f.get('name') or f.get('id') or 'unnamed'}")
            
            if select_fields:
                logger.info("\n下拉选择字段:")
                for f in select_fields:
                    logger.info(f"  - {f.get('name') or f.get('id') or 'unnamed'}: {f.get('label')}")
            
            return field_info
            
        except Exception as e:
            logger.error(f"分析表单字段时出错: {e}")
            return []
    
    async def smart_fill_form(self, field_info: List[Dict[str, Any]]):
        """使用GPT智能填充表单"""
        try:
            # 获取字段映射
            field_mappings = self.smart_filler.analyze_and_match_fields(
                form_fields=field_info,
                personal_data=self.data,
                resume_data=self.resume_data or {}
            )
            
            logger.info(f"\n🎯 GPT分析结果: 找到 {len(field_mappings)} 个字段映射")
            
            # 填充每个字段
            for selector, mapping in field_mappings.items():
                value = mapping.get("value", "")
                field_type = mapping.get("field_type", "text")
                confidence = mapping.get("confidence", 0)
                reasoning = mapping.get("reasoning", "")
                
                logger.info(f"\n填充字段: {selector}")
                logger.debug(f"  - 值: {value[:50]}..." if len(value) > 50 else f"  - 值: {value}")
                logger.debug(f"  - 置信度: {confidence}")
                logger.debug(f"  - 理由: {reasoning}")
                
                if field_type in ["text", "email", "tel", "url", "textarea"]:
                    await self.fill_text_field(selector, value, f"GPT智能填充")
                elif field_type == "select":
                    await self.select_dropdown(selector, value, f"GPT智能选择")
                elif field_type in ["checkbox", "radio"]:
                    if value.lower() in ["yes", "true", "1", "on"]:
                        await self.click_checkbox(selector, f"GPT智能勾选")
                elif field_type == "file":
                    if value and Path(value).exists():
                        logger.info(f"检测到文件上传字段: {value}")
                        # TODO: 实现文件上传
                        
            # 等待表单更新
            await self.page.wait_for_timeout(2000)
            
        except Exception as e:
            logger.error(f"GPT智能填充失败: {e}")
            logger.info("回退到传统规则填充...")
            await self.rule_based_fill()
    
    async def rule_based_fill(self):
        """传统基于规则的填充"""
        # 基本信息
        await self.fill_text_field('input[name="firstName"], input[id*="firstName"], input[placeholder*="First"]', 
                                  self.data["first_name"], "名字")
        await self.fill_text_field('input[name="lastName"], input[id*="lastName"], input[placeholder*="Last"]', 
                                  self.data["last_name"], "姓氏")
        await self.fill_text_field('input[name="email"], input[type="email"], input[placeholder*="Email"]', 
                                  self.data["email"], "邮箱")
        await self.fill_text_field('input[name="phone"], input[type="tel"], input[placeholder*="Phone"]', 
                                  self.data["phone"], "电话")
    
    async def get_field_label(self, field):
        """获取字段的标签"""
        try:
            # 尝试通过for属性找到label
            field_id = await field.get_attribute('id')
            if field_id:
                label = await self.page.query_selector(f'label[for="{field_id}"]')
                if label:
                    return await label.text_content()
            
            # 尝试找到父级label
            parent = await field.evaluate("el => el.closest('label')")
            if parent:
                return await self.page.evaluate("el => el.textContent", parent)
            
            return ''
        except:
            return ''
    
    async def handle_resume_upload(self):
        """处理简历上传"""
        try:
            # 先查找所有文件输入字段
            all_file_inputs = await self.page.query_selector_all('input[type="file"], input[type="File"]')
            logger.info(f"\n找到 {len(all_file_inputs)} 个文件上传字段")
            
            for i, file_input in enumerate(all_file_inputs):
                try:
                    # 检查是否可见
                    is_visible = await file_input.is_visible()
                    
                    # 获取相关属性
                    name = await file_input.get_attribute('name') or ''
                    field_id = await file_input.get_attribute('id') or ''
                    accept = await file_input.get_attribute('accept') or ''
                    
                    logger.debug(f"文件字段 {i+1}: visible={is_visible}, name={name}, id={field_id}, accept={accept}")
                    
                    # 不管是否隐藏，尝试上传
                    if self.data.get("resume_path"):
                        resume_path = Path(self.data["resume_path"])
                        if resume_path.exists():
                            try:
                                # 如果是隐藏的，可能需要先点击某个按钮触发
                                if not is_visible:
                                    # 查找可能的上传按钮或标签
                                    upload_triggers = [
                                        f'label[for="{field_id}"]' if field_id else None,
                                        'button:has-text("Upload")',
                                        'button:has-text("Choose")',
                                        'button:has-text("Select")',
                                        'div:has-text("Drop your")',
                                        'div:has-text("Upload")',
                                        '[class*="upload"]'
                                    ]
                                    
                                    for trigger in upload_triggers:
                                        if trigger:
                                            try:
                                                trigger_elem = await self.page.query_selector(trigger)
                                                if trigger_elem and await trigger_elem.is_visible():
                                                    logger.info(f"点击上传触发器: {trigger}")
                                                    await trigger_elem.click()
                                                    await self.page.wait_for_timeout(500)
                                                    break
                                            except:
                                                continue
                                
                                logger.info(f"尝试上传简历到文件字段 {i+1}: {resume_path}")
                                await file_input.set_input_files(str(resume_path))
                                logger.info("✓ 简历上传成功")
                                return  # 成功上传后退出
                            except Exception as e:
                                logger.warning(f"上传到文件字段 {i+1} 失败: {e}")
                                continue
                        else:
                            logger.warning(f"简历文件不存在: {resume_path}")
                            return
                    else:
                        logger.info("未配置简历路径，跳过上传")
                        return
                        
                except Exception as e:
                    logger.debug(f"处理文件字段 {i+1} 时出错: {e}")
                    continue
                    
            logger.warning("未能成功上传简历到任何文件字段")
                    
        except Exception as e:
            logger.error(f"处理简历上传时出错: {e}")
    
    async def handle_select_fields(self):
        """处理下拉选择字段"""
        try:
            selects = await self.page.query_selector_all('select')
            logger.info(f"\n找到 {len(selects)} 个下拉字段")
            
            for select in selects:
                try:
                    name = await select.get_attribute('name') or ''
                    field_id = await select.get_attribute('id') or ''
                    label = await self.get_field_label(select)
                    
                    logger.info(f"\n下拉字段: name={name}, id={field_id}, label={label}")
                    
                    # 获取所有选项
                    options = await select.query_selector_all('option')
                    option_values = []
                    for option in options:
                        value = await option.get_attribute('value')
                        text = await option.text_content()
                        if value:
                            option_values.append({"value": value, "text": text})
                    
                    logger.debug(f"  可选项: {option_values[:5]}...")  # 只显示前5个
                    
                    # 根据字段名智能选择
                    if "country" in name.lower() or "country" in field_id.lower():
                        await self.select_dropdown(f"#{field_id}" if field_id else f"[name='{name}']", 
                                                 self.data.get("country", "United States"), "国家")
                    elif "state" in name.lower() or "state" in field_id.lower():
                        await self.select_dropdown(f"#{field_id}" if field_id else f"[name='{name}']", 
                                                 self.data.get("state", "CA"), "州")
                    elif "year" in name.lower() or "graduation" in name.lower():
                        await self.select_dropdown(f"#{field_id}" if field_id else f"[name='{name}']", 
                                                 self.data.get("graduation_year", ""), "毕业年份")
                    
                except Exception as e:
                    logger.warning(f"处理下拉字段时出错: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"处理下拉字段时出错: {e}")
            
    async def find_cta_buttons(self):
        """查找可能的CTA按钮"""
        logger.info("\n查找CTA按钮...")
        try:
            # 查找所有可能的申请按钮
            cta_selectors = [
                'button:has-text("Apply")',
                'button:has-text("apply")',
                'button:has-text("申请")',
                'a:has-text("Apply")',
                'a:has-text("apply")',
                'button[class*="apply"]',
                'a[href*="apply"]',
                'button[data-test*="apply"]',
                '[role="button"]:has-text("Apply")',
                '.apply-button',
                '#apply-button'
            ]
            
            found_buttons = []
            for selector in cta_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for elem in elements:
                        text = await elem.text_content()
                        if text:
                            found_buttons.append({
                                'selector': selector,
                                'text': text.strip(),
                                'element': elem
                            })
                            logger.info(f"  找到按钮: {text.strip()} ({selector})")
                except:
                    continue
            
            if found_buttons:
                logger.info(f"\n共找到 {len(found_buttons)} 个可能的CTA按钮")
                # 点击第一个找到的按钮
                best_button = found_buttons[0]
                logger.info(f"\n准备点击按钮: {best_button['text']}")
                await best_button['element'].click()
                logger.info("✓ 已点击CTA按钮")
                
                # 等待页面加载
                await self.page.wait_for_timeout(3000)
                logger.info("等待新页面加载...")
                
                # 重新分析页面
                await self.analyze_page()
            else:
                logger.warning("✗ 未找到任何CTA按钮")
                
        except Exception as e:
            logger.error(f"查找CTA按钮时出错: {e}")
            
    async def submit_form(self):
        """提交表单"""
        # 查找提交按钮
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'input[type="submit"]',
            'button.submit-button'
        ]
        
        for selector in submit_selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=3000)
                logger.info(f"找到提交按钮: {selector}")
                
                # 这里只是演示，实际不提交
                logger.info("⚠️  找到提交按钮但不会真的提交（测试模式）")
                return True
            except:
                continue
                
        logger.warning("未找到提交按钮")
        return False
        
    async def run(self, url: str):
        """运行自动填充流程"""
        try:
            await self.setup()
            await self.goto_url(url)
            
            # 等待页面加载
            logger.debug("等待页面初始渲染...")
            await self.page.wait_for_timeout(3000)
            
            # 分析页面
            await self.analyze_page()
            
            # 检查是否有表单
            forms = await self.page.query_selector_all('form')
            if len(forms) > 0:
                logger.info("\n开始填充表单流程...")
                # 填充表单
                await self.fill_rippling_form()
                
                # 截图
                await self.take_screenshot("rippling_filled_form.png")
                
                # 查找提交按钮（但不提交）
                await self.submit_form()
            else:
                logger.warning("\n当前页面没有表单，可能需要先点击Apply按钮")
                logger.info("请检查页面截图以确认页面状态")
                await self.take_screenshot("rippling_no_form_page.png")
            
            logger.info("\n✅ 流程完成！")
            
            # 保持浏览器打开一段时间供查看
            if not self.headless:
                logger.info("浏览器将保持打开30秒供您查看...")
                await self.page.wait_for_timeout(30000)
                
        except Exception as e:
            logger.error(f"运行过程中出错: {e}")
            await self.take_screenshot("error_screenshot.png")
            raise
        finally:
            if self.browser:
                await self.browser.close()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Rippling职位申请表自动填充')
    parser.add_argument('--url', default="https://ats.rippling.com/rippling/jobs/203e0cac-0e30-4603-8087-f764e8c3f85c?jobSite=LinkedIn",
                        help='职位申请页面URL')
    parser.add_argument('--config', default="config/personal_info.yaml",
                        help='个人信息配置文件路径')
    parser.add_argument('--headless', action='store_true',
                        help='是否使用无头模式')
    parser.add_argument('--no-gpt', action='store_true',
                        help='禁用GPT智能填充')
    
    args = parser.parse_args()
    
    # 检查配置文件是否存在
    config_path = Path(args.config)
    use_gpt = not args.no_gpt
    
    if use_gpt:
        # 检查OpenAI API key
        if not os.getenv('OPENAI_API_KEY'):
            logger.warning("⚠️  未找到OpenAI API key，将使用传统规则填充")
            logger.info("请设置环境变量: export OPENAI_API_KEY='your-api-key'")
            use_gpt = False
        else:
            logger.info("✅ 已启用GPT智能填充")
    else:
        logger.info("使用传统规则填充模式")
    
    if config_path.exists():
        logger.info(f"使用配置文件: {config_path}")
        filler = RipplingJobFiller(headless=args.headless, config_path=str(config_path), use_gpt=use_gpt)
    else:
        logger.warning(f"配置文件不存在: {config_path}")
        logger.info("使用默认测诖数据")
        filler = RipplingJobFiller(headless=args.headless, use_gpt=use_gpt)
    
    # 运行填充
    await filler.run(args.url)


if __name__ == "__main__":
    asyncio.run(main())
