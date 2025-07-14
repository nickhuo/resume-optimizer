#!/usr/bin/env python3
"""
Resume Validator CLI Tool
使用方法：
python validate_resume.py --input path/to/resume.json --output path/to/report.json
"""

import argparse
import sys
import os
from pathlib import Path

# 添加父目录到路径，以便导入 services 模块
sys.path.append(str(Path(__file__).parent.parent))

from services.resume_validator import ResumeValidator

def main():
    parser = argparse.ArgumentParser(
        description="Validate LLM-generated resume data for PDF rendering requirements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python validate_resume.py --input data/sample_resume.json
  python validate_resume.py --input data/sample_resume.json --output validation_report.json
  python validate_resume.py --input data/sample_resume.json --verbose
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the resume JSON file to validate"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Path to save the validation report (JSON format). If not specified, prints to stdout"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed validation results"
    )
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"错误：输入文件 '{args.input}' 不存在", file=sys.stderr)
        sys.exit(1)
    
    # 创建验证器实例
    validator = ResumeValidator()
    
    # 执行验证
    try:
        report = validator.validate_resume(args.input, args.output)
        
        # 输出结果
        if args.verbose or not args.output:
            print(f"\n=== 简历验证报告 ===")
            print(f"文件: {args.input}")
            print(f"验证时间: {report['validation_summary']['validated_at']}")
            print(f"\n=== 验证结果 ===")
            print(f"总错误数: {report['validation_summary']['total_errors']}")
            print(f"是否通过验证: {'✅ 是' if report['validation_summary']['is_valid'] else '❌ 否'}")
            
            if report['validation_details']:
                print(f"\n=== 详细统计 ===")
                details = report['validation_details']
                print(f"技能部分错误: {details['skills_errors']}")
                print(f"隐藏文本错误: {details['hidden_text_errors']}")
                print(f"子弹点错误: {details['bullet_point_errors']}")
                print(f"行数错误: {details['line_count_errors']}")
                print(f"计算总行数: {details['calculated_total_lines']}")
                print(f"期望总行数: {details['expected_total_lines']}")
            
            if report['validation_summary']['total_errors'] > 0:
                print(f"\n=== 错误详情 ===")
                for i, error in enumerate(report['errors'], 1):
                    print(f"{i}. {error['message']}")
                    if 'content_preview' in error:
                        print(f"   内容预览: {error['content_preview']}")
                    print()
            
            if report['fallback_required']:
                print(f"\n⚠️  需要 LLM 修正：{report['fallback_required']}")
            
        if args.output:
            print(f"\n报告已保存到: {args.output}")
        
        # 设置退出代码
        sys.exit(0 if report['validation_summary']['is_valid'] else 1)
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
