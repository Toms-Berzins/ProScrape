import os
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # MongoDB settings
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "proscrape"
    
    # Redis settings for Celery
    redis_url: str = "redis://localhost:6379/0"
    
    # FastAPI settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    
    # Scraping settings
    user_agents: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ]
    
    # Request delays (seconds)
    download_delay: float = 1.0
    randomize_download_delay: bool = True
    
    # Proxy settings
    proxy_list: Optional[List[str]] = None
    rotate_proxies: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "proscrape.log"
    
    # Site-specific settings
    ss_com_enabled: bool = True
    city24_enabled: bool = True
    pp_lv_enabled: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()