"""
Temporary mock implementation for Docker testing.
This should be replaced with the actual implementation.
"""

from typing import Dict, Any
from datetime import datetime


class IssueRelationshipBatchProcessor:
    """Mock batch processor for Docker testing."""

    def __init__(self):
        self.jobs = {}

    async def get_status(self) -> Dict[str, Any]:
        """Return mock status."""
        return {
            "status": "idle",
            "last_run": None,
            "next_run": None,
            "total_processed": 0,
        }

    async def trigger_manual_run(self) -> Dict[str, Any]:
        """Mock manual trigger."""
        return {
            "job_id": "mock_job_123",
            "status": "started",
            "timestamp": datetime.now().isoformat(),
        }

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Mock job status."""
        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "message": "Mock job completed",
        }

    async def get_config(self) -> Dict[str, Any]:
        """Mock configuration."""
        return {"enabled": True, "schedule": "0 2 * * *", "batch_size": 100}

    async def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mock config update."""
        return {"status": "updated", "config": config}
