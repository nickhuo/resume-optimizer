"""
Parser factory for creating appropriate parser instances.
Now simplified to use only the universal parser.
"""
from typing import Optional
import logging

from ..utils.site_detector import JobSite, detect_site
from .base import BaseParser, ParserException
from .universal_parser import UniversalParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """Factory for creating job posting parsers."""
    
    @classmethod
    def get_parser(cls, url: str, use_universal: bool = True) -> BaseParser:
        """
        Get parser for a given URL.
        Now always returns UniversalParser but detects site for logging.
        
        Args:
            url: Job posting URL
            use_universal: Deprecated parameter, kept for compatibility
            
        Returns:
            UniversalParser instance
        """
        # Detect site for logging and future services
        site = detect_site(url)
        
        if site == JobSite.UNKNOWN:
            logger.info(f"Unknown job site for URL: {url}, using universal parser")
        else:
            logger.info(f"Detected {site.value} site for URL: {url}, using universal parser")
        
        return UniversalParser()
    
    @classmethod
    def get_universal_parser(cls) -> BaseParser:
        """
        Get universal parser instance.
        
        Returns:
            UniversalParser instance
        """
        return UniversalParser()
    
    @classmethod
    def is_supported(cls, url: str) -> bool:
        """
        Check if URL can be parsed.
        With universal parser, all URLs are supported.
        
        Args:
            url: Job posting URL
            
        Returns:
            True (always supported with universal parser)
        """
        return True  # Universal parser supports all URLs
