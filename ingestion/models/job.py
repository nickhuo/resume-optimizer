"""
Job data models using Pydantic for validation and serialization.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class JobRow(BaseModel):
    """Represents a job entry from Notion database."""
    page_id: str
    jd_id: Optional[int] = Field(None, description="Job ID in database")
    jd_link: Optional[HttpUrl] = Field(None, description="Job posting URL")
    company: Optional[str] = None
    title: Optional[str] = None
    status: str = Field(default="TODO", pattern="^(TODO|Processing|Parsed|Error|Filling|Submitted|Failed)$")
    llm_notes: Optional[str] = None
    last_error: Optional[str] = None
    my_notes: Optional[str] = None
    created_time: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            HttpUrl: str,
            datetime: lambda v: v.isoformat() if v else None
        }


class JDModel(BaseModel):
    """Structured job description data after parsing."""
    company: str
    title: str
    location: Optional[str] = None
    requirements: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    posted_date: Optional[datetime] = None
    job_type: Optional[str] = None  # SDE/AI/DS/DE
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
