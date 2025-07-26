"""
Docker-specific logging configuration for ProScrape.
This module provides centralized logging configuration optimized for Docker containers.
"""

import os
import logging
import logging.config
from typing import Dict, Any
from pathlib import Path


def get_docker_logging_config() -> Dict[str, Any]:
    """
    Get Docker-optimized logging configuration.
    
    Returns:
        Dict[str, Any]: Logging configuration dictionary
    """
    
    # Ensure log directory exists
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Get environment variables with defaults
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    enable_console = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"
    enable_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    
    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] %(funcName)s(): %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(funcName)s %(message)s"
            },
            "docker": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {},
        "loggers": {
            "": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "api": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "scrapy": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "celery": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "database": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "proxy": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "monitoring": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "uvicorn": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "uvicorn.access": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "ERROR",
                "handlers": [],
                "propagate": False
            }
        }
    }
    
    # Console handler (always enabled in Docker for container logs)
    if enable_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "json" if log_format == "json" else "docker",
            "stream": "ext://sys.stdout"
        }
        
        # Add console handler to all loggers
        for logger_name in config["loggers"]:
            config["loggers"][logger_name]["handlers"].append("console")
    
    # File handlers (optional in Docker)
    if enable_file:
        # Main log file
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": "/app/logs/proscrape.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        
        # Error log file
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "/app/logs/proscrape_error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 3,
            "encoding": "utf-8"
        }
        
        # Structured JSON log file
        config["handlers"]["json_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": "/app/logs/proscrape_structured.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        
        # Add file handlers to appropriate loggers
        for logger_name in config["loggers"]:
            if logger_name in ["monitoring"]:
                config["loggers"][logger_name]["handlers"].extend(["file", "json_file"])
            else:
                config["loggers"][logger_name]["handlers"].append("file")
            
            # Add error handler for ERROR level logs
            config["loggers"][logger_name]["handlers"].append("error_file")
    
    return config


def setup_docker_logging():
    """
    Set up logging configuration for Docker environment.
    """
    try:
        config = get_docker_logging_config()
        logging.config.dictConfig(config)
        
        # Test logging
        logger = logging.getLogger("docker.setup")
        logger.info("Docker logging configuration initialized successfully")
        logger.debug(f"Log level: {config['loggers']['']['level']}")
        logger.debug(f"Console logging: {any('console' in handlers for handlers in [logger_config['handlers'] for logger_config in config['loggers'].values()])}")
        logger.debug(f"File logging: {any('file' in handlers for handlers in [logger_config['handlers'] for logger_config in config['loggers'].values()])}")
        
    except Exception as e:
        # Fallback to basic logging if configuration fails
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        logger = logging.getLogger("docker.setup")
        logger.error(f"Failed to configure Docker logging: {e}")
        logger.info("Using fallback logging configuration")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


# Specialized logger getters for different components
def get_api_logger() -> logging.Logger:
    """Get API logger."""
    return logging.getLogger("api")


def get_scrapy_logger() -> logging.Logger:
    """Get Scrapy logger."""
    return logging.getLogger("scrapy")


def get_celery_logger() -> logging.Logger:
    """Get Celery logger."""
    return logging.getLogger("celery")


def get_database_logger() -> logging.Logger:
    """Get database logger."""
    return logging.getLogger("database")


def get_proxy_logger() -> logging.Logger:
    """Get proxy logger."""
    return logging.getLogger("proxy")


def get_monitoring_logger() -> logging.Logger:
    """Get monitoring logger."""
    return logging.getLogger("monitoring")


# Docker-specific logging utilities
class DockerLogFormatter(logging.Formatter):
    """
    Custom formatter for Docker container logs.
    Optimizes log format for container environments.
    """
    
    def __init__(self):
        super().__init__(
            fmt="[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def format(self, record):
        # Add container-specific information
        if not hasattr(record, 'container_id'):
            record.container_id = os.getenv('HOSTNAME', 'unknown')
        
        if not hasattr(record, 'service_name'):
            record.service_name = os.getenv('SERVICE_NAME', 'proscrape')
        
        return super().format(record)


class StructuredLogger:
    """
    Structured logger for Docker environments with additional context.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.base_context = {
            'container_id': os.getenv('HOSTNAME', 'unknown'),
            'service_name': os.getenv('SERVICE_NAME', 'proscrape'),
            'environment': os.getenv('ENVIRONMENT', 'development')
        }
    
    def log_with_context(self, level: str, message: str, **context):
        """Log message with additional context."""
        extra_context = {**self.base_context, **context}
        getattr(self.logger, level.lower())(message, extra=extra_context)
    
    def info(self, message: str, **context):
        """Log info message with context."""
        self.log_with_context('info', message, **context)
    
    def warning(self, message: str, **context):
        """Log warning message with context."""
        self.log_with_context('warning', message, **context)
    
    def error(self, message: str, **context):
        """Log error message with context."""
        self.log_with_context('error', message, **context)
    
    def debug(self, message: str, **context):
        """Log debug message with context."""
        self.log_with_context('debug', message, **context)


# Health check logging
def log_health_check(service: str, status: str, details: str = None):
    """
    Log health check results in a structured format.
    
    Args:
        service (str): Service name
        status (str): Health status (healthy/unhealthy/degraded)
        details (str, optional): Additional details
    """
    logger = get_monitoring_logger()
    
    log_data = {
        'event_type': 'health_check',
        'service': service,
        'status': status,
        'timestamp': logging.Formatter().formatTime(logging.LogRecord(
            name='health', level=logging.INFO, pathname='', lineno=0,
            msg='', args=(), exc_info=None
        ))
    }
    
    if details:
        log_data['details'] = details
    
    if status == 'healthy':
        logger.info(f"Health check passed for {service}", extra=log_data)
    elif status == 'degraded':
        logger.warning(f"Health check degraded for {service}: {details}", extra=log_data)
    else:
        logger.error(f"Health check failed for {service}: {details}", extra=log_data)


# Performance logging
def log_performance_metric(metric_name: str, value: float, unit: str = None, **context):
    """
    Log performance metrics in a structured format.
    
    Args:
        metric_name (str): Name of the metric
        value (float): Metric value
        unit (str, optional): Unit of measurement
        **context: Additional context
    """
    logger = get_monitoring_logger()
    
    log_data = {
        'event_type': 'performance_metric',
        'metric_name': metric_name,
        'value': value,
        'timestamp': logging.Formatter().formatTime(logging.LogRecord(
            name='performance', level=logging.INFO, pathname='', lineno=0,
            msg='', args=(), exc_info=None
        )),
        **context
    }
    
    if unit:
        log_data['unit'] = unit
    
    logger.info(f"Performance metric: {metric_name}={value}{unit or ''}", extra=log_data)


# Error tracking
def log_error_with_context(error: Exception, context: Dict[str, Any] = None):
    """
    Log errors with full context and stack trace.
    
    Args:
        error (Exception): The exception that occurred
        context (Dict[str, Any], optional): Additional context
    """
    logger = get_logger("error_tracker")
    
    log_data = {
        'event_type': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': logging.Formatter().formatTime(logging.LogRecord(
            name='error', level=logging.ERROR, pathname='', lineno=0,
            msg='', args=(), exc_info=None
        ))
    }
    
    if context:
        log_data.update(context)
    
    logger.error(f"Error occurred: {type(error).__name__}: {str(error)}", 
                exc_info=True, extra=log_data)


# Initialize logging when module is imported
if __name__ != "__main__":
    setup_docker_logging()