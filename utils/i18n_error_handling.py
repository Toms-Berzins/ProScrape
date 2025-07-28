"""
Error Handling and Recovery System for ProScrape i18n Pipeline

This module provides comprehensive error handling, dead letter queues, retry logic,
and failure recovery mechanisms for the multilingual data processing pipeline.
"""

import logging
import json
import uuid
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import smtplib
import requests
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# Redis for dead letter queues
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

# Celery for task management
from celery import Task
from celery.exceptions import Retry, MaxRetriesExceededError

from models.i18n_models import SupportedLanguage, TranslationResult, TranslationQuality
from utils.i18n_database import I18nDatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors in the i18n pipeline."""
    TRANSLATION_SERVICE_ERROR = "translation_service_error"
    LANGUAGE_DETECTION_ERROR = "language_detection_error"
    DATABASE_ERROR = "database_error"
    NORMALIZATION_ERROR = "normalization_error"
    DUPLICATE_DETECTION_ERROR = "duplicate_detection_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    QUOTA_EXCEEDED_ERROR = "quota_exceeded_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryStrategy(Enum):
    """Retry strategies for different error types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"
    IMMEDIATE_RETRY = "immediate_retry"


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    context: Dict[str, Any]
    traceback_str: Optional[str]
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_method: Optional[str] = None


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retry_on_errors: List[ErrorType] = field(default_factory=lambda: [
        ErrorType.NETWORK_ERROR,
        ErrorType.TIMEOUT_ERROR,
        ErrorType.RATE_LIMIT_ERROR,
        ErrorType.TRANSLATION_SERVICE_ERROR
    ])
    no_retry_errors: List[ErrorType] = field(default_factory=lambda: [
        ErrorType.AUTHENTICATION_ERROR,
        ErrorType.VALIDATION_ERROR
    ])


class DeadLetterQueue:
    """Dead letter queue for failed items using Redis."""
    
    def __init__(
        self,
        redis_url: str,
        queue_name: str = "i18n_dead_letter_queue",
        max_items: int = 10000,
        ttl_hours: int = 168  # 1 week
    ):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.max_items = max_items
        self.ttl_seconds = ttl_hours * 3600
        
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            logger.info(f"Connected to Redis for dead letter queue: {queue_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for DLQ: {e}")
            self.redis_client = None
    
    def enqueue_failed_item(
        self,
        item_data: Dict[str, Any],
        error_record: ErrorRecord,
        original_queue: str = "unknown"
    ) -> bool:
        """
        Add a failed item to the dead letter queue.
        
        Args:
            item_data: Original item data that failed
            error_record: Error information
            original_queue: Name of the original queue/process
            
        Returns:
            True if successfully enqueued, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not available for DLQ")
            return False
        
        try:
            # Create DLQ entry
            dlq_entry = {
                'id': str(uuid.uuid4()),
                'original_item': item_data,
                'error_record': {
                    'error_id': error_record.error_id,
                    'error_type': error_record.error_type.value,
                    'severity': error_record.severity.value,
                    'message': error_record.message,
                    'details': error_record.details,
                    'context': error_record.context,
                    'traceback': error_record.traceback_str,
                    'created_at': error_record.created_at.isoformat(),
                    'retry_count': error_record.retry_count
                },
                'original_queue': original_queue,
                'enqueued_at': datetime.utcnow().isoformat(),
                'processing_attempts': 0
            }
            
            # Serialize and add to Redis list
            serialized_entry = json.dumps(dlq_entry, default=str)
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Add to the head of the list
            pipe.lpush(self.queue_name, serialized_entry)
            
            # Set TTL on the list
            pipe.expire(self.queue_name, self.ttl_seconds)
            
            # Trim list to max size
            pipe.ltrim(self.queue_name, 0, self.max_items - 1)
            
            # Execute pipeline
            pipe.execute()
            
            logger.info(f"Item added to dead letter queue: {dlq_entry['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue item to DLQ: {e}")
            return False
    
    def dequeue_failed_item(self) -> Optional[Dict[str, Any]]:
        """
        Remove and return an item from the dead letter queue.
        
        Returns:
            DLQ entry dictionary or None if queue is empty
        """
        if not self.redis_client:
            return None
        
        try:
            # Pop from the tail (FIFO)
            serialized_entry = self.redis_client.rpop(self.queue_name)
            
            if serialized_entry:
                return json.loads(serialized_entry)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue item from DLQ: {e}")
            return None
    
    def peek_failed_items(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Peek at failed items without removing them from the queue.
        
        Args:
            count: Number of items to peek at
            
        Returns:
            List of DLQ entries
        """
        if not self.redis_client:
            return []
        
        try:
            # Get items from the tail (oldest first)
            serialized_entries = self.redis_client.lrange(self.queue_name, -count, -1)
            
            entries = []
            for serialized_entry in serialized_entries:
                try:
                    entry = json.loads(serialized_entry)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to deserialize DLQ entry: {e}")
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to peek at DLQ items: {e}")
            return []
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the dead letter queue."""
        if not self.redis_client:
            return {'error': 'Redis client not available'}
        
        try:
            queue_length = self.redis_client.llen(self.queue_name)
            ttl = self.redis_client.ttl(self.queue_name)
            
            # Get error type distribution from recent items
            recent_items = self.peek_failed_items(100)
            error_type_counts = {}
            severity_counts = {}
            
            for item in recent_items:
                error_record = item.get('error_record', {})
                error_type = error_record.get('error_type', 'unknown')
                severity = error_record.get('severity', 'unknown')
                
                error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            return {
                'queue_name': self.queue_name,
                'queue_length': queue_length,
                'max_items': self.max_items,
                'ttl_seconds': ttl,
                'error_type_distribution': error_type_counts,
                'severity_distribution': severity_counts,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get DLQ stats: {e}")
            return {'error': str(e)}
    
    def clear_queue(self) -> int:
        """
        Clear all items from the dead letter queue.
        
        Returns:
            Number of items removed
        """
        if not self.redis_client:
            return 0
        
        try:
            count = self.redis_client.llen(self.queue_name)
            self.redis_client.delete(self.queue_name)
            logger.info(f"Cleared {count} items from dead letter queue")
            return count
            
        except Exception as e:
            logger.error(f"Failed to clear DLQ: {e}")
            return 0


class RetryManager:
    """Manager for handling retry logic with different strategies."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def should_retry(self, error_type: ErrorType, retry_count: int) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error_type: Type of error that occurred
            retry_count: Current retry count
            
        Returns:
            True if should retry, False otherwise
        """
        # Check if max retries exceeded
        if retry_count >= self.config.max_retries:
            return False
        
        # Check if error type is in no-retry list
        if error_type in self.config.no_retry_errors:
            return False
        
        # Check if error type is in retry list
        if error_type in self.config.retry_on_errors:
            return True
        
        # Default to no retry for unknown error types
        return False
    
    def calculate_retry_delay(self, retry_count: int, error_type: ErrorType) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            retry_count: Current retry count (0-based)
            error_type: Type of error
            
        Returns:
            Delay in seconds
        """
        if error_type == ErrorType.RATE_LIMIT_ERROR:
            # Longer delays for rate limiting
            base_delay = self.config.base_delay_seconds * 10
        else:
            base_delay = self.config.base_delay_seconds
        
        # Calculate delay based on strategy
        if error_type in [ErrorType.NETWORK_ERROR, ErrorType.TIMEOUT_ERROR]:
            # Exponential backoff for network issues
            delay = base_delay * (self.config.backoff_multiplier ** retry_count)
        elif error_type == ErrorType.RATE_LIMIT_ERROR:
            # Linear backoff for rate limiting
            delay = base_delay + (retry_count * 30)  # Add 30s per retry
        else:
            # Fixed delay for other errors
            delay = base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay_seconds)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            import random
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum 0.1 second delay
    
    def get_next_retry_time(self, retry_count: int, error_type: ErrorType) -> datetime:
        """Get the datetime for the next retry attempt."""
        delay = self.calculate_retry_delay(retry_count, error_type)
        return datetime.utcnow() + timedelta(seconds=delay)


class ErrorClassifier:
    """Classify errors and determine appropriate handling strategy."""
    
    def __init__(self):
        # Error classification patterns
        self.error_patterns = {
            ErrorType.TRANSLATION_SERVICE_ERROR: [
                'translation failed', 'service unavailable', 'api error',
                'translation service', 'translate api'
            ],
            ErrorType.RATE_LIMIT_ERROR: [
                'rate limit', 'quota exceeded', 'too many requests',
                'rate limited', 'throttled'
            ],
            ErrorType.NETWORK_ERROR: [
                'connection error', 'network error', 'connection failed',
                'dns error', 'socket error', 'connection timeout'
            ],
            ErrorType.TIMEOUT_ERROR: [
                'timeout', 'timed out', 'request timeout', 'read timeout'
            ],
            ErrorType.AUTHENTICATION_ERROR: [
                'unauthorized', 'authentication failed', 'invalid api key',
                'access denied', 'forbidden'
            ],
            ErrorType.VALIDATION_ERROR: [
                'validation error', 'invalid data', 'schema error',
                'validation failed'
            ],
            ErrorType.DATABASE_ERROR: [
                'database error', 'mongodb error', 'connection pool',
                'database connection', 'query failed'
            ]
        }
        
        # Severity mappings
        self.severity_mappings = {
            ErrorType.AUTHENTICATION_ERROR: ErrorSeverity.CRITICAL,
            ErrorType.DATABASE_ERROR: ErrorSeverity.HIGH,
            ErrorType.TRANSLATION_SERVICE_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.RATE_LIMIT_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.NETWORK_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.TIMEOUT_ERROR: ErrorSeverity.LOW,
            ErrorType.VALIDATION_ERROR: ErrorSeverity.LOW,
            ErrorType.LANGUAGE_DETECTION_ERROR: ErrorSeverity.LOW
        }
    
    def classify_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorType, ErrorSeverity]:
        """
        Classify an exception and determine its type and severity.
        
        Args:
            exception: The exception to classify
            context: Additional context about where the error occurred
            
        Returns:
            Tuple of (error_type, severity)
        """
        error_message = str(exception).lower()
        exception_type = type(exception).__name__.lower()
        
        # Check patterns to classify error type
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if pattern in error_message or pattern in exception_type:
                    severity = self.severity_mappings.get(error_type, ErrorSeverity.MEDIUM)
                    return error_type, severity
        
        # Check specific exception types
        if 'timeout' in exception_type:
            return ErrorType.TIMEOUT_ERROR, ErrorSeverity.LOW
        elif 'connection' in exception_type:
            return ErrorType.NETWORK_ERROR, ErrorSeverity.MEDIUM
        elif 'validation' in exception_type:
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        elif 'auth' in exception_type:
            return ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.CRITICAL
        
        # Default to unknown error
        return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM


class AlertManager:
    """Manager for sending alerts about critical errors."""
    
    def __init__(self):
        self.alert_cooldowns = {}  # Track alert cooldowns to prevent spam
        self.cooldown_duration = timedelta(minutes=15)  # 15 minute cooldown
    
    def should_send_alert(self, error_type: ErrorType, severity: ErrorSeverity) -> bool:
        """Determine if an alert should be sent."""
        # Only send alerts for high/critical severity
        if severity not in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return False
        
        # Check cooldown
        cooldown_key = f"{error_type.value}_{severity.value}"
        now = datetime.utcnow()
        
        if cooldown_key in self.alert_cooldowns:
            last_alert = self.alert_cooldowns[cooldown_key]
            if now - last_alert < self.cooldown_duration:
                return False
        
        # Update cooldown
        self.alert_cooldowns[cooldown_key] = now
        return True
    
    def send_error_alert(
        self,
        error_record: ErrorRecord,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Send error alert via configured channels."""
        if not self.should_send_alert(error_record.error_type, error_record.severity):
            return
        
        # Log the alert
        logger.critical(
            f"Critical Error Alert: {error_record.error_type.value} - {error_record.message}"
        )
        
        # Send email alert if configured
        if hasattr(settings, 'alert_email_recipients') and settings.alert_email_recipients:
            try:
                self._send_email_alert(error_record, additional_context)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")
        
        # Send webhook alert if configured
        if hasattr(settings, 'alert_webhook_url') and settings.alert_webhook_url:
            try:
                self._send_webhook_alert(error_record, additional_context)
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_email_alert(
        self,
        error_record: ErrorRecord,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Send email alert."""
        if not hasattr(settings, 'smtp_server') or not settings.smtp_server:
            return
        
        # Create email message
        msg = MimeMultipart()
        msg['From'] = getattr(settings, 'alert_email_from', 'proscrape@example.com')
        msg['To'] = ', '.join(settings.alert_email_recipients)
        msg['Subject'] = f"ProScrape Critical Error [{error_record.severity.value.upper()}]: {error_record.error_type.value}"
        
        # Email body
        body = f"""
        Critical Error Alert - ProScrape i18n Pipeline
        
        Error ID: {error_record.error_id}
        Error Type: {error_record.error_type.value}
        Severity: {error_record.severity.value.upper()}
        Message: {error_record.message}
        Occurred At: {error_record.created_at.isoformat()}
        Retry Count: {error_record.retry_count}/{error_record.max_retries}
        
        Context:
        {json.dumps(error_record.context, indent=2)}
        
        Details:
        {json.dumps(error_record.details, indent=2)}
        
        Additional Context:
        {json.dumps(additional_context or {}, indent=2)}
        
        Traceback:
        {error_record.traceback_str or 'Not available'}
        
        Please investigate this critical error immediately.
        """
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(settings.smtp_server, getattr(settings, 'smtp_port', 587))
        
        if getattr(settings, 'smtp_use_tls', True):
            server.starttls()
        
        if hasattr(settings, 'smtp_username') and settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        
        server.sendmail(msg['From'], settings.alert_email_recipients, msg.as_string())
        server.quit()
    
    def _send_webhook_alert(
        self,
        error_record: ErrorRecord,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Send webhook alert."""
        payload = {
            'alert_type': 'critical_error',
            'error_id': error_record.error_id,
            'error_type': error_record.error_type.value,
            'severity': error_record.severity.value,
            'message': error_record.message,
            'occurred_at': error_record.created_at.isoformat(),
            'retry_count': error_record.retry_count,
            'max_retries': error_record.max_retries,
            'context': error_record.context,
            'details': error_record.details,
            'additional_context': additional_context or {}
        }
        
        response = requests.post(
            settings.alert_webhook_url,
            json=payload,
            timeout=10
        )
        
        response.raise_for_status()


class I18nErrorHandler:
    """Main error handling system for the i18n pipeline."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        db_manager: Optional[I18nDatabaseManager] = None
    ):
        # Initialize components
        self.redis_url = redis_url or settings.redis_url
        self.db_manager = db_manager
        
        # Error handling components
        self.error_classifier = ErrorClassifier()
        self.retry_manager = RetryManager()
        self.alert_manager = AlertManager()
        self.dead_letter_queue = DeadLetterQueue(self.redis_url)
        
        # Error storage
        self.error_records = {}  # In-memory storage for recent errors
        self.max_error_records = 1000
    
    def handle_error(
        self,
        exception: Exception,
        context: Dict[str, Any],
        item_data: Optional[Dict[str, Any]] = None,
        operation_name: str = "unknown"
    ) -> ErrorRecord:
        """
        Handle an error with classification, logging, and recovery logic.
        
        Args:
            exception: The exception that occurred
            context: Context information about where the error occurred
            item_data: Data being processed when error occurred
            operation_name: Name of the operation that failed
            
        Returns:
            ErrorRecord with error details and recovery information
        """
        # Generate unique error ID
        error_id = str(uuid.uuid4())
        
        # Classify the error
        error_type, severity = self.error_classifier.classify_error(exception, context)
        
        # Create error record
        error_record = ErrorRecord(
            error_id=error_id,
            error_type=error_type,
            severity=severity,
            message=str(exception),
            details={
                'exception_type': type(exception).__name__,
                'operation_name': operation_name,
                'item_data_available': item_data is not None
            },
            context=context,
            traceback_str=traceback.format_exc(),
            created_at=datetime.utcnow()
        )
        
        # Store error record
        self._store_error_record(error_record)
        
        # Log the error
        log_level = logging.CRITICAL if severity == ErrorSeverity.CRITICAL else logging.ERROR
        logger.log(
            log_level,
            f"Error [{error_type.value}] in {operation_name}: {exception}",
            extra={'error_id': error_id, 'context': context}
        )
        
        # Send alerts for critical errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.alert_manager.send_error_alert(error_record, {
                'operation_name': operation_name,
                'has_item_data': item_data is not None
            })
        
        # Add to dead letter queue if item data is available and error is severe
        if item_data and severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.dead_letter_queue.enqueue_failed_item(
                item_data, error_record, operation_name
            )
        
        return error_record
    
    def should_retry_operation(
        self,
        error_record: ErrorRecord,
        increment_retry_count: bool = True
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Determine if an operation should be retried and when.
        
        Args:
            error_record: The error record to evaluate
            increment_retry_count: Whether to increment the retry count
            
        Returns:
            Tuple of (should_retry, next_retry_time)
        """
        if increment_retry_count:
            error_record.retry_count += 1
        
        should_retry = self.retry_manager.should_retry(
            error_record.error_type,
            error_record.retry_count
        )
        
        if should_retry:
            next_retry_time = self.retry_manager.get_next_retry_time(
                error_record.retry_count,
                error_record.error_type
            )
            error_record.next_retry_at = next_retry_time
            return True, next_retry_time
        else:
            return False, None
    
    def create_retry_task(
        self,
        original_task: Callable,
        args: Tuple,
        kwargs: Dict[str, Any],
        error_record: ErrorRecord,
        delay_seconds: float
    ):
        """Create a delayed retry task."""
        try:
            # This would integrate with Celery's retry mechanism
            # For now, we'll just log the intended retry
            logger.info(
                f"Scheduling retry for error {error_record.error_id} "
                f"in {delay_seconds:.1f} seconds (attempt {error_record.retry_count + 1})"
            )
            
            # In a real implementation, you would use:
            # original_task.apply_async(args=args, kwargs=kwargs, countdown=delay_seconds)
            
        except Exception as e:
            logger.error(f"Failed to schedule retry task: {e}")
    
    def _store_error_record(self, error_record: ErrorRecord):
        """Store error record in memory and optionally in database."""
        # Store in memory
        self.error_records[error_record.error_id] = error_record
        
        # Trim old records
        if len(self.error_records) > self.max_error_records:
            # Remove oldest records
            oldest_ids = sorted(
                self.error_records.keys(),
                key=lambda k: self.error_records[k].created_at
            )[:len(self.error_records) - self.max_error_records]
            
            for old_id in oldest_ids:
                del self.error_records[old_id]
        
        # Store in database if available
        if self.db_manager:
            try:
                # Convert to serializable format
                error_data = {
                    'error_id': error_record.error_id,
                    'error_type': error_record.error_type.value,
                    'severity': error_record.severity.value,
                    'message': error_record.message,
                    'details': error_record.details,
                    'context': error_record.context,
                    'traceback': error_record.traceback_str,
                    'created_at': error_record.created_at,
                    'retry_count': error_record.retry_count,
                    'max_retries': error_record.max_retries,
                    'next_retry_at': error_record.next_retry_at,
                    'resolved_at': error_record.resolved_at,
                    'resolution_method': error_record.resolution_method
                }
                
                # Store in MongoDB (you'd need to add this collection to the DB manager)
                # self.db_manager.db.error_records.insert_one(error_data)
                
            except Exception as e:
                logger.warning(f"Failed to store error record in database: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and health metrics."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # Analyze recent errors
        recent_errors = [
            err for err in self.error_records.values()
            if err.created_at >= last_hour
        ]
        
        daily_errors = [
            err for err in self.error_records.values()
            if err.created_at >= last_day
        ]
        
        # Count by type and severity
        hourly_by_type = {}
        hourly_by_severity = {}
        daily_by_type = {}
        daily_by_severity = {}
        
        for err in recent_errors:
            error_type = err.error_type.value
            severity = err.severity.value
            
            hourly_by_type[error_type] = hourly_by_type.get(error_type, 0) + 1
            hourly_by_severity[severity] = hourly_by_severity.get(severity, 0) + 1
        
        for err in daily_errors:
            error_type = err.error_type.value
            severity = err.severity.value
            
            daily_by_type[error_type] = daily_by_type.get(error_type, 0) + 1
            daily_by_severity[severity] = daily_by_severity.get(severity, 0) + 1
        
        # Get DLQ statistics
        dlq_stats = self.dead_letter_queue.get_queue_stats()
        
        return {
            'report_generated_at': now.isoformat(),
            'total_error_records': len(self.error_records),
            'recent_errors': {
                'last_hour': {
                    'total': len(recent_errors),
                    'by_type': hourly_by_type,
                    'by_severity': hourly_by_severity
                },
                'last_day': {
                    'total': len(daily_errors),
                    'by_type': daily_by_type,
                    'by_severity': daily_by_severity
                }
            },
            'dead_letter_queue': dlq_stats,
            'retry_configuration': {
                'max_retries': self.retry_manager.config.max_retries,
                'base_delay_seconds': self.retry_manager.config.base_delay_seconds,
                'max_delay_seconds': self.retry_manager.config.max_delay_seconds
            }
        }
    
    def process_dead_letter_queue(
        self,
        processor_function: Callable[[Dict[str, Any]], bool],
        max_items: int = 10
    ) -> Dict[str, Any]:
        """
        Process items from the dead letter queue.
        
        Args:
            processor_function: Function to process each failed item
            max_items: Maximum number of items to process
            
        Returns:
            Processing results
        """
        processed = 0
        successful = 0
        failed = 0
        
        logger.info(f"Starting DLQ processing (max {max_items} items)")
        
        for _ in range(max_items):
            dlq_entry = self.dead_letter_queue.dequeue_failed_item()
            if not dlq_entry:
                break
            
            processed += 1
            
            try:
                # Attempt to reprocess the item
                original_item = dlq_entry['original_item']
                success = processor_function(original_item)
                
                if success:
                    successful += 1
                    logger.info(f"Successfully reprocessed DLQ item: {dlq_entry['id']}")
                else:
                    failed += 1
                    # Re-enqueue if processing failed
                    error_record = ErrorRecord(
                        error_id=str(uuid.uuid4()),
                        error_type=ErrorType.UNKNOWN_ERROR,
                        severity=ErrorSeverity.MEDIUM,
                        message="DLQ reprocessing failed",
                        details={'dlq_entry_id': dlq_entry['id']},
                        context={'operation': 'dlq_reprocessing'},
                        traceback_str=None,
                        created_at=datetime.utcnow()
                    )
                    
                    self.dead_letter_queue.enqueue_failed_item(
                        original_item, error_record, "dlq_reprocessing"
                    )
                
            except Exception as e:
                failed += 1
                logger.error(f"Error reprocessing DLQ item {dlq_entry['id']}: {e}")
        
        logger.info(f"DLQ processing completed: {processed} processed, {successful} successful, {failed} failed")
        
        return {
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'completed_at': datetime.utcnow().isoformat()
        }


# Decorator for automatic error handling
def handle_i18n_errors(
    operation_name: str,
    context: Optional[Dict[str, Any]] = None,
    error_handler: Optional[I18nErrorHandler] = None
):
    """
    Decorator for automatic error handling in i18n operations.
    
    Args:
        operation_name: Name of the operation for logging
        context: Additional context information
        error_handler: Error handler instance (creates new one if None)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not error_handler:
                handler = I18nErrorHandler()
            else:
                handler = error_handler
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Extract item data if available
                item_data = None
                if args and isinstance(args[0], dict):
                    item_data = args[0]
                elif 'item_data' in kwargs:
                    item_data = kwargs['item_data']
                
                # Handle the error
                error_record = handler.handle_error(
                    e, context or {}, item_data, operation_name
                )
                
                # Check if should retry
                should_retry, next_retry_time = handler.should_retry_operation(error_record)
                
                if should_retry:
                    delay = (next_retry_time - datetime.utcnow()).total_seconds()
                    handler.create_retry_task(func, args, kwargs, error_record, delay)
                
                # Re-raise the exception
                raise
        
        return wrapper
    return decorator


# Convenience functions
def create_error_handler(
    redis_url: Optional[str] = None,
    db_manager: Optional[I18nDatabaseManager] = None
) -> I18nErrorHandler:
    """Create an error handler with default configuration."""
    return I18nErrorHandler(redis_url, db_manager)


def get_error_handler_instance() -> I18nErrorHandler:
    """Get a global error handler instance."""
    if not hasattr(get_error_handler_instance, '_instance'):
        get_error_handler_instance._instance = create_error_handler()
    return get_error_handler_instance._instance