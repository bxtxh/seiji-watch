"""RQ-based task queue for batch processing."""

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis
from rq import Job, Queue, Worker
from rq.exceptions import NoSuchJobError

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TaskResult:
    """Task execution result."""
    success: bool
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    execution_time_ms: float | None = None


class TaskQueue:
    """RQ-based task queue with priority support."""

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_connection = redis.from_url(self.redis_url)

        # Create queues with different priorities
        self.queues = {
            TaskPriority.URGENT: Queue('urgent', connection=self.redis_connection),
            TaskPriority.HIGH: Queue('high', connection=self.redis_connection),
            TaskPriority.NORMAL: Queue('normal', connection=self.redis_connection),
            TaskPriority.LOW: Queue('low', connection=self.redis_connection)
        }

        # Default queue for backward compatibility
        self.default_queue = self.queues[TaskPriority.NORMAL]

    def enqueue_task(self, func: Callable, args: tuple = (), kwargs: dict = None,
                     priority: TaskPriority = TaskPriority.NORMAL,
                     job_timeout: str = "10m",
                     result_ttl: str = "24h",
                     description: str | None = None) -> str:
        """Enqueue a task with specified priority."""
        kwargs = kwargs or {}

        try:
            queue = self.queues[priority]
            job = queue.enqueue(
                func,
                *args,
                **kwargs,
                job_timeout=job_timeout,
                result_ttl=result_ttl,
                description=description or f"{func.__name__} task"
            )

            logger.info(f"Enqueued task {job.id} with priority {priority.value}")
            return job.id

        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            raise

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get job status and metadata."""
        try:
            job = Job.fetch(job_id, connection=self.redis_connection)

            return {
                "id": job.id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "description": job.description,
                "result": job.result,
                "exc_info": job.exc_info,
                "meta": job.meta
            }

        except NoSuchJobError:
            return {"id": job_id, "status": "not_found"}
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return {"id": job_id, "status": "error", "error": str(e)}

    def get_queue_stats(self) -> dict[str, Any]:
        """Get statistics for all queues."""
        stats = {}

        for priority, queue in self.queues.items():
            try:
                stats[priority.value] = {
                    "length": len(queue),
                    "name": queue.name,
                    "failed_jobs": queue.failed_job_registry.count,
                    "deferred_jobs": queue.deferred_job_registry.count,
                    "started_jobs": queue.started_job_registry.count,
                    "finished_jobs": queue.finished_job_registry.count
                }
            except Exception as e:
                logger.error(f"Failed to get stats for queue {priority.value}: {e}")
                stats[priority.value] = {"error": str(e)}

        return stats

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        try:
            job = Job.fetch(job_id, connection=self.redis_connection)
            job.cancel()
            logger.info(f"Cancelled job {job_id}")
            return True

        except NoSuchJobError:
            logger.warning(f"Job {job_id} not found for cancellation")
            return False
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    def clear_queue(self, priority: TaskPriority) -> int:
        """Clear all jobs from a queue."""
        try:
            queue = self.queues[priority]
            cleared_count = len(queue)
            queue.empty()
            logger.info(f"Cleared {cleared_count} jobs from {priority.value} queue")
            return cleared_count

        except Exception as e:
            logger.error(f"Failed to clear queue {priority.value}: {e}")
            return 0

    def start_worker(self, queues: list[TaskPriority] = None,
                     worker_name: str | None = None) -> Worker:
        """Start a worker process."""
        if queues is None:
            # Default priority order: urgent -> high -> normal -> low
            queues = [
                TaskPriority.URGENT,
                TaskPriority.HIGH,
                TaskPriority.NORMAL,
                TaskPriority.LOW]

        worker_queues = [self.queues[priority] for priority in queues]

        worker = Worker(
            worker_queues,
            connection=self.redis_connection,
            name=worker_name or f"worker-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )

        return worker

    def get_failed_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get failed jobs across all queues."""
        failed_jobs = []

        for priority, queue in self.queues.items():
            try:
                registry = queue.failed_job_registry
                for job_id in registry.get_job_ids()[:limit]:
                    job = Job.fetch(job_id, connection=self.redis_connection)
                    failed_jobs.append({
                        "id": job.id,
                        "queue": priority.value,
                        "description": job.description,
                        "failed_at": job.ended_at.isoformat() if job.ended_at else None,
                        "exc_info": job.exc_info,
                        "meta": job.meta
                    })
            except Exception as e:
                logger.error(
                    f"Failed to get failed jobs for queue {priority.value}: {e}")

        return failed_jobs

    def retry_failed_job(self, job_id: str) -> bool:
        """Retry a failed job."""
        try:
            job = Job.fetch(job_id, connection=self.redis_connection)
            job.retry()
            logger.info(f"Retried job {job_id}")
            return True

        except NoSuchJobError:
            logger.warning(f"Job {job_id} not found for retry")
            return False
        except Exception as e:
            logger.error(f"Failed to retry job {job_id}: {e}")
            return False


class BatchProcessor:
    """High-level batch processing coordinator."""

    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.active_batches: dict[str, dict[str, Any]] = {}

    def submit_batch(self, batch_id: str, tasks: list[dict[str, Any]],
                     priority: TaskPriority = TaskPriority.NORMAL) -> dict[str, Any]:
        """Submit a batch of related tasks."""
        job_ids = []

        try:
            for task in tasks:
                job_id = self.task_queue.enqueue_task(
                    func=task["func"],
                    args=task.get("args", ()),
                    kwargs=task.get("kwargs", {}),
                    priority=priority,
                    job_timeout=task.get("timeout", "10m"),
                    description=task.get("description")
                )
                job_ids.append(job_id)

            # Track batch
            self.active_batches[batch_id] = {
                "job_ids": job_ids,
                "created_at": datetime.now().isoformat(),
                "priority": priority.value,
                "total_tasks": len(tasks)
            }

            logger.info(f"Submitted batch {batch_id} with {len(tasks)} tasks")
            return {
                "batch_id": batch_id,
                "job_ids": job_ids,
                "total_tasks": len(tasks)
            }

        except Exception as e:
            logger.error(f"Failed to submit batch {batch_id}: {e}")
            raise

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """Get status of a batch."""
        if batch_id not in self.active_batches:
            return {"batch_id": batch_id, "status": "not_found"}

        batch_info = self.active_batches[batch_id]
        job_statuses = []

        for job_id in batch_info["job_ids"]:
            job_status = self.task_queue.get_job_status(job_id)
            job_statuses.append(job_status)

        # Calculate batch statistics
        status_counts = {}
        for job_status in job_statuses:
            status = job_status["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        # Determine overall batch status
        if status_counts.get("failed", 0) > 0:
            overall_status = "failed"
        elif status_counts.get("finished", 0) == len(job_statuses):
            overall_status = "completed"
        elif status_counts.get("started", 0) > 0:
            overall_status = "running"
        else:
            overall_status = "pending"

        return {
            "batch_id": batch_id,
            "overall_status": overall_status,
            "created_at": batch_info["created_at"],
            "priority": batch_info["priority"],
            "total_tasks": batch_info["total_tasks"],
            "status_counts": status_counts,
            "job_statuses": job_statuses
        }

    def cancel_batch(self, batch_id: str) -> dict[str, Any]:
        """Cancel all jobs in a batch."""
        if batch_id not in self.active_batches:
            return {"batch_id": batch_id, "status": "not_found"}

        batch_info = self.active_batches[batch_id]
        cancelled_count = 0

        for job_id in batch_info["job_ids"]:
            if self.task_queue.cancel_job(job_id):
                cancelled_count += 1

        return {
            "batch_id": batch_id,
            "cancelled_jobs": cancelled_count,
            "total_jobs": len(batch_info["job_ids"])
        }

    def cleanup_completed_batches(self, max_age_hours: int = 24) -> int:
        """Clean up completed batches older than max_age_hours."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        for batch_id, batch_info in list(self.active_batches.items()):
            created_at = datetime.fromisoformat(batch_info["created_at"])
            if created_at < cutoff_time:
                batch_status = self.get_batch_status(batch_id)
                if batch_status["overall_status"] in ["completed", "failed"]:
                    del self.active_batches[batch_id]
                    cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} completed batches")
        return cleaned_count


# Global instances
task_queue = TaskQueue()
batch_processor = BatchProcessor(task_queue)
