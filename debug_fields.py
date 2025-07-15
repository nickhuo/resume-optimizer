#!/usr/bin/env python3
"""
调试字段提取和处理
"""
import asyncio
import os
from dotenv import load_dotenv
import logging
import json
from playwright.async_api import async_playwright

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入必要的模块
from form_filler.services.field_parser import FieldParser
from form_filler.services.smart_form_filler import SmartFormFiller
from form_filler.services.smart_field_handler import SmartFieldHandler


async def debug_fields():
    """调试字段提取"""
    
    # 启动浏览器
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    # 访问Rippling页面
    url = "https://ats.rippling.com/rippling/jobs/203e0cac-0e30-4603-8087-f764e8c3f85c?jobSite=LinkedIn"
    await page.goto(url, wait_until='networkidle')
    
    # 点击Apply按钮
    logger.info("查找并点击Apply按钮...")
    apply_button = await page.query_selector('button:has-text("Apply")')
    if apply_button:
        await apply_button.click()
        await page.wait_for_timeout(3000)
    
    # 提取字段
    logger.info("提取表单字段...")
    field_parser = FieldParser()
    fields = await field_parser.extract_fields(page)
    
    logger.info(f"\n找到 {len(fields)} 个字段\n")
    
    # 按类型分组
    fields_by_type = {}
    for field in fields:
        field_type = field['type']
        if field_type not in fields_by_type:
            fields_by_type[field_type] = []
        fields_by_type[field_type].append(field)
    
    # 显示每种类型的字段
    for field_type, type_fields in fields_by_type.items():
        logger.info(f"\n{field_type.upper()} 类型字段 ({len(type_fields)}个):")
        logger.info("=" * 60)
        
        for i, field in enumerate(type_fields, 1):
            logger.info(f"\n字段 {i}:")
            logger.info(f"  - 名称: {field['name']}")
            logger.info(f"  - ID: {field['id']}")
            logger.info(f"  - 标签: {field['label']}")
            logger.info(f"  - 选择器: {field['selector']}")
            logger.info(f"  - 必填: {field['required']}")
            logger.info(f"  - 可见: {field['visible']}")
            
            if field_type == 'select' and field['options']:
                logger.info(f"  - 选项数: {len(field['options'])}")
                logger.info(f"  - 前5个选项:")
                for opt in field['options'][:5]:
                    logger.info(f"    * {opt['text']} (value={opt['value']})")
            
            if field_type in ['radio', 'checkbox']:
                logger.info(f"  - 值: {field['value']}")
    
    # 保存完整的字段信息
    with open('debug_fields.json', 'w', encoding='utf-8') as f:
        json.dump(fields, f, indent=2, ensure_ascii=False)
    logger.info(f"\n完整字段信息已保存到 debug_fields.json")
    
    # 测试智能填充
    logger.info("\n" + "="*60)
    logger.info("测试智能字段处理")
    logger.info("="*60)
    
    # 加载个人数据
    smart_filler = SmartFormFiller()
    personal_data = smart_filler._load_personal_data()
    
    # 初始化字段处理器
    field_handler = SmartFieldHandler(page)
    
    # 测试一些关键字段
    test_cases = []
    
    # 查找下拉框
    select_fields = [f for f in fields if f['type'] == 'select']
    if select_fields:
        test_cases.append({
            'field': select_fields[0],
            'value': 'United States'  # 测试国家
        })
    
    # 查找文件上传
    file_fields = [f for f in fields if f['type'] == 'file']
    if file_fields:
        test_cases.append({
            'field': file_fields[0],
            'value': personal_data.get('resume', {}).get('file_path')
        })
    
    # 查找单选框
    radio_fields = [f for f in fields if f['type'] == 'radio']
    if radio_fields:
        test_cases.append({
            'field': radio_fields[0],
            'value': 'Yes'
        })
    
    # 执行测试
    for test in test_cases:
        field = test['field']
        value = test['value']
        
        logger.info(f"\n测试字段: {field['label'] or field['name']} ({field['type']})")
        logger.info(f"测试值: {value}")
        
        result = await field_handler.analyze_and_fill_field(
            field_info=field,
            value_to_fill=value,
            personal_data=personal_data
        )
        
        if result['success']:
            logger.info(f"✅ 成功: {result['actual_value']} (置信度: {result['confidence']:.2f})")
        else:
            logger.error(f"❌ 失败: {result['error']}")
    
    # 等待查看
    logger.info("\n按回车键结束...")
    input()
    
    # 清理
    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(debug_fields())
