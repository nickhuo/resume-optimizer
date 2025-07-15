#!/usr/bin/env python3
"""
Script to apply ProFormFiller upgrade to workflow_manager.py
This will modify the existing workflow_manager.py to use ProFormFiller as primary
with SmartFormFiller as fallback
"""

import os
import shutil
from datetime import datetime

def apply_upgrade():
    """Apply the ProFormFiller upgrade to workflow_manager.py"""
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_file = os.path.join(script_dir, "workflow_manager.py")
    
    # Create backup
    backup_file = f"{workflow_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(workflow_file, backup_file)
    print(f"Created backup: {os.path.basename(backup_file)}")
    
    # Read original file
    with open(workflow_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply modifications
    
    # 1. Add new imports
    import_section = """from .services.field_parser import FieldParser
from .services.page_analyzer import PageAnalyzer
from .services.gpt_service import GPTService
from .services.smart_form_filler import SmartFormFiller
from .services.pro_form_filler import ProFormFiller
from .services.dom_snapshot import DOMSnapshot
from .services.action_executor import ActionExecutor
from .services.field_validator import FieldValidator"""
    
    content = content.replace(
        """from .services.field_parser import FieldParser
from .services.page_analyzer import PageAnalyzer
from .services.gpt_service import GPTService
from .services.smart_form_filler import SmartFormFiller
from .services.field_validator import FieldValidator""",
        import_section
    )
    
    # 2. Update __init__ method
    init_old = """        self.gpt_service = GPTService()
        self.page_analyzer = PageAnalyzer(self.gpt_service)
        self.field_parser = FieldParser()
        self.smart_filler = SmartFormFiller(self.gpt_service)
        self.field_validator = None  # Will be initialized per page instance"""
    
    init_new = """        self.gpt_service = GPTService()
        self.page_analyzer = PageAnalyzer(self.gpt_service)
        self.field_parser = FieldParser()
        
        # Use ProFormFiller as primary, keep SmartFormFiller as fallback
        self.pro_filler = ProFormFiller(self.gpt_service)
        self.smart_filler = SmartFormFiller(self.gpt_service)  # Keep as fallback
        
        # Page-specific components (initialized per page)
        self.dom_snapshot = None
        self.action_executor = None
        self.field_validator = None  # Will be initialized per page instance"""
    
    content = content.replace(init_old, init_new)
    
    # 3. Replace _fill_form method
    # Find the _fill_form method
    fill_form_start = content.find("    async def _fill_form(self, page: Page, analysis_result: PageAnalysisResult) -> Dict[str, Any]:")
    if fill_form_start == -1:
        print("ERROR: Could not find _fill_form method")
        return False
    
    # Find the end of the method (next method definition)
    next_method = content.find("\n    async def ", fill_form_start + 1)
    if next_method == -1:
        next_method = content.find("\n    def ", fill_form_start + 1)
    
    # Extract and replace the method
    new_fill_form = '''    async def _fill_form(self, page: Page, analysis_result: PageAnalysisResult) -> Dict[str, Any]:
        """填寫表單 - 使用ProFormFiller with SmartFormFiller fallback"""
        result = {
            'success': False,
            'filled_fields': {},
            'errors': [],
            'method': 'pro_filler'
        }
        
        try:
            # Initialize page-specific components
            self.dom_snapshot = DOMSnapshot(page)
            self.action_executor = ActionExecutor(page)
            
            # Get DOM snapshot
            self._log_step("生成DOM快照", {})
            snapshot = await self.dom_snapshot.capture()
            
            # Get data paths
            from pathlib import Path
            personal_data_path = Path("personal_info.yaml")
            resume_data_path = Path("resume_nick.json")
            
            # Try ProFormFiller first
            self._log_step("使用ProFormFiller填寫表單", {})
            fill_result = await self.pro_filler.fill_form(
                page=page,
                dom_snapshot=snapshot,
                personal_data_path=str(personal_data_path),
                resume_data_path=str(resume_data_path)
            )
            
            if fill_result['success'] and fill_result.get('fields_filled', 0) >= 3:
                self._log_step(f"ProFormFiller成功填寫 {fill_result['fields_filled']} 個字段", {})
                result.update(fill_result)
                return result
            else:
                self._log_step(f"ProFormFiller填寫結果不理想: {fill_result.get('errors', [])}", {})
                
        except Exception as e:
            logger.error(f"ProFormFiller失敗: {str(e)}", exc_info=True)
            result['errors'].append(f"ProFormFiller error: {str(e)}")
        
        # Fallback to SmartFormFiller
        self._log_step("回退到SmartFormFiller", {})
        result['method'] = 'smart_filler_fallback'
        
        try:
            # 提取表單字段
            fields = await self.field_parser.extract_fields(page)
            
            if not fields:
                result['errors'].append("未找到表單字段")
                return result
            
            # 填寫表單
            fill_result = await self.smart_filler.fill_form(page, fields)
            
            result['success'] = fill_result.get('success', False)
            result['filled_fields'] = fill_result.get('filled_fields', {})
            result['errors'].extend(fill_result.get('errors', []))
            
        except Exception as e:
            logger.error(f"SmartFormFiller也失敗: {str(e)}", exc_info=True)
            result['errors'].append(f"SmartFormFiller error: {str(e)}")
        
        return result'''
    
    # Replace the method
    content = content[:fill_form_start] + new_fill_form + content[next_method:]
    
    # Write modified content
    with open(workflow_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Successfully upgraded {workflow_file}")
    print("ProFormFiller is now integrated as the primary form filler with SmartFormFiller as fallback")
    
    return True


def verify_imports():
    """Verify that all required files exist"""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    required_files = [
        os.path.join(script_dir, "services/pro_form_filler.py"),
        os.path.join(script_dir, "services/dom_snapshot.py"), 
        os.path.join(script_dir, "services/action_executor.py"),
        os.path.join(script_dir, "workflow_manager.py")
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            # Show relative path for cleaner output
            rel_path = os.path.relpath(file, script_dir)
            missing.append(rel_path)
    
    if missing:
        print("ERROR: Missing required files:")
        for f in missing:
            print(f"  - {f}")
        return False
    
    return True


if __name__ == "__main__":
    print("ProFormFiller Upgrade Script")
    print("=" * 50)
    
    # Verify files exist
    if not verify_imports():
        print("\nPlease ensure all required files are present before running this script")
        exit(1)
    
    # Confirm with user
    print("\nThis script will modify workflow_manager.py to use ProFormFiller")
    print("A backup will be created before any changes are made")
    response = input("\nProceed with upgrade? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        if apply_upgrade():
            print("\n✓ Upgrade complete!")
            print("\nNext steps:")
            print("1. Test the integration with: python integrate_pro_filler.py")
            print("2. Run your normal workflow to verify everything works")
            print("3. If issues occur, restore from the backup file")
    else:
        print("\nUpgrade cancelled")
