"""
Base parser class for job description extraction.
"""
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging

from ..models.job import JDModel

logger = logging.getLogger(__name__)


class ParserException(Exception):
    """Exception raised during parsing operations."""
    pass


class BaseParser(ABC):
    """Abstract base class for job description parsers."""
    
    def __init__(self, timeout: int = 10, use_llm: bool = True):
        self.timeout = timeout
        self.use_llm = use_llm
        self.llm_parser = None
        
        # Initialize LLM parser if requested
        if self.use_llm:
            try:
                from .llm_parser import LLMParser
                self.llm_parser = LLMParser()
                logger.info("LLM parser initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM parser: {str(e)}. Falling back to traditional parsing.")
                self.llm_parser = None
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url: str) -> str:
        """
        Fetch page content from URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            HTML content as string
            
        Raises:
            ParserException: If page cannot be fetched
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ParserException(f"Failed to fetch page: {str(e)}")
    
    @abstractmethod
    def parse(self, url: str) -> JDModel:
        """
        Parse job description from URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            JDModel instance with parsed data
        """
        pass
    
    def extract_skills(self, text: str) -> List[str]:
        """
        Extract technical skills and keywords from text.
        This is a basic implementation that can be overridden or enhanced with LLM.
        
        Args:
            text: Job description text
            
        Returns:
            List of extracted skills/keywords
        """
        # Common technical skills and keywords patterns
        skill_patterns = [
            # Programming languages
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin|Scala|R)\b',
            # Web frameworks
            r'\b(React|Angular|Vue|Django|Flask|Spring|Rails|Express|FastAPI|Next\.js|Nuxt)\b',
            # Databases
            r'\b(SQL|NoSQL|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Cassandra|DynamoDB)\b',
            # Cloud platforms
            r'\b(AWS|Azure|GCP|Google Cloud|Kubernetes|Docker|CI/CD|DevOps)\b',
            # Data/ML
            r'\b(Machine Learning|Deep Learning|TensorFlow|PyTorch|Pandas|NumPy|Spark|Hadoop)\b',
            # Other technical terms
            r'\b(REST|GraphQL|Microservices|API|Git|Linux|Agile|Scrum)\b',
        ]
        
        skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(match.lower() for match in matches)
        
        # Also extract years of experience requirements
        exp_pattern = r'(\d+)\+?\s*years?\s*(?:of\s*)?experience'
        exp_matches = re.findall(exp_pattern, text, re.IGNORECASE)
        for years in exp_matches:
            skills.add(f"{years}+ years experience")
        
        return sorted(list(skills))
    
    def normalize_text(self, text: Optional[str]) -> Optional[str]:
        """
        Normalize text by stripping whitespace and handling None values.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text or None
        """
        if not text:
            return None
        return text.strip()
    
    def parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string to datetime object.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            datetime object or None
        """
        if not date_str:
            return None
        
        # Common date formats
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # If no format matches, try relative dates
        if "today" in date_str.lower():
            return datetime.now()
        elif "yesterday" in date_str.lower():
            from datetime import timedelta
            return datetime.now() - timedelta(days=1)
        
        return None
    
    def clean_requirements(self, requirements: List[str]) -> List[str]:
        """
        Clean and normalize requirement strings.
        
        Args:
            requirements: List of raw requirement strings
            
        Returns:
            Cleaned list of requirements
        """
        cleaned = []
        for req in requirements:
            if req:
                # Remove leading bullets, numbers, etc.
                req = re.sub(r'^[\s\-\*\•\d\.]+', '', req)
                req = req.strip()
                if req and len(req) > 5:  # Filter out very short strings
                    cleaned.append(req)
        return cleaned
