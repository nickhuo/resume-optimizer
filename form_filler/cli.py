"""
Form Filler CLI工具
"""
import click
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

from .services.gpt_service import GPTService
from .services.page_analyzer import PageAnalyzer
from .utils.dom_extractor import DOMExtractor
from .utils.error_reporter import ErrorReporter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Form Filler 命令行工具"""
    pass


@cli.command()
@click.argument('url')
@click.option('--screenshot', is_flag=True, help='保存页面截图')
@click.option('--timeout', default=60000, help='页面加载超时时间（毫秒），默认60秒')
def analyze(url, screenshot, timeout):
    """分析指定URL的页面类型和CTA按钮"""
    click.echo(f"分析页面: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.set_default_timeout(timeout)
        page = context.new_page()
        
        try:
            # 访问页面
            click.echo("正在加载页面...")
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout)
            except Exception as e:
                if "Timeout" in str(e):
                    click.echo("网络空闲超时，尝试等待DOMContentLoaded...")
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                    page.wait_for_timeout(5000)
                else:
                    raise
            
            # 初始化组件
            gpt_service = GPTService()
            page_analyzer = PageAnalyzer(gpt_service)
            dom_extractor = DOMExtractor(page)
            
            # 提取页面信息
            click.echo("提取页面信息...")
            title = page.title()
            content = dom_extractor.extract_page_content()
            buttons = dom_extractor.extract_buttons()
            forms = dom_extractor.extract_forms()
            
            # 输出基本信息
            click.echo(f"\n页面标题: {title}")
            click.echo(f"内容长度: {len(content)} 字符")
            click.echo(f"按钮数量: {len(buttons)}")
            click.echo(f"表单数量: {len(forms)}")
            
            # 分析页面
            click.echo("\n分析页面类型...")
            analysis_result = page_analyzer.analyze_page(
                url=url,
                title=title,
                content=content,
                buttons=buttons,
                forms=forms
            )
            
            # 输出分析结果
            click.echo(f"\n分析结果:")
            click.echo(f"- 页面类型: {analysis_result.page_type.value}")
            click.echo(f"- 置信度: {analysis_result.confidence:.2f}")
            click.echo(f"- 推理: {analysis_result.reasoning}")
            click.echo(f"- 包含Apply按钮: {analysis_result.has_apply_button}")
            click.echo(f"- GPT分析的表单数: {analysis_result.form_count}")
            click.echo(f"- 实际提取的表单数: {len(forms)}")
            
            # 输出CTA候选
            if analysis_result.cta_candidates:
                click.echo(f"\nCTA候选按钮 ({len(analysis_result.cta_candidates)}个):")
                for i, cta in enumerate(analysis_result.cta_candidates):
                    click.echo(f"  {i+1}. {cta.text}")
                    click.echo(f"     - 选择器: {cta.selector}")
                    click.echo(f"     - 置信度: {cta.confidence:.2f}")
                    click.echo(f"     - 优先级: {cta.priority_score}")
            
            # 获取推荐动作
            click.echo("\n分析推荐动作...")
            recommended_action = page_analyzer.get_recommended_action(
                url=url,
                title=title,
                content=content,
                buttons=buttons,
                forms=forms
            )
            
            # 输出推荐动作
            click.echo(f"\n推荐动作:")
            click.echo(f"- 动作类型: {page_analyzer.get_action_description(recommended_action)}")
            click.echo(f"- 置信度: {recommended_action.confidence:.2f}")
            click.echo(f"- 理由: {recommended_action.reasoning}")
            if recommended_action.target_element:
                click.echo(f"- 目标元素: {recommended_action.target_element}")
            if recommended_action.form_selector:
                click.echo(f"- 表单选择器: {recommended_action.form_selector}")
            
            # 检查是否应该继续
            should_continue = page_analyzer.should_proceed_with_action(analysis_result, recommended_action)
            
            if should_continue:
                if recommended_action.action_type.value == 'fill_form':
                    click.echo(f"\n建议: 继续填写表单")
                elif recommended_action.action_type.value == 'click_cta':
                    click.echo(f"\n建议: 继续点击CTA按钮")
                else:
                    click.echo(f"\n建议: 继续执行{page_analyzer.get_action_description(recommended_action)}")
            else:
                click.echo(f"\n建议: 不建议继续（{recommended_action.reasoning}）")
            
            # 保存截图
            if screenshot:
                screenshot_path = f"page_analysis_{Path(url).name}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                click.echo(f"\n截图已保存: {screenshot_path}")
                
        except Exception as e:
            click.echo(f"\n错误: {e}", err=True)
            
        finally:
            browser.close()


@cli.command()
@click.argument('url')
@click.option('--debug', is_flag=True, help='显示调试信息')
@click.option('--timeout', default=60000, help='页面加载超时时间（毫秒），默认60秒')
def extract_forms(url, debug, timeout):
    """提取指定URL页面的表单信息"""
    click.echo(f"提取表单: {url}")
    
    # 如果开启调试，设置日志级别
    if debug:
        logging.getLogger('form_filler.utils.dom_extractor').setLevel(logging.DEBUG)
        click.echo(f"[调试] 超时设置: {timeout}ms")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 设置默认超时
        context = browser.new_context()
        context.set_default_timeout(timeout)
        page = context.new_page()
        
        try:
            # 访问页面，尝试不同的等待策略
            click.echo("正在加载页面...")
            try:
                # 首先尝试等待networkidle
                page.goto(url, wait_until="networkidle", timeout=timeout)
            except Exception as e:
                if "Timeout" in str(e):
                    click.echo("网络空闲超时，尝试等待DOMContentLoaded...")
                    # 如果networkidle超时，退而求其次等待domcontentloaded
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                    # 额外等待一段时间让页面渲染
                    page.wait_for_timeout(5000)
                else:
                    raise
            
            # 初始化DOM提取器
            dom_extractor = DOMExtractor(page)
            
            # 提取表单
            forms = dom_extractor.extract_forms()
            
            if not forms:
                click.echo("未找到表单")
                return
            
            click.echo(f"\n找到 {len(forms)} 个表单:")
            
            for i, form in enumerate(forms):
                click.echo(f"\n{'='*60}")
                click.echo(f"表单 {i+1}:")
                click.echo(f"  - ID: {form.get('id', 'N/A')}")
                click.echo(f"  - Class: {form.get('className', 'N/A')}")
                click.echo(f"  - Action: {form.get('action', 'N/A')}")
                click.echo(f"  - Method: {form.get('method', 'N/A')}")
                click.echo(f"  - 字段数: {len(form.get('fields', []))}")
                
                fields = form.get('fields', [])
                if fields:
                    click.echo("\n  字段详情:")
                    for j, field in enumerate(fields):
                        click.echo(f"\n  [{j+1}] 字段:")
                        
                        # 基本信息
                        label = field.get('label') or field.get('aria-label') or field.get('placeholder') or field.get('name', 'Unknown')
                        click.echo(f"    标签: {label}")
                        click.echo(f"    类型: {field.get('type', 'unknown')}")
                        click.echo(f"    名称: {field.get('name', 'N/A')}")
                        click.echo(f"    ID: {field.get('id', 'N/A')}")
                        
                        # 必填状态
                        required = field.get('required')
                        aria_required = field.get('aria-required')
                        data_required = field.get('data-required')
                        
                        required_status = "必填" if (required or aria_required == 'true' or data_required) else "选填"
                        click.echo(f"    状态: {required_status}")
                        
                        if debug:
                            click.echo(f"    [调试] required={required}, aria-required='{aria_required}', data-required='{data_required}'")
                            click.echo(f"    [调试] placeholder='{field.get('placeholder')}'")
                            click.echo(f"    [调试] class='{field.get('className')}'")
                            click.echo(f"    [调试] selector='{field.get('selector')}'")
                            
                            # 验证规则
                            if field.get('pattern'):
                                click.echo(f"    [调试] pattern='{field.get('pattern')}'")
                            if field.get('minLength') and field.get('minLength') > 0:
                                click.echo(f"    [调试] minLength={field.get('minLength')}")
                            if field.get('maxLength') and field.get('maxLength') > 0:
                                click.echo(f"    [调试] maxLength={field.get('maxLength')}")
            
            # 检查验证码
            has_captcha = dom_extractor.check_for_captcha()
            if has_captcha:
                click.echo("\n⚠️  警告: 页面包含验证码")
                
        except Exception as e:
            click.echo(f"\n错误: {e}", err=True)
            
        finally:
            browser.close()


@cli.command()
def stats():
    """显示错误统计信息"""
    error_reporter = ErrorReporter()
    stats = error_reporter.get_error_statistics()
    
    click.echo("错误统计:")
    click.echo(f"- 总错误数: {stats['total_errors']}")
    click.echo(f"- 错误文件: {stats.get('errors_file', 'errors.jsonl')}")
    
    if stats['error_types']:
        click.echo("\n错误类型分布:")
        for error_type, count in stats['error_types'].items():
            click.echo(f"  - {error_type}: {count}")
    else:
        click.echo("\n暂无错误记录")


@cli.command()
@click.option('--headless/--no-headless', default=True, help='是否使用无头模式')
def interactive(headless):
    """交互式测试模式"""
    click.echo("进入交互式测试模式")
    click.echo("输入 'quit' 退出\n")
    
    # 初始化服务
    gpt_service = GPTService()
    page_analyzer = PageAnalyzer(gpt_service)
    error_reporter = ErrorReporter()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        dom_extractor = DOMExtractor(page)
        
        try:
            while True:
                url = click.prompt("\n输入URL进行分析", type=str)
                
                if url.lower() == 'quit':
                    break
                
                try:
                    click.echo(f"\n访问: {url}")
                    page.goto(url, wait_until="networkidle")
                    
                    # 提取信息
                    title = page.title()
                    content = dom_extractor.extract_page_content()
                    buttons = dom_extractor.extract_buttons()
                    
                    # 分析
                    result = page_analyzer.analyze_page(url, title, content, buttons)
                    
                    # 显示结果
                    click.echo(f"\n页面类型: {result.page_type.value} (置信度: {result.confidence:.2f})")
                    
                    if result.cta_candidates:
                        click.echo(f"CTA候选: {result.cta_candidates[0].text}")
                    
                    # 询问下一步
                    if click.confirm("\n是否查看详细信息?"):
                        click.echo(f"\n标题: {title}")
                        click.echo(f"推理: {result.reasoning}")
                        click.echo(f"按钮数: {len(buttons)}")
                        
                        if click.confirm("\n是否保存截图?"):
                            screenshot_path = f"interactive_{Path(url).name}.png"
                            page.screenshot(path=screenshot_path)
                            click.echo(f"截图已保存: {screenshot_path}")
                    
                except Exception as e:
                    click.echo(f"错误: {e}", err=True)
                    error_reporter.report_error(
                        error_type="interactive_test_error",
                        error_message=str(e),
                        context={"url": url}
                    )
                    
        finally:
            browser.close()
    
    click.echo("\n退出交互式模式")


@cli.command()
def test_logic():
    """测试新逻辑功能"""
    from .test_new_logic import main as test_main
    test_main()


if __name__ == '__main__':
    cli()
