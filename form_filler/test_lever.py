#!/usr/bin/env python3
"""
测试 Lever 平台表单填写
演示跨平台支持能力
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_filler.workflow_manager import WorkflowManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_lever_form():
    """测试 Lever 表单填写"""
    
    # 测试 Lever 的 URL
    test_urls = [ "https://jobs.lever.co/palantir/37964982-9b4c-471e-a1d8-fb8f45d7f116/apply?lever-source=LinkedIn"
    ]
    

    test_url = test_urls[0]  
    
    logger.info("开始测试 Lever 表单填写")
    logger.info(f"测试URL: {test_url}")
    
    # 配置
    config = {
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'log_dir': 'logs',
        'screenshot_dir': 'screenshots'
    }
    
    # 检查API密钥
    if not config['openai_api_key']:
        logger.error("未找到 OPENAI_API_KEY 环境变量")
        return
    
    # 创建必要的目录
    Path(config['log_dir']).mkdir(exist_ok=True)
    Path(config['screenshot_dir']).mkdir(exist_ok=True)
    
    # 创建 WorkflowManager 实例
    workflow = WorkflowManager(config)
    
    try:
        # 测试表单填写
        logger.info("开始处理 Lever 求职申请...")
        result = await workflow.process_job_application(
            url=test_url,
            submit=False,  # 不实际提交
            headless=False  # 显示浏览器以便观察
        )
        
        # 输出结果
        logger.info("\n" + "="*80)
        logger.info("Lever 测试结果:")
        logger.info("="*80)
        
        if result['success']:
            logger.info("✓ 表单处理成功!")
        else:
            logger.error("✗ 表单处理失败")
        
        # 显示填写统计
        for step in result.get('steps', []):
            if step.get('action') == 'fill_form' and step.get('details'):
                details = step['details']
                if 'stats' in details:
                    stats = details['stats']
                    logger.info(f"\n填写统计:")
                    logger.info(f"  总字段数: {stats.get('total_fields', 0)}")
                    logger.info(f"  成功填写: {stats.get('filled_fields', 0)}")
                    logger.info(f"  失败: {stats.get('failed_fields', 0)}")
                    logger.info(f"  成功率: {stats.get('success_rate', '0%')}")
                    
                    # 显示字段类型分布
                    if 'field_types' in stats:
                        logger.info("\n字段类型分布:")
                        for field_type, type_stats in stats['field_types'].items():
                            logger.info(f"  {field_type}: {type_stats['success']}/{type_stats['total']}")
        
        logger.info("\nLever 测试完成!")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)


async def compare_platforms():
    """比较不同平台的表单结构"""
    from form_filler.services.field_learning_system import FieldLearningSystem
    
    learning_system = FieldLearningSystem()
    
    platforms = ['greenhouse', 'lever', 'workday']
    
    logger.info("平台特性比较:")
    logger.info("="*80)
    
    for platform in platforms:
        insights = learning_system.get_platform_insights(platform)
        
        logger.info(f"\n{platform.upper()}")
        logger.info("-"*40)
        logger.info(f"已知字段类型: {len(insights['known_fields'])}")
        logger.info(f"常见字段: {', '.join(insights['known_fields'][:5])}...")
        
        if insights['tips']:
            logger.info("平台提示:")
            for tip in insights['tips']:
                logger.info(f"  - {tip}")


if __name__ == "__main__":
    logger.info("Lever 平台表单填写测试")
    logger.info("="*80)
    
    # 检查环境
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("请设置 OPENAI_API_KEY 环境变量")
        sys.exit(1)
    
    # 显示平台比较
    asyncio.run(compare_platforms())
    
    # 询问是否继续测试
    response = input("\n是否继续测试 Lever 表单？(y/n): ")
    if response.lower() in ['y', 'yes']:
        # 运行测试
        asyncio.run(test_lever_form())
    else:
        logger.info("测试已取消")
