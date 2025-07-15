"""
Site detector for identifying job board platforms from URLs.
"""
import re
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


class JobSite(Enum):
    """Supported job board platforms."""
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    LEVER = "lever"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ANGELLIST = "angellist"
    RIPPLING = "rippling"
    UNKNOWN = "unknown"


class SiteDetector:
    """Detect job board platform from URL patterns."""
    
    # URL patterns for each job site
    PATTERNS = {
        JobSite.GREENHOUSE: [
            r"greenhouse\.io",
            r"boards\.greenhouse\.io",
            r"jobs\.greenhouse\.io"
        ],
        JobSite.WORKDAY: [
            r"myworkdayjobs\.com",
            r"workday\.com",
            r"wd\d+\.myworkdayjobs\.com"
        ],
        JobSite.LEVER: [
            r"lever\.co",
            r"jobs\.lever\.co"
        ],
        JobSite.LINKEDIN: [
            r"linkedin\.com/jobs",
            r"linkedin\.com/in/jobs"
        ],
        JobSite.INDEED: [
            r"indeed\.com",
            r"indeed\.[a-z]{2,3}"  # indeed.co.uk, indeed.ca, etc.
        ],
        JobSite.GLASSDOOR: [
            r"glassdoor\.com",
            r"glassdoor\.[a-z]{2,3}"
        ],
        JobSite.ANGELLIST: [
            r"angel\.co",
            r"angellist\.com",
            r"wellfound\.com"  # AngelList rebranded to Wellfound
        ],
        JobSite.RIPPLING: [
            r"ats\.rippling\.com",
            r"rippling\.com/jobs",
            r"jobs\.rippling\.com"
        ]
    }
    
    @classmethod
    def detect_site(cls, url: str) -> JobSite:
        """
        Detect job site from URL.
        
        Args:
            url: Job posting URL
            
        Returns:
            JobSite enum value
        """
        if not url:
            return JobSite.UNKNOWN
        
        # Parse URL to get domain
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            full_url = url.lower()
        except Exception:
            return JobSite.UNKNOWN
        
        # Check each pattern
        for site, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, domain) or re.search(pattern, full_url):
                    return site
        
        return JobSite.UNKNOWN
    
    @classmethod
    def is_supported(cls, url: str) -> bool:
        """Check if URL is from a supported job site."""
        site = cls.detect_site(url)
        return site != JobSite.UNKNOWN
    
    @classmethod
    def get_parser_class(cls, site: JobSite):
        """
        Get parser class for a specific job site.
        
        Note: This will be implemented when parsers are created.
        """
        parser_map = {
            JobSite.GREENHOUSE: "GreenhouseParser",
            JobSite.WORKDAY: "WorkdayParser",
            JobSite.LEVER: "LeverParser",
            JobSite.LINKEDIN: "LinkedInParser",
            JobSite.RIPPLING: "RipplingParser",
            # Add more as implemented
        }
        return parser_map.get(site)


def detect_site(url: str) -> JobSite:
    """Convenience function to detect job site."""
    return SiteDetector.detect_site(url)
