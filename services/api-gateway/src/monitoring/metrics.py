"""Metrics collection and monitoring utilities for API Gateway."""

import asyncio
import json
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str]
    unit: str = 'count'


@dataclass
class HealthCheckResult:
    """Health check result."""
    service: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    response_time_ms: float
    timestamp: datetime
    details: dict[str, Any]


class MetricsCollector:
    """Metrics collection and aggregation."""

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.request_counts = defaultdict(int)
        self.response_times: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.error_counts = defaultdict(int)
        self.health_checks: deque = deque(maxlen=100)

        # Performance tracking
        self.active_requests = 0
        self.total_requests = 0
        self.start_time = datetime.utcnow()

        # Rate limiting tracking
        self.rate_limit_violations = defaultdict(int)

        # Security tracking
        self.security_events = defaultdict(int)

    def record_metric(self, name: str, value: float,
                      tags: dict[str, str] = None, unit: str = 'count'):
        """Record a metric point."""
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            unit=unit
        )

        self.metrics[name].append(metric)
        self._cleanup_old_metrics()

    def record_request(
            self,
            method: str,
            path: str,
            status_code: int,
            response_time_ms: float):
        """Record API request metrics."""
        self.total_requests += 1

        # Count by method and status
        self.request_counts[f"{method}:{status_code}"] += 1
        self.request_counts[f"path:{path}"] += 1

        # Track response times
        self.response_times[f"{method}:{path}"].append(response_time_ms)

        # Count errors
        if status_code >= 400:
            self.error_counts[f"{method}:{path}"] += 1
            self.error_counts[f"status:{status_code}"] += 1

        # Record as metrics
        self.record_metric('http_requests_total', 1, {
            'method': method,
            'path': path,
            'status': str(status_code)
        })

        self.record_metric('http_request_duration_ms', response_time_ms, {
            'method': method,
            'path': path
        }, unit='ms')

    def record_error(self, error_type: str, endpoint: str = None,
                     details: dict[str, Any] = None):
        """Record error metrics."""
        tags = {'error_type': error_type}
        if endpoint:
            tags['endpoint'] = endpoint

        self.record_metric('errors_total', 1, tags)

        if details:
            self.record_metric('error_details', 1, {
                **tags,
                **{k: str(v) for k, v in details.items()}
            })

    def record_security_event(
            self,
            event_type: str,
            severity: str,
            source_ip: str = None):
        """Record security event metrics."""
        tags = {
            'event_type': event_type,
            'severity': severity
        }
        if source_ip:
            tags['source_ip'] = source_ip

        self.record_metric('security_events_total', 1, tags)
        self.security_events[f"{event_type}:{severity}"] += 1

    def record_rate_limit_violation(self, client_id: str, endpoint: str):
        """Record rate limiting violations."""
        self.rate_limit_violations[client_id] += 1
        self.record_metric('rate_limit_violations_total', 1, {
            'client_id': client_id[:32],  # Truncate for privacy
            'endpoint': endpoint
        })

    def record_health_check(self, result: HealthCheckResult):
        """Record health check result."""
        self.health_checks.append(result)

        self.record_metric('health_check_response_time_ms', result.response_time_ms, {
            'service': result.service,
            'status': result.status
        }, unit='ms')

        self.record_metric('health_check_status', 1 if result.status ==
                           'healthy' else 0, {'service': result.service})

    def get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        now = datetime.utcnow()
        uptime_seconds = (now - self.start_time).total_seconds()

        # Calculate percentiles for response times
        all_response_times = []
        for times in self.response_times.values():
            all_response_times.extend(times)

        if all_response_times:
            sorted_times = sorted(all_response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            p50 = p95 = p99 = 0

        # Recent error rate (last hour)
        recent_errors = sum(
            1 for metric_list in self.metrics.values()
            for metric in metric_list
            if 'error' in metric.name.lower() and
            (now - metric.timestamp) < timedelta(hours=1)
        )

        recent_requests = sum(
            1 for metric_list in self.metrics.values()
            for metric in metric_list
            if metric.name == 'http_requests_total' and
            (now - metric.timestamp) < timedelta(hours=1)
        )

        error_rate = (
            recent_errors /
            recent_requests *
            100) if recent_requests > 0 else 0

        return {
            'uptime_seconds': uptime_seconds,
            'total_requests': self.total_requests,
            'active_requests': self.active_requests,
            'requests_per_second': self.total_requests / uptime_seconds if uptime_seconds > 0 else 0,
            'response_time_percentiles': {
                'p50_ms': p50,
                'p95_ms': p95,
                'p99_ms': p99},
            'error_rate_percent': error_rate,
            'recent_errors': recent_errors,
            'recent_requests': recent_requests,
            'rate_limit_violations': dict(
                self.rate_limit_violations),
            'security_events': dict(
                self.security_events),
            'last_updated': now.isoformat()}

    def get_metrics_for_export(self, format: str = 'prometheus') -> str:
        """Export metrics in specified format."""
        if format == 'prometheus':
            return self._export_prometheus()
        elif format == 'json':
            return self._export_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Group metrics by name
        metric_groups = defaultdict(list)
        for metric_list in self.metrics.values():
            for metric in metric_list:
                metric_groups[metric.name].append(metric)

        for metric_name, metric_list in metric_groups.items():
            # Add help and type comments
            lines.append(
                f"# HELP {metric_name} {metric_name.replace('_', ' ').title()}")
            lines.append(f"# TYPE {metric_name} counter")

            # Group by tags and sum values
            tag_groups = defaultdict(float)
            for metric in metric_list:
                tag_str = ','.join(f'{k}="{v}"' for k, v in sorted(metric.tags.items()))
                tag_groups[tag_str] += metric.value

            for tags, value in tag_groups.items():
                if tags:
                    lines.append(f"{metric_name}{{{tags}}} {value}")
                else:
                    lines.append(f"{metric_name} {value}")

        return '\n'.join(lines)

    def _export_json(self) -> str:
        """Export metrics in JSON format."""
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'summary': self.get_summary_stats(),
            'metrics': []
        }

        for metric_list in self.metrics.values():
            for metric in metric_list:
                data['metrics'].append(asdict(metric))

        return json.dumps(data, default=str, indent=2)

    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)

        for metric_name, metric_list in self.metrics.items():
            while metric_list and metric_list[0].timestamp < cutoff:
                metric_list.popleft()


class RequestTracker:
    """Context manager for tracking request lifecycle."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.metrics_collector.active_requests += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metrics_collector.active_requests -= 1
        if exc_type:
            self.metrics_collector.record_error(
                error_type=exc_type.__name__,
                details={'error_message': str(exc_val)}
            )


class HealthChecker:
    """Health check utilities."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.checks = {}

    def register_check(self, name: str, check_func):
        """Register a health check function."""
        self.checks[name] = check_func

    async def run_checks(self) -> dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}

        for name, check_func in self.checks.items():
            start_time = time.time()
            try:
                if asyncio.iscoroutinefunction(check_func):
                    status, details = await check_func()
                else:
                    status, details = check_func()

                response_time_ms = (time.time() - start_time) * 1000

                result = HealthCheckResult(
                    service=name,
                    status=status,
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow(),
                    details=details
                )

                results[name] = result
                self.metrics_collector.record_health_check(result)

            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000

                result = HealthCheckResult(
                    service=name,
                    status='unhealthy',
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow(),
                    details={'error': str(e)}
                )

                results[name] = result
                self.metrics_collector.record_health_check(result)

        return results

    def get_overall_status(self, results: dict[str, HealthCheckResult]) -> str:
        """Determine overall system health status."""
        if not results:
            return 'unknown'

        statuses = [result.status for result in results.values()]

        if all(status == 'healthy' for status in statuses):
            return 'healthy'
        elif any(status == 'unhealthy' for status in statuses):
            return 'unhealthy'
        else:
            return 'degraded'


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker(metrics_collector)

# Health check functions


async def check_database_health():
    """Check database connectivity."""
    # This would check Airtable connectivity
    try:
        # Simulate database check
        await asyncio.sleep(0.1)  # Simulate network call
        return 'healthy', {'connection': 'ok'}
    except Exception as e:
        return 'unhealthy', {'error': str(e)}


async def check_vector_store_health():
    """Check vector store connectivity."""
    # This would check Weaviate connectivity
    try:
        # Simulate vector store check
        await asyncio.sleep(0.1)  # Simulate network call
        return 'healthy', {'connection': 'ok'}
    except Exception as e:
        return 'unhealthy', {'error': str(e)}


def check_memory_usage():
    """Check memory usage."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        usage_percent = memory.percent

        if usage_percent > 90:
            return 'unhealthy', {'memory_usage_percent': usage_percent}
        elif usage_percent > 80:
            return 'degraded', {'memory_usage_percent': usage_percent}
        else:
            return 'healthy', {'memory_usage_percent': usage_percent}
    except ImportError:
        return 'unknown', {'error': 'psutil not available'}


def check_disk_usage():
    """Check disk usage."""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100

        if usage_percent > 95:
            return 'unhealthy', {'disk_usage_percent': usage_percent}
        elif usage_percent > 85:
            return 'degraded', {'disk_usage_percent': usage_percent}
        else:
            return 'healthy', {'disk_usage_percent': usage_percent}
    except ImportError:
        return 'unknown', {'error': 'psutil not available'}


# Register default health checks
health_checker.register_check('database', check_database_health)
health_checker.register_check('vector_store', check_vector_store_health)
health_checker.register_check('memory', check_memory_usage)
health_checker.register_check('disk', check_disk_usage)
