"""
Configuration management for the ingestion module.
Loads settings from environment variables with validation.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    # Notion Configuration
    NOTION_TOKEN: str = os.getenv('NOTION_TOKEN', '')
    DATABASE_ID: str = os.getenv('DATABASE_ID', '')
    
    # OpenAI Configuration (for future use)
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    # Application Settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '10'))
    
    # Data Paths
    DATA_DIR: Path = Path(__file__).parent.parent / 'data'
    RAW_DATA_DIR: Path = DATA_DIR / 'raw'
    LOGS_DIR: Path = Path(__file__).parent.parent / 'logs'
    
    @classmethod
    def validate(cls) -> None:
        """Validate required settings are present."""
        errors = []
        
        if not cls.NOTION_TOKEN:
            errors.append("NOTION_TOKEN is required")
        
        if not cls.DATABASE_ID:
            errors.append("DATABASE_ID is required")
            
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (for debugging)."""
        print("Current Configuration:")
        print(f"  NOTION_TOKEN: {'*' * 10 if cls.NOTION_TOKEN else 'NOT SET'}")
        print(f"  DATABASE_ID: {cls.DATABASE_ID or 'NOT SET'}")
        print(f"  LOG_LEVEL: {cls.LOG_LEVEL}")
        print(f"  REQUEST_TIMEOUT: {cls.REQUEST_TIMEOUT}s")
        print(f"  DATA_DIR: {cls.DATA_DIR}")
        print(f"  LOGS_DIR: {cls.LOGS_DIR}")


# Create directories if they don't exist
Settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
Settings.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
Settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # Test configuration loading
    Settings.print_config()
    try:
        Settings.validate()
        print("\n✅ Configuration is valid!")
    except ValueError as e:
        print(f"\n❌ {e}")
