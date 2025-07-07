"""
Automated Ingestion Scheduler for Diet Issue Tracker

This module provides scheduled automation for:
- Daily scraping of new Diet meetings
- Periodic voting data collection
- Batch processing of audio/video transcriptions
- Status tracking and error notifications

Integrates with Google Cloud Scheduler and Pub/Sub for production deployment.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    from google.cloud import pubsub_v1
    from google.cloud import scheduler_v1
    from google.cloud.scheduler_v1 import Job, PubsubTarget, HttpTarget
    from google.api_core import retry
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    pubsub_v1 = None
    scheduler_v1 = None
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Enumeration of available scheduled task types"""
    SCRAPE_BILLS = "scrape_bills"
    COLLECT_VOTING = "collect_voting"
    BATCH_TRANSCRIBE = "batch_transcribe"
    BATCH_EMBEDDINGS = "batch_embeddings"
    HEALTH_CHECK = "health_check"


class TaskStatus(str, Enum):
    """Enumeration of task execution statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Configuration for a scheduled task"""
    task_id: str
    task_type: TaskType
    cron_schedule: str
    description: str
    enabled: bool = True
    retry_count: int = 3
    timeout_minutes: int = 30
    payload: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskExecution:
    """Record of a task execution"""
    execution_id: str
    task_id: str
    task_type: TaskType
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data


class SchedulerConfig(BaseModel):
    """Configuration for the scheduler service"""
    project_id: str
    location: str = "asia-northeast1"
    pubsub_topic: str = "ingest-worker-tasks"
    scheduler_service_account: Optional[str] = None
    max_retry_attempts: int = 3
    default_timeout_minutes: int = 30
    
    @classmethod
    def from_env(cls) -> 'SchedulerConfig':
        """Load configuration from environment variables"""
        return cls(
            project_id=os.environ.get('GOOGLE_CLOUD_PROJECT', ''),
            location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'asia-northeast1'),
            pubsub_topic=os.environ.get('PUBSUB_TOPIC', 'ingest-worker-tasks'),
            scheduler_service_account=os.environ.get('SCHEDULER_SERVICE_ACCOUNT'),
            max_retry_attempts=int(os.environ.get('MAX_RETRY_ATTEMPTS', '3')),
            default_timeout_minutes=int(os.environ.get('DEFAULT_TIMEOUT_MINUTES', '30'))
        )


class IngestionScheduler:
    """
    Automated ingestion scheduler for Diet Issue Tracker
    
    Manages scheduled tasks for:
    - Daily scraping of new Diet meetings
    - Periodic voting data collection  
    - Batch processing operations
    - Status tracking and error notifications
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig.from_env()
        self.publisher_client = None
        self.scheduler_client = None
        self.task_executions: Dict[str, TaskExecution] = {}
        
        # Initialize Google Cloud clients if available and project ID is provided
        if GOOGLE_CLOUD_AVAILABLE and self.config.project_id:
            try:
                self.publisher_client = pubsub_v1.PublisherClient()
                self.scheduler_client = scheduler_v1.CloudSchedulerClient()
                logger.info(f"Initialized Google Cloud clients for project: {self.config.project_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Cloud clients: {e}")
                logger.warning("Scheduler will operate in local mode only")
        else:
            if not GOOGLE_CLOUD_AVAILABLE:
                logger.warning("Google Cloud libraries not available, running in local mode")
            else:
                logger.warning("No project ID provided, running in local mode")
        
        # Define default scheduled tasks
        self.scheduled_tasks = self._create_default_tasks()
    
    def _create_default_tasks(self) -> List[ScheduledTask]:
        """Create default scheduled tasks configuration"""
        return [
            # Daily bill scraping at 7 AM JST
            ScheduledTask(
                task_id="daily_bill_scraping",
                task_type=TaskType.SCRAPE_BILLS,
                cron_schedule="0 7 * * *",  # 7 AM JST daily
                description="Daily scraping of new Diet bills and meetings",
                timeout_minutes=45,
                payload={"force_refresh": False}
            ),
            
            # Voting data collection every 6 hours
            ScheduledTask(
                task_id="periodic_voting_collection",
                task_type=TaskType.COLLECT_VOTING,
                cron_schedule="0 */6 * * *",  # Every 6 hours
                description="Periodic collection of voting data from Diet website",
                timeout_minutes=60,
                payload={"vote_type": "all", "force_refresh": False}
            ),
            
            # Batch transcription processing at 3 AM JST
            ScheduledTask(
                task_id="batch_transcription",
                task_type=TaskType.BATCH_TRANSCRIBE,
                cron_schedule="0 3 * * *",  # 3 AM JST daily
                description="Batch processing of audio/video transcriptions",
                timeout_minutes=120,
                payload={"batch_size": 10, "max_duration_hours": 4}
            ),
            
            # Batch embedding generation at 4 AM JST
            ScheduledTask(
                task_id="batch_embeddings",
                task_type=TaskType.BATCH_EMBEDDINGS,
                cron_schedule="0 4 * * *",  # 4 AM JST daily
                description="Batch generation of vector embeddings",
                timeout_minutes=90,
                payload={"batch_size": 50, "regenerate_existing": False}
            ),
            
            # Health check every hour
            ScheduledTask(
                task_id="health_check",
                task_type=TaskType.HEALTH_CHECK,
                cron_schedule="0 * * * *",  # Every hour
                description="Health check and status monitoring",
                timeout_minutes=5,
                payload={"check_dependencies": True}
            )
        ]
    
    async def setup_cloud_scheduler(self) -> bool:
        """
        Set up Google Cloud Scheduler jobs for all scheduled tasks
        
        Returns:
            bool: True if setup was successful, False otherwise
        """
        if not self.scheduler_client or not self.publisher_client:
            logger.error("Cloud Scheduler clients not initialized")
            return False
        
        try:
            # Ensure Pub/Sub topic exists
            await self._ensure_pubsub_topic()
            
            # Create or update scheduler jobs
            for task in self.scheduled_tasks:
                if task.enabled:
                    await self._create_scheduler_job(task)
            
            logger.info(f"Successfully set up {len([t for t in self.scheduled_tasks if t.enabled])} Cloud Scheduler jobs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up Cloud Scheduler: {e}")
            return False
    
    async def _ensure_pubsub_topic(self) -> None:
        """Ensure the Pub/Sub topic exists"""
        topic_path = self.publisher_client.topic_path(
            self.config.project_id, 
            self.config.pubsub_topic
        )
        
        try:
            # Try to get the topic
            self.publisher_client.get_topic(request={"topic": topic_path})
            logger.info(f"Pub/Sub topic exists: {topic_path}")
            
        except Exception:
            # Create the topic if it doesn't exist
            try:
                self.publisher_client.create_topic(request={"name": topic_path})
                logger.info(f"Created Pub/Sub topic: {topic_path}")
            except Exception as e:
                logger.error(f"Failed to create Pub/Sub topic: {e}")
                raise
    
    async def _create_scheduler_job(self, task: ScheduledTask) -> None:
        """Create a Google Cloud Scheduler job for a scheduled task"""
        parent = self.scheduler_client.location_path(
            self.config.project_id, 
            self.config.location
        )
        
        job_name = f"{parent}/jobs/{task.task_id}"
        
        # Create Pub/Sub target
        pubsub_target = PubsubTarget(
            topic_name=self.publisher_client.topic_path(
                self.config.project_id, 
                self.config.pubsub_topic
            ),
            data=json.dumps({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "payload": task.payload or {}
            }).encode('utf-8')
        )
        
        # Create job configuration
        job = Job(
            name=job_name,
            description=task.description,
            pubsub_target=pubsub_target,
            schedule=task.cron_schedule,
            time_zone="Asia/Tokyo",
            retry_config=scheduler_v1.RetryConfig(
                retry_count=task.retry_count,
                max_retry_duration={"seconds": task.timeout_minutes * 60}
            )
        )
        
        try:
            # Try to update existing job
            self.scheduler_client.update_job(job=job)
            logger.info(f"Updated scheduler job: {task.task_id}")
            
        except Exception:
            # Create new job if update fails
            try:
                self.scheduler_client.create_job(
                    parent=parent,
                    job=job
                )
                logger.info(f"Created scheduler job: {task.task_id}")
                
            except Exception as e:
                logger.error(f"Failed to create scheduler job {task.task_id}: {e}")
                raise
    
    async def handle_pubsub_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle a Pub/Sub message and execute the corresponding task
        
        Args:
            message_data: Decoded Pub/Sub message data
            
        Returns:
            bool: True if task was executed successfully, False otherwise
        """
        try:
            task_id = message_data.get("task_id")
            task_type = TaskType(message_data.get("task_type"))
            payload = message_data.get("payload", {})
            
            logger.info(f"Processing scheduled task: {task_id} ({task_type})")
            
            # Create task execution record
            execution = TaskExecution(
                execution_id=f"{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.RUNNING,
                start_time=datetime.now()
            )
            
            self.task_executions[execution.execution_id] = execution
            
            # Execute the task based on type
            try:
                result = await self._execute_task(task_type, payload)
                
                # Update execution record with success
                execution.status = TaskStatus.COMPLETED
                execution.end_time = datetime.now()
                execution.result_data = result
                
                logger.info(f"Task completed successfully: {task_id}")
                return True
                
            except Exception as e:
                # Update execution record with failure
                execution.status = TaskStatus.FAILED
                execution.end_time = datetime.now()
                execution.error_message = str(e)
                
                logger.error(f"Task failed: {task_id} - {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to handle Pub/Sub message: {e}")
            return False
    
    async def _execute_task(self, task_type: TaskType, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific task type with the given payload
        
        Args:
            task_type: Type of task to execute
            payload: Task-specific payload data
            
        Returns:
            Dict containing task execution results
        """
        if task_type == TaskType.SCRAPE_BILLS:
            return await self._execute_scrape_bills(payload)
        elif task_type == TaskType.COLLECT_VOTING:
            return await self._execute_collect_voting(payload)
        elif task_type == TaskType.BATCH_TRANSCRIBE:
            return await self._execute_batch_transcribe(payload)
        elif task_type == TaskType.BATCH_EMBEDDINGS:
            return await self._execute_batch_embeddings(payload)
        elif task_type == TaskType.HEALTH_CHECK:
            return await self._execute_health_check(payload)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _execute_scrape_bills(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute bill scraping task"""
        logger.info("Executing scheduled bill scraping task")
        
        # Import here to avoid circular imports
        from ..main import diet_scraper, _scrape_bills_task
        
        if not diet_scraper:
            raise RuntimeError("Diet scraper not initialized")
        
        # Execute the scraping task
        await _scrape_bills_task(force_refresh=payload.get("force_refresh", False))
        
        return {
            "task_type": "scrape_bills",
            "force_refresh": payload.get("force_refresh", False),
            "execution_time": datetime.now().isoformat()
        }
    
    async def _execute_collect_voting(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute voting data collection task"""
        logger.info("Executing scheduled voting data collection task")
        
        # Import here to avoid circular imports
        from ..main import voting_scraper, _collect_voting_data_task
        
        if not voting_scraper:
            raise RuntimeError("Voting scraper not initialized")
        
        # Execute the voting data collection task
        await _collect_voting_data_task(
            vote_type=payload.get("vote_type", "all"),
            force_refresh=payload.get("force_refresh", False)
        )
        
        return {
            "task_type": "collect_voting",
            "vote_type": payload.get("vote_type", "all"),
            "force_refresh": payload.get("force_refresh", False),
            "execution_time": datetime.now().isoformat()
        }
    
    async def _execute_batch_transcribe(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute batch transcription task"""
        logger.info("Executing scheduled batch transcription task")
        
        # TODO: Implement batch transcription logic
        # This would process queued audio/video files for transcription
        
        batch_size = payload.get("batch_size", 10)
        max_duration_hours = payload.get("max_duration_hours", 4)
        
        logger.info(f"Batch transcription: max {batch_size} items, max {max_duration_hours} hours")
        
        return {
            "task_type": "batch_transcribe",
            "batch_size": batch_size,
            "max_duration_hours": max_duration_hours,
            "processed_items": 0,  # TODO: Implement actual processing
            "execution_time": datetime.now().isoformat()
        }
    
    async def _execute_batch_embeddings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute batch embedding generation task"""
        logger.info("Executing scheduled batch embedding generation task")
        
        # TODO: Implement batch embedding generation logic
        # This would process queued text content for embedding generation
        
        batch_size = payload.get("batch_size", 50)
        regenerate_existing = payload.get("regenerate_existing", False)
        
        logger.info(f"Batch embeddings: max {batch_size} items, regenerate: {regenerate_existing}")
        
        return {
            "task_type": "batch_embeddings",
            "batch_size": batch_size,
            "regenerate_existing": regenerate_existing,
            "processed_items": 0,  # TODO: Implement actual processing
            "execution_time": datetime.now().isoformat()
        }
    
    async def _execute_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute health check task"""
        logger.info("Executing scheduled health check task")
        
        # Import here to avoid circular imports
        from ..main import diet_scraper, voting_scraper, whisper_client, vector_client
        
        health_status = {
            "diet_scraper": diet_scraper is not None,
            "voting_scraper": voting_scraper is not None,
            "whisper_client": whisper_client is not None,
            "vector_client": vector_client is not None,
            "check_time": datetime.now().isoformat()
        }
        
        # Additional dependency checks if requested
        if payload.get("check_dependencies", False):
            health_status["dependencies"] = await self._check_dependencies()
        
        logger.info(f"Health check completed: {health_status}")
        
        return {
            "task_type": "health_check",
            "health_status": health_status,
            "execution_time": datetime.now().isoformat()
        }
    
    async def _check_dependencies(self) -> Dict[str, bool]:
        """Check external dependencies availability"""
        dependencies = {}
        
        # Check Diet website accessibility
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.sangiin.go.jp/", timeout=10) as response:
                    dependencies["diet_website"] = response.status == 200
        except Exception:
            dependencies["diet_website"] = False
        
        # Check OpenAI API availability
        try:
            import openai
            # Simple API check without using quota
            dependencies["openai_api"] = bool(os.environ.get("OPENAI_API_KEY"))
        except Exception:
            dependencies["openai_api"] = False
        
        # Check Weaviate availability
        try:
            from ..embeddings.vector_client import VectorClient
            dependencies["weaviate"] = bool(os.environ.get("WEAVIATE_URL"))
        except Exception:
            dependencies["weaviate"] = False
        
        return dependencies
    
    def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of scheduled tasks
        
        Args:
            task_id: Optional specific task ID to get status for
            
        Returns:
            Dict containing task status information
        """
        if task_id:
            # Return status for specific task
            task = next((t for t in self.scheduled_tasks if t.task_id == task_id), None)
            if not task:
                return {"error": f"Task not found: {task_id}"}
            
            # Get recent executions for this task
            executions = [
                ex.to_dict() for ex in self.task_executions.values()
                if ex.task_id == task_id
            ]
            executions.sort(key=lambda x: x["start_time"], reverse=True)
            
            return {
                "task": task.to_dict(),
                "recent_executions": executions[:10]  # Last 10 executions
            }
        else:
            # Return status for all tasks
            return {
                "scheduled_tasks": [t.to_dict() for t in self.scheduled_tasks],
                "total_executions": len(self.task_executions),
                "recent_executions": sorted([
                    ex.to_dict() for ex in self.task_executions.values()
                ], key=lambda x: x["start_time"], reverse=True)[:20]
            }
    
    def cleanup_old_executions(self, days_to_keep: int = 30) -> int:
        """
        Clean up old task execution records
        
        Args:
            days_to_keep: Number of days of execution history to keep
            
        Returns:
            Number of cleaned up records
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        old_executions = [
            exec_id for exec_id, execution in self.task_executions.items()
            if execution.start_time < cutoff_date
        ]
        
        for exec_id in old_executions:
            del self.task_executions[exec_id]
        
        logger.info(f"Cleaned up {len(old_executions)} old execution records")
        return len(old_executions)