"""
错误报告工具，用于收集和记录错误信息，支持自学习机制
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class ErrorReporter:
    """错误报告器，负责收集和记录错误信息"""
    
    def __init__(self, errors_file: str = "errors.jsonl", screenshots_dir: str = "error_screenshots"):
        """
        初始化错误报告器
        
        Args:
            errors_file: 错误日志文件路径
            screenshots_dir: 截图保存目录
        """
        self.errors_file = Path(errors_file)
        self.screenshots_dir = Path(screenshots_dir)
        
        # 确保目录存在
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
    async def report_error(self, 
                    error_type: str,
                    error_message: str,
                    context: Dict[str, Any],
                    page: Optional[Page] = None,
                    selector: Optional[str] = None) -> str:
        """
        报告错误信息
        
        Args:
            error_type: 错误类型（如 "cta_not_found", "selector_failed", "form_fill_failed"）
            error_message: 错误消息
            context: 错误上下文信息
            page: Playwright页面对象（用于截图）
            selector: 失败的选择器
            
        Returns:
            错误ID
        """
        error_id = self._generate_error_id()
        timestamp = datetime.now().isoformat()
        
        # 构建错误记录
        error_record = {
            "error_id": error_id,
            "timestamp": timestamp,
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "selector": selector
        }
        
        # 如果提供了页面对象，进行截图
        if page:
            try:
                screenshot_path = await self._take_screenshot(page, error_id)
                error_record["screenshot_path"] = str(screenshot_path)
                
                # 收集页面信息
                error_record["page_info"] = {
                    "url": page.url,
                    "title": await page.title()
                }
                
                # 如果有失败的选择器，尝试收集相关DOM信息
                if selector:
                    dom_info = await self._collect_dom_info(page, selector)
                    error_record["dom_info"] = dom_info
                    
            except Exception as e:
                logger.warning(f"Failed to collect additional error info: {e}")
        
        # 写入错误日志
        self._write_error_record(error_record)
        
        logger.error(f"Error reported: {error_type} - {error_message} (ID: {error_id})")
        
        return error_id
    
    def report_success(self, 
                      operation_type: str,
                      context: Dict[str, Any],
                      selector: Optional[str] = None):
        """
        报告成功的操作（用于收集正面样本）
        
        Args:
            operation_type: 操作类型
            context: 操作上下文
            selector: 使用的选择器
        """
        success_record = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "success": True,
            "context": context,
            "selector": selector
        }
        
        # 写入成功记录（可以用于后续的模式学习）
        self._write_success_record(success_record)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        if not self.errors_file.exists():
            return {"total_errors": 0, "error_types": {}}
        
        error_types = {}
        total_errors = 0
        
        with open(self.errors_file, 'r') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    if "error_type" in record:
                        error_type = record["error_type"]
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                        total_errors += 1
                except json.JSONDecodeError:
                    continue
        
        return {
            "total_errors": total_errors,
            "error_types": error_types,
            "errors_file": str(self.errors_file)
        }
    
    def _generate_error_id(self) -> str:
        """生成唯一的错误ID"""
        import uuid
        return f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    async def _take_screenshot(self, page: Page, error_id: str) -> Path:
        """
        截取页面截图
        
        Args:
            page: Playwright页面对象
            error_id: 错误ID
            
        Returns:
            截图文件路径
        """
        screenshot_path = self.screenshots_dir / f"{error_id}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        return screenshot_path
    
    async def _collect_dom_info(self, page: Page, selector: str) -> Dict[str, Any]:
        """
        收集失败选择器周围的DOM信息
        
        Args:
            page: Playwright页面对象
            selector: 选择器
            
        Returns:
            DOM信息字典
        """
        try:
            dom_info = await page.evaluate(f"""
                (selector) => {{
                    const elements = document.querySelectorAll(selector);
                    const info = {{
                        selector: selector,
                        elements_found: elements.length,
                        similar_elements: []
                    }};
                    
                    if (elements.length === 0) {{
                        // 尝试找到相似的元素
                        const allElements = document.querySelectorAll('*');
                        const selectorParts = selector.toLowerCase();
                        
                        allElements.forEach(el => {{
                            const text = el.textContent.trim().toLowerCase();
                            const classes = el.className.toLowerCase();
                            const id = el.id.toLowerCase();
                            
                            if ((text && selectorParts.includes(text.substring(0, 20))) ||
                                (classes && selectorParts.includes(classes)) ||
                                (id && selectorParts.includes(id))) {{
                                
                                info.similar_elements.push({{
                                    tagName: el.tagName,
                                    id: el.id,
                                    className: el.className,
                                    text: el.textContent.trim().substring(0, 50)
                                }});
                            }}
                        }});
                        
                        info.similar_elements = info.similar_elements.slice(0, 5);
                    }} else {{
                        // 收集找到的元素信息
                        Array.from(elements).slice(0, 3).forEach(el => {{
                            info.similar_elements.push({{
                                tagName: el.tagName,
                                id: el.id,
                                className: el.className,
                                text: el.textContent.trim().substring(0, 50),
                                visible: el.offsetWidth > 0 && el.offsetHeight > 0
                            }});
                        }});
                    }}
                    
                    return info;
                }}
            """, selector)
            
            return dom_info
            
        except Exception as e:
            logger.debug(f"Failed to collect DOM info: {e}")
            return {"error": str(e)}
    
    def _write_error_record(self, record: Dict[str, Any]):
        """写入错误记录到JSONL文件"""
        # 确保所有值都是可序列化的
        serializable_record = self._make_serializable(record)
        with open(self.errors_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(serializable_record, ensure_ascii=False) + '\n')
    
    def _make_serializable(self, obj: Any) -> Any:
        """递归地将对象转换为可JSON序列化的格式"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # 对于其他类型，转换为字符串
            return str(obj)
    
    def _write_success_record(self, record: Dict[str, Any]):
        """写入成功记录到单独的文件"""
        success_file = self.errors_file.parent / "success.jsonl"
        with open(success_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
