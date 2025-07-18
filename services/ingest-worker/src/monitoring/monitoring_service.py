"""
Monitoring Service - Automated monitoring and alerting system for data quality and system health.
Provides continuous monitoring, alerting, and health checks for the bill processing system.
"""

import logging
import asyncio
import smtplib
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from threading import Thread, Event
import time
from collections import defaultdict

from sqlalchemy import create_engine, select, func, and_, or_, desc, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ...shared.src.shared.models.bill import Bill
from ...shared.src.shared.models.bill_process_history import BillProcessHistory
from .data_quality_dashboard import DataQualityDashboard
from ..migration.data_quality_auditor import DataQualityAuditor


class AlertType(Enum):
    """Types of alerts"""
    QUALITY_DEGRADATION = "quality_degradation"
    PROCESSING_FAILURE = "processing_failure"
    SYSTEM_ERROR = "system_error"
    THRESHOLD_BREACH = "threshold_breach"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATA_INCONSISTENCY = "data_inconsistency"


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class NotificationChannel(Enum):
    """Notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: str  # Python expression to evaluate
    threshold: float
    evaluation_window: int  # minutes
    notification_channels: List[NotificationChannel]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'condition': self.condition,
            'threshold': self.threshold,
            'evaluation_window': self.evaluation_window,
            'notification_channels': [ch.value for ch in self.notification_channels],
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledgment_required: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'triggered_at': self.triggered_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledgment_required': self.acknowledgment_required,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by
        }


@dataclass
class HealthCheck:
    """Health check configuration"""
    check_id: str
    name: str
    description: str
    check_function: Callable[[], bool]
    interval: int  # seconds
    timeout: int  # seconds
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'check_id': self.check_id,
            'name': self.name,
            'description': self.description,
            'interval': self.interval,
            'timeout': self.timeout,
            'enabled': self.enabled
        }


@dataclass
class MonitoringStats:
    """Monitoring system statistics"""
    total_alerts: int
    active_alerts: int
    resolved_alerts: int
    alerts_by_severity: Dict[str, int]
    alerts_by_type: Dict[str, int]
    health_checks_passed: int
    health_checks_failed: int
    uptime_percentage: float
    last_alert_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_alerts': self.total_alerts,
            'active_alerts': self.active_alerts,
            'resolved_alerts': self.resolved_alerts,
            'alerts_by_severity': self.alerts_by_severity,
            'alerts_by_type': self.alerts_by_type,
            'health_checks_passed': self.health_checks_passed,
            'health_checks_failed': self.health_checks_failed,
            'uptime_percentage': self.uptime_percentage,
            'last_alert_time': self.last_alert_time.isoformat() if self.last_alert_time else None
        }


class MonitoringService:
    """Automated monitoring and alerting service"""
    
    def __init__(self, database_url: str, config: Optional[Dict[str, Any]] = None):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.dashboard = DataQualityDashboard(database_url)
        self.quality_auditor = DataQualityAuditor(database_url)
        
        # Service configuration
        self.config = config or {
            'evaluation_interval': 300,  # 5 minutes
            'alert_cooldown': 1800,  # 30 minutes
            'max_active_alerts': 100,
            'health_check_interval': 60,  # 1 minute
            'notification_retry_count': 3,
            'notification_retry_delay': 60,
            'email_settings': {
                'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'smtp_user': os.getenv('SMTP_USER', ''),
                'smtp_password': os.getenv('SMTP_PASSWORD', ''),
                'from_email': os.getenv('FROM_EMAIL', 'monitoring@seiji-watch.com'),
                'to_emails': os.getenv('ALERT_EMAILS', '').split(',')
            },
            'webhook_settings': {
                'slack_webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
                'general_webhook_url': os.getenv('WEBHOOK_URL', '')
            }
        }
        
        # Monitoring state
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_check_results: Dict[str, Dict[str, Any]] = {}
        
        # Control threads
        self.monitoring_thread: Optional[Thread] = None
        self.health_check_thread: Optional[Thread] = None
        self.stop_event = Event()
        
        # Alert cooldown tracking
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Initialize default alert rules
        self._initialize_default_rules()
        self._initialize_default_health_checks()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                rule_id="quality_score_critical",
                name="Critical Quality Score",
                description="Data quality score has dropped below critical threshold",
                alert_type=AlertType.QUALITY_DEGRADATION,
                severity=AlertSeverity.CRITICAL,
                condition="quality_score < 0.5",
                threshold=0.5,
                evaluation_window=10,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.LOG],
                acknowledgment_required=True
            ),
            AlertRule(
                rule_id="completeness_low",
                name="Low Data Completeness",
                description="Data completeness rate is below acceptable threshold",
                alert_type=AlertType.QUALITY_DEGRADATION,
                severity=AlertSeverity.HIGH,
                condition="completeness_rate < 0.7",
                threshold=0.7,
                evaluation_window=15,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.LOG]
            ),
            AlertRule(
                rule_id="processing_error_high",
                name="High Processing Error Rate",
                description="Processing error rate is above acceptable threshold",
                alert_type=AlertType.PROCESSING_FAILURE,
                severity=AlertSeverity.HIGH,
                condition="error_rate > 0.1",
                threshold=0.1,
                evaluation_window=5,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.LOG]
            ),
            AlertRule(
                rule_id="migration_failure",
                name="Migration Failure",
                description="Data migration operation has failed",
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.MEDIUM,
                condition="migration_success_rate < 0.8",
                threshold=0.8,
                evaluation_window=30,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.LOG]
            ),
            AlertRule(
                rule_id="database_connection_failure",
                name="Database Connection Failure",
                description="Database connection health check failed",
                alert_type=AlertType.SERVICE_UNAVAILABLE,
                severity=AlertSeverity.CRITICAL,
                condition="database_health < 0.5",
                threshold=0.5,
                evaluation_window=2,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.LOG],
                acknowledgment_required=True
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    def _initialize_default_health_checks(self):
        """Initialize default health checks"""
        self.health_checks = {
            'database_connectivity': HealthCheck(
                check_id='database_connectivity',
                name='Database Connectivity',
                description='Check database connection and basic query',
                check_function=self._check_database_connectivity,
                interval=60,
                timeout=10
            ),
            'data_quality_service': HealthCheck(
                check_id='data_quality_service',
                name='Data Quality Service',
                description='Check data quality auditor service',
                check_function=self._check_data_quality_service,
                interval=300,
                timeout=30
            ),
            'migration_service': HealthCheck(
                check_id='migration_service',
                name='Migration Service',
                description='Check migration service availability',
                check_function=self._check_migration_service,
                interval=300,
                timeout=30
            ),
            'disk_space': HealthCheck(
                check_id='disk_space',
                name='Disk Space',
                description='Check available disk space',
                check_function=self._check_disk_space,
                interval=300,
                timeout=5
            )
        }
    
    def start_monitoring(self):
        """Start monitoring service"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.logger.warning("Monitoring service is already running")
            return
        
        self.stop_event.clear()
        
        # Start monitoring thread
        self.monitoring_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Start health check thread
        self.health_check_thread = Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        self.logger.info("Monitoring service started")
    
    def stop_monitoring(self):
        """Stop monitoring service"""
        self.stop_event.set()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=10)
        
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=10)
        
        self.logger.info("Monitoring service stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.stop_event.is_set():
            try:
                self._evaluate_alert_rules()
                self._cleanup_resolved_alerts()
                self._update_alert_cooldowns()
                
                # Wait for next evaluation
                self.stop_event.wait(self.config['evaluation_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _health_check_loop(self):
        """Health check loop"""
        while not self.stop_event.is_set():
            try:
                self._run_health_checks()
                
                # Wait for next check
                self.stop_event.wait(self.config['health_check_interval'])
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _evaluate_alert_rules(self):
        """Evaluate all alert rules"""
        try:
            # Get current metrics
            metrics = self._get_current_metrics()
            
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if rule_id in self.alert_cooldowns:
                    if datetime.now() < self.alert_cooldowns[rule_id]:
                        continue
                
                # Evaluate condition
                if self._evaluate_condition(rule.condition, metrics):
                    self._trigger_alert(rule, metrics)
                    
        except Exception as e:
            self.logger.error(f"Error evaluating alert rules: {e}")
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # Get metrics from dashboard
            dashboard_data = self.dashboard.get_dashboard_data()
            
            # Extract metrics from panels
            metrics = {}
            
            for panel in dashboard_data.get('panels', []):
                for metric in panel.get('metrics', []):
                    metric_name = metric['name'].lower().replace(' ', '_')
                    metrics[metric_name] = metric['value']
            
            # Add health check results
            for check_id, result in self.health_check_results.items():
                metrics[f"{check_id}_health"] = 1.0 if result.get('success', False) else 0.0
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting current metrics: {e}")
            return {}
    
    def _evaluate_condition(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """Evaluate alert condition"""
        try:
            # Replace metric names in condition with actual values
            safe_metrics = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
            
            # Create safe evaluation environment
            safe_dict = {
                "__builtins__": {},
                **safe_metrics
            }
            
            # Evaluate condition
            result = eval(condition, safe_dict)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger an alert"""
        try:
            # Check if alert is already active
            active_alert_key = f"{rule.rule_id}_{rule.alert_type.value}"
            
            if active_alert_key in self.active_alerts:
                self.logger.debug(f"Alert {active_alert_key} is already active")
                return
            
            # Create alert
            alert_id = f"{rule.rule_id}_{int(datetime.now().timestamp())}"
            
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                alert_type=rule.alert_type,
                severity=rule.severity,
                title=rule.name,
                message=rule.description,
                details={
                    'metrics': metrics,
                    'condition': rule.condition,
                    'threshold': rule.threshold
                },
                triggered_at=datetime.now(),
                acknowledgment_required=rule.acknowledgment_required if hasattr(rule, 'acknowledgment_required') else False
            )
            
            # Store alert
            self.active_alerts[active_alert_key] = alert
            self.alert_history.append(alert)
            
            # Send notifications
            self._send_notifications(alert, rule.notification_channels)
            
            # Set cooldown
            cooldown_end = datetime.now() + timedelta(seconds=self.config['alert_cooldown'])
            self.alert_cooldowns[rule.rule_id] = cooldown_end
            
            self.logger.warning(f"Alert triggered: {alert.title} - {alert.message}")
            
        except Exception as e:
            self.logger.error(f"Error triggering alert: {e}")
    
    def _send_notifications(self, alert: Alert, channels: List[NotificationChannel]):
        """Send alert notifications"""
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    self._send_email_notification(alert)
                elif channel == NotificationChannel.SLACK:
                    self._send_slack_notification(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert)
                elif channel == NotificationChannel.LOG:
                    self._send_log_notification(alert)
                    
            except Exception as e:
                self.logger.error(f"Error sending notification via {channel.value}: {e}")
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        try:
            email_config = self.config['email_settings']
            
            if not email_config['to_emails'] or not email_config['smtp_server']:
                self.logger.debug("Email configuration not complete, skipping email notification")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create body
            body = f"""
Alert Details:
- Alert ID: {alert.alert_id}
- Severity: {alert.severity.value.upper()}
- Type: {alert.alert_type.value}
- Message: {alert.message}
- Triggered: {alert.triggered_at.isoformat()}

Metrics:
{json.dumps(alert.details.get('metrics', {}), indent=2)}

Dashboard: http://localhost:3000/dashboard/quality
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            if email_config['smtp_user'] and email_config['smtp_password']:
                server.starttls()
                server.login(email_config['smtp_user'], email_config['smtp_password'])
            
            server.sendmail(email_config['from_email'], email_config['to_emails'], msg.as_string())
            server.quit()
            
            self.logger.info(f"Email notification sent for alert {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
    
    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        try:
            import requests
            
            webhook_url = self.config['webhook_settings']['slack_webhook_url']
            
            if not webhook_url:
                self.logger.debug("Slack webhook URL not configured, skipping Slack notification")
                return
            
            # Create Slack message
            color = {
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.HIGH: "warning",
                AlertSeverity.MEDIUM: "warning",
                AlertSeverity.LOW: "good",
                AlertSeverity.INFO: "good"
            }.get(alert.severity, "warning")
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.value.upper()}] {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Alert ID",
                                "value": alert.alert_id,
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": alert.alert_type.value,
                                "short": True
                            },
                            {
                                "title": "Triggered",
                                "value": alert.triggered_at.isoformat(),
                                "short": True
                            }
                        ],
                        "footer": "Seiji Watch Monitoring",
                        "ts": int(alert.triggered_at.timestamp())
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Slack notification sent for alert {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {e}")
    
    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification"""
        try:
            import requests
            
            webhook_url = self.config['webhook_settings']['general_webhook_url']
            
            if not webhook_url:
                self.logger.debug("Webhook URL not configured, skipping webhook notification")
                return
            
            payload = alert.to_dict()
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Webhook notification sent for alert {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")
    
    def _send_log_notification(self, alert: Alert):
        """Send log notification"""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.INFO: logging.INFO
        }.get(alert.severity, logging.WARNING)
        
        self.logger.log(log_level, f"ALERT: {alert.title} - {alert.message} [ID: {alert.alert_id}]")
    
    def _run_health_checks(self):
        """Run all health checks"""
        for check_id, check in self.health_checks.items():
            if not check.enabled:
                continue
            
            try:
                start_time = datetime.now()
                
                # Run health check with timeout
                success = check.check_function()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # Store result
                self.health_check_results[check_id] = {
                    'success': success,
                    'duration': duration,
                    'timestamp': end_time.isoformat(),
                    'timeout': duration > check.timeout
                }
                
                if not success:
                    self.logger.warning(f"Health check failed: {check.name}")
                
            except Exception as e:
                self.logger.error(f"Error running health check {check_id}: {e}")
                
                self.health_check_results[check_id] = {
                    'success': False,
                    'duration': 0,
                    'timestamp': datetime.now().isoformat(),
                    'timeout': False,
                    'error': str(e)
                }
    
    def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        try:
            with self.SessionLocal() as session:
                result = session.execute(text("SELECT 1")).scalar()
                return result == 1
                
        except Exception as e:
            self.logger.error(f"Database connectivity check failed: {e}")
            return False
    
    def _check_data_quality_service(self) -> bool:
        """Check data quality service"""
        try:
            # Test quality auditor functionality
            self.quality_auditor.get_quality_trend(1)
            return True
            
        except Exception as e:
            self.logger.error(f"Data quality service check failed: {e}")
            return False
    
    def _check_migration_service(self) -> bool:
        """Check migration service"""
        try:
            # Test migration service functionality
            from ..migration.data_migration_service import DataMigrationService
            service = DataMigrationService(self.database_url)
            service.get_migration_statistics(1)
            return True
            
        except Exception as e:
            self.logger.error(f"Migration service check failed: {e}")
            return False
    
    def _check_disk_space(self) -> bool:
        """Check disk space"""
        try:
            import shutil
            
            # Check available disk space
            total, used, free = shutil.disk_usage("/")
            free_percentage = (free / total) * 100
            
            return free_percentage > 10  # At least 10% free space
            
        except Exception as e:
            self.logger.error(f"Disk space check failed: {e}")
            return False
    
    def _cleanup_resolved_alerts(self):
        """Clean up resolved alerts"""
        try:
            # Auto-resolve alerts that are no longer triggered
            current_metrics = self._get_current_metrics()
            
            for alert_key, alert in list(self.active_alerts.items()):
                rule = self.alert_rules.get(alert.rule_id)
                
                if rule and not self._evaluate_condition(rule.condition, current_metrics):
                    # Alert condition is no longer met, resolve it
                    alert.resolved_at = datetime.now()
                    del self.active_alerts[alert_key]
                    
                    self.logger.info(f"Alert auto-resolved: {alert.title}")
            
            # Clean up old alert history
            cutoff_time = datetime.now() - timedelta(days=30)
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.triggered_at > cutoff_time
            ]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up resolved alerts: {e}")
    
    def _update_alert_cooldowns(self):
        """Update alert cooldowns"""
        current_time = datetime.now()
        
        # Remove expired cooldowns
        expired_cooldowns = [
            rule_id for rule_id, cooldown_end in self.alert_cooldowns.items()
            if current_time >= cooldown_end
        ]
        
        for rule_id in expired_cooldowns:
            del self.alert_cooldowns[rule_id]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts"""
        return [alert.to_dict() for alert in self.active_alerts.values()]
    
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history"""
        # Sort by triggered time (newest first)
        sorted_history = sorted(self.alert_history, key=lambda x: x.triggered_at, reverse=True)
        return [alert.to_dict() for alert in sorted_history[:limit]]
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""
        try:
            # Find alert in active alerts
            for alert in self.active_alerts.values():
                if alert.alert_id == alert_id:
                    alert.acknowledged_at = datetime.now()
                    alert.acknowledged_by = user
                    
                    self.logger.info(f"Alert acknowledged: {alert_id} by {user}")
                    return True
            
            # Find alert in history
            for alert in self.alert_history:
                if alert.alert_id == alert_id:
                    alert.acknowledged_at = datetime.now()
                    alert.acknowledged_by = user
                    
                    self.logger.info(f"Alert acknowledged: {alert_id} by {user}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, user: str = "system") -> bool:
        """Manually resolve an alert"""
        try:
            # Find and resolve alert
            for alert_key, alert in list(self.active_alerts.items()):
                if alert.alert_id == alert_id:
                    alert.resolved_at = datetime.now()
                    del self.active_alerts[alert_key]
                    
                    self.logger.info(f"Alert manually resolved: {alert_id} by {user}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error resolving alert {alert_id}: {e}")
            return False
    
    def get_monitoring_statistics(self) -> MonitoringStats:
        """Get monitoring system statistics"""
        try:
            # Calculate statistics
            total_alerts = len(self.alert_history)
            active_alerts = len(self.active_alerts)
            resolved_alerts = len([a for a in self.alert_history if a.resolved_at])
            
            # Group by severity
            alerts_by_severity = defaultdict(int)
            for alert in self.alert_history:
                alerts_by_severity[alert.severity.value] += 1
            
            # Group by type
            alerts_by_type = defaultdict(int)
            for alert in self.alert_history:
                alerts_by_type[alert.alert_type.value] += 1
            
            # Health check statistics
            health_checks_passed = len([r for r in self.health_check_results.values() if r.get('success', False)])
            health_checks_failed = len([r for r in self.health_check_results.values() if not r.get('success', False)])
            
            # Calculate uptime (mock for now)
            uptime_percentage = 99.5
            
            # Last alert time
            last_alert_time = None
            if self.alert_history:
                last_alert_time = max(alert.triggered_at for alert in self.alert_history)
            
            return MonitoringStats(
                total_alerts=total_alerts,
                active_alerts=active_alerts,
                resolved_alerts=resolved_alerts,
                alerts_by_severity=dict(alerts_by_severity),
                alerts_by_type=dict(alerts_by_type),
                health_checks_passed=health_checks_passed,
                health_checks_failed=health_checks_failed,
                uptime_percentage=uptime_percentage,
                last_alert_time=last_alert_time
            )
            
        except Exception as e:
            self.logger.error(f"Error getting monitoring statistics: {e}")
            return MonitoringStats(0, 0, 0, {}, {}, 0, 0, 0.0)
    
    def get_health_check_status(self) -> Dict[str, Any]:
        """Get health check status"""
        return {
            'health_checks': {
                check_id: {
                    **check.to_dict(),
                    'last_result': self.health_check_results.get(check_id, {})
                }
                for check_id, check in self.health_checks.items()
            },
            'overall_health': all(
                result.get('success', False) 
                for result in self.health_check_results.values()
            )
        }
    
    def add_alert_rule(self, rule: AlertRule):
        """Add custom alert rule"""
        self.alert_rules[rule.rule_id] = rule
        self.logger.info(f"Added alert rule: {rule.rule_id}")
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get monitoring service status"""
        return {
            'status': 'running' if self.monitoring_thread and self.monitoring_thread.is_alive() else 'stopped',
            'configuration': self.config,
            'active_rules': len([r for r in self.alert_rules.values() if r.enabled]),
            'total_rules': len(self.alert_rules),
            'active_alerts': len(self.active_alerts),
            'health_checks': len(self.health_checks),
            'uptime': datetime.now().isoformat()  # Service start time would be tracked in production
        }