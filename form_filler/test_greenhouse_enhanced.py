#!/usr/bin/env python3
"""
测试增强版表单填充器在Greenhouse平台上的表现
基于新的架构和数据管理器
"""
import asyncio
import logging
from pathlib import Path
import os
import sys
import time

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from form_filler.services.pro_form_filler import ProFormFiller
from form_filler.services.gpt_service import GPTService
from form_filler.services.enhanced_data_manager import EnhancedDataManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_url_accessibility(url: str) -> bool:
    """检查URL是否可访问"""
    try:
        # 尝试使用 aiohttp
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return response.status == 200
        except ImportError:
            # 如果没有 aiohttp，使用 urllib 在线程池中执行
            import urllib.request
            import urllib.error
            import concurrent.futures
            
            def _check_url_sync(url):
                try:
                    with urllib.request.urlopen(url, timeout=10) as response:
                        return response.status == 200
                except urllib.error.URLError:
                    return False
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, _check_url_sync, url)
                return result
    except Exception as e:
        logger.warning(f"URL检查失败: {e}")
        return False


async def test_greenhouse_form():
    """测试Greenhouse表单填写"""
    
    # 测试URL
    test_url = "https://boards.greenhouse.io/embed/job_app?token=6651908&gh_src=be8ebc4b1"
    
    logger.info(f"开始测试 Greenhouse 表单填写: {test_url}")
    
    # 检查网络连接
    logger.info("检查网络连接...")
    if not await check_url_accessibility(test_url):
        logger.warning("无法访问目标URL，但将继续尝试...")
    else:
        logger.info("网络连接正常")
    
    # 初始化Playwright
    async with async_playwright() as p:
        # 启动浏览器（设置为非无头模式以便观察）
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=site-per-process',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ]
        )
        
        # 创建浏览器上下文
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        # 创建页面
        page = await context.new_page()
        
        # 设置额外的反检测措施
        await page.add_init_script("""
            // 覆盖 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 覆盖 plugins 长度
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 覆盖 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        try:
            # 导航到页面
            logger.info("导航到Greenhouse页面...")
            # 使用简单高效的页面加载策略
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"尝试加载页面 (第{attempt + 1}/{max_retries}次)...")
                    
                    # 等待 DOM 内容加载完成就足够了
                    await page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
                    logger.info("页面 DOM 内容已加载完成")
                    
                    # 简单等待一下让 JavaScript 初始化
                    await asyncio.sleep(2)
                    
                    # 如果成功加载，跳出重试循环
                    break
                    
                except Exception as e:
                    logger.error(f"页面加载失败 (第{attempt + 1}次): {e}")
                    
                    if attempt < max_retries - 1:
                        logger.info("等待3秒后重试...")
                        await asyncio.sleep(3)
                    else:
                        # 最后一次尝试使用最基本的加载策略
                        logger.info("使用最基本的加载策略进行最后尝试...")
                        try:
                            await page.goto(test_url, wait_until='load', timeout=60000)
                            logger.info("使用基本策略加载成功")
                            await asyncio.sleep(2)
                        except Exception as final_error:
                            logger.error(f"所有加载策略都失败了: {final_error}")
                            raise
            
            # 截图记录初始状态
            await page.screenshot(path='screenshots/greenhouse_initial.png')
            logger.info("已保存初始页面截图")
            
            # 初始化服务
            logger.info("初始化表单填充服务...")
            gpt_service = GPTService()
            form_filler = ProFormFiller(gpt_service)
            
            # 检查数据管理器
            data_manager = form_filler.data_manager
            logger.info("检查数据完整性...")
            
            # 验证必需字段
            required_fields = [
                'first_name', 'last_name', 'email', 'phone',
                'linkedin', 'resume'
            ]
            
            validation_result = data_manager.validate_required_fields(required_fields)
            for field, available in validation_result.items():
                if not available:
                    logger.warning(f"缺少必需字段: {field}")
            
            # 填写表单
            logger.info("开始填写表单...")
            result = await form_filler.fill_form(page)
            
            # 输出结果
            logger.info("\n" + "="*80)
            logger.info("表单填写结果:")
            logger.info("="*80)
            logger.info(f"成功: {result['success']}")
            logger.info(f"填写统计: {result['stats']}")
            
            if result['filled_fields']:
                logger.info("\n已填写的字段:")
                for selector, field_info in result['filled_fields'].items():
                    logger.info(f"  - {selector}: {field_info['value']} (类型: {field_info['type']})")
            
            if result['errors']:
                logger.error("\n遇到的错误:")
                for error in result['errors']:
                    if isinstance(error, dict):
                        logger.error(f"  - {error.get('selector', 'unknown')}: {error.get('error', 'unknown error')}")
                    else:
                        logger.error(f"  - {error}")
            
            # 等待用户交互
            await asyncio.sleep(3)
            
            # 保存填写后的截图
            await page.screenshot(path='screenshots/greenhouse_filled.png')
            logger.info("已保存填写后的截图")
            
            # 如果需要，可以尝试提交（这里设置为False以避免实际提交）
            submit_form = False
            if submit_form and result['success']:
                logger.info("准备提交表单...")
                submit_button = await page.query_selector('button[type="submit"]')
                if submit_button:
                    logger.info("找到提交按钮，准备提交...")
                    # await submit_button.click()
                    logger.info("（测试模式，跳过实际提交）")
                else:
                    logger.warning("未找到提交按钮")
            
            # 等待一段时间以便观察
            logger.info("\n测试完成！浏览器将在10秒后关闭...")
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"测试过程中出错: {e}", exc_info=True)
            await page.screenshot(path='screenshots/greenhouse_error.png')
        
        finally:
            await browser.close()


async def check_data_availability():
    """检查数据文件是否存在"""
    logger.info("检查数据文件...")
    
    data_manager = EnhancedDataManager()
    
    # 检查个人信息文件
    if Path(data_manager.personal_data_path).exists():
        logger.info(f"✓ 找到个人信息文件: {data_manager.personal_data_path}")
        
        # 显示部分数据（隐藏敏感信息）
        basic_info = data_manager.personal_data.get('basic_info', {})
        if basic_info:
            logger.info(f"  - 姓名: {basic_info.get('first_name', 'N/A')} {basic_info.get('last_name', 'N/A')}")
            logger.info(f"  - Email: {'*' * 5 + basic_info.get('email', '')[-10:] if basic_info.get('email') else 'N/A'}")
    else:
        logger.warning(f"✗ 未找到个人信息文件: {data_manager.personal_data_path}")
        logger.warning("  请创建 personal_info.yaml 文件并填写您的信息")
    
    # 检查简历文件
    if Path(data_manager.resume_data_path).exists():
        logger.info(f"✓ 找到简历数据文件: {data_manager.resume_data_path}")
    else:
        logger.warning(f"✗ 未找到简历数据文件: {data_manager.resume_data_path}")
    
    # 检查简历文件路径
    resume_info = data_manager.personal_data.get('files', {}).get('resume', {})
    resume_path = resume_info.get('file_path', '')
    if resume_path and Path(resume_path).exists():
        logger.info(f"✓ 找到简历文件: {resume_path}")
    else:
        logger.warning(f"✗ 简历文件不存在或未配置: {resume_path}")
        logger.warning("  请在 personal_info.yaml 中配置正确的简历文件路径")


def create_sample_personal_info():
    """创建示例个人信息文件"""
    sample_data = """# 个人信息配置文件
# 请根据您的实际情况填写

basic_info:
  first_name: "Your"
  last_name: "Name"
  full_name: "Your Full Name"
  email: "your.email@example.com"
  phone: "1234567890"  # 10位数字，将自动格式化
  linkedin: "https://www.linkedin.com/in/yourprofile"
  github: "https://github.com/yourusername"
  portfolio: "https://yourportfolio.com"
  website: "https://yourwebsite.com"

location:
  country: "United States"
  state: "California"
  city: "San Francisco"
  address: "Your Address"
  zip_code: "94105"

education:
  university: "Your University"
  degree: "Bachelor's Degree"  # Bachelor's/Master's/PhD
  major: "Computer Science"
  graduation_year: "2020"
  graduation_month: "May"
  gpa: "3.8"

work_info:
  current_company: "Current Company"
  current_title: "Software Engineer"
  years_experience: "3"
  most_recent_employer: "Previous Company"
  willing_to_relocate: true
  remote_work_preference: true

legal_status:
  work_authorization: "Yes"  # Yes/No
  require_sponsorship: "No"  # Yes/No
  visa_status: "Authorized to work"

preferences:
  salary_expectation: "120000"  # 年薪期望
  start_date: "Immediately"
  job_type: "Full-time"
  remote_preference: "Remote or Hybrid"

files:
  resume:
    file_path: "/path/to/your/resume.pdf"  # 请更新为实际路径
    file_name: "resume.pdf"
  cover_letter:
    file_path: "/path/to/your/cover_letter.pdf"
    file_name: "cover_letter.pdf"
"""
    
    if not Path("config/personal_info.yaml").exists():
        with open("config/personal_info.yaml", "w", encoding="utf-8") as f:
            f.write(sample_data)
        logger.info("已创建示例 personal_info.yaml 文件，请根据您的情况修改")
    else:
        logger.info("personal_info.yaml 文件已存在")


if __name__ == "__main__":
    logger.info("Greenhouse 表单填写测试")
    logger.info("="*80)
    
    # 创建必要的目录
    Path("screenshots").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # 创建示例配置文件（如果不存在）
    create_sample_personal_info()
    
    # 检查数据可用性
    asyncio.run(check_data_availability())
    
    # 询问是否继续
    response = input("\n是否继续测试？(y/n): ")
    if response.lower() in ['y', 'yes']:
        # 运行测试
        asyncio.run(test_greenhouse_form())
    else:
        logger.info("测试已取消")
