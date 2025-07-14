"""
LLM-based parser for extracting requirements and nice-to-have items from job descriptions.
"""
import os
import json
import logging
from typing import List, Tuple, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMParser:
    """LLM-based parser using OpenAI GPT-4o-mini for requirement extraction."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM parser.
        
        Args:
            api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"
    
    def extract_requirements(self, description: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Extract requirements, nice-to-have items, and responsibilities from job description using LLM.
        
        Args:
            description: The job description text
            
        Returns:
            Tuple of (requirements, nice_to_have, responsibilities) lists
        """
        if not description:
            return ([], [], [])
        
        prompt = self._create_extraction_prompt(description)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a job description parser. Extract requirements, nice-to-have items, and responsibilities from job descriptions. Preserve the original wording as much as possible."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for more consistent results
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            requirements = result.get('requirements', [])
            nice_to_have = result.get('nice_to_have', [])
            responsibilities = result.get('responsibilities', [])
            
            logger.info(f"LLM extracted {len(requirements)} requirements, {len(nice_to_have)} nice-to-have items, and {len(responsibilities)} responsibilities")
            
            return (requirements, nice_to_have, responsibilities)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {str(e)}")
            # Return empty lists on failure, let traditional parser handle it
            return ([], [], [])
    
    def _create_extraction_prompt(self, description: str) -> str:
        """Create the prompt for requirement extraction."""
        return f"""Extract job requirements, nice-to-have items, and responsibilities from the following job description.

IMPORTANT RULES:
1. Preserve the EXACT original wording from the job description
2. Each item should be a complete, self-contained statement
3. Do not paraphrase or summarize - use the exact text from the description
4. Requirements are mandatory qualifications (often marked with "required", "must have", "minimum", etc.)
5. Nice-to-have are optional/preferred qualifications (often marked with "nice to have", "preferred", "bonus", "plus", etc.)
6. Responsibilities are job duties and tasks (often marked with "responsibilities", "duties", "will be responsible for", "you will", etc.)
7. If a bullet point contains multiple items, keep them together as one item
8. Remove only the bullet symbols (•, -, *, etc.) but keep everything else
9. Ignore benefits, perks, and compensation information

Job Description:
{description}

Return a JSON object with three arrays:
{{
    "requirements": ["exact requirement text 1", "exact requirement text 2", ...],
    "nice_to_have": ["exact nice-to-have text 1", "exact nice-to-have text 2", ...],
    "responsibilities": ["exact responsibility text 1", "exact responsibility text 2", ...]
}}
"""
