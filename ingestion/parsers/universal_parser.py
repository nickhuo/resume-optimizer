"""
Universal LLM-based job posting parser.
This parser works with any website by extracting all text content and using LLM to parse it.
"""
import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from .base import BaseParser, ParserException
from ..models.job import JDModel

logger = logging.getLogger(__name__)


class UniversalParser(BaseParser):
    """Universal job posting parser that uses LLM for all content extraction."""
    
    def __init__(self, timeout: int = 10):
        """Initialize the universal parser with LLM enabled by default."""
        super().__init__(timeout=timeout)
        
        # Initialize OpenAI client directly
        import os
        from openai import OpenAI
        
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ParserException("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
    
    def parse(self, url: str) -> JDModel:
        """
        Parse any job posting URL using LLM-based content extraction.
        
        Args:
            url: Job posting URL
            
        Returns:
            JDModel instance with parsed data
        """
        try:
            # 1. Fetch page content
            html = self.fetch_page(url)
            
            # 2. Extract clean text content
            content = self._extract_clean_content(html)
            
            if not content or len(content.strip()) < 100:
                raise ParserException("Insufficient content found on page")
            
            # 3. Use LLM to extract all structured data
            structured_data = self._extract_all_data_with_llm(content)
            
            # 4. Extract technical skills using our CSV-based approach
            skills = self.extract_skills(content)
            
            # 5. Create JDModel
            return JDModel(
                company=structured_data.get('company') or "Unknown Company",
                title=structured_data.get('title') or "Unknown Position",
                location=structured_data.get('location'),
                requirements=structured_data.get('requirements', []),
                nice_to_have=structured_data.get('nice_to_have', []),
                responsibilities=structured_data.get('responsibilities', []),
                skills=skills,
                job_type=structured_data.get('job_type') or self._determine_job_type(
                    structured_data.get('title', ''), content
                )
            )
            
        except Exception as e:
            logger.error(f"Failed to parse URL {url}: {str(e)}")
            raise ParserException(f"Failed to parse job posting: {str(e)}")
    
    def _extract_clean_content(self, html: str) -> str:
        """
        Extract clean, readable text content from HTML.
        This method removes navigation, ads, and other non-content elements.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            'advertisement', 'ad', 'sidebar', 'breadcrumb', 'cookie',
            'social', 'share', 'comment', 'popup', 'modal'
        ]
        
        for tag in unwanted_tags:
            # Remove by tag name
            for element in soup.find_all(tag):
                element.decompose()
            
            # Remove by class/id containing these keywords
            for element in soup.find_all(attrs={'class': lambda x: x and any(keyword in ' '.join(x).lower() for keyword in [tag])}):
                element.decompose()
            
            for element in soup.find_all(attrs={'id': lambda x: x and tag in x.lower()}):
                element.decompose()
        
        # Also remove common unwanted patterns
        unwanted_patterns = [
            'cookie', 'privacy', 'gdpr', 'consent', 'tracking',
            'analytics', 'advertisement', 'promo', 'banner'
        ]
        
        for pattern in unwanted_patterns:
            for element in soup.find_all(attrs={'class': lambda x: x and any(pattern in ' '.join(x).lower() for pattern in [pattern])}):
                element.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n')
        
        # Clean up the text
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 3:  # Skip very short lines
                # Skip lines that look like navigation or metadata
                if not self._is_navigation_line(line):
                    cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _is_navigation_line(self, line: str) -> bool:
        """Check if a line looks like navigation or metadata."""
        line_lower = line.lower()
        
        # Skip navigation-like lines
        nav_keywords = [
            'home', 'about', 'contact', 'careers', 'login', 'sign in',
            'sign up', 'register', 'search', 'menu', 'toggle',
            'cookie', 'privacy', 'terms', 'gdpr', 'consent'
        ]
        
        # Skip if it's very short and matches nav pattern
        if len(line) < 30 and any(keyword in line_lower for keyword in nav_keywords):
            return True
        
        # Skip if it looks like a breadcrumb
        if ' > ' in line or ' / ' in line or ' | ' in line:
            return True
        
        # Skip if it's all uppercase and short (likely a button or nav)
        if line.isupper() and len(line) < 50:
            return True
        
        return False
    
    def _extract_all_data_with_llm(self, content: str) -> Dict[str, Any]:
        """
        Use LLM to extract all structured data from the content.
        """
        # Create a comprehensive extraction prompt
        prompt = f"""Extract all relevant information from this job posting content. 
        
CONTENT:
{content}

Please extract and return a JSON object with the following structure:
{{
    "company": "company name",
    "title": "job title",
    "location": "job location (city, state/country)",
    "requirements": ["requirement 1", "requirement 2", ...],
    "nice_to_have": ["nice to have 1", "nice to have 2", ...],
    "responsibilities": ["responsibility 1", "responsibility 2", ...],
    "job_type": "one of: SDE, DS, PM, Design, Marketing, Sales, Other"
}}

INSTRUCTIONS:
1. Extract the EXACT text from the job posting - don't paraphrase
2. Requirements are mandatory qualifications (often marked as "required", "must have", "minimum")
3. Nice-to-have are optional qualifications (often marked as "preferred", "nice to have", "bonus")
4. Responsibilities are job duties and tasks
5. For job_type, analyze the title and content to determine the most appropriate category
6. If you can't find certain information, use null for that field
7. Remove bullet points and formatting, but keep the actual content
8. Each array item should be a complete, meaningful statement
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a job posting parser that extracts structured information from job descriptions. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            # Clean up the results
            result = self._clean_extracted_data(result)
            
            logger.info(f"LLM extracted data: company={result.get('company')}, title={result.get('title')}, "
                       f"requirements={len(result.get('requirements', []))}, "
                       f"nice_to_have={len(result.get('nice_to_have', []))}, "
                       f"responsibilities={len(result.get('responsibilities', []))}")
            
            return result
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}")
            return {}
    
    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize the extracted data."""
        cleaned = {}
        
        # Clean string fields
        for field in ['company', 'title', 'location', 'job_type']:
            value = data.get(field)
            if value and isinstance(value, str):
                cleaned[field] = self.normalize_text(value)
            else:
                cleaned[field] = None
        
        # Clean array fields
        for field in ['requirements', 'nice_to_have', 'responsibilities']:
            value = data.get(field)
            if value and isinstance(value, list):
                cleaned_items = []
                for item in value:
                    if isinstance(item, str) and item.strip():
                        cleaned_item = self.normalize_text(item.strip())
                        # Skip very short or generic items
                        if cleaned_item and len(cleaned_item) > 10:
                            cleaned_items.append(cleaned_item)
                cleaned[field] = cleaned_items
            else:
                cleaned[field] = []
        
        return cleaned
    
    def _determine_job_type(self, title: str, content: str) -> str:
        """Determine job type from title and content."""
        if not title and not content:
            return "Other"
        
        text = f"{title} {content}".lower()
        
        # Software engineering
        if any(term in text for term in ['software engineer', 'developer', 'sde', 'full stack', 'backend', 'frontend', 'devops']):
            return "SDE"
        
        # Data science
        if any(term in text for term in ['data scient', 'data analyst', 'machine learning', 'ai engineer', 'ml engineer']):
            return "DS"
        
        # Product management
        if any(term in text for term in ['product manager', 'product owner', 'pm', 'product lead']):
            return "PM"
        
        # Design
        if any(term in text for term in ['designer', 'ux', 'ui', 'design', 'creative']):
            return "Design"
        
        # Marketing
        if any(term in text for term in ['marketing', 'growth', 'content', 'social media', 'seo']):
            return "Marketing"
        
        # Sales
        if any(term in text for term in ['sales', 'account manager', 'business development', 'customer success']):
            return "Sales"
        
        return "Other"
