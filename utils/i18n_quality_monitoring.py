"""
Data Quality Monitoring System for ProScrape i18n Pipeline

This module provides comprehensive monitoring and quality assurance for multilingual
real estate data, including translation quality metrics, data consistency checks,
and automated alerting for quality degradation.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import json
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from models.i18n_models import (
    SupportedLanguage, TranslationQuality, TranslationStatus,
    MultilingualListing, TranslationResult
)
from utils.i18n_database import I18nDatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)


class QualityMetricType(Enum):
    """Types of quality metrics."""
    COMPLETENESS = "completeness"        # How complete is the data
    ACCURACY = "accuracy"               # How accurate are translations
    CONSISTENCY = "consistency"         # How consistent across languages
    FRESHNESS = "freshness"            # How recent is the data
    UNIQUENESS = "uniqueness"          # How many duplicates exist
    VALIDITY = "validity"              # How valid is the data format


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityMetric:
    """Individual quality metric."""
    metric_type: QualityMetricType
    name: str
    value: float
    threshold: float
    status: str  # "pass", "warning", "fail"
    details: Dict[str, Any]
    measured_at: datetime


@dataclass
class QualityAlert:
    """Quality alert notification."""
    alert_id: str
    severity: AlertSeverity
    metric_type: QualityMetricType
    message: str
    details: Dict[str, Any]
    created_at: datetime
    resolved_at: Optional[datetime] = None


class DataCompletenessMonitor:
    """Monitor data completeness across languages and fields."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
    
    def check_field_completeness(
        self,
        field_name: str,
        language: Optional[SupportedLanguage] = None
    ) -> QualityMetric:
        """
        Check completeness of a specific field across listings.
        
        Args:
            field_name: Name of the field to check
            language: Specific language to check (if None, checks all)
            
        Returns:
            QualityMetric for field completeness
        """
        try:
            collection = self.db_manager.get_listings_collection()
            
            # Get total listings count
            total_listings = collection.count_documents({})
            
            if total_listings == 0:
                return QualityMetric(
                    metric_type=QualityMetricType.COMPLETENESS,
                    name=f"{field_name}_completeness",
                    value=0.0,
                    threshold=0.8,
                    status="fail",
                    details={"reason": "No listings found"},
                    measured_at=datetime.utcnow()
                )
            
            # Build query for field completeness
            if language:
                lang_key = language.value
                field_path = f"{field_name}.{lang_key}"
                query = {field_path: {"$exists": True, "$ne": None, "$ne": ""}}
            else:
                # Check if any language version exists
                query = {"$or": [
                    {f"{field_name}.en": {"$exists": True, "$ne": None, "$ne": ""}},
                    {f"{field_name}.lv": {"$exists": True, "$ne": None, "$ne": ""}},
                    {f"{field_name}.ru": {"$exists": True, "$ne": None, "$ne": ""}}
                ]}
            
            # Count listings with the field
            complete_listings = collection.count_documents(query)
            
            # Calculate completeness percentage
            completeness = complete_listings / total_listings
            
            # Determine status
            threshold = 0.8  # 80% completeness threshold
            if completeness >= threshold:
                status = "pass"
            elif completeness >= threshold * 0.7:  # 56%
                status = "warning"
            else:
                status = "fail"
            
            return QualityMetric(
                metric_type=QualityMetricType.COMPLETENESS,
                name=f"{field_name}_completeness{f'_{language.value}' if language else ''}",
                value=completeness,
                threshold=threshold,
                status=status,
                details={
                    "total_listings": total_listings,
                    "complete_listings": complete_listings,
                    "missing_listings": total_listings - complete_listings,
                    "language": language.value if language else "all"
                },
                measured_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error checking field completeness for {field_name}: {e}")
            return QualityMetric(
                metric_type=QualityMetricType.COMPLETENESS,
                name=f"{field_name}_completeness",
                value=0.0,
                threshold=0.8,
                status="fail",
                details={"error": str(e)},
                measured_at=datetime.utcnow()
            )
    
    def check_translation_completeness(self) -> Dict[SupportedLanguage, QualityMetric]:
        """Check translation completeness across all supported languages."""
        results = {}
        
        for language in [SupportedLanguage.ENGLISH, SupportedLanguage.LATVIAN, SupportedLanguage.RUSSIAN]:
            # Check completeness for key fields
            field_completeness = []
            
            for field in ['title', 'description']:
                metric = self.check_field_completeness(field, language)
                field_completeness.append(metric.value)
            
            # Calculate average completeness
            avg_completeness = statistics.mean(field_completeness) if field_completeness else 0.0
            
            # Determine overall status
            threshold = 0.7
            if avg_completeness >= threshold:
                status = "pass"
            elif avg_completeness >= threshold * 0.7:
                status = "warning"
            else:
                status = "fail"
            
            results[language] = QualityMetric(
                metric_type=QualityMetricType.COMPLETENESS,
                name=f"translation_completeness_{language.value}",
                value=avg_completeness,
                threshold=threshold,
                status=status,
                details={
                    "field_completeness": {
                        "title": field_completeness[0] if len(field_completeness) > 0 else 0.0,
                        "description": field_completeness[1] if len(field_completeness) > 1 else 0.0
                    }
                },
                measured_at=datetime.utcnow()
            )
        
        return results


class TranslationQualityMonitor:
    """Monitor translation quality and accuracy."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
    
    def check_translation_quality_distribution(self) -> QualityMetric:
        """Check the distribution of translation quality ratings."""
        try:
            collection = self.db_manager.get_translations_collection()
            
            # Get quality distribution
            pipeline = [
                {"$group": {
                    "_id": "$quality_assessment",
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(collection.aggregate(pipeline))
            total_translations = sum(result["count"] for result in results)
            
            if total_translations == 0:
                return QualityMetric(
                    metric_type=QualityMetricType.ACCURACY,
                    name="translation_quality_distribution",
                    value=0.0,
                    threshold=0.7,
                    status="fail",
                    details={"reason": "No translations found"},
                    measured_at=datetime.utcnow()
                )
            
            # Calculate quality distribution
            quality_dist = {}
            for result in results:
                quality = result["_id"] or "unknown"
                count = result["count"]
                quality_dist[quality] = count / total_translations
            
            # Calculate quality score (weighted average)
            quality_weights = {
                "high": 1.0,
                "medium": 0.6,
                "low": 0.2,
                "unknown": 0.0
            }
            
            quality_score = sum(
                quality_dist.get(quality, 0) * weight
                for quality, weight in quality_weights.items()
            )
            
            # Determine status
            threshold = 0.7
            if quality_score >= threshold:
                status = "pass"
            elif quality_score >= threshold * 0.7:
                status = "warning"
            else:
                status = "fail"
            
            return QualityMetric(
                metric_type=QualityMetricType.ACCURACY,
                name="translation_quality_distribution",
                value=quality_score,
                threshold=threshold,
                status=status,
                details={
                    "total_translations": total_translations,
                    "quality_distribution": quality_dist,
                    "high_quality_percentage": quality_dist.get("high", 0) * 100,
                    "low_quality_percentage": quality_dist.get("low", 0) * 100
                },
                measured_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error checking translation quality distribution: {e}")
            return QualityMetric(
                metric_type=QualityMetricType.ACCURACY,
                name="translation_quality_distribution",
                value=0.0,
                threshold=0.7,
                status="fail",
                details={"error": str(e)},
                measured_at=datetime.utcnow()
            )
    
    def check_translation_service_performance(self) -> Dict[str, QualityMetric]:
        """Check performance metrics for each translation service."""
        try:
            collection = self.db_manager.get_translations_collection()
            
            # Get service statistics
            pipeline = [
                {"$group": {
                    "_id": "$translation_service",
                    "count": {"$sum": 1},
                    "avg_time": {"$avg": "$translation_time"},
                    "avg_confidence": {"$avg": "$confidence_score"},
                    "quality_counts": {
                        "$push": "$quality_assessment"
                    }
                }}
            ]
            
            results = list(collection.aggregate(pipeline))
            service_metrics = {}
            
            for result in results:
                service_name = result["_id"] or "unknown"
                count = result["count"]
                avg_time = result.get("avg_time", 0)
                avg_confidence = result.get("avg_confidence", 0)
                quality_counts = result.get("quality_counts", [])
                
                # Calculate quality score for this service
                quality_dist = {}
                for quality in quality_counts:
                    quality_dist[quality] = quality_dist.get(quality, 0) + 1
                
                total = len(quality_counts)
                if total > 0:
                    high_quality_rate = quality_dist.get("high", 0) / total
                else:
                    high_quality_rate = 0.0
                
                # Calculate performance score (combination of quality and speed)
                performance_score = (high_quality_rate * 0.7) + (min(1.0, 5.0 / max(avg_time, 0.1)) * 0.3)
                
                # Determine status
                threshold = 0.6
                if performance_score >= threshold:
                    status = "pass"
                elif performance_score >= threshold * 0.7:
                    status = "warning"
                else:
                    status = "fail"
                
                service_metrics[service_name] = QualityMetric(
                    metric_type=QualityMetricType.ACCURACY,
                    name=f"service_performance_{service_name}",
                    value=performance_score,
                    threshold=threshold,
                    status=status,
                    details={
                        "translation_count": count,
                        "average_time_seconds": avg_time,
                        "average_confidence": avg_confidence,
                        "high_quality_rate": high_quality_rate,
                        "quality_distribution": quality_dist
                    },
                    measured_at=datetime.utcnow()
                )
            
            return service_metrics
            
        except Exception as e:
            logger.error(f"Error checking translation service performance: {e}")
            return {}


class DataConsistencyMonitor:
    """Monitor data consistency across languages and sources."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
    
    def check_price_consistency(self) -> QualityMetric:
        """Check for price consistency and reasonableness."""
        try:
            collection = self.db_manager.get_listings_collection()
            
            # Get price statistics
            pipeline = [
                {"$match": {"price.amount": {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price.amount"},
                    "min_price": {"$min": "$price.amount"},
                    "max_price": {"$max": "$price.amount"},
                    "prices": {"$push": "$price.amount"}
                }}
            ]
            
            results = list(collection.aggregate(pipeline))
            
            if not results:
                return QualityMetric(
                    metric_type=QualityMetricType.VALIDITY,
                    name="price_consistency",
                    value=0.0,
                    threshold=0.8,
                    status="fail",
                    details={"reason": "No price data found"},
                    measured_at=datetime.utcnow()
                )
            
            result = results[0]
            count = result["count"]
            avg_price = result["avg_price"]
            min_price = result["min_price"]
            max_price = result["max_price"]
            prices = result["prices"]
            
            # Check for outliers (prices beyond 3 standard deviations)
            if len(prices) > 1:
                std_dev = statistics.stdev(prices)
                outliers = [
                    p for p in prices 
                    if abs(p - avg_price) > 3 * std_dev
                ]
                outlier_rate = len(outliers) / len(prices)
            else:
                outlier_rate = 0.0
            
            # Check for unreasonable prices (< 1000 or > 10,000,000)
            unreasonable_count = sum(
                1 for p in prices 
                if p < 1000 or p > 10000000
            )
            unreasonable_rate = unreasonable_count / len(prices)
            
            # Calculate consistency score
            consistency_score = 1.0 - max(outlier_rate, unreasonable_rate)
            
            # Determine status
            threshold = 0.8
            if consistency_score >= threshold:
                status = "pass"
            elif consistency_score >= threshold * 0.7:
                status = "warning"
            else:
                status = "fail"
            
            return QualityMetric(
                metric_type=QualityMetricType.VALIDITY,
                name="price_consistency",
                value=consistency_score,
                threshold=threshold,
                status=status,
                details={
                    "total_listings": count,
                    "average_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "outlier_count": len(outliers) if len(prices) > 1 else 0,
                    "outlier_rate": outlier_rate,
                    "unreasonable_count": unreasonable_count,
                    "unreasonable_rate": unreasonable_rate
                },
                measured_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error checking price consistency: {e}")
            return QualityMetric(
                metric_type=QualityMetricType.VALIDITY,
                name="price_consistency",
                value=0.0,
                threshold=0.8,
                status="fail",
                details={"error": str(e)},
                measured_at=datetime.utcnow()
            )
    
    def check_coordinate_validity(self) -> QualityMetric:
        """Check validity of geographic coordinates."""
        try:
            collection = self.db_manager.get_listings_collection()
            
            # Query for listings with coordinates
            query = {
                "address.latitude": {"$exists": True, "$ne": None},
                "address.longitude": {"$exists": True, "$ne": None}
            }
            
            total_with_coords = collection.count_documents(query)
            
            if total_with_coords == 0:
                return QualityMetric(
                    metric_type=QualityMetricType.VALIDITY,
                    name="coordinate_validity",
                    value=0.0,
                    threshold=0.9,
                    status="fail",
                    details={"reason": "No coordinates found"},
                    measured_at=datetime.utcnow()
                )
            
            # Check for coordinates within Latvia bounds
            latvia_bounds = {
                "address.latitude": {"$gte": 55.5, "$lte": 58.1},
                "address.longitude": {"$gte": 20.5, "$lte": 28.5}
            }
            
            valid_coords = collection.count_documents({**query, **latvia_bounds})
            validity_rate = valid_coords / total_with_coords
            
            # Determine status
            threshold = 0.9
            if validity_rate >= threshold:
                status = "pass"
            elif validity_rate >= threshold * 0.8:
                status = "warning"
            else:
                status = "fail"
            
            return QualityMetric(
                metric_type=QualityMetricType.VALIDITY,
                name="coordinate_validity",
                value=validity_rate,
                threshold=threshold,
                status=status,
                details={
                    "total_with_coordinates": total_with_coords,
                    "valid_coordinates": valid_coords,
                    "invalid_coordinates": total_with_coords - valid_coords,
                    "validity_rate": validity_rate
                },
                measured_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error checking coordinate validity: {e}")
            return QualityMetric(
                metric_type=QualityMetricType.VALIDITY,
                name="coordinate_validity",
                value=0.0,
                threshold=0.9,
                status="fail",
                details={"error": str(e)},
                measured_at=datetime.utcnow()
            )


class DataFreshnessMonitor:
    """Monitor data freshness and update frequency."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
    
    def check_data_freshness(self, max_age_days: int = 7) -> QualityMetric:
        """Check how fresh the data is."""
        try:
            collection = self.db_manager.get_listings_collection()
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            # Get total listings
            total_listings = collection.count_documents({})
            
            if total_listings == 0:
                return QualityMetric(
                    metric_type=QualityMetricType.FRESHNESS,
                    name="data_freshness",
                    value=0.0,
                    threshold=0.8,
                    status="fail",
                    details={"reason": "No listings found"},
                    measured_at=datetime.utcnow()
                )
            
            # Count fresh listings
            fresh_listings = collection.count_documents({
                "scraped_at": {"$gte": cutoff_date}
            })
            
            freshness_rate = fresh_listings / total_listings
            
            # Determine status
            threshold = 0.8
            if freshness_rate >= threshold:
                status = "pass"
            elif freshness_rate >= threshold * 0.6:
                status = "warning"
            else:
                status = "fail"
            
            return QualityMetric(
                metric_type=QualityMetricType.FRESHNESS,
                name="data_freshness",
                value=freshness_rate,
                threshold=threshold,
                status=status,
                details={
                    "total_listings": total_listings,
                    "fresh_listings": fresh_listings,
                    "stale_listings": total_listings - fresh_listings,
                    "cutoff_date": cutoff_date.isoformat(),
                    "max_age_days": max_age_days
                },
                measured_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
            return QualityMetric(
                metric_type=QualityMetricType.FRESHNESS,
                name="data_freshness",
                value=0.0,
                threshold=0.8,
                status="fail",
                details={"error": str(e)},
                measured_at=datetime.utcnow()
            )


class DuplicateMonitor:
    """Monitor duplicate detection and data uniqueness."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
    
    def check_duplicate_rate(self) -> QualityMetric:
        """Check the rate of duplicate listings."""
        try:
            collection = self.db_manager.get_listings_collection()
            
            # Get total listings
            total_listings = collection.count_documents({})
            
            if total_listings == 0:
                return QualityMetric(
                    metric_type=QualityMetricType.UNIQUENESS,
                    name="duplicate_rate",
                    value=1.0,  # 100% uniqueness if no data
                    threshold=0.95,
                    status="pass",
                    details={"reason": "No listings found"},
                    measured_at=datetime.utcnow()
                )
            
            # Check for exact duplicates by listing_id + source_site
            pipeline = [
                {"$group": {
                    "_id": {
                        "listing_id": "$listing_id",
                        "source_site": "$source_site"
                    },
                    "count": {"$sum": 1}
                }},
                {"$match": {"count": {"$gt": 1}}}
            ]
            
            duplicate_groups = list(collection.aggregate(pipeline))
            
            # Calculate duplicate count
            duplicate_listings = sum(group["count"] - 1 for group in duplicate_groups)
            uniqueness_rate = 1.0 - (duplicate_listings / total_listings)
            
            # Determine status
            threshold = 0.95
            if uniqueness_rate >= threshold:
                status = "pass"
            elif uniqueness_rate >= threshold * 0.9:
                status = "warning"
            else:
                status = "fail"
            
            return QualityMetric(
                metric_type=QualityMetricType.UNIQUENESS,
                name="duplicate_rate",
                value=uniqueness_rate,
                threshold=threshold,
                status=status,
                details={
                    "total_listings": total_listings,
                    "duplicate_listings": duplicate_listings,
                    "unique_listings": total_listings - duplicate_listings,
                    "duplicate_groups": len(duplicate_groups),
                    "uniqueness_rate": uniqueness_rate
                },
                measured_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error checking duplicate rate: {e}")
            return QualityMetric(
                metric_type=QualityMetricType.UNIQUENESS,
                name="duplicate_rate",
                value=0.0,
                threshold=0.95,
                status="fail",
                details={"error": str(e)},
                measured_at=datetime.utcnow()
            )


class QualityAlertManager:
    """Manage quality alerts and notifications."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
        self.active_alerts = []
    
    def evaluate_metric_for_alerts(self, metric: QualityMetric) -> Optional[QualityAlert]:
        """Evaluate a metric and create an alert if needed."""
        
        # Determine alert severity based on metric status and value
        severity = None
        
        if metric.status == "fail":
            if metric.value < metric.threshold * 0.5:
                severity = AlertSeverity.CRITICAL
            else:
                severity = AlertSeverity.HIGH
        elif metric.status == "warning":
            severity = AlertSeverity.MEDIUM
        
        if not severity:
            return None
        
        # Create alert message
        if metric.metric_type == QualityMetricType.COMPLETENESS:
            message = f"Data completeness for {metric.name} is {metric.value:.1%} (threshold: {metric.threshold:.1%})"
        elif metric.metric_type == QualityMetricType.ACCURACY:
            message = f"Translation accuracy for {metric.name} is {metric.value:.1%} (threshold: {metric.threshold:.1%})"
        elif metric.metric_type == QualityMetricType.VALIDITY:
            message = f"Data validity for {metric.name} is {metric.value:.1%} (threshold: {metric.threshold:.1%})"
        elif metric.metric_type == QualityMetricType.FRESHNESS:
            message = f"Data freshness is {metric.value:.1%} (threshold: {metric.threshold:.1%})"
        elif metric.metric_type == QualityMetricType.UNIQUENESS:
            message = f"Data uniqueness is {metric.value:.1%} (threshold: {metric.threshold:.1%})"
        else:
            message = f"Quality issue detected for {metric.name}: {metric.value:.1%}"
        
        # Create alert
        alert = QualityAlert(
            alert_id=f"{metric.name}_{metric.measured_at.strftime('%Y%m%d_%H%M%S')}",
            severity=severity,
            metric_type=metric.metric_type,
            message=message,
            details={
                "metric_name": metric.name,
                "metric_value": metric.value,
                "threshold": metric.threshold,
                "metric_details": metric.details
            },
            created_at=datetime.utcnow()
        )
        
        return alert
    
    def send_alert_notification(self, alert: QualityAlert):
        """Send alert notification via configured channels."""
        
        # Log the alert
        logger.warning(f"Quality Alert [{alert.severity.value.upper()}]: {alert.message}")
        
        # Send email notification if configured
        if hasattr(settings, 'alert_email_recipients') and settings.alert_email_recipients:
            try:
                self._send_email_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")
        
        # Send webhook notification if configured
        if hasattr(settings, 'alert_webhook_url') and settings.alert_webhook_url:
            try:
                self._send_webhook_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_email_alert(self, alert: QualityAlert):
        """Send email alert notification."""
        if not hasattr(settings, 'smtp_server') or not settings.smtp_server:
            return
        
        # Create email message
        msg = MimeMultipart()
        msg['From'] = getattr(settings, 'alert_email_from', 'proscrape@example.com')
        msg['To'] = ', '.join(settings.alert_email_recipients)
        msg['Subject'] = f"ProScrape Quality Alert [{alert.severity.value.upper()}]: {alert.metric_type.value}"
        
        # Email body
        body = f"""
        Quality Alert Details:
        
        Alert ID: {alert.alert_id}
        Severity: {alert.severity.value.upper()}
        Metric Type: {alert.metric_type.value}
        Message: {alert.message}
        Created At: {alert.created_at.isoformat()}
        
        Details:
        {json.dumps(alert.details, indent=2)}
        
        Please investigate this quality issue in the ProScrape i18n pipeline.
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
    
    def _send_webhook_alert(self, alert: QualityAlert):
        """Send webhook alert notification."""
        import requests
        
        payload = {
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'metric_type': alert.metric_type.value,
            'message': alert.message,
            'details': alert.details,
            'created_at': alert.created_at.isoformat()
        }
        
        response = requests.post(
            settings.alert_webhook_url,
            json=payload,
            timeout=10
        )
        
        response.raise_for_status()


class I18nQualityMonitoringSystem:
    """Main quality monitoring system for the i18n pipeline."""
    
    def __init__(self, db_manager: I18nDatabaseManager):
        self.db_manager = db_manager
        
        # Initialize monitors
        self.completeness_monitor = DataCompletenessMonitor(db_manager)
        self.translation_monitor = TranslationQualityMonitor(db_manager)
        self.consistency_monitor = DataConsistencyMonitor(db_manager)
        self.freshness_monitor = DataFreshnessMonitor(db_manager)
        self.duplicate_monitor = DuplicateMonitor(db_manager)
        self.alert_manager = QualityAlertManager(db_manager)
    
    def run_comprehensive_quality_check(self) -> Dict[str, Any]:
        """Run a comprehensive quality check across all metrics."""
        logger.info("Starting comprehensive quality check")
        
        quality_report = {
            'report_generated_at': datetime.utcnow().isoformat(),
            'overall_status': 'unknown',
            'metrics': {},
            'alerts': [],
            'summary': {}
        }
        
        all_metrics = []
        
        # 1. Check data completeness
        logger.info("Checking data completeness")
        try:
            # Check field completeness
            title_completeness = self.completeness_monitor.check_field_completeness('title')
            desc_completeness = self.completeness_monitor.check_field_completeness('description')
            
            quality_report['metrics']['title_completeness'] = title_completeness.__dict__
            quality_report['metrics']['description_completeness'] = desc_completeness.__dict__
            
            all_metrics.extend([title_completeness, desc_completeness])
            
            # Check translation completeness
            translation_completeness = self.completeness_monitor.check_translation_completeness()
            for lang, metric in translation_completeness.items():
                quality_report['metrics'][f'translation_completeness_{lang.value}'] = metric.__dict__
                all_metrics.append(metric)
                
        except Exception as e:
            logger.error(f"Error in completeness check: {e}")
        
        # 2. Check translation quality
        logger.info("Checking translation quality")
        try:
            quality_dist = self.translation_monitor.check_translation_quality_distribution()
            quality_report['metrics']['translation_quality_distribution'] = quality_dist.__dict__
            all_metrics.append(quality_dist)
            
            service_performance = self.translation_monitor.check_translation_service_performance()
            for service, metric in service_performance.items():
                quality_report['metrics'][f'service_performance_{service}'] = metric.__dict__
                all_metrics.append(metric)
                
        except Exception as e:
            logger.error(f"Error in translation quality check: {e}")
        
        # 3. Check data consistency
        logger.info("Checking data consistency")
        try:
            price_consistency = self.consistency_monitor.check_price_consistency()
            coord_validity = self.consistency_monitor.check_coordinate_validity()
            
            quality_report['metrics']['price_consistency'] = price_consistency.__dict__
            quality_report['metrics']['coordinate_validity'] = coord_validity.__dict__
            
            all_metrics.extend([price_consistency, coord_validity])
            
        except Exception as e:
            logger.error(f"Error in consistency check: {e}")
        
        # 4. Check data freshness
        logger.info("Checking data freshness")
        try:
            freshness = self.freshness_monitor.check_data_freshness()
            quality_report['metrics']['data_freshness'] = freshness.__dict__
            all_metrics.append(freshness)
            
        except Exception as e:
            logger.error(f"Error in freshness check: {e}")
        
        # 5. Check duplicates
        logger.info("Checking duplicates")
        try:
            duplicate_rate = self.duplicate_monitor.check_duplicate_rate()
            quality_report['metrics']['duplicate_rate'] = duplicate_rate.__dict__
            all_metrics.append(duplicate_rate)
            
        except Exception as e:
            logger.error(f"Error in duplicate check: {e}")
        
        # 6. Evaluate alerts
        logger.info("Evaluating alerts")
        for metric in all_metrics:
            alert = self.alert_manager.evaluate_metric_for_alerts(metric)
            if alert:
                quality_report['alerts'].append(alert.__dict__)
                
                # Send alert if enabled
                if settings.quality_monitoring_enabled:
                    self.alert_manager.send_alert_notification(alert)
        
        # 7. Calculate overall status
        status_counts = {'pass': 0, 'warning': 0, 'fail': 0}
        for metric in all_metrics:
            status_counts[metric.status] = status_counts.get(metric.status, 0) + 1
        
        total_metrics = len(all_metrics)
        if total_metrics > 0:
            if status_counts['fail'] > total_metrics * 0.2:  # More than 20% failed
                overall_status = 'critical'
            elif status_counts['fail'] > 0 or status_counts['warning'] > total_metrics * 0.3:
                overall_status = 'warning'
            else:
                overall_status = 'healthy'
        else:
            overall_status = 'unknown'
        
        quality_report['overall_status'] = overall_status
        quality_report['summary'] = {
            'total_metrics': total_metrics,
            'passed_metrics': status_counts['pass'],
            'warning_metrics': status_counts['warning'],
            'failed_metrics': status_counts['fail'],
            'total_alerts': len(quality_report['alerts']),
            'status_distribution': status_counts
        }
        
        logger.info(f"Quality check completed: {overall_status} status with {len(quality_report['alerts'])} alerts")
        
        return quality_report
    
    def get_quality_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get quality trends over the specified period."""
        # This would typically store historical metrics in the database
        # and analyze trends. For now, return current snapshot.
        
        current_report = self.run_comprehensive_quality_check()
        
        return {
            'period_days': days,
            'current_snapshot': current_report,
            'trend_analysis': {
                'note': 'Historical trend analysis requires metric storage implementation'
            }
        }


# Convenience functions
def run_quality_check(db_manager: I18nDatabaseManager) -> Dict[str, Any]:
    """Convenience function to run a quality check."""
    monitoring_system = I18nQualityMonitoringSystem(db_manager)
    return monitoring_system.run_comprehensive_quality_check()


def create_quality_alert(
    metric_type: QualityMetricType,
    message: str,
    severity: AlertSeverity = AlertSeverity.MEDIUM,
    details: Optional[Dict[str, Any]] = None
) -> QualityAlert:
    """Create a custom quality alert."""
    return QualityAlert(
        alert_id=f"custom_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        severity=severity,
        metric_type=metric_type,
        message=message,
        details=details or {},
        created_at=datetime.utcnow()
    )