import json
import datetime
import os
from typing import Dict, List, Any, Tuple

class ResumeValidator:
    """
    Resume Data Validator for LLM-generated resume data
    验证 LLM 生成的简历数据，确保符合 PDF 渲染格式要求
    """
    
    def __init__(self):
        self.skill_requirements = {
            "Programming": {"min": 92, "max": 97},
            "Frameworks": {"min": 92, "max": 97},
            "DevOps": {"min": 103, "max": 108}
        }
        self.hidden_text_length = 200
        self.total_lines_required = 23
        self.single_line_max = 115
        self.double_line_min = 215
        self.double_line_max = 230
        
    def validate_skills(self, skills: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """验证技能部分的字符数"""
        errors = []
        
        for skill_type, requirements in self.skill_requirements.items():
            if skill_type not in skills:
                errors.append({
                    "section": "skills",
                    "field": skill_type,
                    "error_type": "missing_field",
                    "message": f"Missing {skill_type} field in skills section"
                })
                continue
                
            skill_text = ', '.join(skills[skill_type])
            char_count = len(skill_text)
            
            if not (requirements["min"] <= char_count <= requirements["max"]):
                errors.append({
                    "section": "skills",
                    "field": skill_type,
                    "error_type": "character_count",
                    "actual": char_count,
                    "expected": f"{requirements['min']}-{requirements['max']}",
                    "message": f"{skill_type} has {char_count} characters, expected {requirements['min']}-{requirements['max']}"
                })
                
        return errors
    
    def validate_hidden_text(self, footnote: str) -> List[Dict[str, Any]]:
        """验证隐藏文本的字符数"""
        errors = []
        char_count = len(footnote)
        
        if char_count != self.hidden_text_length:
            errors.append({
                "section": "hidden_text",
                "field": "footnote",
                "error_type": "character_count",
                "actual": char_count,
                "expected": self.hidden_text_length,
                "message": f"Hidden text has {char_count} characters, expected {self.hidden_text_length}"
            })
            
        return errors
    
    def validate_bullet_points(self, resume_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """验证项目符号点和计算总行数"""
        errors = []
        total_lines = 0
        
        for section_name in ["experience", "projects"]:
            section_data = resume_data.get(section_name, [])
            
            for entry_idx, entry in enumerate(section_data):
                bullets = entry.get("bullets", [])
                
                for bullet_idx, bullet in enumerate(bullets):
                    char_count = len(bullet)
                    
                    if char_count <= self.single_line_max:
                        # 单行子弹点
                        total_lines += 1
                    elif self.double_line_min <= char_count <= self.double_line_max:
                        # 双行子弹点
                        total_lines += 2
                    else:
                        # 不符合要求的子弹点
                        errors.append({
                            "section": section_name,
                            "field": f"entry_{entry_idx}_bullet_{bullet_idx}",
                            "error_type": "bullet_point_length",
                            "actual": char_count,
                            "expected": f"≤{self.single_line_max} or {self.double_line_min}-{self.double_line_max}",
                            "message": f"Bullet point in {section_name} has {char_count} characters, expected ≤{self.single_line_max} or {self.double_line_min}-{self.double_line_max}",
                            "content_preview": bullet[:50] + "..." if len(bullet) > 50 else bullet
                        })
                        
                        # 对于不符合要求的子弹点，我们假设它占用2行（最坏情况）
                        total_lines += 2
                        
        return errors, total_lines
    
    def validate_total_lines(self, total_lines: int) -> List[Dict[str, Any]]:
        """验证总行数"""
        errors = []
        
        if total_lines != self.total_lines_required:
            errors.append({
                "section": "overall",
                "field": "total_lines",
                "error_type": "line_count",
                "actual": total_lines,
                "expected": self.total_lines_required,
                "message": f"Total lines in experience and projects is {total_lines}, expected {self.total_lines_required}"
            })
            
        return errors
    
    def validate_resume(self, resume_path: str, output_path: str = None) -> Dict[str, Any]:
        """主验证函数"""
        try:
            # 读取简历数据
            with open(resume_path, 'r', encoding='utf-8') as f:
                resume_data = json.load(f)
            
            all_errors = []
            
            # 验证技能部分
            skills_errors = self.validate_skills(resume_data.get("skills", {}))
            all_errors.extend(skills_errors)
            
            # 验证隐藏文本
            hidden_text_errors = self.validate_hidden_text(resume_data.get("footnote", ""))
            all_errors.extend(hidden_text_errors)
            
            # 验证项目符号点和计算总行数
            bullet_errors, total_lines = self.validate_bullet_points(resume_data)
            all_errors.extend(bullet_errors)
            
            # 验证总行数
            line_errors = self.validate_total_lines(total_lines)
            all_errors.extend(line_errors)
            
            # 生成报告
            report = {
                "validation_summary": {
                    "total_errors": len(all_errors),
                    "is_valid": len(all_errors) == 0,
                    "validated_at": datetime.datetime.now().isoformat(),
                    "resume_file": resume_path
                },
                "validation_details": {
                    "skills_errors": len(skills_errors),
                    "hidden_text_errors": len(hidden_text_errors),
                    "bullet_point_errors": len(bullet_errors),
                    "line_count_errors": len(line_errors),
                    "calculated_total_lines": total_lines,
                    "expected_total_lines": self.total_lines_required
                },
                "errors": all_errors,
                "fallback_required": len(all_errors) > 0,
                "execution_context": {
                    "directory_state": {
                        "pwd": os.getcwd(),
                        "home": os.path.expanduser("~")
                    },
                    "operating_system": {
                        "platform": "MacOS"
                    },
                    "current_time": datetime.datetime.now().isoformat(),
                    "shell": {
                        "name": "zsh",
                        "version": "5.9"
                    }
                }
            }
            
            # 输出报告
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                    
            return report
            
        except Exception as e:
            error_report = {
                "validation_summary": {
                    "total_errors": 1,
                    "is_valid": False,
                    "validated_at": datetime.datetime.now().isoformat(),
                    "resume_file": resume_path
                },
                "errors": [{
                    "section": "system",
                    "field": "validation_process",
                    "error_type": "system_error",
                    "message": f"Validation failed: {str(e)}"
                }],
                "fallback_required": True,
                "execution_context": {
                    "directory_state": {
                        "pwd": os.getcwd(),
                        "home": os.path.expanduser("~")
                    },
                    "operating_system": {
                        "platform": "MacOS"
                    },
                    "current_time": datetime.datetime.now().isoformat(),
                    "shell": {
                        "name": "zsh",
                        "version": "5.9"
                    }
                }
            }
            
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(error_report, f, indent=2, ensure_ascii=False)
                    
            return error_report

def main():
    """命令行使用示例"""
    validator = ResumeValidator()
    
    # 默认路径
    resume_path = "/Users/nickhuo/Documents/GitHub/semi-apply/resume_builder/data/sample_resume.json"
    output_path = "/Users/nickhuo/Documents/GitHub/semi-apply/resume_validation_report.json"
    
    # 执行验证
    report = validator.validate_resume(resume_path, output_path)
    
    # 打印摘要
    print(f"验证完成！")
    print(f"总错误数: {report['validation_summary']['total_errors']}")
    print(f"是否通过验证: {report['validation_summary']['is_valid']}")
    print(f"报告已保存到: {output_path}")
    
    if report['validation_summary']['total_errors'] > 0:
        print("\n错误详情:")
        for error in report['errors']:
            print(f"- {error['message']}")

if __name__ == "__main__":
    main()
