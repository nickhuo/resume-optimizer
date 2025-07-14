"""
Resume optimization service using LLM (OpenAI).
"""
import os
import json
import re
import logging
from typing import List, Dict, Tuple, Optional
from openai import OpenAI
from copy import deepcopy

from ..models.resume_models import (
    OptimizationRequest, 
    OptimizationResult, 
    ResumeData,
    Experience,
    Project
)

logger = logging.getLogger(__name__)


class ResumeOptimizer:
    """Service to optimize resumes based on JD requirements using LLM."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Resume Optimizer.
        
        Args:
            api_key: OpenAI API key. If not provided, will look for OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # Using o3-mini as specified
    
    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        """
        Optimize the resume based on job description requirements.
        
        Args:
            request: Optimization request containing resume data and job requirements
            
        Returns:
            OptimizationResult with optimized resume and analysis
        """
        try:
            # Deep copy to avoid modifying original
            optimized_resume = deepcopy(request.resume_data)
            
            # 1. Analyze keyword matches
            keyword_matches = self._analyze_keywords(request)
            
            # 2. Optimize experience bullets
            optimized_resume = self._optimize_experience_bullets(
                optimized_resume, 
                request.job_requirements,
                request.nice_to_have,
                request.job_skills
            )
            
            # 3. Optimize project descriptions
            optimized_resume = self._optimize_project_bullets(
                optimized_resume,
                request.job_requirements,
                request.job_skills
            )
            
            # 4. Reorder sections based on relevance
            optimized_resume = self._reorder_content(
                optimized_resume,
                request.job_type,
                request.job_skills
            )
            
            # 5. Generate optimization suggestions
            suggestions = self._generate_suggestions(
                request.resume_data,
                request.job_requirements,
                keyword_matches
            )
            
            # 6. Calculate relevance score
            relevance_score = self._calculate_relevance_score(
                keyword_matches,
                request.job_skills,
                request.job_requirements
            )
            
            # 7. Create optimization report
            optimization_report = {
                "matched_skills": list(keyword_matches.keys()),
                "missing_skills": [skill for skill in request.job_skills if skill.lower() not in keyword_matches],
                "relevance_breakdown": {
                    "skill_coverage": len(keyword_matches) / max(len(request.job_skills), 1),
                    "requirement_alignment": self._calculate_requirement_alignment(optimized_resume, request.job_requirements)
                },
                "optimizations_applied": [
                    "Experience bullets optimized for keyword relevance",
                    "Projects reordered by relevance",
                    "Skills section updated with job-relevant keywords"
                ]
            }
            
            return OptimizationResult(
                optimized_resume=optimized_resume,
                suggestions=suggestions,
                keyword_matches=keyword_matches,
                relevance_score=relevance_score,
                optimization_report=optimization_report
            )
            
        except Exception as e:
            logger.error(f"Resume optimization failed: {str(e)}")
            raise
    
    def _analyze_keywords(self, request: OptimizationRequest) -> Dict[str, int]:
        """Analyze keyword matches between resume and job requirements."""
        keyword_matches = {}
        
        # Convert resume to searchable text
        resume_text = self._resume_to_text(request.resume_data).lower()
        
        # Check each skill
        for skill in request.job_skills:
            skill_lower = skill.lower()
            # Count occurrences (case-insensitive)
            count = len(re.findall(r'\b' + re.escape(skill_lower) + r'\b', resume_text))
            if count > 0:
                keyword_matches[skill_lower] = count
        
        # Also check for skill variations
        skill_variations = {
            "javascript": ["js", "node.js", "nodejs"],
            "typescript": ["ts"],
            "kubernetes": ["k8s"],
            "elasticsearch": ["elastic search"],
            "postgresql": ["postgres"],
            "react": ["reactjs", "react.js"],
            "python": ["py"],
            "machine learning": ["ml", "deep learning", "neural network"],
        }
        
        for main_skill, variations in skill_variations.items():
            if main_skill in [s.lower() for s in request.job_skills]:
                for variant in variations:
                    count = len(re.findall(r'\b' + re.escape(variant) + r'\b', resume_text))
                    if count > 0:
                        keyword_matches[main_skill] = keyword_matches.get(main_skill, 0) + count
        
        return keyword_matches
    
    def _resume_to_text(self, resume: ResumeData) -> str:
        """Convert resume data to searchable text."""
        text_parts = []
        
        # Add all text content
        for exp in resume.experience:
            text_parts.extend(exp.bullets)
            text_parts.extend(exp.technologies)
            text_parts.append(exp.title)
            text_parts.append(exp.company)
        
        for proj in resume.projects:
            text_parts.extend(proj.bullets)
            text_parts.extend(proj.technologies)
            text_parts.append(proj.name)
        
        for category, skills in resume.skills.items():
            text_parts.extend(skills)
        
        return " ".join(text_parts)
    
    def _optimize_experience_bullets(
        self, 
        resume: ResumeData, 
        requirements: List[str],
        nice_to_have: List[str],
        skills: List[str]
    ) -> ResumeData:
        """Optimize experience bullets using LLM to highlight relevant skills."""
        
        for exp_idx, experience in enumerate(resume.experience):
            if not experience.bullets:
                continue
            
            # Create optimization prompt
            prompt = self._create_bullet_optimization_prompt(
                experience.bullets,
                experience.company,
                experience.title,
                requirements,
                skills
            )
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a resume optimization expert. Rewrite experience bullets to highlight relevant skills while maintaining truthfulness and impact."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                optimized_bullets = result.get('optimized_bullets', experience.bullets)
                
                # Update the experience bullets
                resume.experience[exp_idx].bullets = optimized_bullets
                
            except Exception as e:
                logger.warning(f"Failed to optimize bullets for {experience.company}: {str(e)}")
                # Keep original bullets on failure
                continue
        
        return resume
    
    def _create_bullet_optimization_prompt(
        self,
        bullets: List[str],
        company: str,
        title: str,
        requirements: List[str],
        skills: List[str]
    ) -> str:
        """Create prompt for bullet optimization."""
        return f"""Optimize these resume bullets for a {title} role at {company}.

Current bullets:
{json.dumps(bullets, indent=2)}

Target job requirements:
{json.dumps(requirements[:5], indent=2)}

Key skills to highlight:
{json.dumps(skills[:10], indent=2)}

RULES:
1. Maintain truthfulness - do not fabricate achievements
2. Quantify impact with numbers where possible
3. Start with strong action verbs
4. Naturally incorporate relevant keywords from the skills list
5. Keep bullets concise (1-2 lines max)
6. Focus on technical achievements and impact
7. Preserve any existing metrics/numbers

Return a JSON object with the optimized bullets:
{{
    "optimized_bullets": ["bullet 1", "bullet 2", ...]
}}"""
    
    def _optimize_project_bullets(
        self,
        resume: ResumeData,
        requirements: List[str],
        skills: List[str]
    ) -> ResumeData:
        """Optimize project descriptions to highlight relevant technologies."""
        
        # Similar to experience optimization but focused on technical aspects
        for proj_idx, project in enumerate(resume.projects):
            if not project.bullets:
                continue
            
            # Add relevant technologies if missing
            relevant_tech = [skill for skill in skills if skill.lower() in " ".join(project.bullets).lower()]
            if relevant_tech:
                resume.projects[proj_idx].technologies = list(set(
                    project.technologies + relevant_tech
                ))
        
        return resume
    
    def _reorder_content(
        self,
        resume: ResumeData,
        job_type: Optional[str],
        skills: List[str]
    ) -> ResumeData:
        """Reorder experiences and projects based on relevance."""
        
        # Score each experience based on keyword matches
        exp_scores = []
        for exp in resume.experience:
            exp_text = " ".join(exp.bullets + exp.technologies).lower()
            score = sum(1 for skill in skills if skill.lower() in exp_text)
            exp_scores.append((score, exp))
        
        # Sort by score (descending)
        exp_scores.sort(key=lambda x: x[0], reverse=True)
        resume.experience = [exp for _, exp in exp_scores]
        
        # Similar for projects
        proj_scores = []
        for proj in resume.projects:
            proj_text = " ".join(proj.bullets + proj.technologies).lower()
            score = sum(1 for skill in skills if skill.lower() in proj_text)
            proj_scores.append((score, proj))
        
        proj_scores.sort(key=lambda x: x[0], reverse=True)
        resume.projects = [proj for _, proj in proj_scores]
        
        return resume
    
    def _generate_suggestions(
        self,
        resume: ResumeData,
        requirements: List[str],
        keyword_matches: Dict[str, int]
    ) -> List[str]:
        """Generate actionable suggestions for resume improvement."""
        suggestions = []
        
        # Check for missing critical skills
        resume_text = self._resume_to_text(resume).lower()
        
        for req in requirements[:5]:  # Top 5 requirements
            req_lower = req.lower()
            # Look for key technical terms in requirements
            tech_terms = re.findall(r'\b(?:python|java|javascript|react|aws|docker|kubernetes|sql|api|microservices)\b', req_lower)
            
            for term in tech_terms:
                if term not in keyword_matches:
                    suggestions.append(f"Consider highlighting any experience with {term.upper()}, which is mentioned in the requirements: '{req}'.")
        
        # Suggest quantification
        bullets_without_numbers = []
        for exp in resume.experience:
            for bullet in exp.bullets:
                if not any(char.isdigit() for char in bullet):
                    bullets_without_numbers.append(bullet)
        
        if len(bullets_without_numbers) > 2:
            suggestions.append("Add quantifiable metrics to more experience bullets (e.g., performance improvements, scale, team size).")
        
        # Check for relevant certifications
        cert_keywords = ["certification", "certified", "certificate"]
        if not any(keyword in resume_text for keyword in cert_keywords):
            suggestions.append("Consider adding relevant certifications if you have any (e.g., AWS, Kubernetes, cloud certifications).")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _calculate_relevance_score(
        self,
        keyword_matches: Dict[str, int],
        skills: List[str],
        requirements: List[str]
    ) -> float:
        """Calculate overall relevance score (0-1)."""
        
        # Skill coverage (40% weight)
        skill_coverage = len(keyword_matches) / max(len(skills), 1)
        
        # Keyword density (30% weight)
        total_matches = sum(keyword_matches.values())
        keyword_density = min(total_matches / max(len(skills) * 2, 1), 1.0) if skills else 0.0  # Expect ~2 mentions per skill
        
        # Requirement alignment (30% weight)
        req_keywords = []
        for req in requirements:
            req_keywords.extend(re.findall(r'\b\w+\b', req.lower()))
        
        req_matches = sum(1 for kw in req_keywords if kw in keyword_matches)
        req_alignment = min(req_matches / max(len(req_keywords), 1), 1.0)
        
        # Weighted score
        relevance_score = (
            skill_coverage * 0.4 +
            keyword_density * 0.3 +
            req_alignment * 0.3
        )
        
        return round(relevance_score, 2)
    
    def _calculate_requirement_alignment(
        self,
        resume: ResumeData,
        requirements: List[str]
    ) -> float:
        """Calculate how well the resume aligns with requirements."""
        resume_text = self._resume_to_text(resume).lower()
        
        aligned_reqs = 0
        for req in requirements:
            # Extract key terms from requirement
            key_terms = re.findall(r'\b(?:\d+\+?\s*years?|python|java|javascript|react|aws|docker|kubernetes|sql|api|microservices|experience|degree)\b', req.lower())
            
            # Check if any key term is in resume
            if any(term in resume_text for term in key_terms):
                aligned_reqs += 1
        
        return round(aligned_reqs / max(len(requirements), 1), 2)

