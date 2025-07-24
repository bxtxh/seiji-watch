"""
Monitoring and Alerting System - Comprehensive system health monitoring and alerting.
Provides health checks, metrics collection, SLA monitoring, and alert management.
"""

import asyncio
import logging
import platform
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil

from .error_recovery_system import error_recovery_system

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    component_name: str
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component_name": self.component_name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "error_message": self.error_message,
        }


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: int | float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class Alert:
    """System alert."""

    id: str
    title: str
    description: str
    severity: AlertSeverity
    component: str
    triggered_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None
    status: str = "active"  # active, resolved, suppressed
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "component": self.component,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class SLAMetric:
    """SLA monitoring metric."""

    name: str
    target_value: float
    current_value: float
    threshold_type: str  # "min", "max"
    measurement_period: str  # "1h", "24h", "7d"
    status: HealthStatus = HealthStatus.HEALTHY
    last_updated: datetime = field(default_factory=datetime.now)

    def is_violation(self) -> bool:
        """Check if SLA is being violated."""
        if self.threshold_type == "min":
            return self.current_value < self.target_value
        else:  # max
            return self.current_value > self.target_value


class HealthChecker:
    """Health check management system."""

    def __init__(self):
        self.health_checks: dict[str, Callable] = {}
        self.check_results: dict[str, HealthCheckResult] = {}

    def register_check(self, name: str, check_func: Callable):
        """Register a health check function."""
        self.health_checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        start_time = time.time()

        try:
            check_func = self.health_checks.get(name)
            if not check_func:
                return HealthCheckResult(
                    component_name=name,
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    error_message="Health check not found",
                )

            # Execute health check
            is_healthy = await check_func()
            response_time = (time.time() - start_time) * 1000

            result = HealthCheckResult(
                component_name=name,
                status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                component_name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e),
            )

        self.check_results[name] = result
        return result

    async def run_all_checks(self) -> dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}

        # Run checks concurrently
        tasks = []
        for name in self.health_checks.keys():
            task = asyncio.create_task(self.run_check(name))
            tasks.append((name, task))

        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                results[name] = HealthCheckResult(
                    component_name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    error_message=str(e),
                )

        return results

    def get_overall_status(self, results: dict[str, HealthCheckResult]) -> HealthStatus:
        """Calculate overall system health status."""
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in results.values()]

        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED


class MetricsCollector:
    """Metrics collection and aggregation system."""

    def __init__(self, retention_hours: int = 24):
        self.metrics: dict[str, list[MetricPoint]] = {}
        self.retention_hours = retention_hours

        # System metrics
        self.system_metrics_enabled = True
        self.last_cleanup = datetime.now()

    def record_metric(
        self,
        name: str,
        value: int | float,
        metric_type: MetricType,
        tags: dict[str, str] = None,
    ):
        """Record a metric value."""
        if tags is None:
            tags = {}

        point = MetricPoint(name=name, value=value, metric_type=metric_type, tags=tags)

        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(point)

        # Cleanup old metrics periodically
        if (datetime.now() - self.last_cleanup).total_seconds() > 3600:  # Every hour
            self._cleanup_old_metrics()

    def increment_counter(self, name: str, value: int = 1, tags: dict[str, str] = None):
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, tags)

    def set_gauge(self, name: str, value: int | float, tags: dict[str, str] = None):
        """Set a gauge metric value."""
        self.record_metric(name, value, MetricType.GAUGE, tags)

    def record_timer(self, name: str, duration_ms: float, tags: dict[str, str] = None):
        """Record a timing metric."""
        self.record_metric(name, duration_ms, MetricType.TIMER, tags)

    def record_histogram(
        self, name: str, value: int | float, tags: dict[str, str] = None
    ):
        """Record a histogram metric."""
        self.record_metric(name, value, MetricType.HISTOGRAM, tags)

    async def collect_system_metrics(self):
        """Collect system-level metrics."""
        if not self.system_metrics_enabled:
            return

        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.set_gauge("system.cpu.usage_percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.set_gauge("system.memory.usage_percent", memory.percent)
            self.set_gauge("system.memory.available_bytes", memory.available)
            self.set_gauge("system.memory.used_bytes", memory.used)

            # Disk metrics
            disk = psutil.disk_usage("/")
            self.set_gauge("system.disk.usage_percent", (disk.used / disk.total) * 100)
            self.set_gauge("system.disk.free_bytes", disk.free)

            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                self.increment_counter("system.network.bytes_sent", network.bytes_sent)
                self.increment_counter(
                    "system.network.bytes_received", network.bytes_recv
                )
            except Exception:
                pass  # Network stats not available on all systems

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    def get_metric_summary(self, name: str, period_minutes: int = 60) -> dict[str, Any]:
        """Get summary statistics for a metric over a time period."""
        if name not in self.metrics:
            return {}

        cutoff_time = datetime.now() - timedelta(minutes=period_minutes)
        recent_points = [
            point for point in self.metrics[name] if point.timestamp > cutoff_time
        ]

        if not recent_points:
            return {}

        values = [point.value for point in recent_points]

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "average": sum(values) / len(values),
            "latest": values[-1] if values else None,
            "period_minutes": period_minutes,
        }

    def get_all_metrics(self, period_minutes: int = 60) -> dict[str, Any]:
        """Get all metrics for the specified period."""
        result = {}
        for metric_name in self.metrics.keys():
            summary = self.get_metric_summary(metric_name, period_minutes)
            if summary:
                result[metric_name] = summary
        return result

    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        for metric_name, points in self.metrics.items():
            self.metrics[metric_name] = [
                point for point in points if point.timestamp > cutoff_time
            ]

        self.last_cleanup = datetime.now()


class AlertManager:
    """Alert management and notification system."""

    def __init__(self):
        self.alerts: dict[str, Alert] = {}
        self.alert_rules: list[Callable] = []
        self.notification_handlers: list[Callable] = []

    def register_alert_rule(self, rule_func: Callable):
        """Register an alert rule function."""
        self.alert_rules.append(rule_func)
        logger.info(f"Registered alert rule: {rule_func.__name__}")

    def register_notification_handler(self, handler_func: Callable):
        """Register a notification handler."""
        self.notification_handlers.append(handler_func)
        logger.info(f"Registered notification handler: {handler_func.__name__}")

    async def trigger_alert(self, alert: Alert):
        """Trigger a new alert."""

        # Check if alert already exists and is active
        existing_alert = self.alerts.get(alert.id)
        if existing_alert and existing_alert.status == "active":
            logger.debug(f"Alert {alert.id} already active, skipping")
            return

        self.alerts[alert.id] = alert
        logger.warning(
            f"Alert triggered: {alert.title} (severity: {alert.severity.value})"
        )

        # Send notifications
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Failed to send alert notification: {e}")

    async def resolve_alert(self, alert_id: str, resolved_by: str = "system"):
        """Resolve an active alert."""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            if alert.status == "active":
                alert.status = "resolved"
                alert.resolved_at = datetime.now()
                alert.metadata["resolved_by"] = resolved_by

                logger.info(f"Alert resolved: {alert.title}")

                # Notify about resolution
                for handler in self.notification_handlers:
                    try:
                        await handler(alert)
                    except Exception as e:
                        logger.error(
                            f"Failed to send alert resolution notification: {e}"
                        )

    async def evaluate_alert_rules(
        self,
        health_results: dict[str, HealthCheckResult],
        metrics: dict[str, Any],
        sla_metrics: list[SLAMetric],
    ):
        """Evaluate all alert rules."""

        for rule_func in self.alert_rules:
            try:
                alerts = await rule_func(health_results, metrics, sla_metrics)
                if alerts:
                    for alert in alerts:
                        await self.trigger_alert(alert)
            except Exception as e:
                logger.error(f"Failed to evaluate alert rule {rule_func.__name__}: {e}")

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return [alert for alert in self.alerts.values() if alert.status == "active"]

    def get_alert_statistics(self) -> dict[str, Any]:
        """Get alert statistics."""
        all_alerts = list(self.alerts.values())
        active_alerts = self.get_active_alerts()

        by_severity = {}
        for alert in active_alerts:
            severity = alert.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        by_component = {}
        for alert in active_alerts:
            component = alert.component
            by_component[component] = by_component.get(component, 0) + 1

        return {
            "total_alerts": len(all_alerts),
            "active_alerts": len(active_alerts),
            "alerts_by_severity": by_severity,
            "alerts_by_component": by_component,
            "oldest_active_alert": (
                min([a.triggered_at for a in active_alerts]) if active_alerts else None
            ),
        }


class SLAMonitor:
    """SLA monitoring and tracking."""

    def __init__(self):
        self.sla_metrics: dict[str, SLAMetric] = {}

        # Default SLAs
        self._setup_default_slas()

    def _setup_default_slas(self):
        """Setup default SLA metrics."""
        default_slas = {
            "api_response_time_p95": SLAMetric(
                name="api_response_time_p95",
                target_value=500.0,  # 500ms
                current_value=0.0,
                threshold_type="max",
                measurement_period="1h",
            ),
            "system_uptime": SLAMetric(
                name="system_uptime",
                target_value=99.9,  # 99.9%
                current_value=100.0,
                threshold_type="min",
                measurement_period="24h",
            ),
            "error_rate": SLAMetric(
                name="error_rate",
                target_value=1.0,  # 1%
                current_value=0.0,
                threshold_type="max",
                measurement_period="1h",
            ),
            "issue_extraction_success_rate": SLAMetric(
                name="issue_extraction_success_rate",
                target_value=95.0,  # 95%
                current_value=100.0,
                threshold_type="min",
                measurement_period="24h",
            ),
        }

        self.sla_metrics.update(default_slas)

    def update_sla_metric(self, name: str, current_value: float):
        """Update an SLA metric value."""
        if name in self.sla_metrics:
            self.sla_metrics[name].current_value = current_value
            self.sla_metrics[name].last_updated = datetime.now()

            # Update status based on violation
            if self.sla_metrics[name].is_violation():
                self.sla_metrics[name].status = HealthStatus.UNHEALTHY
            else:
                self.sla_metrics[name].status = HealthStatus.HEALTHY

    def get_sla_violations(self) -> list[SLAMetric]:
        """Get all SLA metrics that are currently in violation."""
        return [sla for sla in self.sla_metrics.values() if sla.is_violation()]

    def get_sla_status(self) -> dict[str, Any]:
        """Get overall SLA status."""
        violations = self.get_sla_violations()

        sla_details = {}
        for name, sla in self.sla_metrics.items():
            sla_details[name] = {
                "target": sla.target_value,
                "current": sla.current_value,
                "status": sla.status.value,
                "violating": sla.is_violation(),
                "last_updated": sla.last_updated.isoformat(),
            }

        return {
            "overall_status": "healthy" if len(violations) == 0 else "violation",
            "total_slas": len(self.sla_metrics),
            "violations": len(violations),
            "sla_details": sla_details,
        }


class MonitoringAlertingSystem:
    """Main monitoring and alerting system coordinator."""

    def __init__(self):
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.sla_monitor = SLAMonitor()

        # System state
        self.monitoring_enabled = True
        self.last_full_check = datetime.now()

        # Setup default health checks and alert rules
        self._setup_default_health_checks()
        self._setup_default_alert_rules()

    def _setup_default_health_checks(self):
        """Setup default health checks."""

        async def error_recovery_health():
            return await error_recovery_system.health_check()

        async def system_resources_health():
            try:
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage("/").percent

                return cpu_percent < 90 and memory_percent < 90 and disk_percent < 90
            except Exception:
                return False

        self.health_checker.register_check(
            "error_recovery_system", error_recovery_health
        )
        self.health_checker.register_check("system_resources", system_resources_health)

    def _setup_default_alert_rules(self):
        """Setup default alert rules."""

        async def high_error_rate_rule(health_results, metrics, sla_metrics):
            alerts = []

            # Check for high error rates
            error_rate_metric = metrics.get("error_rate", {})
            if error_rate_metric.get("latest", 0) > 5.0:  # 5% error rate
                alerts.append(
    Alert(
        id="high_error_rate",
        title="High Error Rate Detected",
        description=f"Error rate is {error_rate_metric['latest']:.1f}%, exceeding 5% threshold",
        severity=AlertSeverity.HIGH,
        component="system",
        metadata={
            "error_rate": error_rate_metric["latest"]},
             ) )

            return alerts

        async def unhealthy_components_rule(health_results, metrics, sla_metrics):
            alerts = []

            for component_name, result in health_results.items():
                if result.status == HealthStatus.UNHEALTHY:
                    alerts.append(
    Alert(
        id=f"component_unhealthy_{component_name}",
        title=f"Component {component_name} Unhealthy",
        description=f"Health check failed: {result.error_message or 'Unknown error'}",
        severity=AlertSeverity.CRITICAL,
        component=component_name,
        metadata={
            "response_time_ms": result.response_time_ms},
             ) )

            return alerts

        async def sla_violation_rule(health_results, metrics, sla_metrics):
            alerts = []

            for sla in sla_metrics:
                if sla.is_violation():
                    alerts.append(
    Alert(
        id=f"sla_violation_{sla.name}",
        title=f"SLA Violation: {sla.name}",
        description=f"SLA {sla.name} violated: {sla.current_value} vs target {sla.target_value}",
        severity=AlertSeverity.HIGH,
        component="sla",
        metadata={
            "sla_name": sla.name,
            "current": sla.current_value,
            "target": sla.target_value,
            },
             ) )

            return alerts

        self.alert_manager.register_alert_rule(high_error_rate_rule)
        self.alert_manager.register_alert_rule(unhealthy_components_rule)
        self.alert_manager.register_alert_rule(sla_violation_rule)

    async def run_full_monitoring_cycle(self):
        """Run a complete monitoring cycle."""
        if not self.monitoring_enabled:
            return

        try:
            # Collect system metrics
            await self.metrics_collector.collect_system_metrics()

            # Run health checks
            health_results = await self.health_checker.run_all_checks()

            # Update SLA metrics based on current data
            await self._update_sla_metrics(health_results)

            # Get current metrics
            current_metrics = self.metrics_collector.get_all_metrics()

            # Evaluate alert rules
            sla_metrics = list(self.sla_monitor.sla_metrics.values())
            await self.alert_manager.evaluate_alert_rules(
                health_results, current_metrics, sla_metrics
            )

            self.last_full_check = datetime.now()

        except Exception as e:
            logger.error(f"Failed to run monitoring cycle: {e}")

    async def _update_sla_metrics(self, health_results: dict[str, HealthCheckResult]):
        """Update SLA metrics based on current system state."""

        # Calculate system uptime based on health checks
        healthy_components = sum(
            1
            for result in health_results.values()
            if result.status == HealthStatus.HEALTHY
        )
        total_components = len(health_results)
        uptime_percentage = (
            (healthy_components / total_components * 100)
            if total_components > 0
            else 100
        )

        self.sla_monitor.update_sla_metric("system_uptime", uptime_percentage)

        # Update API response time from metrics
        api_metrics = self.metrics_collector.get_metric_summary("api_response_time", 60)
        if api_metrics:
            # Use max as P95 approximation (simplified)
            self.sla_monitor.update_sla_metric(
                "api_response_time_p95", api_metrics.get("max", 0)
            )

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data."""

        # Get latest health results
        health_results = await self.health_checker.run_all_checks()
        overall_health = self.health_checker.get_overall_status(health_results)

        # Get metrics
        current_metrics = self.metrics_collector.get_all_metrics()

        # Get alerts
        active_alerts = self.alert_manager.get_active_alerts()
        alert_stats = self.alert_manager.get_alert_statistics()

        # Get SLA status
        sla_status = self.sla_monitor.get_sla_status()

        # Get error recovery status
        error_recovery_status = error_recovery_system.get_system_status()

        return {
            "overall_health": overall_health.value,
            "timestamp": datetime.now().isoformat(),
            "health_checks": {
                name: result.to_dict() for name, result in health_results.items()
            },
            "metrics": current_metrics,
            "alerts": {
                "active_count": len(active_alerts),
                "active_alerts": [alert.to_dict() for alert in active_alerts],
                "statistics": alert_stats,
            },
            "sla": sla_status,
            "error_recovery": error_recovery_status,
            "system_info": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "monitoring_enabled": self.monitoring_enabled,
                "last_full_check": self.last_full_check.isoformat(),
            },
        }

    async def health_check(self) -> bool:
        """Health check for the monitoring system itself."""
        try:
            # Check if monitoring is functional
            test_results = await self.health_checker.run_all_checks()

            # Check if alerts are being processed
            active_alerts = self.alert_manager.get_active_alerts()

            # Check metrics collection
            recent_metrics = self.metrics_collector.get_all_metrics(5)  # Last 5 minutes

            # Basic health criteria
            monitoring_healthy = (
                len(test_results) > 0  # Health checks are running
                and len(active_alerts) < 10  # Not too many alerts
                and len(recent_metrics) > 0  # Metrics being collected
            )

            return monitoring_healthy

        except Exception as e:
            logger.error(f"Monitoring system health check failed: {e}")
            return False


# Global monitoring system instance
monitoring_system = MonitoringAlertingSystem()
