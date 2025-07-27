"""
Monitoring Manager - Central management for monitoring and operational features.
Coordinates dashboard, alerting, and health monitoring services.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..migration.data_migration_service import DataMigrationService
from .data_quality_dashboard import DataQualityDashboard
from .monitoring_service import (
    AlertRule,
    AlertSeverity,
    AlertType,
    MonitoringService,
    NotificationChannel,
)


@dataclass
class MonitoringConfiguration:
    """Central monitoring configuration"""

    dashboard_refresh_interval: int = 300  # seconds
    alert_evaluation_interval: int = 300  # seconds
    health_check_interval: int = 60  # seconds
    data_retention_days: int = 90
    enable_email_alerts: bool = True
    enable_slack_alerts: bool = False
    enable_webhook_alerts: bool = False
    quality_score_threshold: float = 0.7
    completeness_threshold: float = 0.8
    error_rate_threshold: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dashboard_refresh_interval": self.dashboard_refresh_interval,
            "alert_evaluation_interval": self.alert_evaluation_interval,
            "health_check_interval": self.health_check_interval,
            "data_retention_days": self.data_retention_days,
            "enable_email_alerts": self.enable_email_alerts,
            "enable_slack_alerts": self.enable_slack_alerts,
            "enable_webhook_alerts": self.enable_webhook_alerts,
            "quality_score_threshold": self.quality_score_threshold,
            "completeness_threshold": self.completeness_threshold,
            "error_rate_threshold": self.error_rate_threshold,
        }


class MonitoringManager:
    """Central monitoring manager"""

    def __init__(
        self, database_url: str, config: MonitoringConfiguration | None = None
    ):
        self.database_url = database_url
        self.config = config or MonitoringConfiguration()
        self.logger = logging.getLogger(__name__)

        # Initialize services
        self.dashboard = DataQualityDashboard(database_url)
        self.monitoring_service = MonitoringService(
            database_url, self._create_monitoring_config()
        )
        self.migration_service = DataMigrationService(database_url)

        # Service state
        self.is_running = False
        self.start_time: datetime | None = None

    def _create_monitoring_config(self) -> dict[str, Any]:
        """Create monitoring service configuration"""
        return {
            "evaluation_interval": self.config.alert_evaluation_interval,
            "health_check_interval": self.config.health_check_interval,
            "alert_cooldown": 1800,  # 30 minutes
            "max_active_alerts": 100,
            "notification_retry_count": 3,
            "notification_retry_delay": 60,
            "email_settings": {
                "smtp_server": "localhost",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "from_email": "monitoring@seiji-watch.com",
                "to_emails": ["admin@seiji-watch.com"],
            },
            "webhook_settings": {"slack_webhook_url": "", "general_webhook_url": ""},
        }

    def start(self):
        """Start monitoring manager"""
        if self.is_running:
            self.logger.warning("Monitoring manager is already running")
            return

        try:
            self.logger.info("Starting monitoring manager")

            # Start monitoring service
            self.monitoring_service.start_monitoring()

            # Add custom alert rules based on configuration
            self._setup_custom_alert_rules()

            self.is_running = True
            self.start_time = datetime.now()

            self.logger.info("Monitoring manager started successfully")

        except Exception as e:
            self.logger.error(f"Error starting monitoring manager: {e}")
            raise

    def stop(self):
        """Stop monitoring manager"""
        if not self.is_running:
            self.logger.warning("Monitoring manager is not running")
            return

        try:
            self.logger.info("Stopping monitoring manager")

            # Stop monitoring service
            self.monitoring_service.stop_monitoring()

            self.is_running = False

            self.logger.info("Monitoring manager stopped successfully")

        except Exception as e:
            self.logger.error(f"Error stopping monitoring manager: {e}")
            raise

    def _setup_custom_alert_rules(self):
        """Setup custom alert rules based on configuration"""
        try:
            # Quality score alert
            quality_rule = AlertRule(
                rule_id="custom_quality_score",
                name="Quality Score Below Threshold",
                description=f"Data quality score has dropped below {self.config.quality_score_threshold}",
                alert_type=AlertType.QUALITY_DEGRADATION,
                severity=AlertSeverity.HIGH,
                condition=f"overall_quality_score < {self.config.quality_score_threshold}",
                threshold=self.config.quality_score_threshold,
                evaluation_window=10,
                notification_channels=self._get_enabled_channels(),
            )

            self.monitoring_service.add_alert_rule(quality_rule)

            # Completeness alert
            completeness_rule = AlertRule(
                rule_id="custom_completeness",
                name="Data Completeness Below Threshold",
                description=f"Data completeness has dropped below {self.config.completeness_threshold}",
                alert_type=AlertType.QUALITY_DEGRADATION,
                severity=AlertSeverity.MEDIUM,
                condition=f"data_completeness < {self.config.completeness_threshold}",
                threshold=self.config.completeness_threshold,
                evaluation_window=15,
                notification_channels=self._get_enabled_channels(),
            )

            self.monitoring_service.add_alert_rule(completeness_rule)

            # Error rate alert
            error_rule = AlertRule(
                rule_id="custom_error_rate",
                name="Processing Error Rate Too High",
                description=f"Processing error rate has exceeded {self.config.error_rate_threshold}",
                alert_type=AlertType.PROCESSING_FAILURE,
                severity=AlertSeverity.HIGH,
                condition=f"processing_error_rate > {self.config.error_rate_threshold}",
                threshold=self.config.error_rate_threshold,
                evaluation_window=5,
                notification_channels=self._get_enabled_channels(),
            )

            self.monitoring_service.add_alert_rule(error_rule)

        except Exception as e:
            self.logger.error(f"Error setting up custom alert rules: {e}")

    def _get_enabled_channels(self) -> list[NotificationChannel]:
        """Get enabled notification channels"""
        channels = [NotificationChannel.LOG]  # Always include log

        if self.config.enable_email_alerts:
            channels.append(NotificationChannel.EMAIL)

        if self.config.enable_slack_alerts:
            channels.append(NotificationChannel.SLACK)

        if self.config.enable_webhook_alerts:
            channels.append(NotificationChannel.WEBHOOK)

        return channels

    def get_dashboard_data(
        self, dashboard_id: str = "main_quality_dashboard"
    ) -> dict[str, Any]:
        """Get dashboard data"""
        try:
            return self.dashboard.get_dashboard_data(dashboard_id)

        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            raise

    def get_alerts(self) -> list[dict[str, Any]]:
        """Get current alerts"""
        try:
            return self.monitoring_service.get_active_alerts()

        except Exception as e:
            self.logger.error(f"Error getting alerts: {e}")
            return []

    def get_alert_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get alert history"""
        try:
            return self.monitoring_service.get_alert_history(limit)

        except Exception as e:
            self.logger.error(f"Error getting alert history: {e}")
            return []

    def acknowledge_alert(self, alert_id: str, user: str = "admin") -> bool:
        """Acknowledge an alert"""
        try:
            return self.monitoring_service.acknowledge_alert(alert_id, user)

        except Exception as e:
            self.logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False

    def resolve_alert(self, alert_id: str, user: str = "admin") -> bool:
        """Manually resolve an alert"""
        try:
            return self.monitoring_service.resolve_alert(alert_id, user)

        except Exception as e:
            self.logger.error(f"Error resolving alert {alert_id}: {e}")
            return False

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health"""
        try:
            # Get health check status
            health_status = self.monitoring_service.get_health_check_status()

            # Get monitoring statistics
            monitoring_stats = self.monitoring_service.get_monitoring_statistics()

            # Get quality metrics
            dashboard_data = self.dashboard.get_dashboard_data()

            # Extract key metrics
            quality_metrics = {}
            for panel in dashboard_data.get("panels", []):
                if panel["panel_id"] == "quality_overview":
                    for metric in panel.get("metrics", []):
                        quality_metrics[metric["name"]] = metric["value"]

            # Calculate overall health score
            overall_health = self._calculate_overall_health(
                health_status, quality_metrics
            )

            return {
                "overall_health": overall_health,
                "health_checks": health_status,
                "monitoring_stats": monitoring_stats.to_dict(),
                "quality_metrics": quality_metrics,
                "service_status": {
                    "is_running": self.is_running,
                    "start_time": (
                        self.start_time.isoformat() if self.start_time else None
                    ),
                    "uptime_seconds": (
                        (datetime.now() - self.start_time).total_seconds()
                        if self.start_time
                        else 0
                    ),
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting system health: {e}")
            return {
                "overall_health": 0.0,
                "health_checks": {},
                "monitoring_stats": {},
                "quality_metrics": {},
                "service_status": {"is_running": False},
            }

    def _calculate_overall_health(
        self, health_status: dict[str, Any], quality_metrics: dict[str, Any]
    ) -> float:
        """Calculate overall system health score"""
        try:
            health_score = 0.0
            total_weight = 0.0

            # Health checks (30% weight)
            if health_status.get("overall_health", False):
                health_score += 0.3
            total_weight += 0.3

            # Quality metrics (70% weight)
            if quality_metrics:
                quality_score = quality_metrics.get("Overall Quality Score", 0)
                completeness = quality_metrics.get("Data Completeness", 0)
                accuracy = quality_metrics.get("Data Accuracy", 0)

                # Weighted average of quality metrics
                quality_weight = (
                    quality_score * 0.4 + completeness * 0.3 + accuracy * 0.3
                )
                health_score += quality_weight * 0.7
                total_weight += 0.7

            return health_score / total_weight if total_weight > 0 else 0.0

        except Exception as e:
            self.logger.error(f"Error calculating overall health: {e}")
            return 0.0

    def get_performance_metrics(self, hours: int = 24) -> dict[str, Any]:
        """Get performance metrics for the specified period"""
        try:
            # Get migration statistics
            migration_stats = self.migration_service.get_migration_statistics(
                hours // 24
            )

            # Get completion processor statistics
            completion_stats = (
                self.migration_service.completion_processor.get_completion_statistics(
                    hours // 24
                )
            )

            # Get dashboard metrics
            dashboard_data = self.dashboard.get_dashboard_data()

            # Extract processing metrics
            processing_metrics = {}
            for panel in dashboard_data.get("panels", []):
                if panel["panel_id"] == "processing_metrics":
                    for metric in panel.get("metrics", []):
                        processing_metrics[metric["name"]] = metric["value"]

            return {
                "migration_performance": migration_stats,
                "completion_performance": completion_stats,
                "processing_performance": processing_metrics,
                "period_hours": hours,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return {
                "migration_performance": {},
                "completion_performance": {},
                "processing_performance": {},
                "period_hours": hours,
                "generated_at": datetime.now().isoformat(),
            }

    def run_quality_audit(self) -> dict[str, Any]:
        """Run a quality audit and return results"""
        try:
            self.logger.info("Running quality audit")

            # Get fresh dashboard data (this will trigger quality audit)
            dashboard_data = self.dashboard.get_dashboard_data()

            # Clear dashboard cache to ensure fresh data
            self.dashboard.clear_cache()

            # Extract quality metrics
            quality_metrics = {}
            for panel in dashboard_data.get("panels", []):
                if panel["panel_id"] == "quality_overview":
                    for metric in panel.get("metrics", []):
                        quality_metrics[metric["name"]] = {
                            "value": metric["value"],
                            "unit": metric["unit"],
                            "severity": metric["severity"],
                            "description": metric["description"],
                        }

            return {
                "audit_completed_at": datetime.now().isoformat(),
                "quality_metrics": quality_metrics,
                "recommendations": self._generate_audit_recommendations(
                    quality_metrics
                ),
            }

        except Exception as e:
            self.logger.error(f"Error running quality audit: {e}")
            return {
                "audit_completed_at": datetime.now().isoformat(),
                "quality_metrics": {},
                "recommendations": [],
                "error": str(e),
            }

    def _generate_audit_recommendations(
        self, quality_metrics: dict[str, Any]
    ) -> list[str]:
        """Generate recommendations based on quality metrics"""
        recommendations = []

        try:
            # Check overall quality score
            overall_score = quality_metrics.get("Overall Quality Score", {}).get(
                "value", 0
            )
            if overall_score < 0.7:
                recommendations.append(
                    "Consider running data completion migration to improve overall quality"
                )

            # Check completeness
            completeness = quality_metrics.get("Data Completeness", {}).get("value", 0)
            if completeness < 0.8:
                recommendations.append(
                    "Run data completion processor to fill missing bill information"
                )

            # Check accuracy
            accuracy = quality_metrics.get("Data Accuracy", {}).get("value", 0)
            if accuracy < 0.9:
                recommendations.append(
                    "Review data validation rules and fix accuracy issues"
                )

            # Check consistency
            consistency = quality_metrics.get("Data Consistency", {}).get("value", 0)
            if consistency < 0.85:
                recommendations.append(
                    "Investigate data consistency issues between sources"
                )

            if not recommendations:
                recommendations.append(
                    "Data quality is good - maintain current monitoring"
                )

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Error generating recommendations - check logs")

        return recommendations

    def update_configuration(self, new_config: dict[str, Any]) -> bool:
        """Update monitoring configuration"""
        try:
            # Update configuration
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            # Restart monitoring service with new configuration
            if self.is_running:
                self.monitoring_service.stop_monitoring()
                self.monitoring_service = MonitoringService(
                    self.database_url, self._create_monitoring_config()
                )
                self.monitoring_service.start_monitoring()
                self._setup_custom_alert_rules()

            self.logger.info("Monitoring configuration updated")
            return True

        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False

    def export_configuration(self) -> dict[str, Any]:
        """Export current configuration"""
        try:
            return {
                "monitoring_config": self.config.to_dict(),
                "alert_rules": [
                    rule.to_dict()
                    for rule in self.monitoring_service.alert_rules.values()
                ],
                "health_checks": [
                    check.to_dict()
                    for check in self.monitoring_service.health_checks.values()
                ],
                "exported_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return {}

    def get_service_status(self) -> dict[str, Any]:
        """Get detailed service status"""
        try:
            return {
                "manager_status": {
                    "is_running": self.is_running,
                    "start_time": (
                        self.start_time.isoformat() if self.start_time else None
                    ),
                    "uptime_seconds": (
                        (datetime.now() - self.start_time).total_seconds()
                        if self.start_time
                        else 0
                    ),
                },
                "monitoring_service_status": self.monitoring_service.get_service_status(),
                "dashboard_status": self.dashboard.get_dashboard_status(),
                "configuration": self.config.to_dict(),
            }

        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            return {
                "manager_status": {"is_running": False},
                "monitoring_service_status": {},
                "dashboard_status": {},
                "configuration": {},
            }

    def cleanup_old_data(self, retention_days: int | None = None):
        """Clean up old monitoring data"""
        try:
            retention_days = retention_days or self.config.data_retention_days

            self.logger.info(
                f"Cleaning up monitoring data older than {retention_days} days"
            )

            # Clean up migration service data
            self.migration_service.cleanup_old_reports(retention_days)

            # Clean up dashboard cache
            self.dashboard.clear_cache()

            # Clean up alert history
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            self.monitoring_service.alert_history = [
                alert
                for alert in self.monitoring_service.alert_history
                if alert.triggered_at > cutoff_date
            ]

            self.logger.info("Monitoring data cleanup completed")

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
