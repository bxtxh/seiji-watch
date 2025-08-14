"""Cache warming service for preloading frequently accessed data."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

from shared.cache.cache_manager import CacheManager, CacheStrategy
from shared.clients.airtable import AirtableClient
from shared.clients.supabase import SupabaseClient

logger = logging.getLogger(__name__)


class WarmingPriority(Enum):
    """Priority levels for cache warming."""
    CRITICAL = 1   # Must be cached
    HIGH = 2       # Should be cached
    MEDIUM = 3     # Nice to have cached
    LOW = 4        # Cache if resources available


@dataclass
class WarmingTask:
    """Cache warming task definition."""
    name: str
    namespace: str
    loader: Callable
    priority: WarmingPriority
    frequency_minutes: int  # How often to refresh
    dependencies: List[str] = None  # Other tasks that must complete first
    last_warmed: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def needs_warming(self) -> bool:
        """Check if task needs warming."""
        if self.last_warmed is None:
            return True
        elapsed = datetime.utcnow() - self.last_warmed
        return elapsed > timedelta(minutes=self.frequency_minutes)


class CacheWarmer:
    """Service for warming cache with frequently accessed data."""
    
    def __init__(
        self,
        cache_manager: CacheManager,
        airtable_client: Optional[AirtableClient] = None,
        supabase_client: Optional[SupabaseClient] = None
    ):
        """Initialize cache warmer.
        
        Args:
            cache_manager: Cache manager instance
            airtable_client: Airtable client for data loading
            supabase_client: Supabase client for data loading
        """
        self.cache_manager = cache_manager
        self.airtable_client = airtable_client
        self.supabase_client = supabase_client
        
        self.warming_tasks: Dict[str, WarmingTask] = {}
        self.running = False
        self.warm_on_startup = True
        self.concurrent_warming_limit = 5
        
        # Register default warming tasks
        self._register_default_tasks()
        
    def _register_default_tasks(self):
        """Register default cache warming tasks."""
        
        # Critical: Parties (rarely change, frequently accessed)
        self.register_task(
            WarmingTask(
                name="warm_parties",
                namespace="parties",
                loader=self._load_parties,
                priority=WarmingPriority.CRITICAL,
                frequency_minutes=60  # Refresh every hour
            )
        )
        
        # Critical: Members (moderate changes, frequently accessed)
        self.register_task(
            WarmingTask(
                name="warm_members",
                namespace="members",
                loader=self._load_members,
                priority=WarmingPriority.CRITICAL,
                frequency_minutes=30,  # Refresh every 30 minutes
                dependencies=["warm_parties"]  # Load parties first
            )
        )
        
        # Critical: Policy Categories (static, frequently accessed)
        self.register_task(
            WarmingTask(
                name="warm_policy_categories",
                namespace="policy_categories",
                loader=self._load_policy_categories,
                priority=WarmingPriority.CRITICAL,
                frequency_minutes=120  # Refresh every 2 hours
            )
        )
        
        # High: Recent Bills
        self.register_task(
            WarmingTask(
                name="warm_recent_bills",
                namespace="bills",
                loader=self._load_recent_bills,
                priority=WarmingPriority.HIGH,
                frequency_minutes=15  # Refresh every 15 minutes
            )
        )
        
        # High: Active Meetings
        self.register_task(
            WarmingTask(
                name="warm_active_meetings",
                namespace="meetings",
                loader=self._load_active_meetings,
                priority=WarmingPriority.HIGH,
                frequency_minutes=10  # Refresh every 10 minutes
            )
        )
        
        # Medium: Popular Issues
        self.register_task(
            WarmingTask(
                name="warm_popular_issues",
                namespace="issues",
                loader=self._load_popular_issues,
                priority=WarmingPriority.MEDIUM,
                frequency_minutes=30
            )
        )
        
        # Medium: Aggregated Statistics
        self.register_task(
            WarmingTask(
                name="warm_statistics",
                namespace="statistics",
                loader=self._load_statistics,
                priority=WarmingPriority.MEDIUM,
                frequency_minutes=5,  # Refresh every 5 minutes
                dependencies=["warm_recent_bills", "warm_members"]
            )
        )
        
    def register_task(self, task: WarmingTask):
        """Register a warming task.
        
        Args:
            task: Warming task to register
        """
        self.warming_tasks[task.name] = task
        logger.info(f"Registered warming task: {task.name} (priority: {task.priority.name})")
        
    async def _load_parties(self) -> List[Dict[str, Any]]:
        """Load all parties."""
        if self.supabase_client:
            try:
                parties = await self.supabase_client.get_parties()
                logger.info(f"Loaded {len(parties)} parties for cache warming")
                return parties
            except Exception as e:
                logger.error(f"Failed to load parties from Supabase: {e}")
                
        if self.airtable_client:
            try:
                parties = await self.airtable_client.list_parties()
                logger.info(f"Loaded {len(parties)} parties from Airtable for cache warming")
                return parties
            except Exception as e:
                logger.error(f"Failed to load parties from Airtable: {e}")
                
        return []
        
    async def _load_members(self) -> List[Dict[str, Any]]:
        """Load all members."""
        if self.supabase_client:
            try:
                members = await self.supabase_client.get_members(limit=1000)
                logger.info(f"Loaded {len(members)} members for cache warming")
                return members
            except Exception as e:
                logger.error(f"Failed to load members from Supabase: {e}")
                
        if self.airtable_client:
            try:
                members = await self.airtable_client.list_members()
                logger.info(f"Loaded {len(members)} members from Airtable for cache warming")
                return members
            except Exception as e:
                logger.error(f"Failed to load members from Airtable: {e}")
                
        return []
        
    async def _load_policy_categories(self) -> List[Dict[str, Any]]:
        """Load all policy categories."""
        if self.supabase_client:
            try:
                categories = await self.supabase_client.get_policy_categories()
                logger.info(f"Loaded {len(categories)} policy categories for cache warming")
                return categories
            except Exception as e:
                logger.error(f"Failed to load policy categories: {e}")
                
        return []
        
    async def _load_recent_bills(self) -> List[Dict[str, Any]]:
        """Load recent bills."""
        if self.supabase_client:
            try:
                # Load bills from last 30 days
                cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
                bills = await self.supabase_client.get_bills(
                    filters={"submitted_date": {"gte": cutoff_date}},
                    limit=100,
                    order_by="submitted_date desc"
                )
                logger.info(f"Loaded {len(bills)} recent bills for cache warming")
                return bills
            except Exception as e:
                logger.error(f"Failed to load recent bills: {e}")
                
        return []
        
    async def _load_active_meetings(self) -> List[Dict[str, Any]]:
        """Load active meetings."""
        if self.supabase_client:
            try:
                # Load meetings from last 7 days and next 7 days
                start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
                end_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
                
                meetings = await self.supabase_client.get_meetings(
                    filters={
                        "date": {"gte": start_date, "lte": end_date}
                    },
                    limit=50
                )
                logger.info(f"Loaded {len(meetings)} active meetings for cache warming")
                return meetings
            except Exception as e:
                logger.error(f"Failed to load active meetings: {e}")
                
        return []
        
    async def _load_popular_issues(self) -> List[Dict[str, Any]]:
        """Load popular issues."""
        if self.supabase_client:
            try:
                # Load top issues by activity
                issues = await self.supabase_client.select(
                    "issues",
                    columns=["*"],
                    order_by="activity_score desc",
                    limit=50
                )
                logger.info(f"Loaded {len(issues)} popular issues for cache warming")
                return issues
            except Exception as e:
                logger.error(f"Failed to load popular issues: {e}")
                
        return []
        
    async def _load_statistics(self) -> Dict[str, Any]:
        """Load aggregated statistics."""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "counts": {},
            "recent_activity": {}
        }
        
        if self.supabase_client:
            try:
                # Get counts
                stats["counts"]["bills"] = await self.supabase_client.get_table_count("bills")
                stats["counts"]["members"] = await self.supabase_client.get_table_count("members")
                stats["counts"]["meetings"] = await self.supabase_client.get_table_count("meetings")
                stats["counts"]["speeches"] = await self.supabase_client.get_table_count("speeches")
                
                # Get recent activity
                last_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()
                
                recent_bills = await self.supabase_client.select(
                    "bills",
                    columns=["id"],
                    filters={"created_at": {"gte": last_24h}}
                )
                stats["recent_activity"]["new_bills_24h"] = len(recent_bills)
                
                logger.info("Loaded statistics for cache warming")
                
            except Exception as e:
                logger.error(f"Failed to load statistics: {e}")
                
        return stats
        
    async def warm_task(self, task_name: str) -> bool:
        """Warm cache for a specific task.
        
        Args:
            task_name: Name of the task to warm
            
        Returns:
            Success status
        """
        if task_name not in self.warming_tasks:
            logger.warning(f"Unknown warming task: {task_name}")
            return False
            
        task = self.warming_tasks[task_name]
        
        try:
            logger.info(f"Warming cache for task: {task_name}")
            
            # Load data
            data = await task.loader()
            
            if data:
                # Cache the data
                if isinstance(data, list):
                    # Cache list result
                    await self.cache_manager.set(
                        task.namespace,
                        "list",
                        data,
                        tags={"warm", task_name}
                    )
                    
                    # Also cache individual items if they have IDs
                    for item in data[:100]:  # Limit individual caching
                        if isinstance(item, dict) and "id" in item:
                            await self.cache_manager.set(
                                task.namespace,
                                item["id"],
                                item,
                                tags={"warm", task_name}
                            )
                else:
                    # Cache single result
                    await self.cache_manager.set(
                        task.namespace,
                        "aggregate",
                        data,
                        tags={"warm", task_name}
                    )
                    
            # Update task status
            task.last_warmed = datetime.utcnow()
            task.success_count += 1
            
            logger.info(f"Successfully warmed cache for task: {task_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to warm cache for task {task_name}: {e}")
            task.failure_count += 1
            return False
            
    async def warm_by_priority(self, priority: WarmingPriority) -> int:
        """Warm all tasks with given priority or higher.
        
        Args:
            priority: Minimum priority level
            
        Returns:
            Number of tasks warmed
        """
        tasks_to_warm = [
            task for task in self.warming_tasks.values()
            if task.priority.value <= priority.value and task.needs_warming
        ]
        
        # Sort by priority and dependencies
        tasks_to_warm = self._sort_by_dependencies(tasks_to_warm)
        
        warmed = 0
        for task in tasks_to_warm:
            if await self.warm_task(task.name):
                warmed += 1
                
        return warmed
        
    def _sort_by_dependencies(self, tasks: List[WarmingTask]) -> List[WarmingTask]:
        """Sort tasks by dependencies.
        
        Args:
            tasks: List of tasks to sort
            
        Returns:
            Sorted list of tasks
        """
        sorted_tasks = []
        remaining = tasks.copy()
        completed = set()
        
        while remaining:
            # Find tasks with no pending dependencies
            ready = [
                task for task in remaining
                if not task.dependencies or all(dep in completed for dep in task.dependencies)
            ]
            
            if not ready:
                # Circular dependency or missing task
                logger.warning("Circular dependency detected in warming tasks")
                sorted_tasks.extend(remaining)
                break
                
            # Sort ready tasks by priority
            ready.sort(key=lambda t: t.priority.value)
            
            for task in ready:
                sorted_tasks.append(task)
                completed.add(task.name)
                remaining.remove(task)
                
        return sorted_tasks
        
    async def warm_all(self) -> Dict[str, int]:
        """Warm all registered tasks.
        
        Returns:
            Statistics of warming operation
        """
        logger.info("Starting full cache warming...")
        
        start_time = datetime.utcnow()
        stats = {
            "total": len(self.warming_tasks),
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Sort all tasks by dependencies
        all_tasks = self._sort_by_dependencies(list(self.warming_tasks.values()))
        
        # Process tasks with concurrency limit
        semaphore = asyncio.Semaphore(self.concurrent_warming_limit)
        
        async def warm_with_limit(task: WarmingTask):
            async with semaphore:
                if not task.needs_warming:
                    stats["skipped"] += 1
                    return
                    
                if await self.warm_task(task.name):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    
        # Warm tasks concurrently
        await asyncio.gather(*[warm_with_limit(task) for task in all_tasks])
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            f"Cache warming completed in {duration:.2f}s: "
            f"{stats['success']} success, {stats['failed']} failed, {stats['skipped']} skipped"
        )
        
        return stats
        
    async def start_periodic_warming(self):
        """Start periodic cache warming."""
        self.running = True
        
        logger.info("Starting periodic cache warming service")
        
        # Initial warming
        if self.warm_on_startup:
            await self.warm_by_priority(WarmingPriority.HIGH)
            
        while self.running:
            try:
                # Check each task for warming needs
                for task in self.warming_tasks.values():
                    if task.needs_warming:
                        asyncio.create_task(self.warm_task(task.name))
                        
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in periodic warming: {e}")
                await asyncio.sleep(60)
                
    def stop_periodic_warming(self):
        """Stop periodic cache warming."""
        self.running = False
        logger.info("Stopped periodic cache warming service")
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get warming statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_tasks": len(self.warming_tasks),
            "tasks": []
        }
        
        for task in self.warming_tasks.values():
            stats["tasks"].append({
                "name": task.name,
                "namespace": task.namespace,
                "priority": task.priority.name,
                "frequency_minutes": task.frequency_minutes,
                "last_warmed": task.last_warmed.isoformat() if task.last_warmed else None,
                "needs_warming": task.needs_warming,
                "success_count": task.success_count,
                "failure_count": task.failure_count,
                "success_rate": (
                    task.success_count / (task.success_count + task.failure_count) * 100
                    if (task.success_count + task.failure_count) > 0 else 0
                )
            })
            
        # Sort by priority
        stats["tasks"].sort(key=lambda t: t["priority"])
        
        return stats