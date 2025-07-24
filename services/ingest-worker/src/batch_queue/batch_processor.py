"""
Batch Processing Queue System for Diet Issue Tracker

Provides asynchronous task processing capabilities for:
- Embedding generation batches
- Transcription processing queues
- Data processing pipelines
- Resource optimization for batch operations
- Job status tracking and retry logic
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from google.cloud import pubsub_v1

    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False
    pubsub_v1 = None

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskType(str, Enum):
    """Available task types"""

    GENERATE_EMBEDDINGS = "generate_embeddings"
    TRANSCRIBE_AUDIO = "transcribe_audio"
    PROCESS_VOTING_DATA = "process_voting_data"
    SCRAPE_BILLS = "scrape_bills"
    ANALYZE_CONTENT = "analyze_content"
    CUSTOM = "custom"


@dataclass
class BatchTask:
    """Individual task in a batch processing queue"""

    task_id: str
    task_type: TaskType
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300  # 5 minutes default
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error_message: str | None = None
    tags: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)  # Task dependencies

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "payload": self.payload,
            "result": self.result,
            "error_message": self.error_message,
            "tags": self.tags,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchTask":
        """Create task from dictionary representation"""
        task = cls(
            task_id=data["task_id"],
            task_type=TaskType(data["task_type"]),
            priority=TaskPriority(data.get("priority", TaskPriority.NORMAL.value)),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            created_at=datetime.fromisoformat(data["created_at"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds", 300),
            payload=data.get("payload", {}),
            result=data.get("result"),
            error_message=data.get("error_message"),
            tags=data.get("tags", []),
            depends_on=data.get("depends_on", []),
        )

        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])

        return task


@dataclass
class BatchConfig:
    """Configuration for batch processing"""

    max_concurrent_tasks: int = 5
    max_queue_size: int = 1000
    retry_delay_seconds: int = 60
    task_timeout_seconds: int = 300
    enable_persistence: bool = True
    persistence_backend: str = "file"  # "file", "redis", "pubsub"
    redis_url: str | None = None
    pubsub_topic: str | None = None
    batch_size: int = 10
    processing_interval_seconds: float = 1.0


class TaskProcessor:
    """Base class for task processors"""

    async def process(self, task: BatchTask) -> dict[str, Any]:
        """
        Process a single task

        Args:
            task: The task to process

        Returns:
            Dictionary containing task results

        Raises:
            Exception: If task processing fails
        """
        raise NotImplementedError("Subclasses must implement process method")


class EmbeddingTaskProcessor(TaskProcessor):
    """Task processor for embedding generation"""

    def __init__(self, vector_client):
        self.vector_client = vector_client

    async def process(self, task: BatchTask) -> dict[str, Any]:
        """Process embedding generation task"""
        payload = task.payload
        texts = payload.get("texts", [])
        metadata_list = payload.get("metadata_list", [])

        if not texts:
            raise ValueError("No texts provided for embedding generation")

        results = []

        for i, text in enumerate(texts):
            try:
                # Generate embedding
                embedding = self.vector_client.generate_embedding(text)

                # Store if metadata provided
                weaviate_uuid = None
                if i < len(metadata_list) and metadata_list[i]:
                    metadata = metadata_list[i]
                    if "bill_number" in metadata:
                        weaviate_uuid = self.vector_client.store_bill_embedding(
                            metadata, embedding
                        )
                    elif "speaker" in metadata:
                        weaviate_uuid = self.vector_client.store_speech_embedding(
                            metadata, embedding
                        )

                results.append(
                    {
                        "text_index": i,
                        "embedding_dimensions": embedding.dimensions,
                        "model": embedding.model,
                        "weaviate_uuid": weaviate_uuid,
                        "success": True,
                    }
                )

            except Exception as e:
                logger.error(f"Failed to process embedding for text {i}: {e}")
                results.append({"text_index": i, "error": str(e), "success": False})

        successful = len([r for r in results if r.get("success")])

        return {
            "total_texts": len(texts),
            "successful_embeddings": successful,
            "failed_embeddings": len(texts) - successful,
            "results": results,
        }


class TranscriptionTaskProcessor(TaskProcessor):
    """Task processor for audio transcription"""

    def __init__(self, whisper_client):
        self.whisper_client = whisper_client

    async def process(self, task: BatchTask) -> dict[str, Any]:
        """Process transcription task"""
        payload = task.payload
        audio_urls = payload.get("audio_urls", [])
        video_urls = payload.get("video_urls", [])
        language = payload.get("language", "ja")

        if not audio_urls and not video_urls:
            raise ValueError("No audio or video URLs provided for transcription")

        results = []

        # Process audio URLs
        for i, audio_url in enumerate(audio_urls):
            try:
                # Note: This would need actual implementation based on whisper_client API
                # For now, this is a placeholder structure
                result = {
                    "url": audio_url,
                    "type": "audio",
                    "index": i,
                    "success": True,
                    "text": "Transcription placeholder",  # Actual transcription would go here
                    "duration": 0.0,
                    "language": language,
                }
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to transcribe audio {i}: {e}")
                results.append(
                    {
                        "url": audio_url,
                        "type": "audio",
                        "index": i,
                        "error": str(e),
                        "success": False,
                    }
                )

        # Process video URLs
        for i, video_url in enumerate(video_urls):
            try:
                # Download and transcribe video
                transcription_result, audio_file = (
                    self.whisper_client.download_and_transcribe_video(video_url)
                )

                result = {
                    "url": video_url,
                    "type": "video",
                    "index": i,
                    "success": True,
                    "text": transcription_result.text,
                    "duration": transcription_result.duration,
                    "language": transcription_result.language,
                    "segments_count": (
                        len(transcription_result.segments)
                        if transcription_result.segments
                        else 0
                    ),
                }
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to transcribe video {i}: {e}")
                results.append(
                    {
                        "url": video_url,
                        "type": "video",
                        "index": i,
                        "error": str(e),
                        "success": False,
                    }
                )

        successful = len([r for r in results if r.get("success")])

        return {
            "total_urls": len(audio_urls) + len(video_urls),
            "successful_transcriptions": successful,
            "failed_transcriptions": len(results) - successful,
            "results": results,
        }


class BatchProcessor:
    """
    Main batch processing system with queue management
    """

    def __init__(self, config: BatchConfig):
        self.config = config
        self.task_queues: dict[TaskPriority, deque] = {
            priority: deque() for priority in TaskPriority
        }
        self.active_tasks: dict[str, BatchTask] = {}
        self.completed_tasks: dict[str, BatchTask] = {}
        self.failed_tasks: dict[str, BatchTask] = {}
        self.task_processors: dict[TaskType, TaskProcessor] = {}

        # Concurrency control
        self.semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self.processing = False
        self._stop_event = asyncio.Event()

        # Persistence
        self.redis_client: redis.Redis | None = None
        self.pubsub_client: pubsub_v1.PublisherClient | None = None

        # Statistics
        self.stats = defaultdict(int)

        # Initialize persistence backend
        self._init_persistence()

    def _init_persistence(self):
        """Initialize persistence backend"""
        if not self.config.enable_persistence:
            return

        if self.config.persistence_backend == "redis" and self.config.redis_url:
            try:
                self.redis_client = redis.from_url(self.config.redis_url)
                logger.info("Redis persistence initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")

        elif self.config.persistence_backend == "pubsub" and self.config.pubsub_topic:
            try:
                self.pubsub_client = pubsub_v1.PublisherClient()
                logger.info("Pub/Sub persistence initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Pub/Sub: {e}")

    def register_processor(self, task_type: TaskType, processor: TaskProcessor):
        """Register a task processor for a specific task type"""
        self.task_processors[task_type] = processor
        logger.info(f"Registered processor for task type: {task_type}")

    async def add_task(
        self,
        task_type: TaskType,
        payload: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        tags: list[str] | None = None,
        depends_on: list[str] | None = None,
        task_id: str | None = None,
    ) -> str:
        """
        Add a new task to the processing queue

        Args:
            task_type: Type of task to process
            payload: Task data and parameters
            priority: Task priority level
            max_retries: Maximum number of retry attempts
            timeout_seconds: Task timeout in seconds
            tags: Optional tags for task categorization
            depends_on: List of task IDs this task depends on
            task_id: Optional custom task ID

        Returns:
            Generated task ID
        """
        if task_id is None:
            task_id = f"{task_type.value}_{uuid.uuid4().hex[:8]}"

        task = BatchTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            payload=payload,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            tags=tags or [],
            depends_on=depends_on or [],
        )

        # Check queue size limit
        total_queued = sum(len(queue) for queue in self.task_queues.values())
        if total_queued >= self.config.max_queue_size:
            raise ValueError(f"Queue is full (max size: {self.config.max_queue_size})")

        # Add to appropriate priority queue
        task.status = TaskStatus.QUEUED
        self.task_queues[priority].append(task)
        self.stats["tasks_queued"] += 1

        # Persist if enabled
        await self._persist_task(task)

        logger.info(
            f"Added task to queue: {task_id} (type: {task_type}, priority: {priority})"
        )
        return task_id

    async def _persist_task(self, task: BatchTask):
        """Persist task to configured backend"""
        if not self.config.enable_persistence:
            return

        try:
            task_data = task.to_dict()

            if self.redis_client:
                # Store in Redis
                key = f"batch_task:{task.task_id}"
                await self.redis_client.set(
                    key, json.dumps(task_data), ex=86400
                )  # 24 hour expiry

            elif self.config.persistence_backend == "file":
                # Store in file
                cache_dir = Path("/tmp/batch_processor_cache")
                cache_dir.mkdir(exist_ok=True)
                task_file = cache_dir / f"{task.task_id}.json"
                with open(task_file, "w") as f:
                    json.dump(task_data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to persist task {task.task_id}: {e}")

    async def start_processing(self):
        """Start the batch processing loop"""
        if self.processing:
            logger.warning("Batch processor already running")
            return

        self.processing = True
        self._stop_event.clear()

        logger.info("Starting batch processor")

        try:
            while self.processing and not self._stop_event.is_set():
                await self._process_batch()
                await asyncio.sleep(self.config.processing_interval_seconds)

        except Exception as e:
            logger.error(f"Batch processor error: {e}")
        finally:
            self.processing = False
            logger.info("Batch processor stopped")

    async def stop_processing(self):
        """Stop the batch processing loop"""
        self.processing = False
        self._stop_event.set()

        # Wait for active tasks to complete (with timeout)
        if self.active_tasks:
            logger.info(
                f"Waiting for {len(self.active_tasks)} active tasks to complete..."
            )
            await asyncio.sleep(5)  # Give tasks time to finish

    async def _process_batch(self):
        """Process a batch of tasks"""
        # Get next batch of tasks to process
        tasks_to_process = []

        # Process in priority order
        for priority in [
            TaskPriority.URGENT,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ]:
            queue = self.task_queues[priority]

            while queue and len(tasks_to_process) < self.config.batch_size:
                task = queue.popleft()

                # Check dependencies
                if await self._dependencies_satisfied(task):
                    tasks_to_process.append(task)
                else:
                    # Put back in queue for later
                    queue.append(task)
                    break

        # Process tasks concurrently
        if tasks_to_process:
            await asyncio.gather(
                *[self._process_single_task(task) for task in tasks_to_process],
                return_exceptions=True,
            )

    async def _dependencies_satisfied(self, task: BatchTask) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.depends_on:
            return True

        for dep_task_id in task.depends_on:
            # Check if dependency is completed
            if dep_task_id in self.completed_tasks:
                continue
            elif dep_task_id in self.failed_tasks:
                # Dependency failed, mark this task as failed too
                task.status = TaskStatus.FAILED
                task.error_message = f"Dependency {dep_task_id} failed"
                self.failed_tasks[task.task_id] = task
                return False
            else:
                # Dependency not yet completed
                return False

        return True

    async def _process_single_task(self, task: BatchTask):
        """Process a single task with concurrency control"""
        async with self.semaphore:
            try:
                # Check if processor is available
                processor = self.task_processors.get(task.task_type)
                if not processor:
                    raise ValueError(
                        f"No processor registered for task type: {task.task_type}"
                    )

                # Update task status
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now()
                self.active_tasks[task.task_id] = task

                logger.info(f"Processing task: {task.task_id}")

                # Process with timeout
                try:
                    result = await asyncio.wait_for(
                        processor.process(task), timeout=task.timeout_seconds
                    )

                    # Task completed successfully
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.result = result

                    self.completed_tasks[task.task_id] = task
                    self.stats["tasks_completed"] += 1

                    logger.info(f"Task completed: {task.task_id}")

                except TimeoutError:
                    raise Exception(
                        f"Task timed out after {task.timeout_seconds} seconds"
                    )

            except Exception as e:
                # Task failed
                task.retry_count += 1
                task.error_message = str(e)

                if task.retry_count < task.max_retries:
                    # Retry task
                    task.status = TaskStatus.RETRYING

                    # Add back to queue with delay
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    self.task_queues[task.priority].append(task)

                    logger.warning(
                        f"Task failed, retrying ({task.retry_count}/{task.max_retries}): {task.task_id}"
                    )
                    self.stats["tasks_retried"] += 1

                else:
                    # Max retries exceeded
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()

                    self.failed_tasks[task.task_id] = task
                    self.stats["tasks_failed"] += 1

                    logger.error(f"Task failed permanently: {task.task_id} - {e}")

            finally:
                # Remove from active tasks
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]

                # Persist updated task
                await self._persist_task(task)

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get status of a specific task"""
        # Check active tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].to_dict()

        # Check completed tasks
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id].to_dict()

        # Check failed tasks
        if task_id in self.failed_tasks:
            return self.failed_tasks[task_id].to_dict()

        # Check queued tasks
        for priority_queue in self.task_queues.values():
            for task in priority_queue:
                if task.task_id == task_id:
                    return task.to_dict()

        return None

    def get_queue_status(self) -> dict[str, Any]:
        """Get overall queue status and statistics"""
        queue_lengths = {
            priority.value: len(queue) for priority, queue in self.task_queues.items()
        }

        return {
            "processing": self.processing,
            "queue_lengths": queue_lengths,
            "total_queued": sum(queue_lengths.values()),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "statistics": dict(self.stats),
            "configuration": {
                "max_concurrent_tasks": self.config.max_concurrent_tasks,
                "max_queue_size": self.config.max_queue_size,
                "batch_size": self.config.batch_size,
            },
        }

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or active task"""
        # Check queued tasks
        for priority_queue in self.task_queues.values():
            for i, task in enumerate(priority_queue):
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    del priority_queue[i]
                    self.failed_tasks[task_id] = task
                    await self._persist_task(task)
                    logger.info(f"Cancelled queued task: {task_id}")
                    return True

        # Check active tasks (these can't be cancelled immediately)
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            # Note: The task will still complete processing, but will be marked as
            # cancelled
            logger.info(f"Marked active task for cancellation: {task_id}")
            return True

        return False

    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed and failed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        cleaned_count = 0

        # Clean completed tasks
        expired_completed = [
            task_id
            for task_id, task in self.completed_tasks.items()
            if task.completed_at and task.completed_at < cutoff_time
        ]

        for task_id in expired_completed:
            del self.completed_tasks[task_id]
            cleaned_count += 1

        # Clean failed tasks
        expired_failed = [
            task_id
            for task_id, task in self.failed_tasks.items()
            if task.completed_at and task.completed_at < cutoff_time
        ]

        for task_id in expired_failed:
            del self.failed_tasks[task_id]
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} old tasks")
        return cleaned_count
