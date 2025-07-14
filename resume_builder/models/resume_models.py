"""
Data models for resume building and optimization.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Education(BaseModel):
    """Education entry model."""
    school: str
    degree: str
    field: str
    location: str
    start_date: str
    end_date: str
    gpa: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class Experience(BaseModel):
    """Work experience entry model."""
    company: str
    title: str
    location: str
    start_date: str
    end_date: str
    description: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class Project(BaseModel):
    """Project entry model."""
    name: str
    technologies: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class ResumeData(BaseModel):
    """Complete resume data model."""
    # Personal info
    name: str
    email: str
    phone: str
    github: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    
    # Sections
    education: List[Education] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    skills: Dict[str, List[str]] = Field(default_factory=dict)  # e.g., {"Programming": ["Python", "Go"]}
    
    # Metadata
    target_role: Optional[str] = None
    footnote: Optional[str] = None


class OptimizationRequest(BaseModel):
    """Request model for resume optimization."""
    resume_data: ResumeData
    job_requirements: List[str]
    nice_to_have: List[str] = Field(default_factory=list)
    job_skills: List[str] = Field(default_factory=list)
    company: str
    title: str
    job_type: Optional[str] = None  # SDE/AI/DS/DE


class OptimizationResult(BaseModel):
    """Result model for resume optimization."""
    optimized_resume: ResumeData
    suggestions: List[str] = Field(default_factory=list)
    keyword_matches: Dict[str, int] = Field(default_factory=dict)
    relevance_score: float = Field(ge=0, le=1)
    optimization_report: Dict[str, Any] = Field(default_factory=dict)
