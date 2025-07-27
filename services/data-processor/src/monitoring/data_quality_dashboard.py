"""
Data Quality Dashboard - Real-time monitoring and visualization of data quality metrics.
Provides comprehensive dashboards for data quality, processing performance, and system health.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from ...shared.src.shared.models.bill import Bill
from ...shared.src.shared.models.bill_process_history import (
    BillProcessHistory,
)
from ..migration.data_completion_processor import DataCompletionProcessor
from ..migration.data_migration_service import DataMigrationService
from ..migration.data_quality_auditor import DataQualityAuditor


class DashboardMetricType(Enum):
    """Types of dashboard metrics"""

    QUALITY_SCORE = "quality_score"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    PROCESSING_VOLUME = "processing_volume"
    ERROR_RATE = "error_rate"
    MIGRATION_SUCCESS = "migration_success"
    SYSTEM_HEALTH = "system_health"


class MetricSeverity(Enum):
    """Severity levels for metrics"""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


@dataclass
class DashboardMetric:
    """Individual dashboard metric"""

    metric_type: DashboardMetricType
    name: str
    value: float
    unit: str
    severity: MetricSeverity
    description: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            "metric_type": self.metric_type.value,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "severity": self.severity.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DashboardPanel:
    """Dashboard panel containing multiple metrics"""

    panel_id: str
    title: str
    description: str
    metrics: list[DashboardMetric]
    chart_type: str = "line"
    refresh_interval: int = 300  # seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert panel to dictionary"""
        return {
            "panel_id": self.panel_id,
            "title": self.title,
            "description": self.description,
            "chart_type": self.chart_type,
            "refresh_interval": self.refresh_interval,
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


@dataclass
class DashboardLayout:
    """Complete dashboard layout"""

    dashboard_id: str
    title: str
    description: str
    panels: list[DashboardPanel]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert dashboard to dictionary"""
        return {
            "dashboard_id": self.dashboard_id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "panels": [panel.to_dict() for panel in self.panels],
        }


class DataQualityDashboard:
    """Real-time data quality dashboard"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.quality_auditor = DataQualityAuditor(database_url)
        self.completion_processor = DataCompletionProcessor(database_url)
        self.migration_service = DataMigrationService(database_url)

        # Dashboard configuration
        self.config = {
            "default_time_range": 24,  # hours
            "metrics_cache_ttl": 300,  # seconds
            "alert_thresholds": {
                "quality_score_critical": 0.5,
                "quality_score_warning": 0.7,
                "completeness_critical": 0.6,
                "completeness_warning": 0.8,
                "error_rate_critical": 0.1,
                "error_rate_warning": 0.05,
            },
        }

        # Metrics cache
        self.metrics_cache: dict[str, Any] = {}
        self.cache_timestamps: dict[str, datetime] = {}

    def create_main_dashboard(self) -> DashboardLayout:
        """Create the main data quality dashboard"""
        self.logger.info("Creating main data quality dashboard")

        try:
            # Create dashboard panels
            panels = [
                self._create_quality_overview_panel(),
                self._create_processing_metrics_panel(),
                self._create_migration_status_panel(),
                self._create_system_health_panel(),
                self._create_trends_panel(),
            ]

            dashboard = DashboardLayout(
                dashboard_id="main_quality_dashboard",
                title="Data Quality Dashboard",
                description="Comprehensive monitoring of data quality, processing, and system health",
                panels=panels,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            return dashboard

        except Exception as e:
            self.logger.error(f"Error creating main dashboard: {e}")
            raise

    def _create_quality_overview_panel(self) -> DashboardPanel:
        """Create quality overview panel"""
        metrics = []

        # Get current quality metrics
        quality_metrics = self._get_quality_metrics()

        # Overall quality score
        overall_score = quality_metrics.get("overall_score", 0)
        severity = self._determine_severity(overall_score, "quality_score")

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.QUALITY_SCORE,
                name="Overall Quality Score",
                value=overall_score,
                unit="score",
                severity=severity,
                description="Overall data quality score across all bills",
                timestamp=datetime.now(),
                metadata={"threshold_critical": 0.5, "threshold_warning": 0.7},
            )
        )

        # Completeness rate
        completeness = quality_metrics.get("completeness_rate", 0)
        severity = self._determine_severity(completeness, "completeness")

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.COMPLETENESS,
                name="Data Completeness",
                value=completeness,
                unit="percentage",
                severity=severity,
                description="Percentage of bills with complete required data",
                timestamp=datetime.now(),
                metadata={"threshold_critical": 0.6, "threshold_warning": 0.8},
            )
        )

        # Accuracy rate
        accuracy = quality_metrics.get("accuracy_rate", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.ACCURACY,
                name="Data Accuracy",
                value=accuracy,
                unit="percentage",
                severity=(
                    MetricSeverity.SUCCESS if accuracy > 0.9 else MetricSeverity.WARNING
                ),
                description="Percentage of bills with accurate data",
                timestamp=datetime.now(),
            )
        )

        # Consistency rate
        consistency = quality_metrics.get("consistency_rate", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.CONSISTENCY,
                name="Data Consistency",
                value=consistency,
                unit="percentage",
                severity=(
                    MetricSeverity.SUCCESS
                    if consistency > 0.85
                    else MetricSeverity.WARNING
                ),
                description="Percentage of bills with consistent data",
                timestamp=datetime.now(),
            )
        )

        return DashboardPanel(
            panel_id="quality_overview",
            title="Data Quality Overview",
            description="Key data quality metrics and scores",
            metrics=metrics,
            chart_type="gauge",
        )

    def _create_processing_metrics_panel(self) -> DashboardPanel:
        """Create processing metrics panel"""
        metrics = []

        # Get processing metrics
        processing_metrics = self._get_processing_metrics()

        # Processing volume
        daily_volume = processing_metrics.get("daily_volume", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.PROCESSING_VOLUME,
                name="Daily Processing Volume",
                value=daily_volume,
                unit="bills",
                severity=MetricSeverity.INFO,
                description="Number of bills processed in the last 24 hours",
                timestamp=datetime.now(),
            )
        )

        # Error rate
        error_rate = processing_metrics.get("error_rate", 0)
        severity = self._determine_severity(error_rate, "error_rate", inverse=True)

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.ERROR_RATE,
                name="Processing Error Rate",
                value=error_rate,
                unit="percentage",
                severity=severity,
                description="Percentage of processing operations that failed",
                timestamp=datetime.now(),
                metadata={"threshold_critical": 0.1, "threshold_warning": 0.05},
            )
        )

        # Average processing time
        avg_time = processing_metrics.get("avg_processing_time", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.PROCESSING_VOLUME,
                name="Average Processing Time",
                value=avg_time,
                unit="seconds",
                severity=MetricSeverity.INFO,
                description="Average time to process a bill",
                timestamp=datetime.now(),
            )
        )

        return DashboardPanel(
            panel_id="processing_metrics",
            title="Processing Performance",
            description="System processing performance and throughput metrics",
            metrics=metrics,
            chart_type="line",
        )

    def _create_migration_status_panel(self) -> DashboardPanel:
        """Create migration status panel"""
        metrics = []

        # Get migration metrics
        migration_metrics = self._get_migration_metrics()

        # Migration success rate
        success_rate = migration_metrics.get("success_rate", 0)
        severity = (
            MetricSeverity.SUCCESS if success_rate > 0.9 else MetricSeverity.WARNING
        )

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.MIGRATION_SUCCESS,
                name="Migration Success Rate",
                value=success_rate,
                unit="percentage",
                severity=severity,
                description="Percentage of successful migration operations",
                timestamp=datetime.now(),
            )
        )

        # Total migrations
        total_migrations = migration_metrics.get("total_migrations", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.MIGRATION_SUCCESS,
                name="Total Migrations",
                value=total_migrations,
                unit="count",
                severity=MetricSeverity.INFO,
                description="Total number of migration operations",
                timestamp=datetime.now(),
            )
        )

        # Recent migrations
        recent_migrations = migration_metrics.get("recent_migrations", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.MIGRATION_SUCCESS,
                name="Recent Migrations",
                value=recent_migrations,
                unit="count",
                severity=MetricSeverity.INFO,
                description="Number of migrations in the last 7 days",
                timestamp=datetime.now(),
            )
        )

        return DashboardPanel(
            panel_id="migration_status",
            title="Migration Operations",
            description="Data migration and quality improvement operations",
            metrics=metrics,
            chart_type="bar",
        )

    def _create_system_health_panel(self) -> DashboardPanel:
        """Create system health panel"""
        metrics = []

        # Get system health metrics
        health_metrics = self._get_system_health_metrics()

        # Database health
        db_health = health_metrics.get("database_health", 0)
        severity = (
            MetricSeverity.SUCCESS if db_health > 0.95 else MetricSeverity.WARNING
        )

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.SYSTEM_HEALTH,
                name="Database Health",
                value=db_health,
                unit="score",
                severity=severity,
                description="Database connection and performance health",
                timestamp=datetime.now(),
            )
        )

        # Service availability
        service_availability = health_metrics.get("service_availability", 0)
        severity = (
            MetricSeverity.SUCCESS
            if service_availability > 0.99
            else MetricSeverity.WARNING
        )

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.SYSTEM_HEALTH,
                name="Service Availability",
                value=service_availability,
                unit="percentage",
                severity=severity,
                description="Overall service availability",
                timestamp=datetime.now(),
            )
        )

        return DashboardPanel(
            panel_id="system_health",
            title="System Health",
            description="Overall system health and availability metrics",
            metrics=metrics,
            chart_type="status",
        )

    def _create_trends_panel(self) -> DashboardPanel:
        """Create trends panel"""
        metrics = []

        # Get trend metrics
        trend_metrics = self._get_trend_metrics()

        # Quality trend
        quality_trend = trend_metrics.get("quality_trend", 0)
        severity = (
            MetricSeverity.SUCCESS if quality_trend > 0 else MetricSeverity.WARNING
        )

        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.QUALITY_SCORE,
                name="Quality Trend",
                value=quality_trend,
                unit="change",
                severity=severity,
                description="Change in quality score over the last 30 days",
                timestamp=datetime.now(),
            )
        )

        # Volume trend
        volume_trend = trend_metrics.get("volume_trend", 0)
        metrics.append(
            DashboardMetric(
                metric_type=DashboardMetricType.PROCESSING_VOLUME,
                name="Volume Trend",
                value=volume_trend,
                unit="change",
                severity=MetricSeverity.INFO,
                description="Change in processing volume over the last 30 days",
                timestamp=datetime.now(),
            )
        )

        return DashboardPanel(
            panel_id="trends",
            title="Quality & Volume Trends",
            description="Historical trends and patterns in data quality and processing",
            metrics=metrics,
            chart_type="line",
        )

    def _get_quality_metrics(self) -> dict[str, float]:
        """Get current quality metrics"""
        cache_key = "quality_metrics"

        if self._is_cache_valid(cache_key):
            return self.metrics_cache[cache_key]

        try:
            # Get latest audit report
            audit_report = self.quality_auditor.conduct_full_audit()

            metrics = {
                "overall_score": audit_report.overall_metrics.overall_quality_score,
                "completeness_rate": audit_report.overall_metrics.completeness_rate,
                "accuracy_rate": audit_report.overall_metrics.accuracy_rate,
                "consistency_rate": audit_report.overall_metrics.consistency_rate,
                "timeliness_rate": audit_report.overall_metrics.timeliness_rate,
                "total_issues": len(audit_report.issues),
                "critical_issues": len(
                    [i for i in audit_report.issues if i.severity.value == "critical"]
                ),
            }

            self._cache_metrics(cache_key, metrics)
            return metrics

        except Exception as e:
            self.logger.error(f"Error getting quality metrics: {e}")
            return {
                "overall_score": 0,
                "completeness_rate": 0,
                "accuracy_rate": 0,
                "consistency_rate": 0,
                "timeliness_rate": 0,
                "total_issues": 0,
                "critical_issues": 0,
            }

    def _get_processing_metrics(self) -> dict[str, float]:
        """Get processing performance metrics"""
        cache_key = "processing_metrics"

        if self._is_cache_valid(cache_key):
            return self.metrics_cache[cache_key]

        try:
            with self.SessionLocal() as session:
                # Get bills processed in last 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)

                daily_volume = (
                    session.execute(
                        select(func.count(Bill.id)).where(
                            Bill.updated_at >= cutoff_time
                        )
                    ).scalar()
                    or 0
                )

                # Get processing history from bill process history
                history_query = select(BillProcessHistory).where(
                    BillProcessHistory.recorded_at >= cutoff_time
                )

                history_records = session.execute(history_query).scalars().all()

                # Calculate metrics
                total_operations = len(history_records)
                error_operations = len(
                    [r for r in history_records if r.confidence_score < 0.5]
                )

                error_rate = (
                    error_operations / total_operations if total_operations > 0 else 0
                )

                # Calculate average processing time (mock for now)
                avg_processing_time = 2.5  # seconds

                metrics = {
                    "daily_volume": daily_volume,
                    "error_rate": error_rate,
                    "avg_processing_time": avg_processing_time,
                    "total_operations": total_operations,
                }

                self._cache_metrics(cache_key, metrics)
                return metrics

        except Exception as e:
            self.logger.error(f"Error getting processing metrics: {e}")
            return {
                "daily_volume": 0,
                "error_rate": 0,
                "avg_processing_time": 0,
                "total_operations": 0,
            }

    def _get_migration_metrics(self) -> dict[str, float]:
        """Get migration operation metrics"""
        cache_key = "migration_metrics"

        if self._is_cache_valid(cache_key):
            return self.metrics_cache[cache_key]

        try:
            # Get migration statistics
            stats = self.migration_service.get_migration_statistics(30)

            metrics = {
                "success_rate": stats.get("success_rate", 0),
                "total_migrations": stats.get("total_migrations", 0),
                # Same as total for now
                "recent_migrations": stats.get("total_migrations", 0),
                "total_tasks_completed": stats.get("total_tasks_completed", 0),
                # Convert to seconds
                "avg_processing_time": stats.get("average_processing_time_ms", 0)
                / 1000,
            }

            self._cache_metrics(cache_key, metrics)
            return metrics

        except Exception as e:
            self.logger.error(f"Error getting migration metrics: {e}")
            return {
                "success_rate": 0,
                "total_migrations": 0,
                "recent_migrations": 0,
                "total_tasks_completed": 0,
                "avg_processing_time": 0,
            }

    def _get_system_health_metrics(self) -> dict[str, float]:
        """Get system health metrics"""
        cache_key = "system_health"

        if self._is_cache_valid(cache_key):
            return self.metrics_cache[cache_key]

        try:
            # Test database connection
            db_health = self._test_database_health()

            # Mock service availability (would be real monitoring in production)
            service_availability = 0.995

            metrics = {
                "database_health": db_health,
                "service_availability": service_availability,
                "uptime_percentage": 0.998,
            }

            self._cache_metrics(cache_key, metrics)
            return metrics

        except Exception as e:
            self.logger.error(f"Error getting system health metrics: {e}")
            return {
                "database_health": 0,
                "service_availability": 0,
                "uptime_percentage": 0,
            }

    def _get_trend_metrics(self) -> dict[str, float]:
        """Get trend metrics"""
        cache_key = "trend_metrics"

        if self._is_cache_valid(cache_key):
            return self.metrics_cache[cache_key]

        try:
            # Get quality trend
            quality_trend_data = self.quality_auditor.get_quality_trend(30)

            # Parse trend direction
            trend_direction = quality_trend_data.get("trend", "stable")

            if trend_direction == "improving":
                quality_trend = 0.05  # 5% improvement
            elif trend_direction == "declining":
                quality_trend = -0.05  # 5% decline
            else:
                quality_trend = 0.0  # Stable

            # Mock volume trend (would be calculated from historical data)
            volume_trend = 0.1  # 10% increase

            metrics = {
                "quality_trend": quality_trend,
                "volume_trend": volume_trend,
                "trend_period": 30,
            }

            self._cache_metrics(cache_key, metrics)
            return metrics

        except Exception as e:
            self.logger.error(f"Error getting trend metrics: {e}")
            return {"quality_trend": 0, "volume_trend": 0, "trend_period": 30}

    def _test_database_health(self) -> float:
        """Test database connection health"""
        try:
            with self.SessionLocal() as session:
                # Simple query to test connectivity
                result = session.execute(text("SELECT 1")).scalar()
                return 1.0 if result == 1 else 0.0

        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return 0.0

    def _determine_severity(
        self, value: float, metric_type: str, inverse: bool = False
    ) -> MetricSeverity:
        """Determine metric severity based on thresholds"""
        thresholds = self.config["alert_thresholds"]

        if metric_type in ["quality_score", "completeness"]:
            critical_threshold = thresholds.get(f"{metric_type}_critical", 0.5)
            warning_threshold = thresholds.get(f"{metric_type}_warning", 0.7)

            if not inverse:
                if value < critical_threshold:
                    return MetricSeverity.CRITICAL
                elif value < warning_threshold:
                    return MetricSeverity.WARNING
                else:
                    return MetricSeverity.SUCCESS
            else:
                if value > critical_threshold:
                    return MetricSeverity.CRITICAL
                elif value > warning_threshold:
                    return MetricSeverity.WARNING
                else:
                    return MetricSeverity.SUCCESS

        elif metric_type == "error_rate":
            critical_threshold = thresholds.get("error_rate_critical", 0.1)
            warning_threshold = thresholds.get("error_rate_warning", 0.05)

            if value > critical_threshold:
                return MetricSeverity.CRITICAL
            elif value > warning_threshold:
                return MetricSeverity.WARNING
            else:
                return MetricSeverity.SUCCESS

        return MetricSeverity.INFO

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached metrics are still valid"""
        if cache_key not in self.metrics_cache:
            return False

        if cache_key not in self.cache_timestamps:
            return False

        cache_age = datetime.now() - self.cache_timestamps[cache_key]
        return cache_age.total_seconds() < self.config["metrics_cache_ttl"]

    def _cache_metrics(self, cache_key: str, metrics: dict[str, Any]):
        """Cache metrics with timestamp"""
        self.metrics_cache[cache_key] = metrics
        self.cache_timestamps[cache_key] = datetime.now()

    def get_dashboard_data(
        self, dashboard_id: str = "main_quality_dashboard"
    ) -> dict[str, Any]:
        """Get complete dashboard data"""
        try:
            if dashboard_id == "main_quality_dashboard":
                dashboard = self.create_main_dashboard()
                return dashboard.to_dict()
            else:
                raise ValueError(f"Unknown dashboard ID: {dashboard_id}")

        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            raise

    def get_alerts(self) -> list[dict[str, Any]]:
        """Get current system alerts"""
        alerts = []

        try:
            # Get quality metrics for alert checking
            quality_metrics = self._get_quality_metrics()
            processing_metrics = self._get_processing_metrics()

            # Check quality score alerts
            overall_score = quality_metrics.get("overall_score", 0)
            if (
                overall_score
                < self.config["alert_thresholds"]["quality_score_critical"]
            ):
                alerts.append(
                    {
                        "type": "critical",
                        "message": f"Data quality score critically low: {overall_score:.2f}",
                        "timestamp": datetime.now().isoformat(),
                        "metric": "quality_score",
                    }
                )
            elif (
                overall_score < self.config["alert_thresholds"]["quality_score_warning"]
            ):
                alerts.append(
                    {
                        "type": "warning",
                        "message": f"Data quality score below threshold: {overall_score:.2f}",
                        "timestamp": datetime.now().isoformat(),
                        "metric": "quality_score",
                    }
                )

            # Check completeness alerts
            completeness = quality_metrics.get("completeness_rate", 0)
            if completeness < self.config["alert_thresholds"]["completeness_critical"]:
                alerts.append(
                    {
                        "type": "critical",
                        "message": f"Data completeness critically low: {completeness:.2f}",
                        "timestamp": datetime.now().isoformat(),
                        "metric": "completeness",
                    }
                )

            # Check error rate alerts
            error_rate = processing_metrics.get("error_rate", 0)
            if error_rate > self.config["alert_thresholds"]["error_rate_critical"]:
                alerts.append(
                    {
                        "type": "critical",
                        "message": f"Processing error rate too high: {error_rate:.2f}",
                        "timestamp": datetime.now().isoformat(),
                        "metric": "error_rate",
                    }
                )

            # Check for critical issues
            critical_issues = quality_metrics.get("critical_issues", 0)
            if critical_issues > 0:
                alerts.append(
                    {
                        "type": "warning",
                        "message": f"{critical_issues} critical data quality issues detected",
                        "timestamp": datetime.now().isoformat(),
                        "metric": "quality_issues",
                    }
                )

            return alerts

        except Exception as e:
            self.logger.error(f"Error getting alerts: {e}")
            return []

    def export_dashboard_config(
        self, dashboard_id: str = "main_quality_dashboard"
    ) -> dict[str, Any]:
        """Export dashboard configuration"""
        try:
            dashboard = self.create_main_dashboard()

            return {
                "dashboard_config": dashboard.to_dict(),
                "alert_thresholds": self.config["alert_thresholds"],
                "refresh_settings": {
                    "metrics_cache_ttl": self.config["metrics_cache_ttl"],
                    "default_time_range": self.config["default_time_range"],
                },
                "exported_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error exporting dashboard config: {e}")
            raise

    def get_historical_data(
        self, metric_type: str, hours: int = 24
    ) -> list[dict[str, Any]]:
        """Get historical data for a specific metric"""
        try:
            # This would query historical metrics from a time-series database
            # For now, we'll return mock data

            historical_data = []
            start_time = datetime.now() - timedelta(hours=hours)

            for i in range(hours):
                timestamp = start_time + timedelta(hours=i)

                # Mock data generation based on metric type
                if metric_type == "quality_score":
                    value = 0.8 + (0.1 * (i / hours))  # Improving trend
                elif metric_type == "processing_volume":
                    value = 100 + (10 * (i % 12))  # Daily pattern
                elif metric_type == "error_rate":
                    value = 0.02 + (0.01 * (i % 6))  # Periodic pattern
                else:
                    value = 0.5 + (0.1 * (i % 8))

                historical_data.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "value": value,
                        "metric_type": metric_type,
                    }
                )

            return historical_data

        except Exception as e:
            self.logger.error(f"Error getting historical data: {e}")
            return []

    def clear_cache(self):
        """Clear metrics cache"""
        self.metrics_cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("Metrics cache cleared")

    def get_dashboard_status(self) -> dict[str, Any]:
        """Get dashboard service status"""
        return {
            "status": "running",
            "cache_size": len(self.metrics_cache),
            "last_updated": (
                max(self.cache_timestamps.values()).isoformat()
                if self.cache_timestamps
                else None
            ),
            "alert_thresholds": self.config["alert_thresholds"],
            "cache_ttl": self.config["metrics_cache_ttl"],
        }
