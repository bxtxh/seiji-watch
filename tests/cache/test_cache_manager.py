"""Tests for cache management system."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from shared.cache.cache_manager import (
    CacheConfig,
    CacheManager,
    CacheStrategy,
    InvalidationPattern,
)
from shared.cache.cache_warmer import CacheWarmer, WarmingPriority, WarmingTask
from shared.cache.invalidation_patterns import (
    CacheInvalidator,
    ChangeType,
    DataType,
    InvalidationRule,
)


@pytest.fixture
async def redis_mock():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.scan.return_value = (0, [])
    mock.dbsize.return_value = 100
    mock.flushdb.return_value = True
    mock.info.return_value = {"used_memory_human": "10M"}
    mock.config_set.return_value = True
    return mock


@pytest.fixture
def cache_config():
    """Cache configuration for testing."""
    return CacheConfig(
        redis_url="redis://localhost:6379/0",
        ttl_aggressive=3600,
        ttl_moderate=300,
        ttl_light=60,
        ttl_real_time=10,
        use_compression=True,
        track_hit_rate=True,
        track_access_patterns=True,
    )


@pytest.fixture
async def cache_manager(cache_config, redis_mock):
    """Cache manager for testing."""
    manager = CacheManager(cache_config)
    manager.redis_client = redis_mock
    return manager


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.mark.asyncio
    async def test_initialize(self, cache_config, redis_mock):
        """Test cache manager initialization."""
        with patch("redis.asyncio.ConnectionPool.from_url") as pool_mock:
            with patch("redis.asyncio.Redis") as redis_class_mock:
                redis_class_mock.return_value = redis_mock

                manager = CacheManager(cache_config)
                await manager.initialize()

                redis_mock.ping.assert_called_once()
                redis_mock.config_set.assert_called()

    def test_generate_key(self, cache_manager):
        """Test cache key generation."""
        # Simple key
        key = cache_manager._generate_key("bills", "123")
        assert key == "cache:bills:123"

        # Key with parameters
        key = cache_manager._generate_key(
            "bills", "list", {"status": "active", "limit": 10}
        )
        assert key.startswith("cache:bills:list:")
        assert len(key.split(":")) == 4  # namespace:identifier:hash

    def test_get_strategy(self, cache_manager):
        """Test strategy selection."""
        # Direct match
        strategy = cache_manager._get_strategy("parties")
        assert strategy == CacheStrategy.AGGRESSIVE

        # Pattern match
        strategy = cache_manager._get_strategy("list_bills")
        assert strategy == CacheStrategy.MODERATE

        # Default strategy
        strategy = cache_manager._get_strategy("unknown")
        assert strategy == CacheStrategy.MODERATE

    def test_get_ttl(self, cache_manager):
        """Test TTL calculation."""
        ttl = cache_manager._get_ttl(CacheStrategy.AGGRESSIVE)
        assert ttl == 3600

        ttl = cache_manager._get_ttl(CacheStrategy.MODERATE)
        assert ttl == 300

        ttl = cache_manager._get_ttl(CacheStrategy.LIGHT)
        assert ttl == 60

        ttl = cache_manager._get_ttl(CacheStrategy.PERMANENT)
        assert ttl == 0

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_manager):
        """Test cache hit scenario."""
        # Setup cache hit
        test_data = {"id": "123", "title": "Test Bill"}
        cache_manager.redis_client.get.return_value = cache_manager._serialize(
            test_data
        )

        # Get from cache
        result = await cache_manager.get("bills", "123")

        assert result == test_data
        assert cache_manager.statistics.cache_hits == 1
        assert cache_manager.statistics.cache_misses == 0

    @pytest.mark.asyncio
    async def test_get_cache_miss_with_loader(self, cache_manager):
        """Test cache miss with loader."""
        # Setup cache miss
        cache_manager.redis_client.get.return_value = None

        # Mock loader
        test_data = {"id": "123", "title": "Test Bill"}
        loader = AsyncMock(return_value=test_data)

        # Get from cache with loader
        result = await cache_manager.get("bills", "123", loader=loader)

        assert result == test_data
        assert cache_manager.statistics.cache_misses == 1
        loader.assert_called_once()

    @pytest.mark.asyncio
    async def test_set(self, cache_manager):
        """Test setting cache value."""
        test_data = {"id": "123", "title": "Test Bill"}
        tags = {"bills", "recent"}

        result = await cache_manager.set("bills", "123", test_data, tags=tags)

        assert result is True
        cache_manager.redis_client.setex.assert_called()

        # Check registry and tag index
        key = cache_manager._generate_key("bills", "123")
        assert key in cache_manager.cache_registry
        assert "bills" in cache_manager.tag_index
        assert key in cache_manager.tag_index["bills"]

    @pytest.mark.asyncio
    async def test_invalidate_exact(self, cache_manager):
        """Test exact key invalidation."""
        key = "cache:bills:123"

        count = await cache_manager.invalidate(InvalidationPattern.EXACT, key)

        assert count == 1
        cache_manager.redis_client.delete.assert_called_with(key)

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_manager):
        """Test pattern-based invalidation."""
        pattern = "cache:bills:*"
        cache_manager.redis_client.scan.return_value = (
            0,
            [b"cache:bills:1", b"cache:bills:2"],
        )
        cache_manager.redis_client.delete.return_value = 2

        count = await cache_manager.invalidate(InvalidationPattern.PATTERN, pattern)

        assert count == 2
        cache_manager.redis_client.scan.assert_called()
        cache_manager.redis_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_by_tag(self, cache_manager):
        """Test tag-based invalidation."""
        # Setup tag index
        cache_manager.tag_index["bills"] = {
            "cache:bills:1",
            "cache:bills:2",
            "cache:bills:3",
        }
        cache_manager.redis_client.delete.return_value = 3

        count = await cache_manager.invalidate(InvalidationPattern.TAG, "bills")

        assert count == 3
        assert "bills" not in cache_manager.tag_index

    @pytest.mark.asyncio
    async def test_analyze_patterns(self, cache_manager):
        """Test access pattern analysis."""
        now = datetime.utcnow()

        # Add access patterns
        cache_manager.access_patterns["cache:bills:1"] = [
            now - timedelta(minutes=i) for i in range(15)
        ]
        cache_manager.access_patterns["cache:bills:2"] = [now - timedelta(minutes=30)]

        analysis = await cache_manager.analyze_patterns()

        assert len(analysis["hot_keys"]) > 0
        assert analysis["hot_keys"][0]["key"] == "cache:bills:1"
        assert len(analysis["cold_keys"]) > 0
        assert len(analysis["recommendations"]) > 0


class TestCacheWarmer:
    """Test cache warming functionality."""

    @pytest.fixture
    async def cache_warmer(self, cache_manager):
        """Cache warmer for testing."""
        airtable_mock = AsyncMock()
        supabase_mock = AsyncMock()

        warmer = CacheWarmer(cache_manager, airtable_mock, supabase_mock)
        return warmer

    @pytest.mark.asyncio
    async def test_warm_task(self, cache_warmer):
        """Test warming a single task."""
        # Mock data loader
        test_data = [{"id": "1", "name": "Party 1"}]
        cache_warmer.supabase_client.get_parties = AsyncMock(return_value=test_data)

        # Warm parties task
        result = await cache_warmer.warm_task("warm_parties")

        assert result is True
        task = cache_warmer.warming_tasks["warm_parties"]
        assert task.last_warmed is not None
        assert task.success_count == 1

    @pytest.mark.asyncio
    async def test_warm_by_priority(self, cache_warmer):
        """Test warming by priority."""
        # Mock loaders
        cache_warmer.supabase_client.get_parties = AsyncMock(return_value=[{"id": "1"}])
        cache_warmer.supabase_client.get_members = AsyncMock(return_value=[{"id": "1"}])

        # Warm critical priority tasks
        count = await cache_warmer.warm_by_priority(WarmingPriority.CRITICAL)

        assert count > 0

    def test_sort_by_dependencies(self, cache_warmer):
        """Test task dependency sorting."""
        tasks = [
            WarmingTask(
                name="task1",
                namespace="ns1",
                loader=lambda: None,
                priority=WarmingPriority.HIGH,
                frequency_minutes=10,
                dependencies=["task2"],
            ),
            WarmingTask(
                name="task2",
                namespace="ns2",
                loader=lambda: None,
                priority=WarmingPriority.CRITICAL,
                frequency_minutes=10,
            ),
            WarmingTask(
                name="task3",
                namespace="ns3",
                loader=lambda: None,
                priority=WarmingPriority.MEDIUM,
                frequency_minutes=10,
                dependencies=["task1", "task2"],
            ),
        ]

        sorted_tasks = cache_warmer._sort_by_dependencies(tasks)

        assert sorted_tasks[0].name == "task2"  # No dependencies
        assert sorted_tasks[1].name == "task1"  # Depends on task2
        assert sorted_tasks[2].name == "task3"  # Depends on task1 and task2


class TestCacheInvalidator:
    """Test cache invalidation patterns."""

    @pytest.fixture
    async def cache_invalidator(self, cache_manager):
        """Cache invalidator for testing."""
        return CacheInvalidator(cache_manager)

    @pytest.mark.asyncio
    async def test_invalidate_on_change(self, cache_invalidator):
        """Test invalidation on data change."""
        # Mock invalidation
        cache_invalidator.cache_manager.invalidate = AsyncMock(return_value=5)

        # Trigger invalidation
        count = await cache_invalidator.invalidate_on_change(
            DataType.BILL,
            ChangeType.UPDATE,
            entity_id="123",
            old_data={"status": "pending"},
            new_data={"status": "approved"},
        )

        assert count > 0
        cache_invalidator.cache_manager.invalidate.assert_called()

    def test_resolve_pattern(self, cache_invalidator):
        """Test pattern resolution."""
        pattern = "cache:bills:{id}:status:{old_status}:{new_status}"

        resolved = cache_invalidator._resolve_pattern(
            pattern,
            entity_id="123",
            old_data={"status": "pending"},
            new_data={"status": "approved"},
            metadata={"user": "admin"},
        )

        assert resolved == "cache:bills:123:status:pending:approved"

    @pytest.mark.asyncio
    async def test_invalidate_related(self, cache_invalidator):
        """Test related entity invalidation."""
        cache_invalidator.cache_manager.invalidate = AsyncMock(return_value=3)

        count = await cache_invalidator.invalidate_related(
            DataType.BILL, "123", "votes"
        )

        assert count > 0
        cache_invalidator.cache_manager.invalidate.assert_called()

    def test_add_rule(self, cache_invalidator):
        """Test adding invalidation rule."""
        rule = InvalidationRule(
            data_type=DataType.BILL,
            change_type=ChangeType.DELETE,
            patterns=["cache:bills:{id}"],
            cascade=True,
        )

        cache_invalidator.add_rule(rule)

        key = "bill:delete"
        assert key in cache_invalidator.invalidation_rules
        assert rule in cache_invalidator.invalidation_rules[key]

    def test_get_statistics(self, cache_invalidator):
        """Test getting invalidation statistics."""
        # Add some history
        cache_invalidator.invalidation_stats["bill:update"] = 10
        cache_invalidator.invalidation_stats["member:create"] = 5

        stats = cache_invalidator.get_statistics()

        assert stats["total_invalidations"] == 15
        assert "bill:update" in stats["invalidation_by_type"]
        assert len(stats["top_patterns"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
