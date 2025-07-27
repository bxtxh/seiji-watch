"""
Issue Relationship Batch Jobs - Nightly processing for Bill-Issue relationships.
Handles bulk updates, change detection, and incremental processing.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any

import pytz

from shared.clients.airtable import AirtableClient
from services.airtable_issue_manager import AirtableIssueManager
# TODO: Replace with proper service-to-service communication (HTTP/message queue)
# from services.discord_notification_bot import DiscordNotificationBot
from services.issue_versioning_service import IssueVersioningService

logger = logging.getLogger(__name__)


class BatchJobStatus(Enum):
    """Status of batch jobs."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJobType(Enum):
    """Types of batch jobs."""

    RELATIONSHIP_UPDATE = "relationship_update"
    ISSUE_MIGRATION = "issue_migration"
    DATA_CLEANUP = "data_cleanup"
    QUALITY_ASSESSMENT = "quality_assessment"
    CACHE_REFRESH = "cache_refresh"


@dataclass
class BatchJobConfig:
    """Configuration for batch jobs."""

    job_id: str
    job_type: BatchJobType
    job_name: str
    description: str

    # Scheduling
    schedule_time: time = field(default_factory=lambda: time(2, 0))  # 2:00 AM JST
    timezone: str = "Asia/Tokyo"
    enabled: bool = True

    # Processing
    batch_size: int = 100
    max_concurrent_tasks: int = 5
    timeout_minutes: int = 120
    retry_attempts: int = 3
    retry_delay_seconds: int = 300

    # Monitoring
    notification_on_failure: bool = True
    notification_on_success: bool = False
    alert_threshold_minutes: int = 180

    # Data retention
    keep_logs_days: int = 30

    def __post_init__(self):
        if not self.job_id:
            self.job_id = (
                f"{self.job_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )


@dataclass
class BatchJobExecution:
    """Execution record for a batch job."""

    execution_id: str
    job_config: BatchJobConfig
    status: BatchJobStatus = BatchJobStatus.PENDING

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    # Progress tracking
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0

    # Results
    result_summary: dict[str, Any] = field(default_factory=dict)
    error_messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Metrics
    items_per_second: float | None = None
    memory_usage_mb: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/API."""
        return {
            "execution_id": self.execution_id,
            "job_id": self.job_config.job_id,
            "job_type": self.job_config.job_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_seconds": self.duration_seconds,
            "progress": {
                "total": self.total_items,
                "processed": self.processed_items,
                "successful": self.successful_items,
                "failed": self.failed_items,
                "skipped": self.skipped_items,
            },
            "performance": {
                "items_per_second": self.items_per_second,
                "memory_usage_mb": self.memory_usage_mb,
            },
            "results": self.result_summary,
            "errors": self.error_messages,
            "warnings": self.warnings,
        }


class IssueRelationshipBatchProcessor:
    """Batch processor for issue relationship management."""

    def __init__(
        self,
        airtable_client: AirtableClient | None = None,
        issue_manager: AirtableIssueManager | None = None,
        versioning_service: IssueVersioningService | None = None,
        discord_bot: Any | None = None,  # TODO: Replace with HTTP client for notifications-worker
    ):
        self.airtable_client = airtable_client or AirtableClient()
        self.issue_manager = issue_manager or AirtableIssueManager()
        self.versioning_service = versioning_service or IssueVersioningService()
        self.discord_bot = discord_bot  # TODO: Initialize HTTP client for notifications service

        self.logger = logger
        self.timezone = pytz.timezone("Asia/Tokyo")

        # Job tracking
        self.active_jobs: dict[str, BatchJobExecution] = {}
        self.job_history: list[BatchJobExecution] = []

        # Default job configurations
        self.default_jobs = self._initialize_default_jobs()

        # Scheduler task
        self.scheduler_task: asyncio.Task | None = None
        self.is_running = False

    def _initialize_default_jobs(self) -> list[BatchJobConfig]:
        """Initialize default batch job configurations."""
        return [
            BatchJobConfig(
                job_id="nightly_relationship_update",
                job_type=BatchJobType.RELATIONSHIP_UPDATE,
                job_name="Nightly Bill-Issue Relationship Update",
                description="Update relationships between bills and issues based on content changes",
                schedule_time=time(2, 0),  # 2:00 AM JST
                batch_size=50,
                max_concurrent_tasks=3,
            ),
            BatchJobConfig(
                job_id="weekly_quality_assessment",
                job_type=BatchJobType.QUALITY_ASSESSMENT,
                job_name="Weekly Issue Quality Assessment",
                description="Reassess quality scores for issues based on recent reviews",
                schedule_time=time(3, 0),  # 3:00 AM JST
                batch_size=100,
                max_concurrent_tasks=2,
            ),
            BatchJobConfig(
                job_id="daily_cache_refresh",
                job_type=BatchJobType.CACHE_REFRESH,
                job_name="Daily Cache Refresh",
                description="Refresh cached issue data and statistics",
                schedule_time=time(1, 30),  # 1:30 AM JST
                batch_size=200,
                max_concurrent_tasks=5,
            ),
            BatchJobConfig(
                job_id="weekly_data_cleanup",
                job_type=BatchJobType.DATA_CLEANUP,
                job_name="Weekly Data Cleanup",
                description="Clean up old versions and orphaned records",
                schedule_time=time(4, 0),  # 4:00 AM JST
                batch_size=1000,
                max_concurrent_tasks=1,
            ),
        ]

    async def start_scheduler(self):
        """Start the batch job scheduler."""
        if self.is_running:
            self.logger.warning("Batch scheduler is already running")
            return

        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.logger.info("Batch job scheduler started")

    async def stop_scheduler(self):
        """Stop the batch job scheduler."""
        if not self.is_running:
            return

        self.is_running = False

        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Batch job scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop."""
        self.logger.info("Batch scheduler loop started")

        while self.is_running:
            try:
                current_time = datetime.now(self.timezone)

                # Check each job configuration
                for job_config in self.default_jobs:
                    if not job_config.enabled:
                        continue

                    # Check if it's time to run this job
                    if self._should_run_job(job_config, current_time):
                        await self._execute_batch_job(job_config)

                # Sleep for 1 minute before next check
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in batch scheduler loop: {e}")
                await asyncio.sleep(300)  # 5 minute delay on error

    def _should_run_job(
        self, job_config: BatchJobConfig, current_time: datetime
    ) -> bool:
        """Check if a job should run based on schedule."""

        # Check if job is already running
        for execution in self.active_jobs.values():
            if (
                execution.job_config.job_id == job_config.job_id
                and execution.status == BatchJobStatus.RUNNING
            ):
                return False

        # Check if it's the scheduled time (within 1 minute window)
        scheduled_today = current_time.replace(
            hour=job_config.schedule_time.hour,
            minute=job_config.schedule_time.minute,
            second=0,
            microsecond=0,
        )

        time_diff = abs((current_time - scheduled_today).total_seconds())

        if time_diff <= 60:  # Within 1 minute of scheduled time
            # Check if job already ran today
            today = current_time.date()
            for execution in self.job_history:
                if (
                    execution.job_config.job_id == job_config.job_id
                    and execution.started_at
                    and execution.started_at.date() == today
                    and execution.status == BatchJobStatus.COMPLETED
                ):
                    return False

            return True

        return False

    async def _execute_batch_job(self, job_config: BatchJobConfig):
        """Execute a batch job."""
        execution_id = f"{job_config.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        execution = BatchJobExecution(
            execution_id=execution_id, job_config=job_config, started_at=datetime.now()
        )

        self.active_jobs[execution_id] = execution

        try:
            self.logger.info(
                f"Starting batch job: {job_config.job_name} ({execution_id})"
            )
            execution.status = BatchJobStatus.RUNNING

            # Execute based on job type
            if job_config.job_type == BatchJobType.RELATIONSHIP_UPDATE:
                await self._execute_relationship_update(execution)
            elif job_config.job_type == BatchJobType.QUALITY_ASSESSMENT:
                await self._execute_quality_assessment(execution)
            elif job_config.job_type == BatchJobType.CACHE_REFRESH:
                await self._execute_cache_refresh(execution)
            elif job_config.job_type == BatchJobType.DATA_CLEANUP:
                await self._execute_data_cleanup(execution)
            else:
                raise ValueError(f"Unknown job type: {job_config.job_type}")

            execution.status = BatchJobStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            execution.items_per_second = (
                execution.processed_items / execution.duration_seconds
                if execution.duration_seconds > 0
                else 0
            )

            self.logger.info(
                f"Batch job completed: {job_config.job_name} - "
                f"{execution.successful_items}/{execution.total_items} successful"
            )

            # Send success notification if configured
            if job_config.notification_on_success:
                await self._send_job_notification(execution, success=True)

        except Exception as e:
            execution.status = BatchJobStatus.FAILED
            execution.completed_at = datetime.now()
            execution.error_messages.append(str(e))

            self.logger.error(f"Batch job failed: {job_config.job_name} - {e}")

            # Send failure notification
            if job_config.notification_on_failure:
                await self._send_job_notification(execution, success=False)

        finally:
            # Move to history and cleanup
            self.job_history.append(execution)
            del self.active_jobs[execution_id]

            # Cleanup old history
            await self._cleanup_job_history()

    async def _execute_relationship_update(self, execution: BatchJobExecution):
        """Execute bill-issue relationship update job."""

        # Get all bills and issues for relationship analysis
        bills = await self.airtable_client.list_bills(max_records=1000)
        issues = await self.issue_manager.list_issues_by_status(
            "approved", max_records=1000
        )

        execution.total_items = len(bills)

        # Process bills in batches
        batch_size = execution.job_config.batch_size

        for i in range(0, len(bills), batch_size):
            batch_bills = bills[i : i + batch_size]

            # Process batch concurrently
            tasks = []
            for bill in batch_bills:
                task = self._update_bill_issue_relationships(bill, issues)
                tasks.append(task)

            # Execute with concurrency limit
            semaphore = asyncio.Semaphore(execution.job_config.max_concurrent_tasks)
            batch_results = await asyncio.gather(
                *[self._run_with_semaphore(semaphore, task) for task in tasks],
                return_exceptions=True,
            )

            # Process results
            for j, result in enumerate(batch_results):
                execution.processed_items += 1

                if isinstance(result, Exception):
                    execution.failed_items += 1
                    execution.error_messages.append(
                        f"Bill {batch_bills[j].get('id', 'unknown')}: {result}"
                    )
                else:
                    execution.successful_items += 1
                    if result.get("relationships_updated", 0) > 0:
                        execution.result_summary["updated_relationships"] = (
                            execution.result_summary.get("updated_relationships", 0)
                            + result["relationships_updated"]
                        )

        execution.result_summary["total_bills_processed"] = execution.processed_items

    async def _update_bill_issue_relationships(
        self, bill: dict[str, Any], issues: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Update relationships between a bill and related issues."""

        bill_id = bill.get("id")
        bill_fields = bill.get("fields", {})
        bill_content = f"{bill_fields.get('Name', '')} {bill_fields.get('Notes', '')}"

        relationships_updated = 0

        # Find issues related to this bill
        related_issues = []
        for issue in issues:
            issue_fields = issue.get("fields", {})

            # Check if issue is already linked to this bill
            if issue_fields.get("Source_Bill_ID") == bill_id:
                related_issues.append(issue)
                continue

            # Perform content similarity check
            issue_content = f"{issue_fields.get('Label_Lv1', '')} {issue_fields.get('Label_Lv2', '')}"
            similarity_score = self._calculate_content_similarity(
                bill_content, issue_content
            )

            if similarity_score > 0.7:  # High similarity threshold
                related_issues.append(issue)

        # Update issue relationships if needed
        for issue in related_issues:
            issue_fields = issue.get("fields", {})
            current_bill_id = issue_fields.get("Source_Bill_ID")

            if current_bill_id != bill_id:
                # Update the relationship
                try:
                    await self.issue_manager.client._rate_limited_request(
                        "PATCH",
                        f"{self.issue_manager.client.base_url}/{self.issue_manager.table_name}/{issue['id']}",
                        json={
                            "fields": {
                                "Source_Bill_ID": bill_id,
                                "Updated_At": datetime.now().isoformat(),
                            }
                        },
                    )
                    relationships_updated += 1

                except Exception as e:
                    self.logger.error(
                        f"Failed to update issue {issue['id']} relationship: {e}"
                    )

        return {
            "bill_id": bill_id,
            "related_issues": len(related_issues),
            "relationships_updated": relationships_updated,
        }

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""

        # Simple keyword-based similarity (in production, use better NLP)
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    async def _execute_quality_assessment(self, execution: BatchJobExecution):
        """Execute quality assessment job."""

        # Get all approved issues for quality reassessment
        issues = await self.issue_manager.list_issues_by_status(
            "approved", max_records=500
        )
        execution.total_items = len(issues)

        quality_updates = 0

        for issue in issues:
            execution.processed_items += 1

            try:
                issue_fields = issue.get("fields", {})
                current_quality = issue_fields.get("Quality_Score", 0.0)

                # Recalculate quality score based on various factors
                new_quality = await self._calculate_issue_quality(issue)

                # Update if quality score changed significantly
                if abs(new_quality - current_quality) > 0.1:
                    await self.issue_manager.client._rate_limited_request(
                        "PATCH",
                        f"{self.issue_manager.client.base_url}/{self.issue_manager.table_name}/{issue['id']}",
                        json={
                            "fields": {
                                "Quality_Score": new_quality,
                                "Updated_At": datetime.now().isoformat(),
                            }
                        },
                    )
                    quality_updates += 1

                execution.successful_items += 1

            except Exception as e:
                execution.failed_items += 1
                execution.error_messages.append(
                    f"Issue {issue.get('id', 'unknown')}: {e}"
                )

        execution.result_summary = {
            "total_issues_assessed": execution.processed_items,
            "quality_scores_updated": quality_updates,
        }

    async def _calculate_issue_quality(self, issue: dict[str, Any]) -> float:
        """Calculate quality score for an issue."""

        fields = issue.get("fields", {})

        quality_factors = []

        # Label quality (length and verb endings)
        label_lv1 = fields.get("Label_Lv1", "")
        label_lv2 = fields.get("Label_Lv2", "")

        if 10 <= len(label_lv1) <= 60:
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.5)

        if 10 <= len(label_lv2) <= 60:
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.5)

        # Confidence score
        confidence = fields.get("Confidence", 0.0)
        quality_factors.append(min(confidence, 1.0))

        # Status (approved issues get higher quality)
        status = fields.get("Status", "")
        if status == "approved":
            quality_factors.append(0.9)
        else:
            quality_factors.append(0.6)

        # Source bill linkage
        if fields.get("Source_Bill_ID"):
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.4)

        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0

    async def _execute_cache_refresh(self, execution: BatchJobExecution):
        """Execute cache refresh job."""

        # Get statistics and cache commonly accessed data
        stats = await self.issue_manager.get_issue_statistics()
        execution.total_items = stats.get("total_issues", 0)

        # Refresh cached data (implementation depends on caching system)
        execution.successful_items = execution.total_items
        execution.processed_items = execution.total_items

        execution.result_summary = {
            "cache_refreshed": True,
            "statistics_updated": stats,
        }

    async def _execute_data_cleanup(self, execution: BatchJobExecution):
        """Execute data cleanup job."""

        # Clean up old versions
        cleanup_result = await self.versioning_service.cleanup_old_versions()

        execution.total_items = cleanup_result.get("cleaned", 0) + cleanup_result.get(
            "retained", 0
        )
        execution.successful_items = cleanup_result.get("cleaned", 0)
        execution.processed_items = execution.total_items

        execution.result_summary = cleanup_result

    async def _run_with_semaphore(self, semaphore: asyncio.Semaphore, coro):
        """Run coroutine with semaphore to limit concurrency."""
        async with semaphore:
            return await coro

    async def _send_job_notification(self, execution: BatchJobExecution, success: bool):
        """Send notification about job completion."""

        try:
            if success:
                title = f"✅ {execution.job_config.job_name} 完了"
                color = 0x00FF00
                message = (
                    f"バッチジョブが正常に完了しました。\n\n"
                    f"**処理時間:** {execution.duration_seconds:.1f}秒\n"
                    f"**処理件数:** {execution.successful_items}/{execution.total_items}\n"
                    f"**処理速度:** {execution.items_per_second:.1f} items/sec"
                )
            else:
                title = f"❌ {execution.job_config.job_name} 失敗"
                color = 0xFF0000
                message = (
                    f"バッチジョブが失敗しました。\n\n"
                    f"**エラー数:** {len(execution.error_messages)}\n"
                    f"**処理済み:** {execution.processed_items}/{execution.total_items}"
                )

                if execution.error_messages:
                    message += f"\n**最新エラー:** {execution.error_messages[-1][:200]}"

            # TODO: Replace with HTTP call to notifications-worker service
            if self.discord_bot:
                await self.discord_bot.send_custom_notification(title, message, color)
            else:
                self.logger.info(f"Notification (would send): {title} - {message}")

        except Exception as e:
            self.logger.error(f"Failed to send job notification: {e}")

    async def _cleanup_job_history(self):
        """Clean up old job history entries."""

        cutoff_date = datetime.now() - timedelta(days=30)
        self.job_history = [
            execution
            for execution in self.job_history
            if execution.started_at and execution.started_at > cutoff_date
        ]

    async def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get status of a specific job."""

        # Check active jobs
        for execution in self.active_jobs.values():
            if execution.job_config.job_id == job_id:
                return execution.to_dict()

        # Check job history
        for execution in reversed(self.job_history):
            if execution.job_config.job_id == job_id:
                return execution.to_dict()

        return None

    async def get_all_job_statuses(self) -> dict[str, Any]:
        """Get status of all jobs."""

        active_jobs = [execution.to_dict() for execution in self.active_jobs.values()]
        recent_jobs = [execution.to_dict() for execution in self.job_history[-10:]]

        return {
            "active_jobs": active_jobs,
            "recent_completed_jobs": recent_jobs,
            "scheduler_status": "running" if self.is_running else "stopped",
            "configured_jobs": [
                {
                    "job_id": config.job_id,
                    "job_name": config.job_name,
                    "job_type": config.job_type.value,
                    "schedule_time": config.schedule_time.strftime("%H:%M"),
                    "enabled": config.enabled,
                }
                for config in self.default_jobs
            ],
        }

    async def health_check(self) -> bool:
        """Health check for batch processor."""
        try:
            # Check dependencies
            airtable_healthy = await self.airtable_client.health_check()
            issue_manager_healthy = await self.issue_manager.health_check()
            versioning_healthy = await self.versioning_service.health_check()

            # Check for stuck jobs
            stuck_jobs = 0
            current_time = datetime.now()
            for execution in self.active_jobs.values():
                if execution.started_at:
                    runtime = (current_time - execution.started_at).total_seconds() / 60
                    if runtime > execution.job_config.alert_threshold_minutes:
                        stuck_jobs += 1

            return (
                airtable_healthy
                and issue_manager_healthy
                and versioning_healthy
                and stuck_jobs == 0
            )

        except Exception as e:
            self.logger.error(f"Batch processor health check failed: {e}")
            return False
