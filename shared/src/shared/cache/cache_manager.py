"""Cache management and optimization for migration system."""

from __future__ import annotations

import asyncio
import builtins
import hashlib
import json
import logging
import pickle
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for different data types."""

    AGGRESSIVE = "aggressive"  # Long TTL, frequent access
    MODERATE = "moderate"  # Medium TTL, moderate access
    LIGHT = "light"  # Short TTL, infrequent access
    REAL_TIME = "real_time"  # Very short TTL, real-time data
    PERMANENT = "permanent"  # No expiry, static data


class InvalidationPattern(Enum):
    """Cache invalidation patterns."""

    EXACT = "exact"  # Invalidate exact key
    PREFIX = "prefix"  # Invalidate by prefix
    PATTERN = "pattern"  # Invalidate by pattern
    TAG = "tag"  # Invalidate by tag
    CASCADE = "cascade"  # Cascading invalidation
    TIME_BASED = "time_based"  # Time-based invalidation


@dataclass
class CacheConfig:
    """Configuration for cache behavior."""

    # Redis connection
    redis_url: str = "redis://localhost:6379/0"
    max_connections: int = 50

    # TTL settings (in seconds)
    ttl_aggressive: int = 3600  # 1 hour
    ttl_moderate: int = 300  # 5 minutes
    ttl_light: int = 60  # 1 minute
    ttl_real_time: int = 10  # 10 seconds

    # Cache warming
    warm_on_startup: bool = True
    warm_batch_size: int = 100
    warm_interval_minutes: int = 30

    # Eviction policy
    max_memory: str = "1gb"
    eviction_policy: str = "allkeys-lru"

    # Monitoring
    track_hit_rate: bool = True
    track_access_patterns: bool = True

    # Serialization
    use_compression: bool = True
    compression_threshold: int = 1024  # bytes


@dataclass
class CacheEntry:
    """Cache entry metadata."""

    key: str
    value: Any
    ttl: int
    strategy: CacheStrategy
    tags: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False


@dataclass
class CacheStatistics:
    """Cache performance statistics."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_evictions: int = 0
    total_invalidations: int = 0
    total_warm_loads: int = 0
    avg_response_time_ms: float = 0.0
    memory_usage_bytes: int = 0
    active_keys: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_misses / self.total_requests) * 100


class CacheManager:
    """Intelligent cache management system."""

    def __init__(self, config: CacheConfig | None = None):
        """Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config or CacheConfig()
        self.redis_client: redis.Redis | None = None
        self.connection_pool: ConnectionPool | None = None
        self.statistics = CacheStatistics()

        # Cache metadata tracking
        self.cache_registry: dict[str, CacheEntry] = {}
        self.tag_index: dict[str, set[str]] = {}  # tag -> keys
        self.access_patterns: dict[str, list[datetime]] = {}  # key -> access times

        # Warm cache configuration
        self.warm_cache_keys: set[str] = set()
        self.warm_cache_loaders: dict[str, Callable] = {}

        # Strategy configurations
        self.strategy_configs: dict[str, CacheStrategy] = {
            # Table-level strategies
            "parties": CacheStrategy.AGGRESSIVE,
            "members": CacheStrategy.AGGRESSIVE,
            "policy_categories": CacheStrategy.AGGRESSIVE,
            "bills": CacheStrategy.MODERATE,
            "meetings": CacheStrategy.MODERATE,
            "speeches": CacheStrategy.LIGHT,
            "votes": CacheStrategy.LIGHT,
            "issues": CacheStrategy.MODERATE,
            # Operation-level strategies
            "list_*": CacheStrategy.MODERATE,
            "get_*": CacheStrategy.AGGRESSIVE,
            "search_*": CacheStrategy.LIGHT,
            "aggregate_*": CacheStrategy.MODERATE,
        }

    async def initialize(self):
        """Initialize Redis connection and warm cache."""
        try:
            # Create connection pool
            self.connection_pool = ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                decode_responses=False,  # Handle binary data
            )

            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # Test connection
            await self.redis_client.ping()
            logger.info("Cache manager initialized successfully")

            # Configure Redis settings
            await self._configure_redis()

            # Warm cache if enabled
            if self.config.warm_on_startup:
                await self.warm_cache()

        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            raise

    async def _configure_redis(self):
        """Configure Redis settings."""
        if not self.redis_client:
            return

        try:
            # Set memory limit and eviction policy
            await self.redis_client.config_set("maxmemory", self.config.max_memory)
            await self.redis_client.config_set(
                "maxmemory-policy", self.config.eviction_policy
            )

        except Exception as e:
            logger.warning(f"Could not configure Redis settings: {e}")

    def _generate_key(
        self, namespace: str, identifier: str, params: dict | None = None
    ) -> str:
        """Generate cache key.

        Args:
            namespace: Cache namespace (e.g., table name)
            identifier: Unique identifier
            params: Additional parameters

        Returns:
            Cache key
        """
        key_parts = ["cache", namespace, identifier]

        if params:
            # Sort params for consistent key generation
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)

        return ":".join(key_parts)

    def _get_strategy(self, namespace: str) -> CacheStrategy:
        """Get cache strategy for namespace.

        Args:
            namespace: Cache namespace

        Returns:
            Cache strategy
        """
        # Direct match
        if namespace in self.strategy_configs:
            return self.strategy_configs[namespace]

        # Pattern match
        for pattern, strategy in self.strategy_configs.items():
            if "*" in pattern:
                prefix = pattern.replace("*", "")
                if namespace.startswith(prefix):
                    return strategy

        # Default strategy
        return CacheStrategy.MODERATE

    def _get_ttl(self, strategy: CacheStrategy) -> int:
        """Get TTL for cache strategy.

        Args:
            strategy: Cache strategy

        Returns:
            TTL in seconds
        """
        ttl_map = {
            CacheStrategy.AGGRESSIVE: self.config.ttl_aggressive,
            CacheStrategy.MODERATE: self.config.ttl_moderate,
            CacheStrategy.LIGHT: self.config.ttl_light,
            CacheStrategy.REAL_TIME: self.config.ttl_real_time,
            CacheStrategy.PERMANENT: 0,  # No expiry
        }
        return ttl_map.get(strategy, self.config.ttl_moderate)

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for caching.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes
        """
        # Use pickle for complex objects
        serialized = pickle.dumps(value)

        # Compress if enabled and above threshold
        if (
            self.config.use_compression
            and len(serialized) > self.config.compression_threshold
        ):
            import zlib

            serialized = zlib.compress(serialized)

        return serialized

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize cached value.

        Args:
            data: Serialized bytes

        Returns:
            Deserialized value
        """
        try:
            # Try decompression first
            if self.config.use_compression:
                try:
                    import zlib

                    data = zlib.decompress(data)
                except:
                    pass  # Not compressed

            return pickle.loads(data)

        except Exception as e:
            logger.error(f"Failed to deserialize cache data: {e}")
            return None

    async def get(
        self,
        namespace: str,
        identifier: str,
        params: dict | None = None,
        loader: Callable | None = None,
    ) -> Any | None:
        """Get value from cache with automatic loading.

        Args:
            namespace: Cache namespace
            identifier: Unique identifier
            params: Additional parameters
            loader: Function to load data if cache miss

        Returns:
            Cached or loaded value
        """
        if not self.redis_client:
            # Cache disabled, use loader
            if loader:
                return (
                    await loader() if asyncio.iscoroutinefunction(loader) else loader()
                )
            return None

        key = self._generate_key(namespace, identifier, params)
        self.statistics.total_requests += 1

        try:
            # Try to get from cache
            start_time = asyncio.get_event_loop().time()
            cached_data = await self.redis_client.get(key)
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            # Update average response time (avoid division by zero)
            if self.statistics.total_requests > 1:
                # For subsequent requests, calculate weighted average
                self.statistics.avg_response_time_ms = (
                    self.statistics.avg_response_time_ms
                    * (self.statistics.total_requests - 1)
                    + response_time
                ) / self.statistics.total_requests
            else:
                # For first request, just use the response time
                self.statistics.avg_response_time_ms = response_time

            if cached_data:
                # Cache hit
                self.statistics.cache_hits += 1
                value = self._deserialize(cached_data)

                # Track access pattern
                if self.config.track_access_patterns:
                    await self._track_access(key)

                logger.debug(f"Cache hit for {key}")
                return value

            # Cache miss
            self.statistics.cache_misses += 1
            logger.debug(f"Cache miss for {key}")

            # Load data if loader provided
            if loader:
                value = (
                    await loader() if asyncio.iscoroutinefunction(loader) else loader()
                )

                # Store in cache
                if value is not None:
                    await self.set(namespace, identifier, value, params)

                return value

            return None

        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            # Fallback to loader
            if loader:
                return (
                    await loader() if asyncio.iscoroutinefunction(loader) else loader()
                )
            return None

    async def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        params: dict | None = None,
        tags: builtins.set[str] | None = None,
        ttl_override: int | None = None,
    ) -> bool:
        """Set value in cache.

        Args:
            namespace: Cache namespace
            identifier: Unique identifier
            value: Value to cache
            params: Additional parameters
            tags: Tags for invalidation
            ttl_override: Override TTL

        Returns:
            Success status
        """
        if not self.redis_client:
            return False

        key = self._generate_key(namespace, identifier, params)
        strategy = self._get_strategy(namespace)
        ttl = ttl_override or self._get_ttl(strategy)

        try:
            # Serialize value
            serialized = self._serialize(value)

            # Store in Redis
            if ttl > 0:
                await self.redis_client.setex(key, ttl, serialized)
            else:
                await self.redis_client.set(key, serialized)

            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl,
                strategy=strategy,
                tags=tags or set(),
                size_bytes=len(serialized),
                compressed=self.config.use_compression
                and len(serialized) > self.config.compression_threshold,
            )

            # Update registry
            self.cache_registry[key] = entry

            # Update tag index
            if tags:
                for tag in tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = set()
                    self.tag_index[tag].add(key)

            logger.debug(f"Cached {key} with TTL {ttl}s")
            return True

        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    async def invalidate(
        self, pattern: InvalidationPattern, target: str, cascade: bool = False
    ) -> int:
        """Invalidate cache entries.

        Args:
            pattern: Invalidation pattern
            target: Target for invalidation
            cascade: Enable cascading invalidation

        Returns:
            Number of invalidated entries
        """
        if not self.redis_client:
            return 0

        invalidated = 0

        try:
            if pattern == InvalidationPattern.EXACT:
                # Invalidate exact key
                result = await self.redis_client.delete(target)
                invalidated = result

            elif pattern == InvalidationPattern.PREFIX:
                # Invalidate by prefix
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, match=f"{target}*", count=100
                    )
                    if keys:
                        result = await self.redis_client.delete(*keys)
                        invalidated += result
                    if cursor == 0:
                        break

            elif pattern == InvalidationPattern.PATTERN:
                # Invalidate by pattern
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, match=target, count=100
                    )
                    if keys:
                        result = await self.redis_client.delete(*keys)
                        invalidated += result
                    if cursor == 0:
                        break

            elif pattern == InvalidationPattern.TAG:
                # Invalidate by tag
                if target in self.tag_index:
                    keys = list(self.tag_index[target])
                    if keys:
                        result = await self.redis_client.delete(*keys)
                        invalidated = result
                    # Clear tag index
                    del self.tag_index[target]

            elif pattern == InvalidationPattern.CASCADE:
                # Cascading invalidation
                # First invalidate the target
                result = await self.redis_client.delete(target)
                invalidated = result

                # Then invalidate related keys
                if cascade:
                    # Invalidate dependent keys (implement based on your logic)
                    related_pattern = f"*:{target}:*"
                    cursor = 0
                    while True:
                        cursor, keys = await self.redis_client.scan(
                            cursor, match=related_pattern, count=100
                        )
                        if keys:
                            result = await self.redis_client.delete(*keys)
                            invalidated += result
                        if cursor == 0:
                            break

            # Update statistics
            self.statistics.total_invalidations += invalidated

            logger.info(
                f"Invalidated {invalidated} cache entries with pattern {pattern.value}: {target}"
            )
            return invalidated

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    async def warm_cache(self, keys: list[str] | None = None):
        """Warm cache with frequently accessed data.

        Args:
            keys: Specific keys to warm (optional)
        """
        logger.info("Starting cache warming...")

        warm_keys = keys or list(self.warm_cache_keys)
        warmed = 0

        for key in warm_keys:
            if key in self.warm_cache_loaders:
                try:
                    # Get loader for this key
                    loader = self.warm_cache_loaders[key]

                    # Parse key to get namespace and identifier
                    parts = key.split(":")
                    if len(parts) >= 3:
                        namespace = parts[1]
                        identifier = parts[2]

                        # Load and cache data
                        value = (
                            await loader()
                            if asyncio.iscoroutinefunction(loader)
                            else loader()
                        )
                        if value is not None:
                            await self.set(namespace, identifier, value)
                            warmed += 1

                except Exception as e:
                    logger.error(f"Failed to warm cache for {key}: {e}")

        self.statistics.total_warm_loads += warmed
        logger.info(f"Cache warming completed: {warmed} keys loaded")

    def register_warm_cache(
        self,
        namespace: str,
        identifier: str,
        loader: Callable,
        params: dict | None = None,
    ):
        """Register a key for cache warming.

        Args:
            namespace: Cache namespace
            identifier: Unique identifier
            loader: Function to load data
            params: Additional parameters
        """
        key = self._generate_key(namespace, identifier, params)
        self.warm_cache_keys.add(key)
        self.warm_cache_loaders[key] = loader

    async def _track_access(self, key: str):
        """Track cache access pattern.

        Args:
            key: Cache key
        """
        now = datetime.utcnow()

        if key not in self.access_patterns:
            self.access_patterns[key] = []

        self.access_patterns[key].append(now)

        # Keep only recent accesses (last hour)
        cutoff = now - timedelta(hours=1)
        self.access_patterns[key] = [t for t in self.access_patterns[key] if t > cutoff]

        # Update cache entry
        if key in self.cache_registry:
            self.cache_registry[key].accessed_at = now
            self.cache_registry[key].access_count += 1

    async def analyze_patterns(self) -> dict[str, Any]:
        """Analyze cache access patterns.

        Returns:
            Pattern analysis results
        """
        hot_keys = []
        cold_keys = []

        now = datetime.utcnow()

        for key, accesses in self.access_patterns.items():
            recent_accesses = len(accesses)

            if recent_accesses > 10:  # Hot key threshold
                hot_keys.append(
                    {
                        "key": key,
                        "accesses": recent_accesses,
                        "last_access": max(accesses) if accesses else None,
                    }
                )
            elif recent_accesses < 2:  # Cold key threshold
                cold_keys.append(
                    {
                        "key": key,
                        "accesses": recent_accesses,
                        "last_access": max(accesses) if accesses else None,
                    }
                )

        # Sort by access count
        hot_keys.sort(key=lambda x: x["accesses"], reverse=True)
        cold_keys.sort(key=lambda x: x["accesses"])

        return {
            "hot_keys": hot_keys[:10],  # Top 10 hot keys
            "cold_keys": cold_keys[:10],  # Top 10 cold keys
            "total_tracked_keys": len(self.access_patterns),
            "recommendations": self._generate_recommendations(hot_keys, cold_keys),
        }

    def _generate_recommendations(self, hot_keys: list, cold_keys: list) -> list[str]:
        """Generate cache optimization recommendations.

        Args:
            hot_keys: List of hot keys
            cold_keys: List of cold keys

        Returns:
            List of recommendations
        """
        recommendations = []

        # Hot key recommendations
        if hot_keys:
            recommendations.append(
                f"Consider increasing TTL for {len(hot_keys)} frequently accessed keys"
            )

        # Cold key recommendations
        if len(cold_keys) > 20:
            recommendations.append(
                f"Consider removing {len(cold_keys)} rarely accessed keys from cache warming"
            )

        # Hit rate recommendations
        if self.statistics.hit_rate < 80:
            recommendations.append(
                f"Cache hit rate is {self.statistics.hit_rate:.1f}%, consider adjusting TTL or warming strategy"
            )

        return recommendations

    async def get_statistics(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Statistics dictionary
        """
        info = {}

        if self.redis_client:
            try:
                # Get Redis info
                redis_info = await self.redis_client.info("memory")
                info["memory_usage"] = redis_info.get("used_memory_human", "N/A")

                # Get key count
                info["total_keys"] = await self.redis_client.dbsize()

            except Exception as e:
                logger.error(f"Failed to get Redis info: {e}")

        return {
            "hit_rate": f"{self.statistics.hit_rate:.2f}%",
            "miss_rate": f"{self.statistics.miss_rate:.2f}%",
            "total_requests": self.statistics.total_requests,
            "cache_hits": self.statistics.cache_hits,
            "cache_misses": self.statistics.cache_misses,
            "total_invalidations": self.statistics.total_invalidations,
            "total_warm_loads": self.statistics.total_warm_loads,
            "avg_response_time_ms": f"{self.statistics.avg_response_time_ms:.2f}",
            "redis_info": info,
            "active_tags": len(self.tag_index),
            "tracked_keys": len(self.cache_registry),
        }

    async def clear_all(self) -> bool:
        """Clear all cache entries.

        Returns:
            Success status
        """
        if not self.redis_client:
            return False

        try:
            await self.redis_client.flushdb()

            # Clear internal tracking
            self.cache_registry.clear()
            self.tag_index.clear()
            self.access_patterns.clear()

            logger.info("All cache entries cleared")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

        if self.connection_pool:
            await self.connection_pool.disconnect()
