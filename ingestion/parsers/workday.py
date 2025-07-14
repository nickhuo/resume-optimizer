"""
Parser for Workday job postings.
"""
import json
import re
import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from .base import BaseParser, ParserException
from ..models.job import JDModel

logger = logging.getLogger(__name__)


class WorkdayParser(BaseParser):
    """Parser for Workday job board postings."""

    def parse(self, url: str) -> JDModel:
        """
        Parse Workday job posting.

        Workday postings can be identified by an inline JSON within a <script> tag.
        """
        try:
            html = self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')

            # First try to extract data from JSON script tag
            jd_data = self._extract_json(soup)
            
            if jd_data:
                # Populate from JSON-LD data
                company = self.normalize_text(jd_data.get('hiringOrganization', {}).get('name'))
                title = self.normalize_text(jd_data.get('title'))
                
                # Try different location formats
                job_location = jd_data.get('jobLocation', {})
                if isinstance(job_location, dict):
                    address = job_location.get('address', {})
                    if isinstance(address, dict):
                        location = self.normalize_text(
                            address.get('addressLocality') or 
                            address.get('addressRegion') or
                            address.get('addressCountry')
                        )
                    else:
                        location = self.normalize_text(str(address))
                else:
                    location = None
                    
                description = jd_data.get('description', '')
            else:
                # Fallback to HTML parsing
                company = self._extract_company_from_html(soup)
                title = self._extract_title_from_html(soup)
                location = self._extract_location_from_html(soup)
                description = self._extract_description_from_html(soup)

            # Debug: Log description content
            logger.info(f"Description found: {bool(description)}")
            if description:
                logger.info(f"Description length: {len(description)}")
                # Save description to file for analysis
                with open('workday_description.txt', 'w', encoding='utf-8') as f:
                    f.write(description)
                logger.info("Saved description to workday_description.txt")
            
            # Extract skills/keywords
            skills = self.extract_skills(description) if description else []

            # Requirements, nice-to-have, and responsibilities
            requirements, nice_to_have, responsibilities = self._parse_requirements(description) if description else ([], [], [])
            
            # Determine job type
            job_type = self._determine_job_type(title or '', description or '')
            
            return JDModel(
                company=company or "Unknown Company",
                title=title or "Unknown Title",
                location=location,
                requirements=requirements,
                nice_to_have=nice_to_have,
                responsibilities=responsibilities,
                skills=skills,
                job_type=job_type
            )

        except Exception as e:
            logger.error(f"Failed to parse Workday URL {url}: {str(e)}")
            raise ParserException(f"Failed to parse Workday posting: {str(e)}")

    def _extract_json(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract JSON data from a script tag."""
        script = soup.find('script', type='application/ld+json')
        if script:
            try:
                return json.loads(script.string)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decoding error: {str(e)}")
                return None
        return None

    def _extract_company_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company name from HTML."""
        # Try common patterns for company name
        selectors = [
            ('meta', {'property': 'og:site_name'}),
            ('meta', {'name': 'twitter:site'}),
            ('div', {'class': 'company-name'}),
            ('h1', {'class': 'company'}),
        ]
        
        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem:
                if tag == 'meta':
                    return self.normalize_text(elem.get('content'))
                else:
                    return self.normalize_text(elem.get_text())
        
        return None
    
    def _extract_title_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract job title from HTML."""
        # Try common patterns for job title
        selectors = [
            ('h1', {'data-automation-id': 'jobPostingHeader'}),
            ('h1', {'class': 'job-title'}),
            ('meta', {'property': 'og:title'}),
            ('title', {}),
        ]
        
        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem:
                if tag == 'meta':
                    return self.normalize_text(elem.get('content'))
                else:
                    return self.normalize_text(elem.get_text())
        
        return None
    
    def _extract_location_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract location from HTML."""
        # Try common patterns for location
        selectors = [
            ('div', {'data-automation-id': 'jobPostingLocation'}),
            ('span', {'class': 'job-location'}),
            ('div', {'class': 'location'}),
        ]
        
        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem:
                return self.normalize_text(elem.get_text())
        
        return None
    
    def _extract_description_from_html(self, soup: BeautifulSoup) -> str:
        """Extract job description from HTML."""
        # Try common patterns for job description
        selectors = [
            ('div', {'data-automation-id': 'jobPostingDescription'}),
            ('div', {'class': 'job-description'}),
            ('section', {'class': 'job-details'}),
        ]
        
        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem:
                return elem.get_text(separator='\n')
        
        # Fallback to body text
        return soup.get_text(separator='\n')

    def _parse_requirements(self, description: str) -> tuple[List[str], List[str], List[str]]:
        """Parse requirements, nice-to-have, and responsibilities from description."""
        if not description:
            return ([], [], [])

        # Clean up special characters
        description = description.replace('â¯', ' ').replace('&amp;', '&')
        
        # Try LLM parsing first if available
        if self.llm_parser:
            logger.info("Attempting LLM-based requirement extraction for Workday")
            llm_requirements, llm_nice_to_have, llm_responsibilities = self.llm_parser.extract_requirements(description)
            
            if llm_requirements or llm_nice_to_have or llm_responsibilities:
                logger.info(f"LLM successfully extracted {len(llm_requirements)} requirements, {len(llm_nice_to_have)} nice-to-have items, and {len(llm_responsibilities)} responsibilities")
                return (llm_requirements, llm_nice_to_have, llm_responsibilities)
            else:
                logger.info("LLM extraction returned empty results, falling back to traditional parsing")
        
        # Traditional parsing as fallback
        requirements = []
        nice_to_have = []
        
        # For Workday, content is often in a single line with sentence breaks
        # Try to split by common sentence patterns
        sentences = re.split(r'(?<=[.!?])\s+', description)
        
        # Look for qualification sections
        in_qualifications = False
        in_nice_to_have = False
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
                
            sent_lower = sent.lower()
            
            # Check for section markers
            if any(marker in sent_lower for marker in ['general qualifications', 'required skills', 'requirements', 'must have']):
                in_qualifications = True
                in_nice_to_have = False
                continue
            elif any(marker in sent_lower for marker in ['nice to have', 'preferred', 'bonus', 'optional']):
                in_qualifications = False
                in_nice_to_have = True
                continue
            elif any(marker in sent_lower for marker in ['critical qualities', 'application process', 'how to apply']):
                break  # Stop parsing at these sections
                
            # Handle the case where "Nice to have:" appears within a sentence
            if 'nice to have:' in sent_lower:
                # Split the sentence at "Nice to have:"
                parts = re.split(r'nice to have:', sent, flags=re.IGNORECASE)
                if len(parts) > 1:
                    # Process the part before "Nice to have:" as requirements
                    req_part = parts[0].strip()
                    if req_part:
                        # Split by semicolons for individual requirements
                        sub_requirements = re.split(r'[;]', req_part)
                        for req in sub_requirements:
                            req = req.strip()
                            if req and len(req) > 15 and not self._is_obvious_benefit(req):
                                requirements.append(req)
                    
                    # Process the part after "Nice to have:" as nice-to-have items
                    nice_part = parts[1].strip()
                    if nice_part:
                        # Split by semicolons for individual items
                        sub_items = re.split(r'[;]', nice_part)
                        for item in sub_items:
                            item = item.strip()
                            if item and len(item) > 15:
                                nice_to_have.append(item)
                    continue
            
            # Extract requirements from qualification sections
            if in_qualifications and len(sent) > 20:
                # Split by semicolons for individual requirements
                sub_requirements = re.split(r'[;]', sent)
                for req in sub_requirements:
                    req = req.strip()
                    if req and len(req) > 15 and not self._is_obvious_benefit(req):
                        requirements.append(req)
            
            # Extract nice-to-have items
            elif in_nice_to_have and len(sent) > 20:
                # Split by semicolons for individual items
                sub_items = re.split(r'[;]', sent)
                for item in sub_items:
                    item = item.strip()
                    if item and len(item) > 15:
                        nice_to_have.append(item)
            
            # Also look for requirement patterns in any sentence (if not in nice-to-have section)
            elif not in_nice_to_have and self._looks_like_requirement(sent) and len(sent) > 20:
                if not self._is_obvious_benefit(sent):
                    requirements.append(sent)

        # Debug: Log what we're finding
        logger.info(f"Found {len(requirements)} requirements and {len(nice_to_have)} nice-to-have items in structured parsing")
        
        # If still no requirements found, try to extract all potential requirements
        if not requirements and not nice_to_have:
            logger.info("No requirements found, trying fallback parsing...")
            # Split by newlines for line-based parsing
            lines = description.split('\n')
            bullet_count = 0
            in_nice_to_have_section = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for nice-to-have section headers
                line_lower = line.lower()
                if any(marker in line_lower for marker in ['nice to have:', 'preferred:', 'bonus:', 'optional:']):
                    in_nice_to_have_section = True
                    logger.info(f"Found nice-to-have section: {line}")
                    continue
                elif any(marker in line_lower for marker in ['general qualifications:', 'requirements:', 'required skills:', 'must have:']):
                    in_nice_to_have_section = False
                    logger.info(f"Found requirements section: {line}")
                    continue
                
                # Look for bullet points that might be requirements or nice-to-have
                if re.match(r'^[\-\*\•]+\s*.+', line) and len(line) > 15:
                    bullet_count += 1
                    # Clean the bullet point (only remove bullet symbols, not numbers)
                    cleaned_line = re.sub(r'^[\-\*\•]+\s*', '', line).strip()
                    
                    if in_nice_to_have_section:
                        nice_to_have.append(cleaned_line)
                    elif self._looks_like_requirement(line) and not self._is_obvious_benefit(line):
                        requirements.append(cleaned_line)
            
            logger.info(f"Found {bullet_count} bullet points, {len(requirements)} requirements, {len(nice_to_have)} nice-to-have")
            
            # If no bullet points, try another approach
            if bullet_count == 0:
                logger.info("No bullet points found, looking for requirement-like sentences...")
                in_nice_to_have_section = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    line_lower = line.lower()
                    if any(marker in line_lower for marker in ['nice to have:', 'preferred:', 'bonus:', 'optional:']):
                        in_nice_to_have_section = True
                        continue
                    elif any(marker in line_lower for marker in ['general qualifications:', 'requirements:', 'required skills:', 'must have:']):
                        in_nice_to_have_section = False
                        continue
                        
                    if line and len(line) > 20:
                        if in_nice_to_have_section:
                            nice_to_have.append(line)
                        elif self._looks_like_requirement(line):
                            requirements.append(line)

        return (self.clean_requirements(requirements), self.clean_requirements(nice_to_have), [])

    def _determine_job_type(self, title: str, description: str) -> Optional[str]:
        """Determine job type from title and description."""
        text = f"{title} {description}".lower()

        if any(term in text for term in ['machine learning', 'ml engineer', 'ai engineer', 'deep learning']):
            return "AI"
        elif any(term in text for term in ['data scientist', 'data science']):
            return "DS"
        elif any(term in text for term in ['data engineer', 'etl', 'data pipeline']):
            return "DE"
        elif any(term in text for term in ['software engineer', 'software developer', 'backend', 'frontend', 'full stack']):
            return "SDE"

        return None
    
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

