"""
Batch Job Management API - Monitor and control batch processing jobs.
Provides endpoints for job status, manual triggers, and configuration.
"""

import logging
import os

# Import the batch processing system
import sys
from datetime import datetime, time, timedelta
from typing import Any

from batch.issue_relationship_batch import IssueRelationshipBatchProcessor
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

from ..security.validation import InputValidator

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ingest-worker", "src")
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["Batch Management"])


# Request/Response Models
class BatchJobTriggerRequest(BaseModel):
    """Request to manually trigger a batch job."""

    job_id: str
    force_run: bool = False
    custom_params: dict[str, Any] | None = None

    @validator("job_id")
    def validate_job_id(self, v):
        if not v or not v.strip():
            raise ValueError("Job ID cannot be empty")
        return InputValidator.sanitize_string(v, 100)


class BatchJobConfigUpdateRequest(BaseModel):
    """Request to update batch job configuration."""

    enabled: bool | None = None
    schedule_time: str | None = None  # Format: "HH:MM"
    batch_size: int | None = Field(None, ge=1, le=1000)
    max_concurrent_tasks: int | None = Field(None, ge=1, le=20)
    timeout_minutes: int | None = Field(None, ge=5, le=720)
    notification_on_success: bool | None = None
    notification_on_failure: bool | None = None

    @validator("schedule_time")
    def validate_schedule_time(self, v):
        if v is not None:
            try:
                hour, minute = map(int, v.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time format")
                return v
            except (ValueError, AttributeError):
                raise ValueError("Schedule time must be in HH:MM format")
        return v


# Dependencies
async def get_batch_processor() -> IssueRelationshipBatchProcessor:
    """Get batch processor instance."""
    return IssueRelationshipBatchProcessor()


# Batch Job Status Endpoints
@router.get("/jobs")
async def get_all_batch_jobs(
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Get status of all batch jobs."""
    try:
        job_statuses = await batch_processor.get_all_job_statuses()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": job_statuses,
        }

    except Exception as e:
        logger.error(f"Failed to get batch job statuses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job statuses")


@router.get("/jobs/{job_id}")
async def get_batch_job_status(
    job_id: str,
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Get status of a specific batch job."""
    try:
        job_id = InputValidator.sanitize_string(job_id, 100)

        job_status = await batch_processor.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")

        return {"success": True, "job_id": job_id, "status": job_status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")


@router.get("/jobs/{job_id}/history")
async def get_job_execution_history(
    job_id: str,
    limit: int = Query(10, ge=1, le=100),
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Get execution history for a specific job."""
    try:
        job_id = InputValidator.sanitize_string(job_id, 100)

        # Get job history from batch processor
        all_statuses = await batch_processor.get_all_job_statuses()
        job_history = []

        # Filter history for specific job
        for execution in all_statuses.get("recent_completed_jobs", []):
            if execution.get("job_id") == job_id:
                job_history.append(execution)

        # Sort by started_at and limit
        job_history.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        limited_history = job_history[:limit]

        return {
            "success": True,
            "job_id": job_id,
            "history": limited_history,
            "total_executions": len(job_history),
        }

    except Exception as e:
        logger.error(f"Failed to get job history for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job history")


# Job Control Endpoints
@router.post("/jobs/{job_id}/trigger")
async def trigger_batch_job(
    job_id: str,
    request: BatchJobTriggerRequest,
    background_tasks: BackgroundTasks,
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Manually trigger a batch job."""
    try:
        job_id = InputValidator.sanitize_string(job_id, 100)

        # Validate job exists
        configured_jobs = [config.job_id for config in batch_processor.default_jobs]
        if job_id not in configured_jobs:
            raise HTTPException(status_code=404, detail="Job configuration not found")

        # Check if job is already running (unless force_run is True)
        if not request.force_run:
            current_status = await batch_processor.get_job_status(job_id)
            if current_status and current_status.get("status") == "running":
                raise HTTPException(status_code=409, detail="Job is already running")

        # Find job configuration
        job_config = None
        for config in batch_processor.default_jobs:
            if config.job_id == job_id:
                job_config = config
                break

        if not job_config:
            raise HTTPException(status_code=404, detail="Job configuration not found")

        # Trigger job in background
        background_tasks.add_task(batch_processor._execute_batch_job, job_config)

        logger.info(f"Manually triggered batch job: {job_id}")

        return {
            "success": True,
            "message": f"Job {job_id} has been triggered",
            "job_id": job_id,
            "triggered_at": datetime.now().isoformat(),
            "force_run": request.force_run,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger job")


@router.post("/jobs/{job_id}/cancel")
async def cancel_batch_job(
    job_id: str,
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Cancel a running batch job."""
    try:
        job_id = InputValidator.sanitize_string(job_id, 100)

        # Check if job is running
        current_status = await batch_processor.get_job_status(job_id)
        if not current_status or current_status.get("status") != "running":
            raise HTTPException(status_code=400, detail="Job is not currently running")

        # Find and cancel the job
        execution_id = current_status.get("execution_id")
        if execution_id in batch_processor.active_jobs:
            execution = batch_processor.active_jobs[execution_id]
            execution.status = "cancelled"
            execution.completed_at = datetime.now()

            # Move to history
            batch_processor.job_history.append(execution)
            del batch_processor.active_jobs[execution_id]

            logger.info(f"Cancelled batch job: {job_id}")

            return {
                "success": True,
                "message": f"Job {job_id} has been cancelled",
                "job_id": job_id,
                "cancelled_at": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=400, detail="Could not find active job execution"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel job")


# Configuration Management
@router.get("/jobs/{job_id}/config")
async def get_job_configuration(
    job_id: str,
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Get configuration for a specific job."""
    try:
        job_id = InputValidator.sanitize_string(job_id, 100)

        # Find job configuration
        for config in batch_processor.default_jobs:
            if config.job_id == job_id:
                return {
                    "success": True,
                    "job_id": job_id,
                    "configuration": {
                        "job_name": config.job_name,
                        "job_type": config.job_type.value,
                        "description": config.description,
                        "schedule_time": config.schedule_time.strftime("%H:%M"),
                        "timezone": config.timezone,
                        "enabled": config.enabled,
                        "batch_size": config.batch_size,
                        "max_concurrent_tasks": config.max_concurrent_tasks,
                        "timeout_minutes": config.timeout_minutes,
                        "retry_attempts": config.retry_attempts,
                        "retry_delay_seconds": config.retry_delay_seconds,
                        "notification_on_failure": config.notification_on_failure,
                        "notification_on_success": config.notification_on_success,
                        "alert_threshold_minutes": config.alert_threshold_minutes,
                        "keep_logs_days": config.keep_logs_days,
                    },
                }

        raise HTTPException(status_code=404, detail="Job configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job configuration for {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job configuration")


@router.patch("/jobs/{job_id}/config")
async def update_job_configuration(
    job_id: str,
    request: BatchJobConfigUpdateRequest,
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Update configuration for a specific job."""
    try:
        job_id = InputValidator.sanitize_string(job_id, 100)

        # Find job configuration
        job_config = None
        for config in batch_processor.default_jobs:
            if config.job_id == job_id:
                job_config = config
                break

        if not job_config:
            raise HTTPException(status_code=404, detail="Job configuration not found")

        # Update configuration fields
        updated_fields = []

        if request.enabled is not None:
            job_config.enabled = request.enabled
            updated_fields.append("enabled")

        if request.schedule_time is not None:
            hour, minute = map(int, request.schedule_time.split(":"))
            job_config.schedule_time = time(hour, minute)
            updated_fields.append("schedule_time")

        if request.batch_size is not None:
            job_config.batch_size = request.batch_size
            updated_fields.append("batch_size")

        if request.max_concurrent_tasks is not None:
            job_config.max_concurrent_tasks = request.max_concurrent_tasks
            updated_fields.append("max_concurrent_tasks")

        if request.timeout_minutes is not None:
            job_config.timeout_minutes = request.timeout_minutes
            updated_fields.append("timeout_minutes")

        if request.notification_on_success is not None:
            job_config.notification_on_success = request.notification_on_success
            updated_fields.append("notification_on_success")

        if request.notification_on_failure is not None:
            job_config.notification_on_failure = request.notification_on_failure
            updated_fields.append("notification_on_failure")

        logger.info(f"Updated job configuration for {job_id}: {updated_fields}")

        return {
            "success": True,
            "message": f"Job configuration updated for {job_id}",
            "job_id": job_id,
            "updated_fields": updated_fields,
            "updated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job configuration for {job_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update job configuration"
        )


# Scheduler Management
@router.get("/scheduler/status")
async def get_scheduler_status(
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Get batch job scheduler status."""
    try:
        return {
            "success": True,
            "scheduler_running": batch_processor.is_running,
            "active_jobs_count": len(batch_processor.active_jobs),
            "total_configured_jobs": len(batch_processor.default_jobs),
            "enabled_jobs_count": len(
                [config for config in batch_processor.default_jobs if config.enabled]
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scheduler status")


@router.post("/scheduler/start")
async def start_scheduler(
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Start the batch job scheduler."""
    try:
        if batch_processor.is_running:
            return {
                "success": False,
                "message": "Scheduler is already running",
                "scheduler_running": True,
            }

        await batch_processor.start_scheduler()

        return {
            "success": True,
            "message": "Batch job scheduler started",
            "scheduler_running": True,
            "started_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scheduler")


@router.post("/scheduler/stop")
async def stop_scheduler(
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Stop the batch job scheduler."""
    try:
        if not batch_processor.is_running:
            return {
                "success": False,
                "message": "Scheduler is not running",
                "scheduler_running": False,
            }

        await batch_processor.stop_scheduler()

        return {
            "success": True,
            "message": "Batch job scheduler stopped",
            "scheduler_running": False,
            "stopped_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop scheduler")


# Statistics and Monitoring
@router.get("/statistics")
async def get_batch_statistics(
    days: int = Query(7, ge=1, le=30),
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Get batch job statistics for the specified period."""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        # Analyze job history
        recent_executions = [
            execution
            for execution in batch_processor.job_history
            if execution.started_at and execution.started_at > cutoff_date
        ]

        statistics = {
            "period_days": days,
            "total_executions": len(recent_executions),
            "successful_executions": len(
                [e for e in recent_executions if e.status.value == "completed"]
            ),
            "failed_executions": len(
                [e for e in recent_executions if e.status.value == "failed"]
            ),
            "cancelled_executions": len(
                [e for e in recent_executions if e.status.value == "cancelled"]
            ),
            "average_duration_seconds": 0,
            "total_items_processed": sum(e.successful_items for e in recent_executions),
            "by_job_type": {},
            "by_job_id": {},
        }

        # Calculate average duration
        completed_executions = [e for e in recent_executions if e.duration_seconds]
        if completed_executions:
            statistics["average_duration_seconds"] = sum(
                e.duration_seconds for e in completed_executions
            ) / len(completed_executions)

        # Group by job type and job ID
        for execution in recent_executions:
            job_type = execution.job_config.job_type.value
            job_id = execution.job_config.job_id

            if job_type not in statistics["by_job_type"]:
                statistics["by_job_type"][job_type] = {"count": 0, "success_rate": 0}
            statistics["by_job_type"][job_type]["count"] += 1

            if job_id not in statistics["by_job_id"]:
                statistics["by_job_id"][job_id] = {"count": 0, "success_rate": 0}
            statistics["by_job_id"][job_id]["count"] += 1

        # Calculate success rates
        for job_type_stats in statistics["by_job_type"].values():
            job_type_executions = [
                e for e in recent_executions if e.job_config.job_type.value == job_type
            ]
            successful = len(
                [e for e in job_type_executions if e.status.value == "completed"]
            )
            job_type_stats["success_rate"] = (
                successful / len(job_type_executions) if job_type_executions else 0
            )

        for job_id_stats in statistics["by_job_id"].values():
            job_executions = [
                e for e in recent_executions if e.job_config.job_id == job_id
            ]
            successful = len(
                [e for e in job_executions if e.status.value == "completed"]
            )
            job_id_stats["success_rate"] = (
                successful / len(job_executions) if job_executions else 0
            )

        return {
            "success": True,
            "statistics": statistics,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get batch statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch batch statistics")


# Health Check
@router.get("/health")
async def batch_health_check(
    batch_processor: IssueRelationshipBatchProcessor = Depends(get_batch_processor),
):
    """Health check for batch processing system."""
    try:
        health_status = await batch_processor.health_check()

        return {
            "status": "healthy" if health_status else "unhealthy",
            "scheduler_running": batch_processor.is_running,
            "active_jobs": len(batch_processor.active_jobs),
            "dependencies_healthy": health_status,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Batch health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
