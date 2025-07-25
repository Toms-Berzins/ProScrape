import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from config.settings import settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to the log level
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(
    log_level: str = None,
    log_file: str = None,
    spider_name: str = None,
    enable_colors: bool = True
):
    """
    Configure logging for the application.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        spider_name: Name of the spider (for specific log files)
        enable_colors: Whether to enable colored console output
    """
    
    # Use settings defaults if not provided
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if enable_colors and sys.stdout.isatty():
        console_format = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Main log file with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Log all levels to file
        
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
        
        # Spider-specific log file
        if spider_name:
            spider_log_file = log_path.parent / f"{spider_name}_{datetime.now().strftime('%Y%m%d')}.log"
            spider_handler = logging.handlers.RotatingFileHandler(
                spider_log_file,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            spider_handler.setLevel(logging.INFO)
            spider_handler.setFormatter(file_format)
            
            # Add spider-specific handler to spider logger
            spider_logger = logging.getLogger(f'spiders.{spider_name}')
            spider_logger.addHandler(spider_handler)
    
    # Configure specific loggers
    configure_third_party_loggers()
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, file={log_file}")


def configure_third_party_loggers():
    """Configure logging for third-party libraries."""
    
    # Scrapy loggers
    logging.getLogger('scrapy').setLevel(logging.INFO)
    logging.getLogger('scrapy.crawler').setLevel(logging.WARNING)
    logging.getLogger('scrapy.middleware').setLevel(logging.WARNING)
    logging.getLogger('scrapy.extensions').setLevel(logging.WARNING)
    
    # Playwright loggers  
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('scrapy_playwright').setLevel(logging.INFO)
    
    # MongoDB loggers
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('motor').setLevel(logging.WARNING)
    
    # Celery loggers
    logging.getLogger('celery').setLevel(logging.INFO)
    logging.getLogger('celery.worker').setLevel(logging.INFO)
    logging.getLogger('celery.beat').setLevel(logging.INFO)
    
    # HTTP libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # FastAPI/Uvicorn
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.INFO)


def get_spider_logger(spider_name: str) -> logging.Logger:
    """
    Get a configured logger for a specific spider.
    
    Args:
        spider_name: Name of the spider
        
    Returns:
        Configured logger instance
    """
    logger_name = f'spiders.{spider_name}'
    logger = logging.getLogger(logger_name)
    
    # Add spider-specific context
    class SpiderLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return f'[{self.extra["spider"]}] {msg}', kwargs
    
    return SpiderLoggerAdapter(logger, {'spider': spider_name})


def log_spider_stats(spider_name: str, stats: dict):
    """
    Log spider statistics in a structured format.
    
    Args:
        spider_name: Name of the spider
        stats: Dictionary of spider statistics
    """
    logger = get_spider_logger(spider_name)
    
    logger.info("Spider execution completed")
    logger.info(f"Items scraped: {stats.get('item_scraped_count', 0)}")
    logger.info(f"Items dropped: {stats.get('item_dropped_count', 0)}")
    logger.info(f"Requests made: {stats.get('downloader/request_count', 0)}")
    logger.info(f"Responses received: {stats.get('downloader/response_count', 0)}")
    logger.info(f"Response status counts: {stats.get('downloader/response_status_count', {})}")
    
    # Log any errors or warnings
    if stats.get('spider_exceptions', 0) > 0:
        logger.error(f"Spider exceptions: {stats['spider_exceptions']}")
    
    if stats.get('downloader/exception_count', 0) > 0:
        logger.warning(f"Download exceptions: {stats['downloader/exception_count']}")


class StructuredLogger:
    """Logger with structured logging capabilities."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_scraping_attempt(self, url: str, spider: str):
        """Log scraping attempt."""
        self.logger.info(f"Attempting to scrape: {url}", extra={
            'event': 'scraping_attempt',
            'url': url,
            'spider': spider
        })
    
    def log_scraping_success(self, url: str, spider: str, items_count: int):
        """Log successful scraping."""
        self.logger.info(f"Successfully scraped {items_count} items from: {url}", extra={
            'event': 'scraping_success',
            'url': url,
            'spider': spider,
            'items_count': items_count
        })
    
    def log_scraping_failure(self, url: str, spider: str, error: str):
        """Log scraping failure."""
        self.logger.error(f"Failed to scrape: {url} - {error}", extra={
            'event': 'scraping_failure',
            'url': url,
            'spider': spider,
            'error': error
        })
    
    def log_item_processed(self, item_id: str, spider: str, action: str):
        """Log item processing."""
        self.logger.info(f"Item {action}: {item_id}", extra={
            'event': 'item_processed',
            'item_id': item_id,
            'spider': spider,
            'action': action
        })
    
    def log_pipeline_action(self, pipeline: str, action: str, item_id: str = None, details: dict = None):
        """Log pipeline actions."""
        message = f"Pipeline {pipeline}: {action}"
        if item_id:
            message += f" (Item: {item_id})"
        
        extra = {
            'event': 'pipeline_action',
            'pipeline': pipeline,
            'action': action,
            'item_id': item_id
        }
        
        if details:
            extra.update(details)
        
        self.logger.info(message, extra=extra)