import logging
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages critical failure alerts and notifications."""
    
    def __init__(self):
        self.alert_thresholds = {
            'dead_letter_queue_size': 50,
            'proxy_failure_rate': 0.8,
            'spider_failure_rate': 0.7,
            'database_connection_failures': 5
        }
        self.alert_history = []
    
    def check_and_send_alerts(self):
        """Check all alert conditions and send notifications if needed."""
        alerts = []
        
        # Check dead letter queue size
        alerts.extend(self._check_dead_letter_queue())
        
        # Check proxy health
        alerts.extend(self._check_proxy_health())
        
        # Check database connectivity
        alerts.extend(self._check_database_health())
        
        # Send alerts if any were triggered
        for alert in alerts:
            self._send_alert(alert)
    
    def _check_dead_letter_queue(self) -> List[Dict]:
        """Check if dead letter queue is getting too large."""
        alerts = []
        
        try:
            from spiders.middlewares import retry_middleware_instance
            if retry_middleware_instance:
                stats = retry_middleware_instance.get_dead_letter_stats()
                if stats['total'] > self.alert_thresholds['dead_letter_queue_size']:
                    alerts.append({
                        'type': 'dead_letter_queue_overflow',
                        'severity': 'high',
                        'message': f'Dead letter queue has {stats["total"]} failed requests',
                        'details': stats,
                        'timestamp': datetime.now().isoformat()
                    })
        except Exception as e:
            logger.error(f"Error checking dead letter queue: {e}")
        
        return alerts
    
    def _check_proxy_health(self) -> List[Dict]:
        """Check proxy health and failure rates."""
        alerts = []
        
        try:
            from utils.proxies import proxy_rotator
            if proxy_rotator.proxy_list:
                stats = proxy_rotator.get_proxy_statistics()
                failure_rate = 1 - stats.get('health_rate', 1)
                
                if failure_rate > self.alert_thresholds['proxy_failure_rate']:
                    alerts.append({
                        'type': 'proxy_high_failure_rate',
                        'severity': 'medium',
                        'message': f'Proxy failure rate is {failure_rate:.2%} ({stats["failed_proxies"]}/{stats["total_proxies"]} failed)',
                        'details': stats,
                        'timestamp': datetime.now().isoformat()
                    })
        except Exception as e:
            logger.error(f"Error checking proxy health: {e}")
        
        return alerts
    
    def _check_database_health(self) -> List[Dict]:
        """Check database connectivity issues."""
        alerts = []
        
        try:
            # This would be implemented based on your database monitoring
            # For now, just a placeholder
            pass
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
        
        return alerts
    
    def _send_alert(self, alert: Dict):
        """Send alert notification."""
        # Log the alert
        logger.critical(f"ALERT: {alert['type']} - {alert['message']}")
        
        # Add to alert history
        self.alert_history.append(alert)
        
        # Keep only recent alerts (last 100)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
        
        # Send email if configured
        if hasattr(settings, 'smtp_server') and settings.smtp_server:
            self._send_email_alert(alert)
        
        # Send webhook if configured
        if hasattr(settings, 'webhook_url') and settings.webhook_url:
            self._send_webhook_alert(alert)
    
    def _send_email_alert(self, alert: Dict):
        """Send email alert notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = getattr(settings, 'smtp_from', 'proscrape@localhost')
            msg['To'] = getattr(settings, 'alert_email', 'admin@localhost')
            msg['Subject'] = f"ProScrape Alert: {alert['type']}"
            
            body = f"""
ProScrape Alert Notification

Type: {alert['type']}
Severity: {alert['severity']}
Time: {alert['timestamp']}
Message: {alert['message']}

Details:
{json.dumps(alert.get('details', {}), indent=2)}

This is an automated alert from ProScrape monitoring system.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(settings.smtp_server, getattr(settings, 'smtp_port', 587))
            if getattr(settings, 'smtp_tls', True):
                server.starttls()
            if hasattr(settings, 'smtp_username') and settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            
            text = msg.as_string()
            server.sendmail(msg['From'], msg['To'], text)
            server.quit()
            
            logger.info(f"Alert email sent for {alert['type']}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_webhook_alert(self, alert: Dict):
        """Send webhook alert notification."""
        try:
            import requests
            
            payload = {
                'text': f"🚨 ProScrape Alert: {alert['type']}",
                'attachments': [{
                    'color': 'danger' if alert['severity'] == 'high' else 'warning',
                    'fields': [
                        {'title': 'Type', 'value': alert['type'], 'short': True},
                        {'title': 'Severity', 'value': alert['severity'], 'short': True},
                        {'title': 'Time', 'value': alert['timestamp'], 'short': True},
                        {'title': 'Message', 'value': alert['message'], 'short': False}
                    ]
                }]
            }
            
            response = requests.post(
                settings.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook alert sent for {alert['type']}")
            else:
                logger.error(f"Webhook alert failed with status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts."""
        return self.alert_history[-limit:] if self.alert_history else []
    
    def get_alert_summary(self) -> Dict:
        """Get summary of alert activity."""
        if not self.alert_history:
            return {'total': 0, 'by_type': {}, 'by_severity': {}}
        
        by_type = {}
        by_severity = {}
        
        for alert in self.alert_history:
            alert_type = alert['type']
            severity = alert['severity']
            
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            'total': len(self.alert_history),
            'by_type': by_type,
            'by_severity': by_severity,
            'latest': self.alert_history[-5:] if self.alert_history else []
        }


# Global alert manager instance
alert_manager = AlertManager()