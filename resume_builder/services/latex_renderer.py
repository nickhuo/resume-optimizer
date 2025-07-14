"""
LaTeX rendering service using Jinja2 templates.
"""
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models.resume_models import ResumeData

logger = logging.getLogger(__name__)


class LatexRenderer:
    """Service to render LaTeX files from resume data using Jinja2."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the LaTeX renderer.
        
        Args:
            template_dir: Directory containing Jinja2 templates. 
                         If not provided, uses default templates directory.
        """
        if template_dir is None:
            # Get the templates directory relative to this file
            current_dir = Path(__file__).parent.parent
            template_dir = current_dir / "templates"
        
        self.template_dir = template_dir
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(disabled_extensions=('tex', 'j2')),
            block_start_string='<%',
            block_end_string='%>',
            variable_start_string='<<',
            variable_end_string='>>',
            comment_start_string='<#',
            comment_end_string='#>',
        )
        
        # Add custom filters
        self.env.filters['latex_escape'] = self._latex_escape
        self.env.filters['format_date'] = self._format_date
    
    def render(
        self, 
        resume_data: ResumeData,
        template_name: str = "base_resume.tex.j2",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render LaTeX content from resume data.
        
        Args:
            resume_data: Resume data to render
            template_name: Name of the template file to use
            additional_context: Additional context variables for rendering
            
        Returns:
            Rendered LaTeX content as string
        """
        try:
            template = self.env.get_template(template_name)
            
            # Prepare context
            context = {
                "resume": resume_data,
                "company": additional_context.get("company", "") if additional_context else "",
                "title": additional_context.get("title", "") if additional_context else "",
            }
            
            if additional_context:
                context.update(additional_context)
            
            # Render template
            latex_content = template.render(**context)
            
            logger.info(f"Successfully rendered LaTeX using template: {template_name}")
            return latex_content
            
        except Exception as e:
            logger.error(f"Failed to render LaTeX: {str(e)}")
            raise
    
    def save_tex_file(self, content: str, output_path: Path) -> Path:
        """
        Save LaTeX content to a .tex file.
        
        Args:
            content: LaTeX content to save
            output_path: Path where to save the file
            
        Returns:
            Path to the saved file
        """
        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            output_path.write_text(content, encoding='utf-8')
            
            logger.info(f"Saved LaTeX file to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save LaTeX file: {str(e)}")
            raise
    
    @staticmethod
    def _latex_escape(text: str) -> str:
        """
        Escape special LaTeX characters in text.
        
        Args:
            text: Text to escape
            
        Returns:
            LaTeX-safe text
        """
        if not text:
            return ""
        
        # LaTeX special characters that need escaping
        # Order matters - escape backslash first
        replacements = [
            ('\\', r'\textbackslash{}'),
            ('&', r'\&'),
            ('%', r'\%'),
            ('$', r'\$'),
            ('#', r'\#'),
            ('_', r'\_'),
            ('{', r'\{'),
            ('}', r'\}'),
            ('~', r'\textasciitilde{}'),
            ('^', r'\textasciicircum{}'),
        ]
        
        for char, replacement in replacements:
            text = text.replace(char, replacement)
        
        return text
    
    @staticmethod
    def _format_date(date_str: str) -> str:
        """
        Format date string for display.
        
        Args:
            date_str: Date string to format
            
        Returns:
            Formatted date string
        """
        if not date_str:
            return ""
        
        # Handle common date formats
        if date_str.lower() in ["present", "current", "now"]:
            return "Present"
        
        # For now, just return as-is
        # Could add more sophisticated date formatting here
        return date_str
