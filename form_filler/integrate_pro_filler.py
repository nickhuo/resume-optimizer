#!/usr/bin/env python3
"""
Integration script using ProFormFiller in WorkflowManager
This script demonstrates the changes needed to upgrade to the new professional form filling system
"""

import asyncio
import logging
from pathlib import Path
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_filler.services.pro_form_filler import ProFormFiller
from form_filler.services.dom_snapshot import DOMSnapshot
from form_filler.services.action_executor import ActionExecutor
from form_filler.workflow_manager import WorkflowManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UpgradedWorkflowManager(WorkflowManager):
    """Enhanced WorkflowManager using ProFormFiller"""
    
    def __init__(self, config: dict):
        """Initialize with ProFormFiller components"""
        # Call parent init first to set up basic services
        super().__init__(config)
        
        # Initialize ProFormFiller components
        logger.info("Initializing ProFormFiller components...")
        self.pro_filler = ProFormFiller(self.gpt_service)
        
        # New components for pro filling
        self.dom_snapshot = None  # Will be initialized per page
        self.action_executor = None  # Will be initialized per page
        
        logger.info("ProFormFiller integration complete")
    
    async def _fill_form(self, page, analysis_result):
        """Enhanced form filling using ProFormFiller"""
        logger.info("Starting enhanced form filling with ProFormFiller")
        
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
            logger.info("Generating DOM snapshot...")
            snapshot = await self.dom_snapshot.capture()
            
            # Get personal and resume data
            personal_data_path = Path("personal_info.yaml")
            resume_data_path = Path("resume_nick.json")
            
            # Use ProFormFiller
            logger.info("Executing ProFormFiller...")
            fill_result = await self.pro_filler.fill_form(
                page=page,
                dom_snapshot=snapshot,
                personal_data_path=str(personal_data_path),
                resume_data_path=str(resume_data_path)
            )
            
            if fill_result['success']:
                logger.info(f"ProFormFiller succeeded! Filled {fill_result['fields_filled']} fields")
                result.update(fill_result)
                return result
            else:
                logger.warning(f"ProFormFiller had issues: {fill_result.get('errors', [])}")
                result.update(fill_result)
                    
        except Exception as e:
            logger.error(f"Form filling failed: {str(e)}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    async def _validate_form(self, page, filled_fields=None):
        """Enhanced validation with immediate feedback"""
        logger.info("Running enhanced form validation...")
        
        # First run parent validation
        parent_result = await super()._validate_form(page, filled_fields)
        
        # Add pro validation if available
        if hasattr(self, 'action_executor') and self.action_executor:
            try:
                # Get current DOM state
                snapshot = await self.dom_snapshot.capture()
                
                # Check for validation errors
                validation_errors = []
                for element in snapshot.get('elements', []):
                    # Look for error messages
                    if element.get('role') == 'alert' or 'error' in element.get('class', '').lower():
                        if element.get('text'):
                            validation_errors.append({
                                'field': element.get('for', 'unknown'),
                                'error': element['text']
                            })
                
                if validation_errors:
                    logger.warning(f"Found {len(validation_errors)} validation errors")
                    parent_result['pro_validation_errors'] = validation_errors
                    parent_result['valid'] = False
                    
            except Exception as e:
                logger.error(f"Pro validation failed: {str(e)}")
        
        return parent_result


async def test_integration():
    """Test the integrated ProFormFiller workflow"""
    config = {
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'log_dir': 'logs',
        'screenshot_dir': 'screenshots'
    }
    
    # Create upgraded workflow manager
    workflow = UpgradedWorkflowManager(config)
    
    # Test URL - Rippling job application
    test_url = "https://www.rippling.com/careers/6413041?gh_jid=6413041"
    
    logger.info("Testing ProFormFiller integration on Rippling job page...")
    
    # Process job application
    result = await workflow.process_job_application(
        url=test_url,
        submit=False,  # Don't actually submit
        headless=False  # Show browser for debugging
    )
    
    # Print results
    logger.info("\n" + "="*80)
    logger.info("INTEGRATION TEST RESULTS")
    logger.info("="*80)
    
    logger.info(f"Success: {result['success']}")
    logger.info(f"Method used: {result.get('filled_fields', {}).get('method', 'unknown')}")
    logger.info(f"Fields filled: {len(result.get('filled_fields', {}))}")
    
    if result.get('errors'):
        logger.error(f"Errors: {result['errors']}")
    
    # Print filled fields summary
    if result.get('filled_fields'):
        logger.info("\nFilled Fields Summary:")
        for step in result.get('steps', []):
            if step.get('action') == 'fill_form' and step.get('details'):
                details = step['details']
                if 'filled_fields' in details:
                    for selector, field_info in list(details['filled_fields'].items())[:10]:
                        logger.info(f"  - {field_info.get('label', selector)}: {field_info.get('value', 'N/A')}")
                    if len(details['filled_fields']) > 10:
                        logger.info(f"  ... and {len(details['filled_fields']) - 10} more fields")


def create_patch_file():
    """Create a patch file showing the changes needed in workflow_manager.py"""
    patch_content = """
--- workflow_manager.py.original
+++ workflow_manager.py.updated
@@ -17,6 +17,9 @@
 from .services.page_analyzer import PageAnalyzer
 from .services.gpt_service import GPTService
 from .services.smart_form_filler import SmartFormFiller
+from .services.pro_form_filler import ProFormFiller
+from .services.dom_snapshot import DOMSnapshot
+from .services.action_executor import ActionExecutor
 from .services.field_validator import FieldValidator
 from .models.page_types import PageType, ActionType, PageAnalysisResult
 from .models.form_fields import FormField
@@ -46,7 +49,13 @@ class WorkflowManager:
         self.gpt_service = GPTService()
         self.page_analyzer = PageAnalyzer(self.gpt_service)
         self.field_parser = FieldParser()
-        self.smart_filler = SmartFormFiller(self.gpt_service)
+        
+        # Use ProFormFiller as primary, keep SmartFormFiller as fallback
+        self.pro_filler = ProFormFiller(self.gpt_service)
+        self.smart_filler = SmartFormFiller(self.gpt_service)  # Keep as fallback
+        
+        # Page-specific components (initialized per page)
+        self.dom_snapshot = None
+        self.action_executor = None
         self.field_validator = None  # Will be initialized per page instance
         self.dom_extractor = None  # Will be initialized per page instance
         self.error_reporter = ErrorReporter(
@@ -351,6 +360,81 @@ class WorkflowManager:
     
     async def _fill_form(self, page: Page, analysis_result: PageAnalysisResult) -> Dict[str, Any]:
         "Fill form using ProFormFiller with SmartFormFiller fallback"
+        result = {
+            'success': False,
+            'filled_fields': {},
+            'errors': [],
+            'method': 'pro_filler'
+        }
+        
+        try:
+            # Initialize page-specific components
+            self.dom_snapshot = DOMSnapshot(page)
+            self.action_executor = ActionExecutor(page)
+            
+            # Get DOM snapshot
+            snapshot = await self.dom_snapshot.capture()
+            
+            # Get data paths
+            personal_data_path = Path("personal_info.yaml")
+            resume_data_path = Path("resume_nick.json")
+            
+            # Try ProFormFiller first
+            fill_result = await self.pro_filler.fill_form(
+                page=page,
+                dom_snapshot=snapshot,
+                personal_data_path=str(personal_data_path),
+                resume_data_path=str(resume_data_path)
+            )
+            
+            if fill_result['success'] and fill_result.get('fields_filled', 0) >= 3:
+                result.update(fill_result)
+                return result
+                
+        except Exception as e:
+            logger.error(f"ProFormFiller failed: {str(e)}", exc_info=True)
+            result['errors'].append(f"ProFormFiller error: {str(e)}")
+        
+        # Fallback to SmartFormFiller
+        logger.info("Falling back to SmartFormFiller...")
+        result['method'] = 'smart_filler_fallback'
+        
         result = {
             'success': False,
             'filled_fields': {},
"""
    
    with open('workflow_manager_profiller.patch', 'w') as f:
        f.write(patch_content)
    
    logger.info("Created patch file: workflow_manager_profiller.patch")
    logger.info("Apply with: patch -p0 < workflow_manager_profiller.patch")


if __name__ == "__main__":
    # Create patch file
    create_patch_file()
    
    # Run integration test
    asyncio.run(test_integration())
