"""Metrics collection and monitoring for Airtable to Supabase migration."""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    """Alert definition."""

    name: str
    message: str
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: datetime | None = None


@dataclass
class HealthStatus:
    """Health status of a component."""

    component: str
    healthy: bool
    message: str = ""
    last_check: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and manages metrics for the migration system."""

    def __init__(self, namespace: str = "seiji_watch"):
        """Initialize metrics collector.

        Args:
            namespace: Prometheus namespace for metrics
        """
        self.namespace = namespace

        # Prometheus metrics
        self._init_prometheus_metrics()

        # In-memory metrics storage (for custom analytics)
        self.metrics_buffer: deque = deque(maxlen=10000)
        self.alerts: list[Alert] = []
        self.health_status: dict[str, HealthStatus] = {}

        # Performance tracking
        self.operation_timings: dict[str, list[float]] = {}

        # Alert thresholds
        self.alert_thresholds = self._load_alert_thresholds()

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        # Data source metrics
        self.airtable_requests = Counter(
            f"{self.namespace}_airtable_requests_total",
            "Total Airtable API requests",
            ["operation", "status"],
        )

        self.supabase_requests = Counter(
            f"{self.namespace}_supabase_requests_total",
            "Total Supabase API requests",
            ["operation", "status"],
        )

        # Sync metrics
        self.sync_operations = Counter(
            f"{self.namespace}_sync_operations_total",
            "Total sync operations",
            ["table", "operation", "status"],
        )

        self.sync_duration = Histogram(
            f"{self.namespace}_sync_duration_seconds",
            "Sync operation duration",
            ["table", "mode"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        self.sync_records_processed = Counter(
            f"{self.namespace}_sync_records_processed_total",
            "Total records processed in sync",
            ["table", "operation"],
        )

        # Cache metrics
        self.cache_hits = Counter(
            f"{self.namespace}_cache_hits_total", "Cache hit count", ["cache_type"]
        )

        self.cache_misses = Counter(
            f"{self.namespace}_cache_misses_total", "Cache miss count", ["cache_type"]
        )

        # Error metrics
        self.errors = Counter(
            f"{self.namespace}_errors_total",
            "Total errors",
            ["component", "error_type"],
        )

        # Performance metrics
        self.api_latency = Histogram(
            f"{self.namespace}_api_latency_seconds",
            "API response latency",
            ["endpoint", "method"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )

        self.query_duration = Summary(
            f"{self.namespace}_query_duration_seconds",
            "Database query duration",
            ["database", "operation"],
        )

        # System metrics
        self.active_connections = Gauge(
            f"{self.namespace}_active_connections",
            "Active database connections",
            ["database"],
        )

        self.queue_size = Gauge(
            f"{self.namespace}_queue_size", "Size of processing queues", ["queue_name"]
        )

        # Data consistency metrics
        self.data_consistency_score = Gauge(
            f"{self.namespace}_data_consistency_score",
            "Data consistency score between Airtable and Supabase",
            ["table"],
        )

        self.sync_lag_seconds = Gauge(
            f"{self.namespace}_sync_lag_seconds", "Sync lag in seconds", ["table"]
        )

    def _load_alert_thresholds(self) -> dict[str, Any]:
        """Load alert threshold configuration."""
        return {
            "error_rate": {
                "warning": 0.01,  # 1% error rate
                "critical": 0.05,  # 5% error rate
            },
            "sync_lag": {
                "warning": 300,  # 5 minutes
                "critical": 1800,  # 30 minutes
            },
            "api_latency": {
                "warning": 1.0,  # 1 second
                "critical": 5.0,  # 5 seconds
            },
            "consistency_score": {
                "warning": 0.95,  # 95% consistency
                "critical": 0.90,  # 90% consistency
            },
            "queue_size": {
                "warning": 1000,
                "critical": 5000,
            },
        }

    # =====================================================
    # Metric Recording Methods
    # =====================================================

    def record_api_request(
        self, service: str, operation: str, status: str, duration: float
    ):
        """Record an API request metric."""
        if service == "airtable":
            self.airtable_requests.labels(operation=operation, status=status).inc()
        elif service == "supabase":
            self.supabase_requests.labels(operation=operation, status=status).inc()

        # Record latency
        self.api_latency.labels(
            endpoint=f"{service}_{operation}", method="GET"
        ).observe(duration)

        # Store in buffer for analysis
        self.metrics_buffer.append(
            MetricPoint(
                name=f"{service}_request",
                value=duration,
                labels={"operation": operation, "status": status},
                metric_type=MetricType.HISTOGRAM,
            )
        )

        # Check for latency alerts
        self._check_latency_alert(service, operation, duration)

    def record_sync_operation(
        self,
        table: str,
        operation: str,
        status: str,
        records_count: int = 0,
        duration: float = 0,
    ):
        """Record a sync operation metric."""
        self.sync_operations.labels(
            table=table, operation=operation, status=status
        ).inc()

        if duration > 0:
            self.sync_duration.labels(table=table, mode=operation).observe(duration)

        if records_count > 0:
            self.sync_records_processed.labels(table=table, operation=operation).inc(
                records_count
            )

        # Store in buffer
        self.metrics_buffer.append(
            MetricPoint(
                name="sync_operation",
                value=records_count,
                labels={"table": table, "operation": operation, "status": status},
            )
        )

    def record_cache_access(self, cache_type: str, hit: bool):
        """Record cache access."""
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()

    def record_error(self, component: str, error_type: str, error_message: str = ""):
        """Record an error."""
        self.errors.labels(component=component, error_type=error_type).inc()

        # Create alert for critical errors
        if error_type in ["database_connection", "sync_failure", "data_corruption"]:
            self.create_alert(
                name=f"{component}_{error_type}",
                message=f"Error in {component}: {error_message}",
                severity=AlertSeverity.ERROR,
                metadata={"component": component, "error_type": error_type},
            )

    def record_query_duration(self, database: str, operation: str, duration: float):
        """Record database query duration."""
        self.query_duration.labels(database=database, operation=operation).observe(
            duration
        )

    def update_connection_count(self, database: str, count: int):
        """Update active connection count."""
        self.active_connections.labels(database=database).set(count)

    def update_queue_size(self, queue_name: str, size: int):
        """Update queue size."""
        self.queue_size.labels(queue_name=queue_name).set(size)

        # Check for queue size alerts
        if size > self.alert_thresholds["queue_size"]["critical"]:
            self.create_alert(
                name=f"queue_size_{queue_name}",
                message=f"Queue {queue_name} size critical: {size}",
                severity=AlertSeverity.CRITICAL,
                metadata={"queue": queue_name, "size": size},
            )
        elif size > self.alert_thresholds["queue_size"]["warning"]:
            self.create_alert(
                name=f"queue_size_{queue_name}",
                message=f"Queue {queue_name} size warning: {size}",
                severity=AlertSeverity.WARNING,
                metadata={"queue": queue_name, "size": size},
            )

    def update_consistency_score(self, table: str, score: float):
        """Update data consistency score."""
        self.data_consistency_score.labels(table=table).set(score)

        # Check for consistency alerts
        if score < self.alert_thresholds["consistency_score"]["critical"]:
            self.create_alert(
                name=f"consistency_{table}",
                message=f"Critical data consistency issue in {table}: {score:.2%}",
                severity=AlertSeverity.CRITICAL,
                metadata={"table": table, "score": score},
            )
        elif score < self.alert_thresholds["consistency_score"]["warning"]:
            self.create_alert(
                name=f"consistency_{table}",
                message=f"Data consistency warning in {table}: {score:.2%}",
                severity=AlertSeverity.WARNING,
                metadata={"table": table, "score": score},
            )

    def update_sync_lag(self, table: str, lag_seconds: float):
        """Update sync lag metric."""
        self.sync_lag_seconds.labels(table=table).set(lag_seconds)

        # Check for sync lag alerts
        if lag_seconds > self.alert_thresholds["sync_lag"]["critical"]:
            self.create_alert(
                name=f"sync_lag_{table}",
                message=f"Critical sync lag for {table}: {lag_seconds}s",
                severity=AlertSeverity.CRITICAL,
                metadata={"table": table, "lag": lag_seconds},
            )
        elif lag_seconds > self.alert_thresholds["sync_lag"]["warning"]:
            self.create_alert(
                name=f"sync_lag_{table}",
                message=f"Sync lag warning for {table}: {lag_seconds}s",
                severity=AlertSeverity.WARNING,
                metadata={"table": table, "lag": lag_seconds},
            )

    # =====================================================
    # Alert Management
    # =====================================================

    def create_alert(
        self,
        name: str,
        message: str,
        severity: AlertSeverity,
        metadata: dict[str, Any] | None = None,
    ):
        """Create a new alert."""
        # Check if alert already exists
        existing = next(
            (a for a in self.alerts if a.name == name and not a.resolved), None
        )

        if not existing:
            alert = Alert(
                name=name, message=message, severity=severity, metadata=metadata or {}
            )
            self.alerts.append(alert)

            logger.warning(f"Alert created: {severity.value} - {message}")

            # Send notification for critical alerts
            if severity == AlertSeverity.CRITICAL:
                self._send_critical_alert(alert)

    def resolve_alert(self, name: str):
        """Resolve an existing alert."""
        for alert in self.alerts:
            if alert.name == name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info(f"Alert resolved: {name}")

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return [a for a in self.alerts if not a.resolved]

    def _check_latency_alert(self, service: str, operation: str, duration: float):
        """Check if latency exceeds thresholds."""
        if duration > self.alert_thresholds["api_latency"]["critical"]:
            self.create_alert(
                name=f"latency_{service}_{operation}",
                message=f"Critical latency for {service} {operation}: {duration:.2f}s",
                severity=AlertSeverity.CRITICAL,
                metadata={
                    "service": service,
                    "operation": operation,
                    "duration": duration,
                },
            )
        elif duration > self.alert_thresholds["api_latency"]["warning"]:
            self.create_alert(
                name=f"latency_{service}_{operation}",
                message=f"High latency for {service} {operation}: {duration:.2f}s",
                severity=AlertSeverity.WARNING,
                metadata={
                    "service": service,
                    "operation": operation,
                    "duration": duration,
                },
            )

    def _send_critical_alert(self, alert: Alert):
        """Send critical alert notification."""
        # In production, this would send to PagerDuty, Slack, etc.
        logger.critical(f"CRITICAL ALERT: {alert.message}")

    # =====================================================
    # Health Monitoring
    # =====================================================

    def update_health_status(
        self,
        component: str,
        healthy: bool,
        message: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        """Update health status of a component."""
        self.health_status[component] = HealthStatus(
            component=component,
            healthy=healthy,
            message=message,
            metadata=metadata or {},
        )

        # Create alert for unhealthy components
        if not healthy:
            self.create_alert(
                name=f"health_{component}",
                message=f"Component unhealthy: {component} - {message}",
                severity=AlertSeverity.ERROR,
                metadata={"component": component},
            )
        else:
            # Resolve existing health alert if component is now healthy
            self.resolve_alert(f"health_{component}")

    def get_overall_health(self) -> dict[str, Any]:
        """Get overall system health."""
        healthy_count = sum(1 for s in self.health_status.values() if s.healthy)
        total_count = len(self.health_status)

        return {
            "healthy": healthy_count == total_count,
            "components": {
                name: {
                    "healthy": status.healthy,
                    "message": status.message,
                    "last_check": status.last_check.isoformat(),
                }
                for name, status in self.health_status.items()
            },
            "health_score": healthy_count / total_count if total_count > 0 else 0,
            "active_alerts": len(self.get_active_alerts()),
        }

    # =====================================================
    # Analytics and Reporting
    # =====================================================

    def get_metrics_summary(self, time_window_minutes: int = 60) -> dict[str, Any]:
        """Get summary of metrics for a time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        # Filter recent metrics
        recent_metrics = [m for m in self.metrics_buffer if m.timestamp > cutoff_time]

        # Calculate summaries
        summary = {
            "time_window_minutes": time_window_minutes,
            "total_metrics": len(recent_metrics),
            "metrics_by_type": {},
            "error_rate": self._calculate_error_rate(recent_metrics),
            "average_latencies": self._calculate_average_latencies(recent_metrics),
            "sync_statistics": self._calculate_sync_statistics(recent_metrics),
        }

        # Group by metric type
        for metric in recent_metrics:
            metric_type = metric.metric_type.value
            if metric_type not in summary["metrics_by_type"]:
                summary["metrics_by_type"][metric_type] = 0
            summary["metrics_by_type"][metric_type] += 1

        return summary

    def _calculate_error_rate(self, metrics: list[MetricPoint]) -> float:
        """Calculate error rate from metrics."""
        error_count = sum(1 for m in metrics if m.labels.get("status") == "error")
        total_count = len(metrics)

        return error_count / total_count if total_count > 0 else 0

    def _calculate_average_latencies(
        self, metrics: list[MetricPoint]
    ) -> dict[str, float]:
        """Calculate average latencies by service."""
        latencies = {}
        counts = {}

        for metric in metrics:
            if metric.name.endswith("_request"):
                service = metric.name.replace("_request", "")
                if service not in latencies:
                    latencies[service] = 0
                    counts[service] = 0
                latencies[service] += metric.value
                counts[service] += 1

        return {
            service: latencies[service] / counts[service]
            for service in latencies
            if counts[service] > 0
        }

    def _calculate_sync_statistics(self, metrics: list[MetricPoint]) -> dict[str, Any]:
        """Calculate sync statistics."""
        sync_metrics = [m for m in metrics if m.name == "sync_operation"]

        if not sync_metrics:
            return {}

        total_records = sum(m.value for m in sync_metrics)
        successful = sum(
            m.value for m in sync_metrics if m.labels.get("status") == "success"
        )

        return {
            "total_sync_operations": len(sync_metrics),
            "total_records_synced": total_records,
            "success_rate": successful / total_records if total_records > 0 else 0,
            "tables_synced": list(set(m.labels.get("table", "") for m in sync_metrics)),
        }

    def export_metrics_json(self) -> str:
        """Export metrics as JSON."""
        return json.dumps(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "health": self.get_overall_health(),
                "summary": self.get_metrics_summary(),
                "active_alerts": [asdict(a) for a in self.get_active_alerts()],
            },
            default=str,
        )

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.metrics_buffer.clear()
        self.alerts.clear()
        self.health_status.clear()
        self.operation_timings.clear()
