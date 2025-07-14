"""
Parser for Greenhouse job postings.
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup
import logging

from .base import BaseParser, ParserException
from ..models.job import JDModel

logger = logging.getLogger(__name__)


class GreenhouseParser(BaseParser):
    """Parser for Greenhouse job board postings."""
    
    def parse(self, url: str) -> JDModel:
        """
        Parse Greenhouse job posting.
        
        Greenhouse structure typically includes:
        - Company name in header or og:site_name meta tag
        - Job title in h1 or og:title
        - Location in div.location or similar
        - Requirements in section#content or div.content
        """
        try:
            html = self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract company name
            company = self._extract_company(soup)
            if not company:
                # Try to extract from URL pattern (e.g., boards.greenhouse.io/companyname/)
                match = re.search(r'boards\.greenhouse\.io/([^/]+)', url)
                if match:
                    company = match.group(1).replace('-', ' ').title()
            
            # Extract job title
            title = self._extract_title(soup)
            
            # Extract location
            location = self._extract_location(soup)
            
            # Extract job content
            content_text = self._extract_content(soup)
            
            # Parse requirements, nice-to-haves, and responsibilities
            requirements, nice_to_have, responsibilities = self._parse_requirements(soup, content_text)
            
            # Extract skills/keywords
            skills = self.extract_skills(content_text)
            
            # Try to determine job type
            job_type = self._determine_job_type(title, content_text)
            
            return JDModel(
                company=company or "Unknown Company",
                title=title or "Unknown Position",
                location=location,
                requirements=requirements,
                nice_to_have=nice_to_have,
                responsibilities=responsibilities,
                skills=skills,
                job_type=job_type
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Greenhouse URL {url}: {str(e)}")
            raise ParserException(f"Failed to parse Greenhouse posting: {str(e)}")
    
    def _extract_company(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company name from page."""
        # Try meta tag
        meta_company = soup.find('meta', {'property': 'og:site_name'})
        if meta_company and meta_company.get('content'):
            return self.normalize_text(meta_company['content'])
        
        # Try company name in header
        company_elem = soup.find('div', class_='company-name')
        if company_elem:
            return self.normalize_text(company_elem.get_text())
        
        # Try header image alt text
        header_img = soup.find('img', class_='logo')
        if header_img and header_img.get('alt'):
            return self.normalize_text(header_img['alt'])
        
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract job title from page."""
        # Try h1 tag first
        h1 = soup.find('h1')
        if h1:
            return self.normalize_text(h1.get_text())
        
        # Try meta tag
        meta_title = soup.find('meta', {'property': 'og:title'})
        if meta_title and meta_title.get('content'):
            return self.normalize_text(meta_title['content'])
        
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text()
            # Remove company name suffix if present
            if ' at ' in title_text:
                return self.normalize_text(title_text.split(' at ')[0])
            return self.normalize_text(title_text)
        
        return None
    
    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract job location from page."""
        # Common location selectors
        location_selectors = [
            ('div', {'class': 'location'}),
            ('span', {'class': 'location'}),
            ('div', {'class': 'job-location'}),
            ('p', {'class': 'location'}),
        ]
        
        for tag, attrs in location_selectors:
            elem = soup.find(tag, attrs)
            if elem:
                return self.normalize_text(elem.get_text())
        
        # Try to find location in header area
        header = soup.find('div', {'id': 'header'}) or soup.find('header')
        if header:
            # Look for text patterns like "San Francisco, CA"
            text = header.get_text()
            location_pattern = r'([A-Z][a-z]+(?: [A-Z][a-z]+)*(?:,? [A-Z]{2})?)'
            match = re.search(location_pattern, text)
            if match:
                return self.normalize_text(match.group(1))
        
        return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main job description content."""
        # Try common content containers
        content_selectors = [
            ('div', {'id': 'content'}),
            ('section', {'id': 'content'}),
            ('div', {'class': 'content'}),
            ('div', {'class': 'job-description'}),
            ('div', {'class': 'description'}),
        ]
        
        for tag, attrs in content_selectors:
            content = soup.find(tag, attrs)
            if content:
                return content.get_text(separator='\n')
        
        # If no specific content div, try to get all text
        return soup.get_text(separator='\n')
    
    def _parse_requirements(self, soup: BeautifulSoup, content_text: str) -> tuple[List[str], List[str], List[str]]:
        """Parse requirements, nice-to-have sections, and responsibilities."""
        # Try LLM parsing first if available
        if self.llm_parser and content_text:
            logger.info("Attempting LLM-based requirement extraction for Greenhouse")
            llm_requirements, llm_nice_to_have, llm_responsibilities = self.llm_parser.extract_requirements(content_text)
            
            if llm_requirements or llm_nice_to_have or llm_responsibilities:
                logger.info(f"LLM successfully extracted {len(llm_requirements)} requirements, {len(llm_nice_to_have)} nice-to-have items, and {len(llm_responsibilities)} responsibilities")
                return (llm_requirements, llm_nice_to_have, llm_responsibilities)
            else:
                logger.info("LLM extraction returned empty results, falling back to traditional parsing")
        
        # Traditional parsing as fallback
        requirements = []
        nice_to_have = []
        
        # Look for specific sections
        content_div = soup.find('div', {'id': 'content'}) or soup.find('section', {'id': 'content'})
        
        if content_div:
            # Find all list items
            current_section = "requirements"  # Default to requirements
            
            for elem in content_div.find_all(['h2', 'h3', 'h4', 'ul', 'ol']):
                if elem.name in ['h2', 'h3', 'h4']:
                    header_text = elem.get_text().lower()
                    if any(term in header_text for term in ['nice to have', 'preferred', 'bonus', 'plus']):
                        current_section = "nice_to_have"
                    elif any(term in header_text for term in ['requirement', 'qualification', 'must have', 'looking for']):
                        current_section = "requirements"
                    elif any(term in header_text for term in ['benefit', 'compensation', 'perks', 'what we offer', 'our benefits']):
                        current_section = "skip"  # Skip benefits section
                
                elif elem.name in ['ul', 'ol']:
                    items = [li.get_text() for li in elem.find_all('li')]
                    # Only filter out obvious benefits
                    filtered_items = [item for item in items if not self._is_obvious_benefit(item)]
                    
                    if current_section == "requirements":
                        requirements.extend(filtered_items)
                    elif current_section == "nice_to_have":
                        nice_to_have.extend(filtered_items)
        
        # If no structured lists found, try to parse from text
        if not requirements:
            lines = content_text.split('\n')
            in_requirements = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for section headers
                line_lower = line.lower()
                if any(term in line_lower for term in ['requirement', 'qualification', 'you have', 'you will']):
                    in_requirements = True
                    continue
                elif any(term in line_lower for term in ['nice to have', 'preferred', 'bonus']):
                    in_requirements = False
                    continue
                
                # Check if line looks like a requirement (starts with bullet, number, etc.)
                if re.match(r'^[\-\*\•\d\.]+\s*.+', line) and len(line) > 10:
                    # Only filter out obvious benefits
                    if not self._is_obvious_benefit(line):
                        if in_requirements:
                            requirements.append(line)
                        else:
                            nice_to_have.append(line)
        
        return (self.clean_requirements(requirements), self.clean_requirements(nice_to_have), [])
    
    def _determine_job_type(self, title: str, content: str) -> Optional[str]:
        """Determine job type from title and content."""
        text = f"{title} {content}".lower()
        
        if any(term in text for term in ['machine learning', 'ml engineer', 'ai engineer', 'deep learning']):
            return "AI"
        elif any(term in text for term in ['data scientist', 'data science']):
            return "DS"
        elif any(term in text for term in ['data engineer', 'etl', 'data pipeline']):
            return "DE"
        elif any(term in text for term in ['software engineer', 'software developer', 'backend', 'frontend', 'full stack']):
            return "SDE"
        
        return None
    
    def _is_benefit_item(self, text: str) -> bool:
        """Check if a text line describes benefits rather than requirements."""
        text_lower = text.lower()
        
        # Common benefit keywords
        benefit_keywords = [
            'compensation', 'salary', 'package', 'benefits', 'perks',
            'free', 'housing', 'accommodation', 'breakfast', 'lunch', 'snacks',
            'networking', 'social events', 'broadway', 'escape rooms', 'cooking classes',
            'opportunities to learn', 'mentors', 'alma mater', 'institutions',
            'health insurance', 'dental', 'vision', '401k', 'retirement',
            'vacation', 'pto', 'time off', 'flexible', 'remote work',
            'gym', 'fitness', 'wellness', 'stipend', 'reimbursement'
        ]
        
        # Check if text contains benefit keywords
        return any(keyword in text_lower for keyword in benefit_keywords)
    
    def _filter_benefits(self, items: List[str]) -> List[str]:
        """Filter out benefit items from a list of strings."""
        return [item for item in items if not self._is_benefit_item(item)]
    
    def _is_obvious_benefit(self, text: str) -> bool:
        """Check if a text line is obviously a benefit (conservative filtering)."""
        text_lower = text.lower()
        
        # Only filter very obvious benefit keywords
        obvious_benefit_keywords = [
            'competitive compensation', 'salary range', 'benefits package',
            'free breakfast', 'free lunch', 'free snacks', 
            'housing accommodation', 'broadway shows', 'escape rooms', 'cooking classes',
            'networking events', 'social events'
        ]
        
        # Check if text contains obvious benefit keywords
        return any(keyword in text_lower for keyword in obvious_benefit_keywords)
    
    def _looks_like_requirement(self, text: str) -> bool:
        """Check if a text line looks like a job requirement."""
        text_lower = text.lower()
        
        # Technical requirement indicators
        requirement_indicators = [
            'experience', 'proficiency', 'knowledge', 'skilled', 'familiar',
            'degree', 'bachelor', 'master', 'phd', 'certification',
            'python', 'java', 'javascript', 'sql', 'aws', 'docker', 'kubernetes',
            'years', 'minimum', 'required', 'must', 'should', 'ability to',
            'understanding of', 'working knowledge', 'hands-on', 'expertise'
        ]
        
        return any(indicator in text_lower for indicator in requirement_indicators)
