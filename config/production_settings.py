"""
Production configuration settings for ProScrape.
Optimized for large-scale scraping operations.
"""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings

class ProductionSettings(BaseSettings):
    """Production configuration settings."""
    
    # Database Configuration
    mongodb_url: str = 'mongodb://localhost:27017'
    mongodb_database: str = 'proscrape'
    
    # Redis Configuration
    redis_url: str = 'redis://localhost:6379/0'
    redis_password: str = 'proscrape2025redis'
    
    # API Configuration
    api_host: str = '0.0.0.0'
    api_port: int = 8000
    
    # Scraping Configuration - Production optimized
    download_delay: float = 3.0
    randomize_download_delay: bool = True
    concurrent_requests: int = 1
    
    # AutoThrottle Configuration
    autothrottle_enabled: bool = True
    autothrottle_start_delay: float = 2.0
    autothrottle_max_delay: float = 10.0
    autothrottle_target_concurrency: float = 1.0
    
    # Retry Configuration
    retry_times: int = 5
    retry_http_codes: list = [500, 502, 503, 504, 408, 429, 403]
    
    # Timeout Configuration
    download_timeout: int = 60
    
    # Site Configuration
    ss_com_enabled: bool = True
    city24_enabled: bool = False
    pp_lv_enabled: bool = False
    
    # Proxy Configuration
    proxy_enabled: bool = False
    proxy_rotation_enabled: bool = False
    
    # Celery Configuration
    celery_concurrency: int = 4
    celery_max_tasks_per_child: int = 50
    celery_time_limit: int = 7200  # 2 hours
    celery_soft_time_limit: int = 6000  # 100 minutes
    
    # Logging Configuration
    log_level: str = 'INFO'
    log_dir: Path = Path('./logs')
    log_max_size: str = '100MB'
    log_backup_count: int = 10
    
    # Monitoring Configuration
    flower_enabled: bool = True
    flower_port: int = 5555
    flower_user: str = 'admin'
    flower_password: str = 'proscrape2025'
    
    # Performance Configuration
    memory_limit: str = '4G'
    cpu_limit: str = '2.0'
    
    # Data Quality Configuration
    enable_duplicate_filter: bool = True
    enable_data_validation: bool = True
    enable_data_normalization: bool = True
    
    # Alert Configuration
    alert_enabled: bool = True
    alert_email: str = ''
    alert_webhook: str = ''
    
    # Production Flags
    production: bool = True
    debug: bool = False
    
    class Config:
        env_file = '.env'
        case_sensitive = False


# Global production settings instance
production_settings = ProductionSettings()


def setup_production_logging():
    """Set up production logging configuration."""
    
    # Ensure log directory exists
    production_settings.log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, production_settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.handlers.RotatingFileHandler(
                production_settings.log_dir / 'proscrape.log',
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=10
            )
        ]
    )
    
    # Configure specific loggers
    loggers = {
        'scrapy': logging.INFO,
        'celery': logging.INFO,
        'spiders': logging.INFO,
        'tasks': logging.INFO,
        'api': logging.INFO,
        'utils': logging.INFO,
        'pymongo': logging.WARNING,
        'urllib3': logging.WARNING,
        'requests': logging.WARNING,
    }
    
    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # Add file handler for critical components
        if logger_name in ['scrapy', 'celery', 'spiders', 'tasks']:
            handler = logging.handlers.RotatingFileHandler(
                production_settings.log_dir / f'{logger_name}.log',
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=5
            )
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(handler)


def get_scrapy_production_settings():
    """Get Scrapy settings optimized for production."""
    
    return {
        # Bot Settings
        'BOT_NAME': 'proscrape-production',
        'ROBOTSTXT_OBEY': False,
        
        # Performance Settings
        'CONCURRENT_REQUESTS': production_settings.concurrent_requests,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': production_settings.download_delay,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        
        # AutoThrottle
        'AUTOTHROTTLE_ENABLED': production_settings.autothrottle_enabled,
        'AUTOTHROTTLE_START_DELAY': production_settings.autothrottle_start_delay,
        'AUTOTHROTTLE_MAX_DELAY': production_settings.autothrottle_max_delay,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': production_settings.autothrottle_target_concurrency,
        'AUTOTHROTTLE_DEBUG': False,
        
        # Retry Settings
        'RETRY_ENABLED': True,
        'RETRY_TIMES': production_settings.retry_times,
        'RETRY_HTTP_CODES': production_settings.retry_http_codes,
        
        # Timeout Settings
        'DOWNLOAD_TIMEOUT': production_settings.download_timeout,
        
        # Memory and Performance
        'MEMUSAGE_ENABLED': True,
        'MEMUSAGE_LIMIT_MB': 3000,  # 3GB limit
        'MEMUSAGE_WARNING_MB': 2500,  # Warning at 2.5GB
        
        # Cookies
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': False,
        
        # Compression
        'COMPRESSION_ENABLED': True,
        
        # DNS Cache
        'DNSCACHE_ENABLED': True,
        'DNSCACHE_SIZE': 10000,
        
        # Connection Pool
        'REACTOR_THREADPOOL_MAXSIZE': 20,
        
        # Statistics
        'STATS_CLASS': 'scrapy.statscollectors.MemoryStatsCollector',
        
        # Logging
        'LOG_LEVEL': production_settings.log_level,
        'LOG_FILE': str(production_settings.log_dir / 'scrapy.log'),
        'LOG_STDOUT': False,
        
        # Extensions
        'EXTENSIONS': {
            'scrapy.extensions.memusage.MemoryUsage': 100,
            'scrapy.extensions.logstats.LogStats': 200,
        },
        
        # Disable Telnet Console in production
        'TELNETCONSOLE_ENABLED': False,
    }


def get_celery_production_config():
    """Get Celery configuration optimized for production."""
    
    return {
        'broker_url': production_settings.redis_url,
        'result_backend': production_settings.redis_url,
        'result_expires': 7200,  # 2 hours
        
        # Task Settings
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        'timezone': 'UTC',
        'enable_utc': True,
        
        # Worker Settings
        'worker_concurrency': production_settings.celery_concurrency,
        'worker_prefetch_multiplier': 1,
        'worker_max_tasks_per_child': production_settings.celery_max_tasks_per_child,
        'task_acks_late': True,
        'task_reject_on_worker_lost': True,
        
        # Time Limits
        'task_time_limit': production_settings.celery_time_limit,
        'task_soft_time_limit': production_settings.celery_soft_time_limit,
        
        # Retry Settings
        'task_default_retry_delay': 300,  # 5 minutes
        'task_max_retries': 3,
        
        # Routing
        'task_routes': {
            'tasks.scraping_tasks.*': {'queue': 'scraping'},
            'tasks.cleanup_tasks.*': {'queue': 'maintenance'},
        },
        
        # Beat Schedule
        'beat_schedule': {
            'scrape-ss-com-hourly': {
                'task': 'tasks.scraping_tasks.scrape_ss_com',
                'schedule': 3600.0,  # Every hour
            },
            'scrape-all-sites-daily': {
                'task': 'tasks.scraping_tasks.scrape_all_sites',
                'schedule': 24 * 3600.0,  # Every 24 hours
            },
        },
        
        # Monitoring
        'worker_send_task_events': True,
        'task_send_sent_event': True,
        
        # Security
        'worker_hijack_root_logger': False,
        'worker_log_color': False,
    }