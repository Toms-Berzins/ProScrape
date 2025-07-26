"""
Docker-specific configuration settings for ProScrape.
This module provides settings optimized for Docker deployment.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class DockerSettings(BaseSettings):
    """Configuration settings for Docker deployment."""
    
    # =============================================================================
    # API Configuration
    # =============================================================================
    
    api_host: str = Field(default="0.0.0.0", description="API host binding")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable API auto-reload")
    api_workers: int = Field(default=1, description="Number of API workers")
    
    # CORS Configuration
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:5174",
        description="Allowed CORS origins (comma-separated)"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allow_methods: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS",
        description="Allowed CORS methods (comma-separated)"
    )
    cors_allow_headers: str = Field(default="*", description="Allowed CORS headers (comma-separated)")
    
    # =============================================================================
    # Database Configuration
    # =============================================================================
    
    # MongoDB
    mongodb_url: str = Field(
        default="mongodb://proscrape_user:proscrape_password@mongodb:27017/proscrape",
        description="MongoDB connection URL"
    )
    mongodb_database: str = Field(default="proscrape", description="MongoDB database name")
    
    # PostgreSQL (for metadata)
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="proscrape_db", description="PostgreSQL database")
    postgres_user: str = Field(default="proscrape_user", description="PostgreSQL user")
    postgres_password: str = Field(default="proscrape_password", description="PostgreSQL password")
    postgres_url: str = Field(
        default="postgresql://proscrape_user:proscrape_password@postgres:5432/proscrape_db",
        description="PostgreSQL connection URL"
    )
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis connection URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", description="Celery broker URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", description="Celery result backend")
    
    # =============================================================================
    # Scraping Configuration
    # =============================================================================
    
    # Scrapy Settings
    download_delay: float = Field(default=1.0, description="Delay between requests")
    randomize_download_delay: float = Field(default=0.5, description="Random delay factor")
    concurrent_requests: int = Field(default=8, description="Max concurrent requests")
    concurrent_requests_per_domain: int = Field(default=1, description="Max requests per domain")
    autothrottle_enabled: bool = Field(default=True, description="Enable auto-throttling")
    autothrottle_start_delay: float = Field(default=1.0, description="Auto-throttle start delay")
    autothrottle_max_delay: float = Field(default=60.0, description="Auto-throttle max delay")
    autothrottle_target_concurrency: float = Field(default=2.0, description="Auto-throttle target concurrency")
    
    # User Agent Configuration
    user_agent_list: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ],
        description="List of User-Agent strings"
    )
    
    # Proxy Configuration
    proxy_enabled: bool = Field(default=False, description="Enable proxy rotation")
    proxy_list: List[str] = Field(default=[], description="List of proxy URLs")
    proxy_health_check_interval: int = Field(default=300, description="Proxy health check interval (seconds)")
    proxy_max_consecutive_failures: int = Field(default=3, description="Max consecutive proxy failures")
    
    # Spider Control
    ss_spider_enabled: bool = Field(default=True, description="Enable SS spider")
    city24_spider_enabled: bool = Field(default=True, description="Enable City24 spider")
    pp_spider_enabled: bool = Field(default=True, description="Enable PP spider")
    
    # =============================================================================
    # Celery Configuration
    # =============================================================================
    
    celery_task_serializer: str = Field(default="json", description="Celery task serializer")
    celery_result_serializer: str = Field(default="json", description="Celery result serializer")
    celery_accept_content: List[str] = Field(default=["json"], description="Celery accepted content types")
    celery_timezone: str = Field(default="UTC", description="Celery timezone")
    celery_enable_utc: bool = Field(default=True, description="Enable UTC in Celery")
    
    # Scheduling
    scraping_schedule_interval: int = Field(default=3600, description="Scraping schedule interval (seconds)")
    health_check_interval: int = Field(default=300, description="Health check interval (seconds)")
    cleanup_interval: int = Field(default=86400, description="Cleanup interval (seconds)")
    
    # Task Routing
    celery_routes: Dict[str, Dict[str, str]] = Field(
        default={
            "tasks.scraping_tasks.run_spider": {"queue": "scraping"},
            "tasks.scraping_tasks.health_check": {"queue": "monitoring"},
            "tasks.scraping_tasks.cleanup_old_data": {"queue": "maintenance"}
        },
        description="Celery task routing configuration"
    )
    
    # =============================================================================
    # Logging Configuration
    # =============================================================================
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: str = Field(default="/app/logs/proscrape.log", description="Log file path")
    log_max_size: str = Field(default="10MB", description="Max log file size")
    log_backup_count: int = Field(default=5, description="Number of log backup files")
    
    enable_structured_logging: bool = Field(default=True, description="Enable structured logging")
    log_to_console: bool = Field(default=True, description="Log to console")
    log_to_file: bool = Field(default=True, description="Log to file")
    
    # =============================================================================
    # Monitoring & Alerting
    # =============================================================================
    
    # Health Checks
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_endpoints: List[str] = Field(
        default=["/health", "/metrics"],
        description="Health check endpoints"
    )
    
    # Alerting
    alerting_enabled: bool = Field(default=True, description="Enable alerting")
    alert_email_enabled: bool = Field(default=False, description="Enable email alerts")
    alert_webhook_enabled: bool = Field(default=False, description="Enable webhook alerts")
    
    # Email Configuration
    alert_email_smtp_host: str = Field(default="smtp.gmail.com", description="SMTP host")
    alert_email_smtp_port: int = Field(default=587, description="SMTP port")
    alert_email_username: Optional[str] = Field(default=None, description="SMTP username")
    alert_email_password: Optional[str] = Field(default=None, description="SMTP password")
    alert_email_from: str = Field(default="alerts@proscrape.com", description="Alert sender email")
    alert_email_to: str = Field(default="admin@proscrape.com", description="Alert recipient email")
    
    # Webhook Configuration
    alert_webhook_url: Optional[str] = Field(default=None, description="Alert webhook URL")
    
    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_interval: int = Field(default=60, description="Metrics collection interval")
    prometheus_enabled: bool = Field(default=False, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    
    # =============================================================================
    # Security Configuration
    # =============================================================================
    
    # API Security
    api_key_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_key: Optional[str] = Field(default=None, description="API key")
    jwt_secret_key: Optional[str] = Field(default=None, description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=30, description="JWT expiration time")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Rate limit per minute")
    rate_limit_burst: int = Field(default=10, description="Rate limit burst")
    
    # =============================================================================
    # Data Processing
    # =============================================================================
    
    # Validation
    strict_validation: bool = Field(default=False, description="Enable strict validation")
    price_min: int = Field(default=1000, description="Minimum price (EUR)")
    price_max: int = Field(default=10000000, description="Maximum price (EUR)")
    area_min: int = Field(default=10, description="Minimum area (sqm)")
    area_max: int = Field(default=1000, description="Maximum area (sqm)")
    
    # Data Management
    auto_remove_duplicates: bool = Field(default=True, description="Auto-remove duplicates")
    duplicate_threshold: float = Field(default=0.95, description="Duplicate similarity threshold")
    data_retention_days: int = Field(default=365, description="Data retention period")
    
    # Image Processing
    download_images: bool = Field(default=False, description="Download listing images")
    image_store_s3_bucket: Optional[str] = Field(default=None, description="S3 bucket for images")
    image_quality: int = Field(default=80, description="Image quality (1-100)")
    image_max_size: str = Field(default="1920x1080", description="Maximum image size")
    
    # =============================================================================
    # Development Settings
    # =============================================================================
    
    debug: bool = Field(default=True, description="Enable debug mode")
    development_mode: bool = Field(default=True, description="Enable development mode")
    testing_mode: bool = Field(default=False, description="Enable testing mode")
    
    # Performance
    enable_profiling: bool = Field(default=False, description="Enable performance profiling")
    profile_output_dir: str = Field(default="/app/profiles", description="Profile output directory")
    
    # Cache
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL (seconds)")
    cache_max_size: int = Field(default=1000, description="Max cache entries")
    
    # Development Tools
    hot_reload: bool = Field(default=True, description="Enable hot reload")
    auto_restart: bool = Field(default=True, description="Enable auto restart")
    enable_debug_toolbar: bool = Field(default=True, description="Enable debug toolbar")
    
    # =============================================================================
    # Validators
    # =============================================================================
    
    @field_validator('cors_origins', mode='after')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string."""
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            return ','.join(v)
        return v
    
    
    @field_validator('user_agent_list', mode='before')
    @classmethod
    def parse_user_agents(cls, v):
        """Parse user agents from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [ua.strip() for ua in v.split('\n') if ua.strip()]
        return v
    
    @field_validator('proxy_list', mode='before')
    @classmethod
    def parse_proxy_list(cls, v):
        """Parse proxy list from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [proxy.strip() for proxy in v.split(',') if proxy.strip()]
        return v
    
    @field_validator('celery_accept_content', mode='before')
    @classmethod
    def parse_celery_content(cls, v):
        """Parse Celery accept content from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [content.strip() for content in v.split(',')]
        return v
    
    @field_validator('celery_routes', mode='before')
    @classmethod
    def parse_celery_routes(cls, v):
        """Parse Celery routes from string or dict."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v
    
    @field_validator('health_check_endpoints', mode='before')
    @classmethod
    def parse_health_endpoints(cls, v):
        """Parse health check endpoints from string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [endpoint.strip() for endpoint in v.split(',')]
        return v
    
    model_config = {
        "env_file": [".env.docker", ".env"],
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "populate_by_name": True,
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "frontend_url": "http://localhost:3000",
                "mongodb_url": "mongodb://proscrape_user:proscrape_password@mongodb:27017/proscrape",
                "redis_url": "redis://redis:6379/0",
                "debug": True,
                "development_mode": True
            }
        }
    }


# Global settings instance
docker_settings = DockerSettings()


def get_docker_settings() -> DockerSettings:
    """Get Docker settings instance."""
    return docker_settings


def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration for FastAPI."""
    settings = get_docker_settings()
    return {
        "allow_origins": settings.cors_origins,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
    }


def get_celery_config() -> Dict[str, Any]:
    """Get Celery configuration."""
    settings = get_docker_settings()
    return {
        "broker_url": settings.celery_broker_url,
        "result_backend": settings.celery_result_backend,
        "task_serializer": settings.celery_task_serializer,
        "result_serializer": settings.celery_result_serializer,
        "accept_content": settings.celery_accept_content,
        "timezone": settings.celery_timezone,
        "enable_utc": settings.celery_enable_utc,
        "task_routes": settings.celery_routes,
        "beat_schedule": {
            "run-scrapers": {
                "task": "tasks.scraping_tasks.run_all_spiders",
                "schedule": settings.scraping_schedule_interval,
            },
            "health-check": {
                "task": "tasks.scraping_tasks.health_check",
                "schedule": settings.health_check_interval,
            },
            "cleanup-old-data": {
                "task": "tasks.scraping_tasks.cleanup_old_data",
                "schedule": settings.cleanup_interval,
            },
        }
    }


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration."""
    settings = get_docker_settings()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            }
        },
        "handlers": {
            "console": {
                "level": settings.log_level,
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.log_format == "json" else "standard",
            },
            "file": {
                "level": settings.log_level,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": settings.log_file,
                "maxBytes": int(settings.log_max_size.replace("MB", "")) * 1024 * 1024,
                "backupCount": settings.log_backup_count,
                "formatter": "json" if settings.log_format == "json" else "standard",
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"] + (["file"] if settings.log_to_file else []),
                "level": settings.log_level,
                "propagate": False
            }
        }
    }