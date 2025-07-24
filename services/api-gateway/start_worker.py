#!/usr/bin/env python3
"""RQ worker startup script."""

import logging
import os
import sys
from pathlib import Path

from batch.task_queue import TaskPriority, task_queue

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start RQ worker."""
    logger.info("Starting RQ worker...")

    # Get worker configuration from environment
    worker_name = os.getenv("WORKER_NAME", "diet-tracker-worker")
    worker_queues = os.getenv("WORKER_QUEUES", "urgent,high,normal,low").split(",")

    # Convert queue names to TaskPriority enums
    queue_priorities = []
    for queue_name in worker_queues:
        try:
            priority = TaskPriority(queue_name.strip())
            queue_priorities.append(priority)
        except ValueError:
            logger.warning(f"Invalid queue name: {queue_name}")

    if not queue_priorities:
        # Default to all queues in priority order
        queue_priorities = [
            TaskPriority.URGENT,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW
        ]

    logger.info(
        f"Worker {worker_name} will process queues: {[q.value for q in queue_priorities]}")

    # Start worker
    try:
        worker = task_queue.start_worker(
            queues=queue_priorities,
            worker_name=worker_name
        )

        logger.info(f"Worker {worker_name} started successfully")
        worker.work()

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
