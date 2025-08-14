"""Hybrid API routes for Airtable to Supabase migration."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from shared.dal.hybrid_data_access import HybridDataAccessLayer
from shared.migration.sync_service import AirtableSupabaseSyncService, SyncMode
from shared.monitoring.metrics_collector import MetricsCollector
from shared.monitoring.dashboard import MonitoringDashboard
from shared.migration.rollback_manager import RollbackManager, RollbackType

logger = logging.getLogger(__name__)

# Initialize components (these would be dependency injected in production)
hybrid_dal = HybridDataAccessLayer()
sync_service = AirtableSupabaseSyncService()
metrics_collector = MetricsCollector()
monitoring_dashboard = MonitoringDashboard(metrics_collector, hybrid_dal, sync_service)
rollback_manager = RollbackManager()

# Create router
router = APIRouter(prefix="/api/v2", tags=["hybrid"])


# =====================================================
# Request/Response Models
# =====================================================

class BillResponse(BaseModel):
    """Bill response model."""
    id: str
    bill_number: str
    title: str
    status: str
    category: Optional[str] = None
    submitted_date: Optional[str] = None
    data_source: str = Field(description="Source of data (airtable/supabase/cache)")


class MemberResponse(BaseModel):
    """Member response model."""
    id: str
    name: str
    house: str
    party: Optional[str] = None
    constituency: Optional[str] = None
    data_source: str


class PolicyCategoryResponse(BaseModel):
    """Policy category response model."""
    id: str
    cap_code: str
    layer: str
    title_ja: str
    title_en: Optional[str] = None
    parent_id: Optional[str] = None
    data_source: str


class SyncRequest(BaseModel):
    """Sync operation request."""
    tables: Optional[List[str]] = None
    mode: str = "incremental"
    force: bool = False


class RollbackRequest(BaseModel):
    """Rollback operation request."""
    rollback_point_id: str
    tables: Optional[List[str]] = None
    confirm: bool = False


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    components: Dict[str, Any]
    metrics: Dict[str, Any]


# =====================================================
# Data Access Endpoints
# =====================================================

@router.get("/bills", response_model=List[BillResponse])
async def get_bills(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    no_cache: bool = Query(False, description="Bypass cache")
):
    """Get bills using hybrid data access layer."""
    start_time = datetime.utcnow()
    
    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
            
        # Get bills from hybrid DAL
        bills = await hybrid_dal.get_bills(
            filters=filters,
            limit=limit,
            offset=offset,
            use_cache=not no_cache
        )
        
        # Determine data source
        dal_metrics = hybrid_dal.get_metrics()
        if dal_metrics["cache_hits"] > 0:
            data_source = "cache"
        elif dal_metrics["supabase_hits"] > dal_metrics["airtable_hits"]:
            data_source = "supabase"
        else:
            data_source = "airtable"
            
        # Convert to response model
        response = [
            BillResponse(
                id=bill.get("id", bill.get("airtable_id", "")),
                bill_number=bill.get("bill_number", ""),
                title=bill.get("title", ""),
                status=bill.get("status", ""),
                category=bill.get("category"),
                submitted_date=bill.get("submitted_date"),
                data_source=data_source
            )
            for bill in bills
        ]
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        metrics_collector.record_api_request(
            service="hybrid_api",
            operation="get_bills",
            status="success",
            duration=duration
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get bills: {e}")
        metrics_collector.record_error("hybrid_api", "get_bills", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/members", response_model=List[MemberResponse])
async def get_members(
    house: Optional[str] = Query(None, description="Filter by house"),
    party: Optional[str] = Query(None, description="Filter by party"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get members using hybrid data access layer."""
    start_time = datetime.utcnow()
    
    try:
        # Build filters
        filters = {}
        if house:
            filters["house"] = house
        if party:
            filters["party_id"] = party
            
        # Get members from hybrid DAL
        members = await hybrid_dal.get_members(
            filters=filters,
            limit=limit,
            offset=offset
        )
        
        # Determine data source
        dal_metrics = hybrid_dal.get_metrics()
        if dal_metrics["cache_hits"] > 0:
            data_source = "cache"
        elif dal_metrics["supabase_hits"] > dal_metrics["airtable_hits"]:
            data_source = "supabase"
        else:
            data_source = "airtable"
            
        # Convert to response model
        response = [
            MemberResponse(
                id=member.get("id", member.get("airtable_id", "")),
                name=member.get("name", ""),
                house=member.get("house", ""),
                party=member.get("party"),
                constituency=member.get("constituency"),
                data_source=data_source
            )
            for member in members
        ]
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        metrics_collector.record_api_request(
            service="hybrid_api",
            operation="get_members",
            status="success",
            duration=duration
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get members: {e}")
        metrics_collector.record_error("hybrid_api", "get_members", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy-categories", response_model=List[PolicyCategoryResponse])
async def get_policy_categories(
    layer: Optional[str] = Query(None, description="Filter by layer (L1/L2/L3)"),
    parent_id: Optional[str] = Query(None, description="Filter by parent category")
):
    """Get policy categories using hybrid data access layer."""
    start_time = datetime.utcnow()
    
    try:
        # Get categories from hybrid DAL
        categories = await hybrid_dal.get_policy_categories(
            layer=layer,
            parent_id=parent_id
        )
        
        # Determine data source
        dal_metrics = hybrid_dal.get_metrics()
        if dal_metrics["cache_hits"] > 0:
            data_source = "cache"
        elif dal_metrics["supabase_hits"] > dal_metrics["airtable_hits"]:
            data_source = "supabase"
        else:
            data_source = "airtable"
            
        # Convert to response model
        response = [
            PolicyCategoryResponse(
                id=cat.get("id", cat.get("airtable_id", "")),
                cap_code=cat.get("cap_code", ""),
                layer=cat.get("layer", ""),
                title_ja=cat.get("title_ja", ""),
                title_en=cat.get("title_en"),
                parent_id=cat.get("parent_id"),
                data_source=data_source
            )
            for cat in categories
        ]
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        metrics_collector.record_api_request(
            service="hybrid_api",
            operation="get_policy_categories",
            status="success",
            duration=duration
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get policy categories: {e}")
        metrics_collector.record_error("hybrid_api", "get_policy_categories", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Sync Management Endpoints
# =====================================================

@router.post("/sync/start")
async def start_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks
):
    """Start synchronization service."""
    try:
        if request.tables:
            sync_service.config.tables_to_sync = request.tables
            
        sync_service.config.mode = SyncMode(request.mode)
        
        # Start sync in background
        background_tasks.add_task(sync_service.start)
        
        return {
            "status": "started",
            "mode": request.mode,
            "tables": request.tables or "all",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/stop")
async def stop_sync():
    """Stop synchronization service."""
    try:
        await sync_service.stop()
        
        return {
            "status": "stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status")
async def get_sync_status():
    """Get synchronization status."""
    try:
        status = await sync_service.get_sync_status()
        
        return {
            "is_running": status.get("is_running"),
            "mode": status.get("mode"),
            "last_sync_times": status.get("last_sync_times"),
            "queue_size": status.get("queue_size"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/table/{table_name}")
async def sync_table(
    table_name: str,
    mode: str = Query("incremental", description="Sync mode"),
    background_tasks: BackgroundTasks
):
    """Sync a specific table."""
    try:
        # Sync table in background
        background_tasks.add_task(
            sync_service.sync_table,
            table_name,
            SyncMode(mode)
        )
        
        return {
            "status": "started",
            "table": table_name,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to sync table {table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Monitoring Endpoints
# =====================================================

@router.get("/monitoring/dashboard")
async def get_dashboard():
    """Get monitoring dashboard data."""
    try:
        dashboard_data = monitoring_dashboard.get_dashboard_data()
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/metrics")
async def get_metrics(
    time_window: int = Query(60, description="Time window in minutes")
):
    """Get metrics summary."""
    try:
        metrics_summary = metrics_collector.get_metrics_summary(time_window)
        return metrics_summary
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/alerts")
async def get_alerts():
    """Get active alerts."""
    try:
        alerts = metrics_collector.get_active_alerts()
        
        return {
            "active_alerts": len(alerts),
            "alerts": [
                {
                    "name": alert.name,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/health", response_model=HealthResponse)
async def health_check():
    """Perform health check."""
    try:
        # Run health checks
        health_results = await monitoring_dashboard.run_health_check()
        
        # Get metrics
        dal_metrics = hybrid_dal.get_metrics() if hybrid_dal else {}
        
        # Overall status
        all_healthy = all(h.get("healthy", False) for h in health_results.values())
        
        return HealthResponse(
            status="healthy" if all_healthy else "degraded",
            timestamp=datetime.utcnow().isoformat(),
            components=health_results,
            metrics={
                "dal_metrics": dal_metrics,
                "active_alerts": len(metrics_collector.get_active_alerts())
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            components={},
            metrics={"error": str(e)}
        )


# =====================================================
# Rollback Management Endpoints
# =====================================================

@router.post("/rollback/create")
async def create_rollback_point(
    phase: int = Query(..., description="Migration phase"),
    description: str = Query(..., description="Rollback point description"),
    rollback_type: str = Query("full", description="Type of rollback"),
    background_tasks: BackgroundTasks
):
    """Create a new rollback point."""
    try:
        # Create rollback point in background
        background_tasks.add_task(
            rollback_manager.create_rollback_point,
            phase,
            description,
            RollbackType(rollback_type)
        )
        
        return {
            "status": "creating",
            "phase": phase,
            "description": description,
            "type": rollback_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create rollback point: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rollback/list")
async def list_rollback_points(
    phase: Optional[int] = Query(None, description="Filter by phase")
):
    """List available rollback points."""
    try:
        points = rollback_manager.list_rollback_points(phase=phase)
        
        return {
            "count": len(points),
            "rollback_points": [
                {
                    "id": point.id,
                    "phase": point.phase,
                    "timestamp": point.timestamp.isoformat(),
                    "description": point.description,
                    "type": point.rollback_type.value,
                    "is_valid": point.is_valid
                }
                for point in points
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list rollback points: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback/execute")
async def execute_rollback(
    request: RollbackRequest,
    background_tasks: BackgroundTasks
):
    """Execute rollback to a specific point."""
    try:
        if not request.confirm:
            raise HTTPException(
                status_code=400,
                detail="Rollback must be confirmed with confirm=true"
            )
            
        # Validate rollback point
        if not rollback_manager.validate_rollback_point(request.rollback_point_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid or corrupted rollback point"
            )
            
        # Execute rollback in background
        background_tasks.add_task(
            rollback_manager.execute_rollback,
            request.rollback_point_id,
            request.tables
        )
        
        return {
            "status": "executing",
            "rollback_point_id": request.rollback_point_id,
            "tables": request.tables or "all",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# Cache Management Endpoints
# =====================================================

@router.post("/cache/invalidate")
async def invalidate_cache(
    pattern: str = Query("*", description="Cache key pattern to invalidate")
):
    """Invalidate cache entries."""
    try:
        await hybrid_dal.invalidate_cache(pattern)
        
        return {
            "status": "invalidated",
            "pattern": pattern,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        dal_metrics = hybrid_dal.get_metrics()
        
        total_cache_requests = dal_metrics.get("cache_hits", 0) + dal_metrics.get("cache_misses", 0)
        hit_rate = dal_metrics.get("cache_hit_rate", 0)
        
        return {
            "total_requests": total_cache_requests,
            "hits": dal_metrics.get("cache_hits", 0),
            "misses": dal_metrics.get("cache_misses", 0),
            "hit_rate": f"{hit_rate * 100:.1f}%",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))