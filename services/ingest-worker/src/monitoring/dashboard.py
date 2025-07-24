"""
Performance Dashboard and Monitoring API

This module provides comprehensive dashboard APIs for monitoring:
- Real-time system performance metrics
- Processing pipeline health and statistics
- Data quality trends and analysis
- Alert status and management
- Historical performance analysis
- Resource utilization monitoring
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .alerting import get_active_alerts, get_alert_stats
from .metrics import get_metrics_summary, get_prometheus_metrics, ingest_metrics


class DashboardDataProvider:
    """Provider for dashboard data and analytics."""

    def __init__(self):
        self.cache_duration_minutes = 5
        self._cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, datetime] = {}

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_timestamps:
            return False

        age = datetime.utcnow() - self._cache_timestamps[key]
        return age.total_seconds() < (self.cache_duration_minutes * 60)

    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp."""
        self._cache[key] = data
        self._cache_timestamps[key] = datetime.utcnow()

    def get_overview_metrics(self) -> dict[str, Any]:
        """Get high-level overview metrics."""
        cache_key = "overview_metrics"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Get comprehensive summary
        summary = get_metrics_summary()

        # Calculate derived metrics
        now = datetime.utcnow()
        uptime_hours = summary['uptime_seconds'] / 3600

        # Processing throughput calculations
        processing_stats = summary.get('processing_stats', {})
        total_processed = sum(
            stats.get('total_processed', 0)
            for stats in processing_stats.values()
        )

        processing_per_hour = total_processed / uptime_hours if uptime_hours > 0 else 0

        # Overall success rate
        total_successful = sum(
            stats.get('successful', 0)
            for stats in processing_stats.values()
        )
        overall_success_rate = total_successful / total_processed if total_processed > 0 else 0

        # System health score (0-100)
        system_metrics = summary.get('system_metrics', {})
        if system_metrics:
            cpu_health = max(0, 100 - system_metrics.get('cpu_percent', 0))
            memory_health = max(0, 100 - system_metrics.get('memory_percent', 0))
            disk_health = max(0, 100 - system_metrics.get('disk_usage_percent', 0))
            health_score = (cpu_health + memory_health + disk_health) / 3
        else:
            health_score = 100

        # Alert status
        alert_stats = get_alert_stats()
        active_alerts = alert_stats.get('active_alerts_count', 0)

        overview = {
            'service_status': 'healthy' if health_score > 70 and active_alerts == 0 else 'degraded',
            'uptime_hours': round(
                uptime_hours,
                2),
            'total_operations_processed': total_processed,
            'processing_rate_per_hour': round(
                processing_per_hour,
                2),
            'overall_success_rate': round(
                overall_success_rate * 100,
                2),
            'system_health_score': round(
                health_score,
                1),
            'active_alerts': active_alerts,
            'timestamp': now.isoformat()}

        self._cache_data(cache_key, overview)
        return overview

    def get_processing_pipeline_status(self) -> dict[str, Any]:
        """Get detailed processing pipeline status."""
        cache_key = "pipeline_status"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        summary = get_metrics_summary()
        processing_stats = summary.get('processing_stats', {})

        pipeline_status = {}

        for operation, stats in processing_stats.items():
            pipeline_status[operation] = {
                'total_processed': stats.get('total_processed', 0),
                'successful': stats.get('successful', 0),
                'failed': stats.get('failed', 0),
                'success_rate': round(stats.get('success_rate', 0) * 100, 2),
                'error_rate': round(stats.get('error_rate', 0) * 100, 2),
                'avg_processing_time': round(stats.get('avg_processing_time', 0), 3),
                'last_processed': stats.get('last_processed'),
                'status': self._determine_pipeline_status(stats)
            }

        self._cache_data(cache_key, pipeline_status)
        return pipeline_status

    def _determine_pipeline_status(self, stats: dict[str, Any]) -> str:
        """Determine pipeline component status."""
        success_rate = stats.get('success_rate', 0)
        last_processed = stats.get('last_processed')

        # Check if recently active
        if last_processed:
            if isinstance(last_processed, str):
                try:
                    last_processed = datetime.fromisoformat(
                        last_processed.replace('Z', '+00:00'))
                except Exception:
                    last_processed = None

            if last_processed and (
                    datetime.utcnow() -
                    last_processed.replace(
                        tzinfo=None)) > timedelta(
                    hours=2):
                return 'idle'

        # Check success rate
        if success_rate >= 0.95:
            return 'healthy'
        elif success_rate >= 0.8:
            return 'degraded'
        else:
            return 'unhealthy'

    def get_data_quality_metrics(self) -> dict[str, Any]:
        """Get data quality metrics and trends."""
        cache_key = "data_quality"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        summary = get_metrics_summary()
        quality_metrics = summary.get('quality_metrics', {})

        quality_status = {}

        for metric_name, metric_data in quality_metrics.items():
            if isinstance(metric_data, dict):
                current_value = metric_data.get('average', 0)

                # Determine quality status
                if 'accuracy' in metric_name or 'completeness' in metric_name:
                    # Higher is better (0-1 scale)
                    if current_value >= 0.9:
                        status = 'excellent'
                    elif current_value >= 0.8:
                        status = 'good'
                    elif current_value >= 0.7:
                        status = 'acceptable'
                    else:
                        status = 'poor'
                elif 'error_rate' in metric_name:
                    # Lower is better (0-1 scale)
                    if current_value <= 0.05:
                        status = 'excellent'
                    elif current_value <= 0.1:
                        status = 'good'
                    elif current_value <= 0.2:
                        status = 'acceptable'
                    else:
                        status = 'poor'
                else:
                    status = 'unknown'

                quality_status[metric_name] = {
                    'current_value': round(current_value, 3),
                    'min_value': round(metric_data.get('min', 0), 3),
                    'max_value': round(metric_data.get('max', 0), 3),
                    'sample_count': metric_data.get('count', 0),
                    'status': status
                }

        self._cache_data(cache_key, quality_status)
        return quality_status

    def get_system_resource_metrics(self) -> dict[str, Any]:
        """Get system resource utilization metrics."""
        cache_key = "system_resources"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        summary = get_metrics_summary()
        system_metrics = summary.get('system_metrics', {})

        if not system_metrics:
            return {}

        resources = {
            'cpu': {
                'current_percent': system_metrics.get('cpu_percent', 0),
                'status': self._get_resource_status(system_metrics.get('cpu_percent', 0), [70, 85])
            },
            'memory': {
                'current_percent': system_metrics.get('memory_percent', 0),
                'status': self._get_resource_status(system_metrics.get('memory_percent', 0), [80, 90])
            },
            'disk': {
                'current_percent': system_metrics.get('disk_usage_percent', 0),
                'status': self._get_resource_status(system_metrics.get('disk_usage_percent', 0), [85, 95])
            },
            'network_io_bytes': system_metrics.get('network_io_bytes', 0),
            'disk_io_bytes': system_metrics.get('disk_io_bytes', 0),
            'open_file_descriptors': system_metrics.get('open_file_descriptors', 0),
            'timestamp': system_metrics.get('timestamp')
        }

        self._cache_data(cache_key, resources)
        return resources

    def _get_resource_status(self, value: float, thresholds: list[float]) -> str:
        """Determine resource status based on thresholds."""
        if value >= thresholds[1]:
            return 'critical'
        elif value >= thresholds[0]:
            return 'warning'
        else:
            return 'normal'

    def get_alert_summary(self) -> dict[str, Any]:
        """Get comprehensive alert summary."""
        active_alerts = get_active_alerts()
        alert_stats = get_alert_stats()

        # Categorize active alerts
        alerts_by_severity = defaultdict(list)
        for alert in active_alerts:
            alerts_by_severity[alert.severity.value].append({
                'id': alert.id,
                'rule_name': alert.rule_name,
                'message': alert.message,
                'metric_value': alert.metric_value,
                'threshold': alert.threshold,
                'triggered_at': alert.triggered_at.isoformat(),
                'status': alert.status.value
            })

        return {
            'active_alerts_count': len(active_alerts),
            'alerts_by_severity': dict(alerts_by_severity),
            'alerts_last_24h': alert_stats.get('alerts_last_24h', 0),
            'severity_distribution': alert_stats.get('severity_distribution', {}),
            'enabled_rules': alert_stats.get('enabled_rules', 0),
            'suppressed_rules': alert_stats.get('suppressed_rules', 0)
        }

    def get_performance_trends(self, hours_back: int = 24) -> dict[str, Any]:
        """Get performance trends over time."""
        cache_key = f"performance_trends_{hours_back}h"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Collect time-series data
        trends = {
            'processing_times': defaultdict(list),
            'success_rates': defaultdict(list),
            'system_metrics': {
                'cpu_percent': [],
                'memory_percent': [],
                'disk_percent': []
            },
            'timestamps': []
        }

        # Get recent metrics
        for metric_name, metric_list in ingest_metrics.metrics.items():
            for metric in metric_list:
                if metric.timestamp >= cutoff_time:
                    if 'duration' in metric_name:
                        operation = metric_name.replace('_duration_seconds', '')
                        trends['processing_times'][operation].append({
                            'timestamp': metric.timestamp.isoformat(),
                            'value': metric.value
                        })
                    elif metric_name.startswith('system_'):
                        metric_type = metric_name.replace(
                            'system_', '').replace('_percent', '')
                        if metric_type in trends['system_metrics']:
                            trends['system_metrics'][metric_type].append({
                                'timestamp': metric.timestamp.isoformat(),
                                'value': metric.value
                            })

        # Calculate trend summaries
        trend_summary = {}
        for operation, times in trends['processing_times'].items():
            if times:
                values = [t['value'] for t in times]
                trend_summary[f'{operation}_avg_time'] = statistics.mean(values)
                trend_summary[f'{operation}_median_time'] = statistics.median(values)
                if len(values) > 1:
                    trend_summary[f'{operation}_time_trend'] = self._calculate_trend(
                        values)

        trends['summary'] = trend_summary

        self._cache_data(cache_key, trends)
        return trends

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate simple trend direction."""
        if len(values) < 2:
            return 'stable'

        # Simple linear trend
        n = len(values)
        first_half = statistics.mean(values[:n // 2])
        second_half = statistics.mean(values[n // 2:])

        change_percent = ((second_half - first_half) /
                          first_half * 100) if first_half > 0 else 0

        if change_percent > 10:
            return 'increasing'
        elif change_percent < -10:
            return 'decreasing'
        else:
            return 'stable'

    def get_health_check_status(self) -> dict[str, Any]:
        """Get comprehensive health check status."""
        self.get_overview_metrics()
        pipeline_status = self.get_processing_pipeline_status()
        system_resources = self.get_system_resource_metrics()
        alert_summary = self.get_alert_summary()

        # Overall health determination
        health_factors = []

        # System health
        if system_resources:
            cpu_ok = system_resources['cpu']['status'] in ['normal', 'warning']
            memory_ok = system_resources['memory']['status'] in ['normal', 'warning']
            disk_ok = system_resources['disk']['status'] in ['normal', 'warning']
            health_factors.extend([cpu_ok, memory_ok, disk_ok])

        # Pipeline health
        for component, status_info in pipeline_status.items():
            component_ok = status_info['status'] in ['healthy', 'idle']
            health_factors.append(component_ok)

        # Alert status
        critical_alerts = alert_summary['active_alerts_count'] == 0
        health_factors.append(critical_alerts)

        # Calculate overall health
        if all(health_factors):
            overall_status = 'healthy'
        elif sum(health_factors) / len(health_factors) >= 0.7:
            overall_status = 'degraded'
        else:
            overall_status = 'unhealthy'

        return {
            'overall_status': overall_status,
            'health_score': round(sum(health_factors) / len(health_factors) * 100, 1),
            'components': {
                'system_resources': 'healthy' if all([
                    system_resources.get('cpu', {}).get('status') in ['normal', 'warning'],
                    system_resources.get('memory', {}).get('status') in ['normal', 'warning'],
                    system_resources.get('disk', {}).get('status') in ['normal', 'warning']
                ]) else 'unhealthy',
                'processing_pipeline': 'healthy' if all(
                    status['status'] in ['healthy', 'idle']
                    for status in pipeline_status.values()
                ) else 'degraded',
                'alerting_system': 'healthy' if alert_summary['active_alerts_count'] == 0 else 'degraded'
            },
            'last_updated': datetime.utcnow().isoformat()
        }


# Global dashboard provider
dashboard = DashboardDataProvider()


# API endpoint functions
def get_dashboard_overview():
    """Get dashboard overview data."""
    return dashboard.get_overview_metrics()


def get_pipeline_status():
    """Get processing pipeline status."""
    return dashboard.get_processing_pipeline_status()


def get_quality_metrics():
    """Get data quality metrics."""
    return dashboard.get_data_quality_metrics()


def get_system_status():
    """Get system resource status."""
    return dashboard.get_system_resource_metrics()


def get_alerts_dashboard():
    """Get alerts dashboard data."""
    return dashboard.get_alert_summary()


def get_performance_dashboard(hours: int = 24):
    """Get performance trends dashboard."""
    return dashboard.get_performance_trends(hours)


def get_health_status():
    """Get comprehensive health status."""
    return dashboard.get_health_check_status()


def get_metrics_export(format: str = 'json'):
    """Get metrics in specified format."""
    if format == 'prometheus':
        return get_prometheus_metrics()
    else:
        return get_metrics_summary()
