"""Hybrid Data Access Layer for Airtable to Supabase migration."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Union
from datetime import datetime, timedelta

import redis.asyncio as redis

from ..clients.airtable import AirtableClient
from ..clients.supabase import SupabaseClient

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DataSource(Enum):
    """Data source preference."""
    SUPABASE = "supabase"
    AIRTABLE = "airtable"
    HYBRID = "hybrid"


class CacheStrategy(Enum):
    """Cache strategy for different data types."""
    AGGRESSIVE = 3600  # 1 hour for static data
    MODERATE = 300     # 5 minutes for semi-static data
    LIGHT = 60        # 1 minute for dynamic data
    NONE = 0          # No caching


class HybridDataAccessLayer:
    """Hybrid DAL for seamless migration from Airtable to Supabase."""
    
    def __init__(
        self,
        airtable_client: Optional[AirtableClient] = None,
        supabase_client: Optional[SupabaseClient] = None,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize Hybrid DAL.
        
        Args:
            airtable_client: Airtable client instance
            supabase_client: Supabase client instance
            redis_client: Redis client for caching
        """
        # Initialize clients
        self.airtable = airtable_client or AirtableClient()
        self.supabase = supabase_client or SupabaseClient()
        
        # Redis configuration
        self.redis = redis_client
        self.cache_prefix = os.getenv("REDIS_CACHE_KEY_PREFIX", "seiji:")
        self.cache_ttl = int(os.getenv("REDIS_CACHE_TTL_SECONDS", 300))
        
        # Feature flags from environment
        self.supabase_read_enabled = os.getenv(
            "FEATURE_SUPABASE_READ_ENABLED", "true"
        ).lower() == "true"
        self.supabase_write_enabled = os.getenv(
            "FEATURE_SUPABASE_WRITE_ENABLED", "false"
        ).lower() == "true"
        self.airtable_fallback_enabled = os.getenv(
            "FEATURE_AIRTABLE_FALLBACK_ENABLED", "true"
        ).lower() == "true"
        self.cache_enabled = os.getenv(
            "FEATURE_CACHE_ENABLED", "true"
        ).lower() == "true"
        
        # Performance metrics
        self.metrics = {
            "supabase_hits": 0,
            "airtable_hits": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
        }
        
        # Cache configuration per table
        self.cache_config = {
            "parties": CacheStrategy.AGGRESSIVE,
            "members": CacheStrategy.AGGRESSIVE,
            "policy_categories": CacheStrategy.AGGRESSIVE,
            "bills": CacheStrategy.MODERATE,
            "meetings": CacheStrategy.MODERATE,
            "speeches": CacheStrategy.LIGHT,
            "votes": CacheStrategy.LIGHT,
            "issues": CacheStrategy.MODERATE,
            "issue_tags": CacheStrategy.AGGRESSIVE,
        }
        
    async def initialize(self):
        """Initialize all connections."""
        # Initialize Redis connection
        if not self.redis and self.cache_enabled:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = await redis.from_url(redis_url)
            
        # Initialize Supabase database pool
        if self.supabase_read_enabled:
            await self.supabase.initialize_db_pool()
            
        logger.info("Hybrid DAL initialized with features: "
                   f"supabase_read={self.supabase_read_enabled}, "
                   f"supabase_write={self.supabase_write_enabled}, "
                   f"cache={self.cache_enabled}")
                   
    async def close(self):
        """Close all connections."""
        if self.redis:
            await self.redis.close()
        await self.supabase.close_db_pool()
        
    # =====================================================
    # Cache Management
    # =====================================================
    
    def _generate_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key from operation and parameters."""
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        return f"{self.cache_prefix}{operation}:{hash(sorted_params)}"
        
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.cache_enabled or not self.redis:
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                self.metrics["cache_hits"] += 1
                return json.loads(value)
            else:
                self.metrics["cache_misses"] += 1
                return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
            
    async def _set_in_cache(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in cache."""
        if not self.cache_enabled or not self.redis:
            return
            
        try:
            ttl = ttl or self.cache_ttl
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            
    async def invalidate_cache(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        if not self.redis:
            return
            
        try:
            cursor = b'0'
            while cursor:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match=f"{self.cache_prefix}{pattern}*",
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            
    # =====================================================
    # Bills Operations
    # =====================================================
    
    async def get_bills(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get bills with hybrid data source strategy."""
        # Generate cache key
        cache_key = self._generate_cache_key(
            "bills",
            {"filters": filters, "limit": limit, "offset": offset}
        )
        
        # Try cache first
        if use_cache:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
                
        # Try Supabase first if enabled
        if self.supabase_read_enabled:
            try:
                result = await self.supabase.get_bills(filters, limit, offset)
                self.metrics["supabase_hits"] += 1
                
                # Cache the result
                if use_cache:
                    ttl = self.cache_config["bills"].value
                    await self._set_in_cache(cache_key, result, ttl)
                    
                return result
                
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"Supabase query failed: {e}")
                
                # Fall back to Airtable if enabled
                if not self.airtable_fallback_enabled:
                    raise
                    
        # Use Airtable as fallback or primary
        try:
            # Build Airtable filter formula
            filter_formula = self._build_airtable_filter(filters) if filters else None
            result = await self.airtable.list_bills(
                filter_formula=filter_formula,
                max_records=limit
            )
            self.metrics["airtable_hits"] += 1
            
            # Convert Airtable format to standardized format
            result = self._standardize_airtable_response(result, "bills")
            
            # Cache the result
            if use_cache:
                ttl = self.cache_config["bills"].value
                await self._set_in_cache(cache_key, result, ttl)
                
            return result
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Airtable query failed: {e}")
            raise
            
    async def get_bill_by_id(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Get a bill by ID."""
        # Check if it's an Airtable ID or Supabase UUID
        is_airtable_id = bill_id.startswith("rec")
        
        if self.supabase_read_enabled and not is_airtable_id:
            try:
                return await self.supabase.get_bill_by_id(bill_id)
            except Exception as e:
                logger.error(f"Supabase get_bill_by_id failed: {e}")
                if not self.airtable_fallback_enabled:
                    raise
                    
        # Use Airtable for Airtable IDs or as fallback
        if is_airtable_id:
            result = await self.airtable.get_bill(bill_id)
            return self._standardize_airtable_record(result, "bills")
            
        return None
        
    async def create_bill(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bill."""
        if self.supabase_write_enabled:
            # Write to Supabase
            result = await self.supabase.create_bill(bill_data)
            
            # Also write to Airtable for sync
            await self._sync_to_airtable("bills", bill_data)
            
            # Invalidate cache
            await self.invalidate_cache("bills:")
            
            return result
        else:
            # Write to Airtable only
            result = await self.airtable.create_bill(bill_data)
            
            # Trigger async sync to Supabase
            asyncio.create_task(self._sync_to_supabase("bills", result))
            
            # Invalidate cache
            await self.invalidate_cache("bills:")
            
            return self._standardize_airtable_record(result, "bills")
            
    async def update_bill(
        self,
        bill_id: str,
        bill_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a bill."""
        if self.supabase_write_enabled:
            # Update in Supabase
            result = await self.supabase.update_bill(bill_id, bill_data)
            
            # Also update in Airtable for sync
            await self._sync_update_to_airtable("bills", bill_id, bill_data)
            
            # Invalidate cache
            await self.invalidate_cache(f"bills:*{bill_id}*")
            
            return result
        else:
            # Update in Airtable only
            result = await self.airtable.update_bill(bill_id, bill_data)
            
            # Trigger async sync to Supabase
            asyncio.create_task(self._sync_update_to_supabase("bills", bill_id, result))
            
            # Invalidate cache
            await self.invalidate_cache(f"bills:*{bill_id}*")
            
            return self._standardize_airtable_record(result, "bills")
            
    # =====================================================
    # Members Operations
    # =====================================================
    
    async def get_members(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get members with hybrid data source strategy."""
        cache_key = self._generate_cache_key(
            "members",
            {"filters": filters, "limit": limit, "offset": offset}
        )
        
        # Try cache first
        if use_cache:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
                
        # Try Supabase first if enabled
        if self.supabase_read_enabled:
            try:
                result = await self.supabase.get_members(filters, limit, offset)
                self.metrics["supabase_hits"] += 1
                
                # Cache the result
                if use_cache:
                    ttl = self.cache_config["members"].value
                    await self._set_in_cache(cache_key, result, ttl)
                    
                return result
                
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"Supabase query failed: {e}")
                
                if not self.airtable_fallback_enabled:
                    raise
                    
        # Use Airtable as fallback
        try:
            filter_formula = self._build_airtable_filter(filters) if filters else None
            result = await self.airtable.list_members(
                filter_formula=filter_formula,
                max_records=limit
            )
            self.metrics["airtable_hits"] += 1
            
            result = self._standardize_airtable_response(result, "members")
            
            # Cache the result
            if use_cache:
                ttl = self.cache_config["members"].value
                await self._set_in_cache(cache_key, result, ttl)
                
            return result
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Airtable query failed: {e}")
            raise
            
    # =====================================================
    # Policy Categories Operations
    # =====================================================
    
    async def get_policy_categories(
        self,
        layer: Optional[str] = None,
        parent_id: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """Get policy categories."""
        cache_key = self._generate_cache_key(
            "policy_categories",
            {"layer": layer, "parent_id": parent_id}
        )
        
        # Try cache first
        if use_cache:
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
                
        # Try Supabase first if enabled
        if self.supabase_read_enabled:
            try:
                result = await self.supabase.get_policy_categories(layer, parent_id)
                self.metrics["supabase_hits"] += 1
                
                # Cache the result
                if use_cache:
                    ttl = self.cache_config["policy_categories"].value
                    await self._set_in_cache(cache_key, result, ttl)
                    
                return result
                
            except Exception as e:
                self.metrics["errors"] += 1
                logger.error(f"Supabase query failed: {e}")
                
                if not self.airtable_fallback_enabled:
                    raise
                    
        # Use Airtable as fallback
        try:
            filters = {}
            if layer:
                filters["Layer"] = layer
            filter_formula = self._build_airtable_filter(filters) if filters else None
            
            result = await self.airtable.list_issue_categories(
                filter_formula=filter_formula,
                max_records=1000
            )
            self.metrics["airtable_hits"] += 1
            
            # Filter by parent_id if specified
            if parent_id:
                result = [
                    r for r in result
                    if r.get("fields", {}).get("Parent_Category") == [parent_id]
                ]
                
            result = self._standardize_airtable_response(result, "policy_categories")
            
            # Cache the result
            if use_cache:
                ttl = self.cache_config["policy_categories"].value
                await self._set_in_cache(cache_key, result, ttl)
                
            return result
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Airtable query failed: {e}")
            raise
            
    # =====================================================
    # Sync Operations
    # =====================================================
    
    async def _sync_to_supabase(self, table: str, airtable_record: Dict[str, Any]):
        """Sync a record from Airtable to Supabase."""
        if not self.supabase_read_enabled:
            return
            
        try:
            # Convert to Supabase format
            from ..migration.schema_mapper import SchemaMapper
            mapper = SchemaMapper()
            
            airtable_table = self._get_airtable_table_name(table)
            supabase_record = mapper.airtable_to_supabase(
                airtable_table,
                airtable_record
            )
            
            # Upsert to Supabase
            await self.supabase.upsert(
                table,
                supabase_record,
                on_conflict="airtable_id"
            )
            
            logger.info(f"Synced {table} record to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to sync to Supabase: {e}")
            
    async def _sync_to_airtable(self, table: str, supabase_data: Dict[str, Any]):
        """Sync a record from Supabase to Airtable."""
        # This would be implemented in Phase 2 for bidirectional sync
        pass
        
    async def _sync_update_to_supabase(
        self,
        table: str,
        record_id: str,
        airtable_record: Dict[str, Any]
    ):
        """Sync an update from Airtable to Supabase."""
        if not self.supabase_read_enabled:
            return
            
        try:
            # Get Supabase ID from Airtable ID
            supabase_record = await self.supabase.select(
                table,
                filters={"airtable_id": record_id},
                limit=1
            )
            
            if supabase_record:
                supabase_id = supabase_record[0]["id"]
                
                # Convert and update
                from ..migration.schema_mapper import SchemaMapper
                mapper = SchemaMapper()
                
                airtable_table = self._get_airtable_table_name(table)
                update_data = mapper.airtable_to_supabase(
                    airtable_table,
                    {"id": record_id, "fields": airtable_record}
                )
                
                await self.supabase.update(
                    table,
                    update_data,
                    {"id": supabase_id}
                )
                
                logger.info(f"Synced update for {table} record to Supabase")
                
        except Exception as e:
            logger.error(f"Failed to sync update to Supabase: {e}")
            
    async def _sync_update_to_airtable(
        self,
        table: str,
        supabase_id: str,
        supabase_data: Dict[str, Any]
    ):
        """Sync an update from Supabase to Airtable."""
        # This would be implemented in Phase 2 for bidirectional sync
        pass
        
    # =====================================================
    # Helper Methods
    # =====================================================
    
    def _build_airtable_filter(self, filters: Dict[str, Any]) -> str:
        """Build Airtable filter formula from filters dict."""
        if not filters:
            return ""
            
        conditions = []
        for field, value in filters.items():
            # Map common field names
            airtable_field = self._map_to_airtable_field(field)
            
            if value is None:
                conditions.append(f"{{{{field}}}} = BLANK()")
            elif isinstance(value, bool):
                conditions.append(f"{{{airtable_field}}} = {str(value).upper()}")
            elif isinstance(value, (int, float)):
                conditions.append(f"{{{airtable_field}}} = {value}")
            else:
                # Escape single quotes in value
                escaped_value = str(value).replace("'", "\\'")
                conditions.append(f"{{{airtable_field}}} = '{escaped_value}'")
                
        if len(conditions) == 1:
            return conditions[0]
        else:
            return f"AND({', '.join(conditions)})"
            
    def _map_to_airtable_field(self, field: str) -> str:
        """Map standardized field name to Airtable field name."""
        field_map = {
            "bill_number": "Bill_Number",
            "title": "Title",
            "status": "Status",
            "category": "Category",
            "house": "House",
            "name": "Name",
            "party_id": "Party",
            "layer": "Layer",
            "cap_code": "CAP_Code",
        }
        
        return field_map.get(field, field)
        
    def _get_airtable_table_name(self, supabase_table: str) -> str:
        """Get Airtable table name from Supabase table name."""
        table_map = {
            "bills": "Bills (法案)",
            "members": "Members",
            "parties": "Parties",
            "policy_categories": "IssueCategories",
            "bills_policy_categories": "Bills_PolicyCategories",
            "meetings": "Meetings",
            "speeches": "Speeches",
            "votes": "Votes (投票)",
            "issues": "Issues",
            "issue_tags": "IssueTags",
        }
        
        return table_map.get(supabase_table, supabase_table)
        
    def _standardize_airtable_response(
        self,
        records: List[Dict[str, Any]],
        table: str
    ) -> List[Dict[str, Any]]:
        """Standardize Airtable response to match Supabase format."""
        standardized = []
        
        for record in records:
            standardized.append(
                self._standardize_airtable_record(record, table)
            )
            
        return standardized
        
    def _standardize_airtable_record(
        self,
        record: Dict[str, Any],
        table: str
    ) -> Dict[str, Any]:
        """Standardize single Airtable record."""
        # This is a simplified version - full implementation would use SchemaMapper
        fields = record.get("fields", {})
        standardized = {
            "id": record.get("id"),
            "airtable_id": record.get("id"),
            **fields
        }
        
        return standardized
        
    # =====================================================
    # Metrics and Monitoring
    # =====================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        total_hits = (
            self.metrics["supabase_hits"] +
            self.metrics["airtable_hits"] +
            self.metrics["cache_hits"]
        )
        
        return {
            **self.metrics,
            "total_requests": total_hits,
            "cache_hit_rate": (
                self.metrics["cache_hits"] / total_hits
                if total_hits > 0 else 0
            ),
            "supabase_usage_rate": (
                self.metrics["supabase_hits"] / 
                (self.metrics["supabase_hits"] + self.metrics["airtable_hits"])
                if (self.metrics["supabase_hits"] + self.metrics["airtable_hits"]) > 0
                else 0
            ),
        }
        
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all data sources."""
        health = {
            "airtable": False,
            "supabase": False,
            "cache": False,
        }
        
        # Check Airtable
        try:
            health["airtable"] = await self.airtable.health_check()
        except Exception as e:
            logger.error(f"Airtable health check failed: {e}")
            
        # Check Supabase
        if self.supabase_read_enabled:
            try:
                health["supabase"] = await self.supabase.health_check()
            except Exception as e:
                logger.error(f"Supabase health check failed: {e}")
                
        # Check Redis
        if self.redis:
            try:
                await self.redis.ping()
                health["cache"] = True
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                
        return health