"""Monitoring dashboard for Airtable to Supabase migration."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from .metrics_collector import MetricsCollector, AlertSeverity
from ..clients.airtable import AirtableClient
from ..clients.supabase import SupabaseClient
from ..dal.hybrid_data_access import HybridDataAccessLayer
from ..migration.sync_service import AirtableSupabaseSyncService

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetric:
    """Dashboard metric display."""
    name: str
    value: Any
    unit: str = ""
    trend: str = "stable"  # up, down, stable
    status: str = "normal"  # normal, warning, critical


@dataclass
class SystemOverview:
    """System overview data."""
    timestamp: datetime
    overall_health: bool
    sync_status: str
    data_sources: Dict[str, bool]
    active_alerts: int
    error_rate: float
    average_latency: float
    data_consistency: float


class MonitoringDashboard:
    """Real-time monitoring dashboard for migration system."""
    
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        hybrid_dal: Optional[HybridDataAccessLayer] = None,
        sync_service: Optional[AirtableSupabaseSyncService] = None,
        refresh_interval: int = 30
    ):
        """Initialize monitoring dashboard.
        
        Args:
            metrics_collector: Metrics collector instance
            hybrid_dal: Hybrid DAL instance
            sync_service: Sync service instance
            refresh_interval: Dashboard refresh interval in seconds
        """
        self.metrics = metrics_collector
        self.dal = hybrid_dal
        self.sync_service = sync_service
        self.refresh_interval = refresh_interval
        
        # Dashboard state
        self.is_running = False
        self.dashboard_task: Optional[asyncio.Task] = None
        self.last_update = datetime.utcnow()
        
        # Cached dashboard data
        self.system_overview: Optional[SystemOverview] = None
        self.key_metrics: List[DashboardMetric] = []
        self.sync_progress: Dict[str, Any] = {}
        self.performance_stats: Dict[str, Any] = {}
        
    async def start(self):
        """Start the monitoring dashboard."""
        if self.is_running:
            logger.warning("Dashboard is already running")
            return
            
        self.is_running = True
        logger.info("Starting monitoring dashboard")
        
        # Start refresh loop
        self.dashboard_task = asyncio.create_task(self._refresh_loop())
        
        # Initial data load
        await self.refresh()
        
    async def stop(self):
        """Stop the monitoring dashboard."""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.info("Stopping monitoring dashboard")
        
        if self.dashboard_task:
            self.dashboard_task.cancel()
            try:
                await self.dashboard_task
            except asyncio.CancelledError:
                pass
                
    async def _refresh_loop(self):
        """Main dashboard refresh loop."""
        while self.is_running:
            try:
                await self.refresh()
                await asyncio.sleep(self.refresh_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dashboard refresh error: {e}")
                await asyncio.sleep(self.refresh_interval)
                
    async def refresh(self):
        """Refresh dashboard data."""
        try:
            # Update system overview
            self.system_overview = await self._get_system_overview()
            
            # Update key metrics
            self.key_metrics = await self._get_key_metrics()
            
            # Update sync progress
            self.sync_progress = await self._get_sync_progress()
            
            # Update performance stats
            self.performance_stats = await self._get_performance_stats()
            
            self.last_update = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to refresh dashboard: {e}")
            
    async def _get_system_overview(self) -> SystemOverview:
        """Get system overview data."""
        # Get health status
        health = self.metrics.get_overall_health()
        
        # Get sync status
        sync_status = "stopped"
        if self.sync_service:
            status = await self.sync_service.get_sync_status()
            sync_status = "running" if status.get("is_running") else "stopped"
            
        # Check data source availability
        data_sources = {"airtable": False, "supabase": False, "cache": False}
        
        if self.dal:
            health_check = await self.dal.health_check()
            data_sources.update(health_check)
            
        # Get metrics summary
        summary = self.metrics.get_metrics_summary(60)
        
        return SystemOverview(
            timestamp=datetime.utcnow(),
            overall_health=health["healthy"],
            sync_status=sync_status,
            data_sources=data_sources,
            active_alerts=health["active_alerts"],
            error_rate=summary.get("error_rate", 0),
            average_latency=self._calculate_average_latency(summary),
            data_consistency=self._calculate_overall_consistency()
        )
        
    async def _get_key_metrics(self) -> List[DashboardMetric]:
        """Get key dashboard metrics."""
        metrics = []
        
        # Get DAL metrics if available
        if self.dal:
            dal_metrics = self.dal.get_metrics()
            
            # Request distribution
            total_requests = dal_metrics.get("total_requests", 0)
            if total_requests > 0:
                metrics.append(
                    DashboardMetric(
                        name="Supabase Usage",
                        value=f"{dal_metrics.get('supabase_usage_rate', 0) * 100:.1f}",
                        unit="%",
                        trend="up" if dal_metrics.get('supabase_usage_rate', 0) > 0.5 else "down"
                    )
                )
                
                metrics.append(
                    DashboardMetric(
                        name="Cache Hit Rate",
                        value=f"{dal_metrics.get('cache_hit_rate', 0) * 100:.1f}",
                        unit="%",
                        status="normal" if dal_metrics.get('cache_hit_rate', 0) > 0.8 else "warning"
                    )
                )
                
        # Sync metrics
        if self.sync_service:
            sync_status = await self.sync_service.get_sync_status()
            
            metrics.append(
                DashboardMetric(
                    name="Sync Queue Size",
                    value=sync_status.get("queue_size", 0),
                    unit="items",
                    status=self._get_queue_status(sync_status.get("queue_size", 0))
                )
            )
            
        # Error metrics
        summary = self.metrics.get_metrics_summary(60)
        error_rate = summary.get("error_rate", 0)
        
        metrics.append(
            DashboardMetric(
                name="Error Rate",
                value=f"{error_rate * 100:.2f}",
                unit="%",
                status="critical" if error_rate > 0.05 else ("warning" if error_rate > 0.01 else "normal")
            )
        )
        
        # Active alerts
        active_alerts = len(self.metrics.get_active_alerts())
        metrics.append(
            DashboardMetric(
                name="Active Alerts",
                value=active_alerts,
                unit="",
                status="critical" if active_alerts > 5 else ("warning" if active_alerts > 0 else "normal")
            )
        )
        
        return metrics
        
    async def _get_sync_progress(self) -> Dict[str, Any]:
        """Get sync progress for each table."""
        progress = {}
        
        # Get sync status for each table
        tables = [
            "parties", "members", "bills", "policy_categories",
            "meetings", "speeches", "votes", "issues"
        ]
        
        for table in tables:
            try:
                # Get last sync status from Supabase
                if hasattr(self, 'supabase'):
                    status = await self.supabase.get_last_sync_status(table)
                    
                    if status:
                        progress[table] = {
                            "last_sync": status.get("last_sync_at"),
                            "status": status.get("status"),
                            "records_processed": status.get("records_processed", 0),
                            "sync_mode": status.get("sync_mode"),
                        }
                        
                        # Calculate sync lag
                        if status.get("last_sync_at"):
                            last_sync = datetime.fromisoformat(status["last_sync_at"])
                            lag = (datetime.utcnow() - last_sync).total_seconds()
                            progress[table]["lag_seconds"] = lag
                            
                            # Update metric
                            self.metrics.update_sync_lag(table, lag)
                            
            except Exception as e:
                logger.error(f"Failed to get sync progress for {table}: {e}")
                
        return progress
        
    async def _get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        summary = self.metrics.get_metrics_summary(60)
        
        stats = {
            "average_latencies": summary.get("average_latencies", {}),
            "sync_statistics": summary.get("sync_statistics", {}),
            "total_metrics": summary.get("total_metrics", 0),
            "time_window_minutes": summary.get("time_window_minutes", 60),
        }
        
        # Add percentile latencies if available
        # This would require more sophisticated metric tracking
        
        return stats
        
    def _calculate_average_latency(self, summary: Dict[str, Any]) -> float:
        """Calculate overall average latency."""
        latencies = summary.get("average_latencies", {})
        
        if not latencies:
            return 0
            
        total = sum(latencies.values())
        return total / len(latencies)
        
    def _calculate_overall_consistency(self) -> float:
        """Calculate overall data consistency score."""
        # This would aggregate consistency scores from all tables
        # For now, return a placeholder
        return 0.95
        
    def _get_queue_status(self, queue_size: int) -> str:
        """Determine queue status based on size."""
        if queue_size > 5000:
            return "critical"
        elif queue_size > 1000:
            return "warning"
        return "normal"
        
    # =====================================================
    # Dashboard API Methods
    # =====================================================
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data for API/UI."""
        return {
            "last_update": self.last_update.isoformat(),
            "system_overview": asdict(self.system_overview) if self.system_overview else {},
            "key_metrics": [asdict(m) for m in self.key_metrics],
            "sync_progress": self.sync_progress,
            "performance_stats": self.performance_stats,
            "alerts": [
                {
                    "name": alert.name,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat(),
                }
                for alert in self.metrics.get_active_alerts()
            ]
        }
        
    def get_metric_history(
        self,
        metric_name: str,
        time_window_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        history = []
        for point in self.metrics.metrics_buffer:
            if point.name == metric_name and point.timestamp > cutoff_time:
                history.append({
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "labels": point.labels,
                })
                
        return history
        
    def get_alert_history(
        self,
        severity_filter: Optional[AlertSeverity] = None,
        include_resolved: bool = False
    ) -> List[Dict[str, Any]]:
        """Get alert history."""
        alerts = []
        
        for alert in self.metrics.alerts:
            if not include_resolved and alert.resolved:
                continue
                
            if severity_filter and alert.severity != severity_filter:
                continue
                
            alerts.append({
                "name": alert.name,
                "message": alert.message,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "metadata": alert.metadata,
            })
            
        return alerts
        
    async def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check."""
        health_results = {}
        
        # Check Airtable
        try:
            if hasattr(self, 'airtable'):
                airtable_healthy = await self.airtable.health_check()
                health_results["airtable"] = {
                    "healthy": airtable_healthy,
                    "message": "Connected" if airtable_healthy else "Connection failed"
                }
                
                self.metrics.update_health_status(
                    "airtable",
                    airtable_healthy,
                    health_results["airtable"]["message"]
                )
        except Exception as e:
            health_results["airtable"] = {
                "healthy": False,
                "message": str(e)
            }
            
        # Check Supabase
        try:
            if hasattr(self, 'supabase'):
                supabase_healthy = await self.supabase.health_check()
                health_results["supabase"] = {
                    "healthy": supabase_healthy,
                    "message": "Connected" if supabase_healthy else "Connection failed"
                }
                
                self.metrics.update_health_status(
                    "supabase",
                    supabase_healthy,
                    health_results["supabase"]["message"]
                )
        except Exception as e:
            health_results["supabase"] = {
                "healthy": False,
                "message": str(e)
            }
            
        # Check sync service
        if self.sync_service:
            sync_status = await self.sync_service.get_sync_status()
            sync_healthy = sync_status.get("is_running", False)
            
            health_results["sync_service"] = {
                "healthy": sync_healthy,
                "message": f"Sync mode: {sync_status.get('mode', 'unknown')}"
            }
            
            self.metrics.update_health_status(
                "sync_service",
                sync_healthy,
                health_results["sync_service"]["message"]
            )
            
        return health_results
        
    def export_dashboard_json(self) -> str:
        """Export dashboard data as JSON."""
        return json.dumps(self.get_dashboard_data(), default=str, ensure_ascii=False)