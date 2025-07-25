"""
Monitoring API - System health, metrics, and alerting endpoints.
Provides comprehensive visibility into system status and performance.
"""

import logging
import os

# Import the monitoring systems
import sys
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from monitoring.error_recovery_system import error_recovery_system
from monitoring.monitoring_alerting_system import monitoring_system
from pydantic import BaseModel, Field, validator

from ..security.validation import InputValidator

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ingest-worker", "src")
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["System Monitoring"])


# Request/Response Models
class AlertFilterRequest(BaseModel):
    """Request to filter alerts."""

    severity: str | None = None
    component: str | None = None
    status: str | None = None
    hours_back: int = Field(24, ge=1, le=168)  # 1 hour to 1 week

    @validator("severity")
    def validate_severity(self, v):
        if v and v not in ["critical", "high", "medium", "low", "info"]:
            raise ValueError("Invalid severity level")
        return v

    @validator("status")
    def validate_status(self, v):
        if v and v not in ["active", "resolved", "suppressed"]:
            raise ValueError("Invalid alert status")
        return v


class MetricsQueryRequest(BaseModel):
    """Request to query metrics."""

    metric_names: list[str] | None = None
    period_minutes: int = Field(60, ge=5, le=1440)  # 5 minutes to 24 hours
    tags: dict[str, str] | None = None


class HealthCheckRequest(BaseModel):
    """Request to trigger health checks."""

    components: list[str] | None = None
    force_refresh: bool = False


# Dependencies
async def get_monitoring_system():
    """Get monitoring system instance."""
    return monitoring_system


async def get_error_recovery_system():
    """Get error recovery system instance."""
    return error_recovery_system


# Health Check Endpoints
@router.get("/health")
async def get_system_health(monitoring_sys=Depends(get_monitoring_system)):
    """Get overall system health status."""
    try:
        health_results = await monitoring_sys.health_checker.run_all_checks()
        overall_status = monitoring_sys.health_checker.get_overall_status(
            health_results
        )

        return {
            "success": True,
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "components": {
                name: {
                    "status": result.status.value,
                    "response_time_ms": result.response_time_ms,
                    "error_message": result.error_message,
                }
                for name, result in health_results.items()
            },
        }

    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system health")


@router.post("/health/check")
async def trigger_health_checks(
    request: HealthCheckRequest,
    background_tasks: BackgroundTasks,
    monitoring_sys=Depends(get_monitoring_system),
):
    """Trigger health checks for specific components or all components."""
    try:
        if request.components:
            # Check specific components
            results = {}
            for component in request.components:
                component = InputValidator.sanitize_string(component, 100)
                result = await monitoring_sys.health_checker.run_check(component)
                results[component] = result.to_dict()
        else:
            # Check all components
            if request.force_refresh or not monitoring_sys.health_checker.check_results:
                results = await monitoring_sys.health_checker.run_all_checks()
                results = {name: result.to_dict() for name, result in results.items()}
            else:
                # Return cached results
                results = {
                    name: result.to_dict()
                    for name, result in monitoring_sys.health_checker.check_results.items()
                }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "components_checked": len(results),
            "results": results,
        }

    except Exception as e:
        logger.error(f"Failed to trigger health checks: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger health checks")


@router.get("/health/{component}")
async def get_component_health(
    component: str, monitoring_sys=Depends(get_monitoring_system)
):
    """Get health status for a specific component."""
    try:
        component = InputValidator.sanitize_string(component, 100)

        # Check if component exists
        if component not in monitoring_sys.health_checker.health_checks:
            raise HTTPException(status_code=404, detail="Component not found")

        result = await monitoring_sys.health_checker.run_check(component)

        return {"success": True, "component": component, "result": result.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get component health for {component}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch component health")


# Metrics Endpoints
@router.get("/metrics")
async def get_system_metrics(
    period_minutes: int = Query(60, ge=5, le=1440),
    monitoring_sys=Depends(get_monitoring_system),
):
    """Get system metrics for the specified period."""
    try:
        metrics = monitoring_sys.metrics_collector.get_all_metrics(period_minutes)

        return {
            "success": True,
            "period_minutes": period_minutes,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "total_metrics": len(metrics),
        }

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system metrics")


@router.post("/metrics/query")
async def query_metrics(
    request: MetricsQueryRequest, monitoring_sys=Depends(get_monitoring_system)
):
    """Query specific metrics with filtering."""
    try:
        if request.metric_names:
            # Get specific metrics
            results = {}
            for metric_name in request.metric_names:
                metric_name = InputValidator.sanitize_string(metric_name, 100)
                summary = monitoring_sys.metrics_collector.get_metric_summary(
                    metric_name, request.period_minutes
                )
                if summary:
                    results[metric_name] = summary
        else:
            # Get all metrics
            results = monitoring_sys.metrics_collector.get_all_metrics(
                request.period_minutes
            )

        return {
            "success": True,
            "period_minutes": request.period_minutes,
            "timestamp": datetime.now().isoformat(),
            "metrics": results,
            "metric_count": len(results),
        }

    except Exception as e:
        logger.error(f"Failed to query metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to query metrics")


@router.get("/metrics/system")
async def get_system_resource_metrics(monitoring_sys=Depends(get_monitoring_system)):
    """Get current system resource metrics."""
    try:
        # Trigger system metrics collection
        await monitoring_sys.metrics_collector.collect_system_metrics()

        # Get latest system metrics
        system_metrics = {}
        metric_names = [
            "system.cpu.usage_percent",
            "system.memory.usage_percent",
            "system.memory.available_bytes",
            "system.disk.usage_percent",
            "system.disk.free_bytes",
        ]

        for metric_name in metric_names:
            summary = monitoring_sys.metrics_collector.get_metric_summary(
                metric_name, 5
            )  # Last 5 minutes
            if summary:
                system_metrics[metric_name] = summary

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "system_metrics": system_metrics,
        }

    except Exception as e:
        logger.error(f"Failed to get system resource metrics: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch system resource metrics"
        )


# Alert Endpoints
@router.get("/alerts")
async def get_alerts(
    severity: str | None = Query(None),
    component: str | None = Query(None),
    status: str = Query("active"),
    limit: int = Query(50, ge=1, le=200),
    monitoring_sys=Depends(get_monitoring_system),
):
    """Get alerts with optional filtering."""
    try:
        all_alerts = list(monitoring_sys.alert_manager.alerts.values())

        # Apply filters
        filtered_alerts = all_alerts

        if status:
            filtered_alerts = [
                alert for alert in filtered_alerts if alert.status == status
            ]

        if severity:
            filtered_alerts = [
                alert for alert in filtered_alerts if alert.severity.value == severity
            ]

        if component:
            component = InputValidator.sanitize_string(component, 100)
            filtered_alerts = [
                alert for alert in filtered_alerts if alert.component == component
            ]

        # Sort by triggered_at (newest first)
        filtered_alerts.sort(key=lambda x: x.triggered_at, reverse=True)

        # Apply limit
        limited_alerts = filtered_alerts[:limit]

        return {
            "success": True,
            "total_alerts": len(filtered_alerts),
            "returned_alerts": len(limited_alerts),
            "filters": {"severity": severity, "component": component, "status": status},
            "alerts": [alert.to_dict() for alert in limited_alerts],
        }

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@router.get("/alerts/{alert_id}")
async def get_alert_details(
    alert_id: str, monitoring_sys=Depends(get_monitoring_system)
):
    """Get details for a specific alert."""
    try:
        alert_id = InputValidator.sanitize_string(alert_id, 100)

        alert = monitoring_sys.alert_manager.alerts.get(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"success": True, "alert": alert.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert details for {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert details")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, monitoring_sys=Depends(get_monitoring_system)):
    """Resolve an active alert."""
    try:
        alert_id = InputValidator.sanitize_string(alert_id, 100)

        await monitoring_sys.alert_manager.resolve_alert(alert_id, "manual_api")

        return {
            "success": True,
            "message": f"Alert {alert_id} has been resolved",
            "alert_id": alert_id,
            "resolved_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.get("/alerts/statistics")
async def get_alert_statistics(monitoring_sys=Depends(get_monitoring_system)):
    """Get alert statistics and trends."""
    try:
        stats = monitoring_sys.alert_manager.get_alert_statistics()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
        }

    except Exception as e:
        logger.error(f"Failed to get alert statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert statistics")


# SLA Endpoints
@router.get("/sla")
async def get_sla_status(monitoring_sys=Depends(get_monitoring_system)):
    """Get SLA monitoring status."""
    try:
        sla_status = monitoring_sys.sla_monitor.get_sla_status()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "sla_status": sla_status,
        }

    except Exception as e:
        logger.error(f"Failed to get SLA status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch SLA status")


@router.get("/sla/violations")
async def get_sla_violations(monitoring_sys=Depends(get_monitoring_system)):
    """Get current SLA violations."""
    try:
        violations = monitoring_sys.sla_monitor.get_sla_violations()

        violation_data = []
        for violation in violations:
            violation_data.append(
                {
                    "name": violation.name,
                    "target_value": violation.target_value,
                    "current_value": violation.current_value,
                    "threshold_type": violation.threshold_type,
                    "measurement_period": violation.measurement_period,
                    "status": violation.status.value,
                    "last_updated": violation.last_updated.isoformat(),
                }
            )

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "violations_count": len(violations),
            "violations": violation_data,
        }

    except Exception as e:
        logger.error(f"Failed to get SLA violations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch SLA violations")


# Error Recovery Endpoints
@router.get("/error-recovery")
async def get_error_recovery_status(
    error_recovery_sys=Depends(get_error_recovery_system),
):
    """Get error recovery system status."""
    try:
        status = error_recovery_sys.get_system_status()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "error_recovery_status": status,
        }

    except Exception as e:
        logger.error(f"Failed to get error recovery status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch error recovery status"
        )


@router.get("/error-recovery/circuit-breakers")
async def get_circuit_breaker_status(
    error_recovery_sys=Depends(get_error_recovery_system),
):
    """Get circuit breaker statuses."""
    try:
        circuit_statuses = {}
        for name, breaker in error_recovery_sys.circuit_breakers.items():
            circuit_statuses[name] = breaker.get_status()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "circuit_breakers": circuit_statuses,
            "total_breakers": len(circuit_statuses),
        }

    except Exception as e:
        logger.error(f"Failed to get circuit breaker status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch circuit breaker status"
        )


@router.get("/error-recovery/dead-letter-queue")
async def get_dlq_status(error_recovery_sys=Depends(get_error_recovery_system)):
    """Get dead letter queue status."""
    try:
        dlq_stats = error_recovery_sys.dead_letter_queue.get_statistics()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "dlq_statistics": dlq_stats,
        }

    except Exception as e:
        logger.error(f"Failed to get DLQ status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch DLQ status")


@router.post("/error-recovery/process-dlq")
async def process_dlq_retries(
    background_tasks: BackgroundTasks,
    error_recovery_sys=Depends(get_error_recovery_system),
):
    """Trigger processing of dead letter queue retries."""
    try:
        # Process DLQ retries in background
        background_tasks.add_task(error_recovery_sys.process_dlq_retries)

        return {
            "success": True,
            "message": "DLQ processing triggered",
            "triggered_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to trigger DLQ processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger DLQ processing")


# Dashboard Endpoint
@router.get("/dashboard")
async def get_monitoring_dashboard(monitoring_sys=Depends(get_monitoring_system)):
    """Get comprehensive monitoring dashboard data."""
    try:
        dashboard_data = await monitoring_sys.get_dashboard_data()

        return {"success": True, "dashboard": dashboard_data}

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data")


# System Control Endpoints
@router.post("/system/monitoring/enable")
async def enable_monitoring(monitoring_sys=Depends(get_monitoring_system)):
    """Enable system monitoring."""
    try:
        monitoring_sys.monitoring_enabled = True

        return {
            "success": True,
            "message": "System monitoring enabled",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to enable monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to enable monitoring")


@router.post("/system/monitoring/disable")
async def disable_monitoring(monitoring_sys=Depends(get_monitoring_system)):
    """Disable system monitoring."""
    try:
        monitoring_sys.monitoring_enabled = False

        return {
            "success": True,
            "message": "System monitoring disabled",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to disable monitoring: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable monitoring")


@router.post("/system/full-check")
async def trigger_full_monitoring_cycle(
    background_tasks: BackgroundTasks, monitoring_sys=Depends(get_monitoring_system)
):
    """Trigger a full monitoring cycle."""
    try:
        # Run full monitoring cycle in background
        background_tasks.add_task(monitoring_sys.run_full_monitoring_cycle)

        return {
            "success": True,
            "message": "Full monitoring cycle triggered",
            "triggered_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to trigger full monitoring cycle: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to trigger full monitoring cycle"
        )


# Health check for monitoring API itself
@router.get("/health-check")
async def monitoring_api_health_check(
    monitoring_sys=Depends(get_monitoring_system),
    error_recovery_sys=Depends(get_error_recovery_system),
):
    """Health check for the monitoring API itself."""
    try:
        monitoring_healthy = await monitoring_sys.health_check()
        error_recovery_healthy = await error_recovery_sys.health_check()

        overall_healthy = monitoring_healthy and error_recovery_healthy

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": {
                "monitoring_system": "healthy" if monitoring_healthy else "unhealthy",
                "error_recovery_system": (
                    "healthy" if error_recovery_healthy else "unhealthy"
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Monitoring API health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
