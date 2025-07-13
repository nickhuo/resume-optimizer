"""
Notion API service for interacting with the job database.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from notion_client import Client
from notion_client.errors import APIResponseError

from ..settings import Settings
from ..models.job import JobRow

logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion database."""
    
    def __init__(self, token: Optional[str] = None, database_id: Optional[str] = None):
        """Initialize Notion client with credentials."""
        self.token = token or Settings.NOTION_TOKEN
        self.database_id = database_id or Settings.DATABASE_ID
        
        if not self.token or not self.database_id:
            raise ValueError("Notion token and database ID are required")
            
        self.client = Client(auth=self.token)
        logger.info(f"Initialized Notion client for database: {self.database_id[:8]}...")
    
    def fetch_jobs(self, status: str = "TODO", limit: int = 100) -> List[JobRow]:
        """
        Fetch job entries from Notion database.
        
        Args:
            status: Filter by job status (TODO, Processing, etc.)
            limit: Maximum number of entries to fetch
            
        Returns:
            List of JobRow objects
        """
        try:
            logger.info(f"Fetching jobs with status: {status}")
            
            # Build filter
            filter_params = {}
            if status:
                filter_params = {
                    "filter": {
                        "property": "Status",
                        "select": {
                            "equals": status
                        }
                    }
                }
            
            # Query database
            response = self.client.databases.query(
                database_id=self.database_id,
                page_size=min(limit, 100),
                **filter_params
            )
            
            jobs = []
            for page in response["results"]:
                try:
                    job = self._parse_job_page(page)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.error(f"Failed to parse page {page.get('id')}: {e}")
                    continue
            
            logger.info(f"Fetched {len(jobs)} jobs")
            return jobs
            
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching jobs: {e}")
            raise
    
    def update_job(self, page_id: str, **fields) -> bool:
        """
        Update job entry in Notion.
        
        Args:
            page_id: Notion page ID
            **fields: Fields to update (status, last_error, llm_notes, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Updating job {page_id} with fields: {list(fields.keys())}")
            
            properties = {}
            
            # Map fields to Notion properties
            if "status" in fields:
                properties["Status"] = {
                    "select": {"name": fields["status"]}
                }
            
            if "last_error" in fields:
                properties["Last_Error"] = {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": str(fields["last_error"])[:2000]}  # Notion limit
                    }]
                }
            
            if "llm_notes" in fields:
                properties["LLM_Notes"] = {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": str(fields["llm_notes"])[:2000]}
                    }]
                }
            
            if "my_notes" in fields:
                properties["My_Notes"] = {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": str(fields["my_notes"])[:2000]}
                    }]
                }
            
            # Update the page
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Successfully updated job {page_id}")
            return True
            
        except APIResponseError as e:
            logger.error(f"Notion API error updating {page_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating {page_id}: {e}")
            return False
    
    def _parse_job_page(self, page: Dict[str, Any]) -> Optional[JobRow]:
        """Parse Notion page into JobRow object."""
        try:
            props = page["properties"]
            
            # Debug: Print property names and types
            logger.debug(f"Page ID: {page['id']}")
            logger.debug(f"Properties: {list(props.keys())}")
            for key, value in props.items():
                logger.debug(f"  {key}: type={value.get('type', 'unknown')}")
            
            # Extract text from different property types
            def get_text(prop):
                if not prop or "type" not in prop:
                    return None
                    
                prop_type = prop["type"]
                
                if prop_type == "title":
                    return "".join([t["plain_text"] for t in prop.get("title", [])])
                elif prop_type == "rich_text":
                    return "".join([t["plain_text"] for t in prop.get("rich_text", [])])
                elif prop_type == "url":
                    return prop.get("url")
                elif prop_type == "select":
                    return prop.get("select", {}).get("name") if prop.get("select") else None
                elif prop_type == "number":
                    return prop.get("number")
                elif prop_type == "date":
                    return prop.get("date", {}).get("start") if prop.get("date") else None
                elif prop_type == "created_time":
                    return prop.get("created_time")
                elif prop_type == "unique_id":
                    # For unique_id type, get the number from the prefix
                    unique_id = prop.get("unique_id", {})
                    if unique_id and "number" in unique_id:
                        return unique_id["number"]
                    return None
                return None
            
            # Map Notion properties to JobRow fields
            job_data = {
                "page_id": page["id"],
                "jd_id": get_text(props.get("JD_ID", {})),
                "jd_link": get_text(props.get("JD_Link", {})),
                "company": get_text(props.get("Company", {})),
                "title": get_text(props.get("Title", {})),
                "status": get_text(props.get("Status", {})) or "TODO",
                "llm_notes": get_text(props.get("LLM_Notes", {})),
                "last_error": get_text(props.get("Last_Error", {})),
                "my_notes": get_text(props.get("My_Notes", {})),
            }
            
            # Handle created time
            created_time = get_text(props.get("Created_Time", {}))
            if created_time:
                job_data["created_time"] = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            
            return JobRow(**job_data)
            
        except Exception as e:
            logger.error(f"Failed to parse Notion page: {e}")
            return None


# Singleton instance
_notion_service: Optional[NotionService] = None


def get_notion_service() -> NotionService:
    """Get or create singleton NotionService instance."""
    global _notion_service
    if _notion_service is None:
        _notion_service = NotionService()
    return _notion_service
