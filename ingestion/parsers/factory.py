"""
Parser factory for creating appropriate parser instances.
"""
from typing import Optional
import logging

from ..utils.site_detector import JobSite, detect_site
from .base import BaseParser, ParserException
from .greenhouse import GreenhouseParser
from .workday import WorkdayParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating job posting parsers."""
    
    # Mapping of job sites to parser classes
    PARSER_MAP = {
        JobSite.GREENHOUSE: GreenhouseParser,
        JobSite.WORKDAY: WorkdayParser,
        # Additional parsers can be added here
        # JobSite.LEVER: LeverParser,
        # JobSite.LINKEDIN: LinkedInParser,
    }
    
    @classmethod
    def get_parser(cls, url: str) -> BaseParser:
        """
        Get appropriate parser for a given URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            Parser instance
            
        Raises:
            ParserException: If no parser available for the site
        """
        site = detect_site(url)
        
        if site == JobSite.UNKNOWN:
            raise ParserException(f"Unknown job site for URL: {url}")
        
        parser_class = cls.PARSER_MAP.get(site)
        
        if not parser_class:
            raise ParserException(f"No parser implemented for {site.value} yet")
        
        logger.info(f"Using {parser_class.__name__} for {url}")
        return parser_class()
    
    @classmethod
    def is_supported(cls, url: str) -> bool:
        """
        Check if URL can be parsed.
        
        Args:
            url: Job posting URL
            
        Returns:
            True if parser is available
        """
        site = detect_site(url)
        return site != JobSite.UNKNOWN and site in cls.PARSER_MAP
