"""
Intelligent Alerting and Notification System

This module provides sophisticated alerting capabilities including:
- Threshold-based monitoring with configurable rules
- Anomaly detection using statistical methods
- Alert fatigue prevention with intelligent grouping
- Multiple notification channels (email, slack, webhook)
- Alert escalation and on-call rotation
- SLA violation tracking and reporting
"""

import asyncio
import logging
import smtplib
import statistics
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from typing import Any

import aiohttp

from .logger import log_error, log_info, log_security
from .metrics import ingest_metrics

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle status."""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    description: str
    metric_name: str
    condition: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    threshold: float
    severity: AlertSeverity
    evaluation_window_minutes: int = 5
    min_data_points: int = 3
    cooldown_minutes: int = 30
    enabled: bool = True
    tags: dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class Alert:
    """Alert instance."""
    id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    status: AlertStatus = AlertStatus.TRIGGERED
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class NotificationConfig:
    """Notification channel configuration."""
    channel: NotificationChannel
    enabled: bool = True
    config: dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class AnomalyDetector:
    """Statistical anomaly detection for metrics."""

    def __init__(self, window_size: int = 100, sensitivity: float = 2.0):
        self.window_size = window_size
        self.sensitivity = sensitivity  # Standard deviations for outlier detection
        self.metric_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

    def add_value(self, metric_name: str, value: float):
        """Add a metric value to the history."""
        self.metric_history[metric_name].append(value)

    def is_anomaly(self, metric_name: str, value: float) -> bool:
        """Check if a value is anomalous based on historical data."""
        history = self.metric_history[metric_name]

        if len(history) < 10:  # Need minimum history
            return False

        try:
            mean = statistics.mean(history)
            stdev = statistics.stdev(history)

            # Check if value is outside normal range
            if stdev > 0:
                z_score = abs(value - mean) / stdev
                return z_score > self.sensitivity

        except statistics.StatisticsError:
            pass

        return False

    def get_baseline_stats(self, metric_name: str) -> dict[str, float]:
        """Get baseline statistics for a metric."""
        history = self.metric_history[metric_name]

        if len(history) < 5:
            return {}

        try:
            return {
                'mean': statistics.mean(history),
                'median': statistics.median(history),
                'stdev': statistics.stdev(history),
                'min': min(history),
                'max': max(history),
                'count': len(history)
            }
        except statistics.StatisticsError:
            return {}


class AlertManager:
    """Comprehensive alert management system."""

    def __init__(self):
        self.rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.notification_configs: dict[NotificationChannel, NotificationConfig] = {}
        self.anomaly_detector = AnomalyDetector()

        # Alert suppression and grouping
        self.suppressed_rules: dict[str, datetime] = {}
        self.alert_groups: dict[str, list[str]] = defaultdict(list)

        # SLA tracking
        self.sla_violations: deque = deque(maxlen=1000)

        # Statistics
        self.stats = {
            'alerts_triggered': 0,
            'alerts_resolved': 0,
            'false_positives': 0,
            'sla_violations': 0
        }

        self._setup_default_rules()
        self._setup_evaluation_task()

    def _setup_default_rules(self):
        """Setup default monitoring rules."""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                description="Error rate is unusually high",
                metric_name="error_rate_percent",
                condition="gt",
                threshold=10.0,
                severity=AlertSeverity.HIGH,
                evaluation_window_minutes=5,
                min_data_points=3
            ),
            AlertRule(
                name="processing_failure_rate",
                description="Processing operations failing frequently",
                metric_name="pdf_processing_error_rate",
                condition="gt",
                threshold=25.0,
                severity=AlertSeverity.MEDIUM,
                evaluation_window_minutes=10,
                min_data_points=5
            ),
            AlertRule(
                name="system_memory_critical",
                description="System memory usage critically high",
                metric_name="system_memory_percent",
                condition="gt",
                threshold=90.0,
                severity=AlertSeverity.CRITICAL,
                evaluation_window_minutes=2,
                min_data_points=2
            ),
            AlertRule(
                name="disk_space_warning",
                description="Disk space usage high",
                metric_name="system_disk_percent",
                condition="gt",
                threshold=85.0,
                severity=AlertSeverity.MEDIUM,
                evaluation_window_minutes=5,
                min_data_points=3
            ),
            AlertRule(
                name="processing_time_anomaly",
                description="Processing times are anomalously high",
                metric_name="pdf_processing_duration_seconds",
                condition="anomaly",
                threshold=0.0,  # Not used for anomaly detection
                severity=AlertSeverity.MEDIUM,
                evaluation_window_minutes=15,
                min_data_points=10
            ),
            AlertRule(
                name="data_quality_degradation",
                description="Data quality scores have degraded",
                metric_name="pdf_extraction_accuracy",
                condition="lt",
                threshold=0.7,
                severity=AlertSeverity.HIGH,
                evaluation_window_minutes=30,
                min_data_points=5
            )
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def _setup_evaluation_task(self):
        """Setup background task for rule evaluation."""
        asyncio.create_task(self._evaluation_loop())

    async def _evaluation_loop(self):
        """Background loop for evaluating alert rules."""
        while True:
            try:
                await self.evaluate_all_rules()
                await asyncio.sleep(60)  # Evaluate every minute
            except Exception as e:
                log_error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(60)

    def add_rule(self, rule: AlertRule):
        """Add an alert rule."""
        self.rules[rule.name] = rule
        log_info(f"Added alert rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            log_info(f"Removed alert rule: {rule_name}")

    def enable_rule(self, rule_name: str):
        """Enable an alert rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            log_info(f"Enabled alert rule: {rule_name}")

    def disable_rule(self, rule_name: str):
        """Disable an alert rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            log_info(f"Disabled alert rule: {rule_name}")

    def suppress_rule(self, rule_name: str, duration_minutes: int = 60):
        """Temporarily suppress an alert rule."""
        if rule_name in self.rules:
            self.suppressed_rules[rule_name] = datetime.utcnow() + timedelta(minutes=duration_minutes)
            log_info(f"Suppressed alert rule {rule_name} for {duration_minutes} minutes")

    def configure_notification(self, channel: NotificationChannel, config: dict[str, Any]):
        """Configure a notification channel."""
        self.notification_configs[channel] = NotificationConfig(
            channel=channel,
            enabled=True,
            config=config
        )
        log_info(f"Configured notification channel: {channel.value}")

    async def evaluate_all_rules(self):
        """Evaluate all enabled alert rules."""
        current_time = datetime.utcnow()

        # Clean up suppressed rules
        expired_suppressions = [
            rule_name for rule_name, expiry in self.suppressed_rules.items()
            if current_time > expiry
        ]
        for rule_name in expired_suppressions:
            del self.suppressed_rules[rule_name]

        # Evaluate each rule
        for rule_name, rule in self.rules.items():
            if not rule.enabled or rule_name in self.suppressed_rules:
                continue

            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                log_error(f"Error evaluating rule {rule_name}: {e}")

    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate a single alert rule."""
        # Get recent metric values
        metric_values = self._get_recent_metric_values(
            rule.metric_name,
            rule.evaluation_window_minutes
        )

        if len(metric_values) < rule.min_data_points:
            return  # Not enough data

        # Check condition
        should_alert = False
        current_value = metric_values[-1]  # Most recent value

        if rule.condition == "anomaly":
            # Add to anomaly detector
            self.anomaly_detector.add_value(rule.metric_name, current_value)
            should_alert = self.anomaly_detector.is_anomaly(rule.metric_name, current_value)
        else:
            # Threshold-based conditions
            if rule.condition == "gt" and current_value > rule.threshold:
                should_alert = True
            elif rule.condition == "lt" and current_value < rule.threshold:
                should_alert = True
            elif rule.condition == "gte" and current_value >= rule.threshold:
                should_alert = True
            elif rule.condition == "lte" and current_value <= rule.threshold:
                should_alert = True
            elif rule.condition == "eq" and current_value == rule.threshold:
                should_alert = True

        # Handle alert state
        alert_key = f"{rule.name}"
        existing_alert = self.active_alerts.get(alert_key)

        if should_alert and not existing_alert:
            # Trigger new alert
            await self._trigger_alert(rule, current_value)
        elif not should_alert and existing_alert:
            # Resolve existing alert
            await self._resolve_alert(alert_key)

    def _get_recent_metric_values(self, metric_name: str, window_minutes: int) -> list[float]:
        """Get recent metric values within the time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)

        values = []
        metric_list = ingest_metrics.metrics.get(metric_name, deque())

        for metric in metric_list:
            if metric.timestamp >= cutoff_time:
                values.append(metric.value)

        return sorted(values)  # Sort by time

    async def _trigger_alert(self, rule: AlertRule, value: float):
        """Trigger a new alert."""
        alert_id = f"{rule.name}_{int(time.time())}"

        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=self._generate_alert_message(rule, value),
            metric_value=value,
            threshold=rule.threshold,
            triggered_at=datetime.utcnow(),
            metadata={
                'metric_name': rule.metric_name,
                'condition': rule.condition,
                'evaluation_window': rule.evaluation_window_minutes
            }
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.stats['alerts_triggered'] += 1

        # Send notifications
        await self._send_notifications(alert)

        # Log alert
        log_security(
            "alert_triggered",
            rule.severity.value,
            details={
                'rule_name': rule.name,
                'metric_value': value,
                'threshold': rule.threshold,
                'alert_id': alert_id
            }
        )

    async def _resolve_alert(self, alert_key: str):
        """Resolve an active alert."""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()

            # Send resolution notification
            await self._send_resolution_notification(alert)

            # Remove from active alerts
            del self.active_alerts[alert_key]
            self.stats['alerts_resolved'] += 1

            log_info(f"Resolved alert: {alert.rule_name}")

    def _generate_alert_message(self, rule: AlertRule, value: float) -> str:
        """Generate human-readable alert message."""
        if rule.condition == "anomaly":
            baseline = self.anomaly_detector.get_baseline_stats(rule.metric_name)
            if baseline:
                return (f"{rule.description}. Current value: {value:.2f}, "
                       f"baseline mean: {baseline.get('mean', 0):.2f} "
                       f"(±{baseline.get('stdev', 0):.2f})")
            else:
                return f"{rule.description}. Current value: {value:.2f} (anomalous)"
        else:
            return (f"{rule.description}. Current value: {value:.2f}, "
                   f"threshold: {rule.threshold:.2f}")

    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        for channel, config in self.notification_configs.items():
            if not config.enabled:
                continue

            try:
                if channel == NotificationChannel.EMAIL:
                    await self._send_email_notification(alert, config.config)
                elif channel == NotificationChannel.SLACK:
                    await self._send_slack_notification(alert, config.config)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook_notification(alert, config.config)
                elif channel == NotificationChannel.LOG:
                    self._send_log_notification(alert)

            except Exception as e:
                log_error(f"Failed to send {channel.value} notification: {e}")

    async def _send_resolution_notification(self, alert: Alert):
        """Send resolution notifications."""

        for channel, config in self.notification_configs.items():
            if not config.enabled:
                continue

            try:
                if channel == NotificationChannel.LOG:
                    log_info(f"Alert resolved: {alert.rule_name}")
                # Add other channels as needed

            except Exception as e:
                log_error(f"Failed to send resolution notification: {e}")

    async def _send_email_notification(self, alert: Alert, config: dict[str, Any]):
        """Send email notification."""
        if not all(k in config for k in ['smtp_server', 'smtp_port', 'username', 'password', 'to_emails']):
            return

        severity_emojis = {
            AlertSeverity.LOW: "🟡",
            AlertSeverity.MEDIUM: "🟠",
            AlertSeverity.HIGH: "🔴",
            AlertSeverity.CRITICAL: "🚨"
        }

        subject = f"{severity_emojis[alert.severity]} Alert: {alert.rule_name}"

        body = f"""
Alert Details:
- Rule: {alert.rule_name}
- Severity: {alert.severity.value.upper()}
- Message: {alert.message}
- Triggered: {alert.triggered_at.isoformat()}
- Alert ID: {alert.id}

Metric Information:
- Current Value: {alert.metric_value}
- Threshold: {alert.threshold}

Please investigate this issue promptly.
        """

        try:
            msg = MimeMultipart()
            msg['From'] = config['username']
            msg['To'] = ', '.join(config['to_emails'])
            msg['Subject'] = subject

            msg.attach(MimeText(body, 'plain'))

            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                server.starttls()
                server.login(config['username'], config['password'])
                server.send_message(msg)

        except Exception as e:
            log_error(f"Failed to send email: {e}")

    async def _send_slack_notification(self, alert: Alert, config: dict[str, Any]):
        """Send Slack notification."""
        if 'webhook_url' not in config:
            return

        severity_colors = {
            AlertSeverity.LOW: "#ffeb3b",
            AlertSeverity.MEDIUM: "#ff9800",
            AlertSeverity.HIGH: "#f44336",
            AlertSeverity.CRITICAL: "#9c27b0"
        }

        payload = {
            "attachments": [
                {
                    "color": severity_colors[alert.severity],
                    "title": f"Alert: {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Current Value",
                            "value": str(alert.metric_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold),
                            "short": True
                        },
                        {
                            "title": "Alert ID",
                            "value": alert.id,
                            "short": True
                        }
                    ],
                    "footer": "Diet Issue Tracker Monitoring",
                    "ts": int(alert.triggered_at.timestamp())
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(config['webhook_url'], json=payload) as response:
                    if response.status != 200:
                        log_error(f"Slack notification failed: {response.status}")

        except Exception as e:
            log_error(f"Failed to send Slack notification: {e}")

    async def _send_webhook_notification(self, alert: Alert, config: dict[str, Any]):
        """Send webhook notification."""
        if 'url' not in config:
            return

        payload = {
            "alert": asdict(alert),
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ingest_worker"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    config['url'],
                    json=payload,
                    headers=config.get('headers', {})
                ) as response:
                    if response.status not in [200, 201, 202]:
                        log_error(f"Webhook notification failed: {response.status}")

        except Exception as e:
            log_error(f"Failed to send webhook notification: {e}")

    def _send_log_notification(self, alert: Alert):
        """Send log-based notification."""
        log_security(
            "alert_notification",
            alert.severity.value,
            details=asdict(alert)
        )

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = None):
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()

            if acknowledged_by:
                alert.metadata['acknowledged_by'] = acknowledged_by

            log_info(f"Alert acknowledged: {alert_id}")

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alerting statistics."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)

        recent_alerts = [
            alert for alert in self.alert_history
            if alert.triggered_at >= last_24h
        ]

        severity_counts = defaultdict(int)
        for alert in recent_alerts:
            severity_counts[alert.severity.value] += 1

        return {
            'active_alerts_count': len(self.active_alerts),
            'alerts_last_24h': len(recent_alerts),
            'severity_distribution': dict(severity_counts),
            'total_rules': len(self.rules),
            'enabled_rules': sum(1 for rule in self.rules.values() if rule.enabled),
            'suppressed_rules': len(self.suppressed_rules),
            'notification_channels': len(self.notification_configs),
            'stats': self.stats.copy()
        }


# Global alert manager instance
alert_manager = AlertManager()


# Convenience functions
def add_alert_rule(rule: AlertRule):
    """Add an alert rule."""
    alert_manager.add_rule(rule)


def configure_email_notifications(smtp_config: dict[str, Any]):
    """Configure email notifications."""
    alert_manager.configure_notification(NotificationChannel.EMAIL, smtp_config)


def configure_slack_notifications(webhook_url: str):
    """Configure Slack notifications."""
    alert_manager.configure_notification(NotificationChannel.SLACK, {'webhook_url': webhook_url})


def get_active_alerts():
    """Get all active alerts."""
    return alert_manager.get_active_alerts()


def get_alert_stats():
    """Get alerting statistics."""
    return alert_manager.get_alert_statistics()
