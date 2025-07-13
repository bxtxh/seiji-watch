"""Redis client for member data caching with stale-while-revalidate strategy."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
from redis.asyncio.client import Redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis client for member data caching with intelligent cache management."""
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 86400):
        """Initialize Redis client with default TTL of 24 hours."""
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl
        self.redis: Optional[Redis] = None
        
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        if not self.redis:
            await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache with TTL."""
        if not self.redis:
            await self.connect()
        
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        if not self.redis:
            await self.connect()
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.exists(key)
        except Exception as e:
            logger.error(f"Redis exists check failed for key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> int:
        """Get TTL for a key."""
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL check failed for key {key}: {e}")
            return -1
    
    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values from Redis cache."""
        if not self.redis:
            await self.connect()
        
        try:
            values = await self.redis.mget(keys)
            return [json.loads(v) if v else None for v in values]
        except Exception as e:
            logger.error(f"Redis mget failed for keys {keys}: {e}")
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in Redis cache."""
        if not self.redis:
            await self.connect()
        
        try:
            ttl = ttl or self.default_ttl
            serialized_mapping = {k: json.dumps(v, default=str) for k, v in mapping.items()}
            
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()
            await pipe.mset(serialized_mapping)
            
            # Set TTL for all keys
            for key in serialized_mapping.keys():
                await pipe.expire(key, ttl)
            
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis mset failed: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in Redis."""
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis increment failed for key {key}: {e}")
            return 0
    
    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not self.redis:
            await self.connect()
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Redis flush pattern failed for pattern {pattern}: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            if not self.redis:
                await self.connect()
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


class MemberCache:
    """Specialized cache for member data with stale-while-revalidate strategy."""
    
    def __init__(self, redis_cache: RedisCache):
        self.redis = redis_cache
        self.prefix = "member:"
        self.list_prefix = "members:"
        self.stats_prefix = "member_stats:"
    
    async def get_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get member data from cache."""
        key = f"{self.prefix}{member_id}"
        return await self.redis.get(key)
    
    async def set_member(self, member_id: str, member_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set member data in cache."""
        key = f"{self.prefix}{member_id}"
        return await self.redis.set(key, member_data, ttl)
    
    async def get_members_list(self, filter_key: str = "all") -> Optional[List[Dict[str, Any]]]:
        """Get cached member list."""
        key = f"{self.list_prefix}{filter_key}"
        return await self.redis.get(key)
    
    async def set_members_list(self, filter_key: str, members_list: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Set cached member list."""
        key = f"{self.list_prefix}{filter_key}"
        return await self.redis.set(key, members_list, ttl)
    
    async def get_member_stats(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get member statistics from cache."""
        key = f"{self.stats_prefix}{member_id}"
        return await self.redis.get(key)
    
    async def set_member_stats(self, member_id: str, stats: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set member statistics in cache."""
        key = f"{self.stats_prefix}{member_id}"
        return await self.redis.set(key, stats, ttl)
    
    async def get_member_voting_history(self, member_id: str, offset: int = 0, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """Get member voting history from cache."""
        key = f"{self.prefix}{member_id}:votes:{offset}:{limit}"
        return await self.redis.get(key)
    
    async def set_member_voting_history(self, member_id: str, offset: int, limit: int, 
                                       voting_history: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Set member voting history in cache."""
        key = f"{self.prefix}{member_id}:votes:{offset}:{limit}"
        return await self.redis.set(key, voting_history, ttl)
    
    async def is_stale(self, key: str, stale_threshold: int = 21600) -> bool:
        """Check if cached data is stale (older than 6 hours by default)."""
        ttl = await self.redis.get_ttl(key)
        if ttl == -1:  # Key doesn't exist
            return True
        
        # Calculate remaining time vs stale threshold
        remaining_time = ttl
        initial_ttl = self.redis.default_ttl
        age = initial_ttl - remaining_time
        
        return age > stale_threshold
    
    async def warmup_cache(self, members_data: List[Dict[str, Any]]) -> bool:
        """Warm up cache with member data."""
        try:
            # Prepare member data mapping
            member_mapping = {}
            for member in members_data:
                member_id = member.get("id", member.get("record_id"))
                if member_id:
                    member_mapping[f"{self.prefix}{member_id}"] = member
            
            # Cache all members
            success = await self.redis.mset(member_mapping)
            
            # Cache members list
            await self.set_members_list("all", members_data)
            
            logger.info(f"Warmed up cache with {len(members_data)} members")
            return success
        except Exception as e:
            logger.error(f"Cache warmup failed: {e}")
            return False
    
    async def invalidate_member(self, member_id: str) -> bool:
        """Invalidate all cached data for a member."""
        pattern = f"{self.prefix}{member_id}*"
        deleted_count = await self.redis.flush_pattern(pattern)
        
        # Also invalidate member lists
        await self.redis.flush_pattern(f"{self.list_prefix}*")
        
        logger.info(f"Invalidated {deleted_count} cache entries for member {member_id}")
        return deleted_count > 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            # Count cached members
            member_keys = await self.redis.redis.keys(f"{self.prefix}*")
            member_count = len([k for k in member_keys if ":" not in k.split(self.prefix)[1]])
            
            # Count cached lists
            list_keys = await self.redis.redis.keys(f"{self.list_prefix}*")
            list_count = len(list_keys)
            
            # Count cached stats
            stats_keys = await self.redis.redis.keys(f"{self.stats_prefix}*")
            stats_count = len(stats_keys)
            
            return {
                "cached_members": member_count,
                "cached_lists": list_count,
                "cached_stats": stats_count,
                "total_keys": len(member_keys) + len(list_keys) + len(stats_keys)
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}