"""Enhanced Hybrid Data Access Layer with integrated cache management."""

from __future__ import annotations

import asyncio
import logging
import os
from enum import Enum
from typing import Any, TypeVar

from shared.cache.cache_manager import CacheConfig, CacheManager
from shared.cache.cache_warmer import CacheWarmer, WarmingPriority
from shared.cache.invalidation_patterns import CacheInvalidator, ChangeType, DataType
from shared.clients.airtable import AirtableClient
from shared.clients.supabase import SupabaseClient

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataSource(Enum):
    """Data source preference."""

    SUPABASE = "supabase"
    AIRTABLE = "airtable"
    CACHE = "cache"
    HYBRID = "hybrid"


class HybridDataAccessLayerV2:
    """Enhanced Hybrid DAL with intelligent cache management."""

    def __init__(
        self,
        airtable_client: AirtableClient | None = None,
        supabase_client: SupabaseClient | None = None,
        cache_config: CacheConfig | None = None,
    ):
        """Initialize Enhanced Hybrid DAL.

        Args:
            airtable_client: Airtable client instance
            supabase_client: Supabase client instance
            cache_config: Cache configuration
        """
        self.airtable_client = airtable_client or AirtableClient()
        self.supabase_client = supabase_client or SupabaseClient()

        # Initialize cache management
        self.cache_manager = CacheManager(cache_config or CacheConfig())
        self.cache_warmer = CacheWarmer(
            self.cache_manager, self.airtable_client, self.supabase_client
        )
        self.cache_invalidator = CacheInvalidator(self.cache_manager)

        # Feature flags
        self.supabase_read_enabled = (
            os.getenv("FEATURE_SUPABASE_READ_ENABLED", "true").lower() == "true"
        )
        self.supabase_write_enabled = (
            os.getenv("FEATURE_SUPABASE_WRITE_ENABLED", "false").lower() == "true"
        )
        self.airtable_fallback_enabled = (
            os.getenv("FEATURE_AIRTABLE_FALLBACK_ENABLED", "true").lower() == "true"
        )
        self.cache_enabled = (
            os.getenv("FEATURE_CACHE_ENABLED", "true").lower() == "true"
        )

        # Metrics tracking
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "supabase_hits": 0,
            "airtable_hits": 0,
            "errors": 0,
            "last_source": None,
        }

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing Hybrid DAL v2...")

        # Initialize clients
        await self.airtable_client.initialize()
        await self.supabase_client.initialize()

        # Initialize cache
        if self.cache_enabled:
            await self.cache_manager.initialize()

            # Start cache warming
            await self.cache_warmer.warm_by_priority(WarmingPriority.CRITICAL)

            # Start periodic warming in background
            asyncio.create_task(self.cache_warmer.start_periodic_warming())

        logger.info("Hybrid DAL v2 initialized successfully")

    async def get_bills(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Get bills with intelligent caching.

        Args:
            filters: Filter criteria
            limit: Maximum records
            offset: Skip records
            order_by: Sort order
            use_cache: Whether to use cache

        Returns:
            List of bills
        """
        # Generate cache key
        cache_key = self.cache_manager._generate_key(
            "bills",
            "list",
            {
                "filters": filters,
                "limit": limit,
                "offset": offset,
                "order_by": order_by,
            },
        )

        # Try cache first if enabled
        if self.cache_enabled and use_cache:
            cached = await self.cache_manager.get(
                "bills",
                "list",
                params={"filters": filters, "limit": limit, "offset": offset},
            )

            if cached is not None:
                self.metrics["cache_hits"] += 1
                self.metrics["last_source"] = DataSource.CACHE
                return cached

            self.metrics["cache_misses"] += 1

        # Try Supabase if enabled
        if self.supabase_read_enabled:
            try:
                logger.debug("Fetching bills from Supabase")
                bills = await self.supabase_client.get_bills(
                    filters=filters, limit=limit, offset=offset, order_by=order_by
                )

                self.metrics["supabase_hits"] += 1
                self.metrics["last_source"] = DataSource.SUPABASE

                # Cache the result
                if self.cache_enabled and use_cache:
                    await self.cache_manager.set(
                        "bills",
                        "list",
                        bills,
                        params={"filters": filters, "limit": limit, "offset": offset},
                        tags={"bills", "list"},
                    )

                return bills

            except Exception as e:
                logger.error(f"Supabase read failed: {e}")
                self.metrics["errors"] += 1

                if not self.airtable_fallback_enabled:
                    raise

        # Fallback to Airtable
        if self.airtable_fallback_enabled or not self.supabase_read_enabled:
            try:
                logger.debug("Fetching bills from Airtable")
                bills = await self.airtable_client.list_bills(
                    filters=filters, max_records=limit
                )

                self.metrics["airtable_hits"] += 1
                self.metrics["last_source"] = DataSource.AIRTABLE

                # Cache the result
                if self.cache_enabled and use_cache:
                    await self.cache_manager.set(
                        "bills",
                        "list",
                        bills,
                        params={"filters": filters, "limit": limit},
                        tags={"bills", "list", "airtable"},
                    )

                return bills

            except Exception as e:
                logger.error(f"Airtable read failed: {e}")
                self.metrics["errors"] += 1
                raise

        return []

    async def create_bill(
        self, data: dict[str, Any], invalidate_cache: bool = True
    ) -> dict[str, Any]:
        """Create a new bill.

        Args:
            data: Bill data
            invalidate_cache: Whether to invalidate related cache

        Returns:
            Created bill
        """
        result = None

        # Write to Airtable (source of truth in Phase 1)
        if not self.supabase_write_enabled:
            result = await self.airtable_client.create_bill(data)

            # Also write to Supabase for sync
            if self.supabase_read_enabled:
                try:
                    await self.supabase_client.create_bill(data)
                except Exception as e:
                    logger.error(f"Failed to sync create to Supabase: {e}")

        else:
            # Phase 2/3: Write to Supabase
            result = await self.supabase_client.create_bill(data)

        # Invalidate cache
        if invalidate_cache and self.cache_enabled:
            await self.cache_invalidator.invalidate_on_change(
                DataType.BILL,
                ChangeType.CREATE,
                entity_id=result.get("id"),
                new_data=result,
            )

        return result

    async def update_bill(
        self, bill_id: str, updates: dict[str, Any], invalidate_cache: bool = True
    ) -> dict[str, Any]:
        """Update a bill.

        Args:
            bill_id: Bill ID
            updates: Update data
            invalidate_cache: Whether to invalidate related cache

        Returns:
            Updated bill
        """
        # Get old data for cache invalidation
        old_data = None
        if invalidate_cache:
            old_data = await self.get_bill(bill_id, use_cache=False)

        result = None

        # Write to appropriate source
        if not self.supabase_write_enabled:
            result = await self.airtable_client.update_bill(bill_id, updates)

            # Sync to Supabase
            if self.supabase_read_enabled:
                try:
                    await self.supabase_client.update_bill(bill_id, updates)
                except Exception as e:
                    logger.error(f"Failed to sync update to Supabase: {e}")

        else:
            result = await self.supabase_client.update_bill(bill_id, updates)

        # Invalidate cache
        if invalidate_cache and self.cache_enabled:
            await self.cache_invalidator.invalidate_on_change(
                DataType.BILL,
                ChangeType.UPDATE,
                entity_id=bill_id,
                old_data=old_data,
                new_data=result,
            )

        return result

    async def get_bill(
        self, bill_id: str, use_cache: bool = True
    ) -> dict[str, Any] | None:
        """Get a single bill.

        Args:
            bill_id: Bill ID
            use_cache: Whether to use cache

        Returns:
            Bill data or None
        """

        # Define loader function
        async def load_bill():
            if self.supabase_read_enabled:
                try:
                    return await self.supabase_client.get_bill(bill_id)
                except Exception as e:
                    logger.error(f"Supabase read failed: {e}")
                    if not self.airtable_fallback_enabled:
                        raise

            # Fallback to Airtable
            return await self.airtable_client.get_bill(bill_id)

        # Use cache manager with loader
        if self.cache_enabled and use_cache:
            return await self.cache_manager.get("bills", bill_id, loader=load_bill)
        else:
            return await load_bill()

    async def get_members(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Get members with caching.

        Args:
            filters: Filter criteria
            limit: Maximum records
            offset: Skip records
            use_cache: Whether to use cache

        Returns:
            List of members
        """

        # Define loader
        async def load_members():
            if self.supabase_read_enabled:
                try:
                    return await self.supabase_client.get_members(
                        filters=filters, limit=limit, offset=offset
                    )
                except Exception as e:
                    logger.error(f"Supabase read failed: {e}")
                    if not self.airtable_fallback_enabled:
                        raise

            return await self.airtable_client.list_members(
                filters=filters, max_records=limit
            )

        # Use cache manager
        if self.cache_enabled and use_cache:
            return (
                await self.cache_manager.get(
                    "members",
                    "list",
                    params={"filters": filters, "limit": limit, "offset": offset},
                    loader=load_members,
                )
                or []
            )
        else:
            return await load_members()

    async def get_policy_categories(
        self,
        layer: str | None = None,
        parent_id: str | None = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Get policy categories with caching.

        Args:
            layer: Category layer (L1, L2, L3)
            parent_id: Parent category ID
            use_cache: Whether to use cache

        Returns:
            List of categories
        """

        # Define loader
        async def load_categories():
            if self.supabase_read_enabled:
                try:
                    return await self.supabase_client.get_policy_categories(
                        layer=layer, parent_id=parent_id
                    )
                except Exception as e:
                    logger.error(f"Supabase read failed: {e}")
                    if not self.airtable_fallback_enabled:
                        raise

            return await self.airtable_client.list_issue_categories(
                filters={"Layer": layer} if layer else None
            )

        # Use cache manager with aggressive caching (rarely changes)
        if self.cache_enabled and use_cache:
            return (
                await self.cache_manager.get(
                    "policy_categories",
                    "list",
                    params={"layer": layer, "parent_id": parent_id},
                    loader=load_categories,
                )
                or []
            )
        else:
            return await load_categories()

    async def warm_cache(self, priority: WarmingPriority = WarmingPriority.HIGH):
        """Manually trigger cache warming.

        Args:
            priority: Minimum priority to warm
        """
        if not self.cache_enabled:
            logger.warning("Cache is disabled, skipping warming")
            return

        logger.info(f"Starting manual cache warming (priority: {priority.name})")
        stats = await self.cache_warmer.warm_by_priority(priority)
        logger.info(f"Cache warming completed: {stats}")

    async def invalidate_cache(self, pattern: str, cascade: bool = False) -> int:
        """Manually invalidate cache.

        Args:
            pattern: Cache key pattern
            cascade: Whether to cascade invalidation

        Returns:
            Number of invalidated entries
        """
        if not self.cache_enabled:
            return 0

        from shared.cache.cache_manager import InvalidationPattern

        return await self.cache_manager.invalidate(
            InvalidationPattern.PATTERN, pattern, cascade=cascade
        )

    async def get_cache_statistics(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        if not self.cache_enabled:
            return {"cache_enabled": False}

        cache_stats = await self.cache_manager.get_statistics()
        warmer_stats = self.cache_warmer.get_statistics()
        invalidator_stats = self.cache_invalidator.get_statistics()

        return {
            "cache_enabled": True,
            "cache_manager": cache_stats,
            "cache_warmer": warmer_stats,
            "cache_invalidator": invalidator_stats,
            "dal_metrics": self.metrics,
        }

    async def health_check(self) -> dict[str, bool]:
        """Check health of all components.

        Returns:
            Health status
        """
        health = {"airtable": False, "supabase": False, "cache": False}

        # Check Airtable
        try:
            health["airtable"] = await self.airtable_client.health_check()
        except Exception as e:
            logger.error(f"Airtable health check failed: {e}")

        # Check Supabase
        try:
            health["supabase"] = await self.supabase_client.health_check()
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")

        # Check cache
        if self.cache_enabled:
            try:
                await self.cache_manager.redis_client.ping()
                health["cache"] = True
            except Exception as e:
                logger.error(f"Cache health check failed: {e}")

        return health

    async def close(self):
        """Close all connections."""
        logger.info("Closing Hybrid DAL v2...")

        # Stop cache warming
        if self.cache_enabled:
            self.cache_warmer.stop_periodic_warming()
            await self.cache_manager.close()

        # Close clients
        await self.airtable_client.close()
        await self.supabase_client.close()

        logger.info("Hybrid DAL v2 closed")
