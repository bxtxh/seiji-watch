"""Supabase client for Diet Issue Tracker."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic
from urllib.parse import quote

import asyncpg
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from postgrest import AsyncPostgrestClient

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SupabaseClient:
    """Async Supabase client for Diet Issue Tracker data management."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        service_key: Optional[str] = None,
        use_service_role: bool = False,
    ):
        """Initialize Supabase client.
        
        Args:
            url: Supabase project URL
            key: Supabase anon key for public access
            service_key: Supabase service key for admin access
            use_service_role: Whether to use service role for elevated permissions
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = service_key if use_service_role else (key or os.getenv("SUPABASE_ANON_KEY"))
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL and key are required")
        
        # Initialize Supabase client
        options = ClientOptions(
            auto_refresh_token=True,
            persist_session=True,
        )
        self.client: Client = create_client(self.url, self.key, options)
        
        # Database connection pool for direct queries
        self.db_pool: Optional[asyncpg.Pool] = None
        self.db_config = {
            "host": os.getenv("SUPABASE_DB_HOST"),
            "port": int(os.getenv("SUPABASE_DB_PORT", 5432)),
            "database": os.getenv("SUPABASE_DB_NAME", "postgres"),
            "user": os.getenv("SUPABASE_DB_USER", "postgres"),
            "password": os.getenv("SUPABASE_DB_PASSWORD"),
            "ssl": os.getenv("SUPABASE_DB_SSL_MODE", "require"),
            "min_size": int(os.getenv("SUPABASE_DB_POOL_MIN", 2)),
            "max_size": int(os.getenv("SUPABASE_DB_POOL_MAX", 10)),
        }
        
        # Performance settings
        self.batch_size = int(os.getenv("SUPABASE_MIGRATION_BATCH_SIZE", 100))
        self.max_retries = int(os.getenv("SUPABASE_MIGRATION_MAX_RETRIES", 3))
        
    async def initialize_db_pool(self):
        """Initialize database connection pool for direct queries."""
        if not self.db_pool and all(self.db_config.values()):
            try:
                self.db_pool = await asyncpg.create_pool(
                    host=self.db_config["host"],
                    port=self.db_config["port"],
                    database=self.db_config["database"],
                    user=self.db_config["user"],
                    password=self.db_config["password"],
                    ssl=self.db_config["ssl"],
                    min_size=self.db_config["min_size"],
                    max_size=self.db_config["max_size"],
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                
    async def close_db_pool(self):
        """Close database connection pool."""
        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None
            
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a direct SQL query using connection pool."""
        if not self.db_pool:
            await self.initialize_db_pool()
            
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
            
    async def execute_many(self, query: str, args_list: List[tuple]) -> int:
        """Execute multiple queries in a batch."""
        if not self.db_pool:
            await self.initialize_db_pool()
            
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.db_pool.acquire() as conn:
            result = await conn.executemany(query, args_list)
            return int(result.split()[-1]) if result else 0
            
    # =====================================================
    # Generic CRUD Operations
    # =====================================================
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record into a table."""
        try:
            response = self.client.table(table).insert(data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Failed to insert into {table}: {e}")
            raise
            
    async def insert_many(self, table: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert multiple records into a table."""
        results = []
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            try:
                response = self.client.table(table).insert(batch).execute()
                results.extend(response.data)
            except Exception as e:
                logger.error(f"Failed to insert batch into {table}: {e}")
                raise
        return results
        
    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Select records from a table."""
        query = self.client.table(table).select(columns)
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    query = query.in_(key, value)
                elif value is None:
                    query = query.is_(key, "null")
                else:
                    query = query.eq(key, value)
                    
        if order_by:
            desc = order_by.startswith("-")
            column = order_by[1:] if desc else order_by
            query = query.order(column, desc=desc)
            
        if limit:
            query = query.limit(limit)
            
        if offset:
            query = query.offset(offset)
            
        try:
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to select from {table}: {e}")
            raise
            
    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Update records in a table."""
        query = self.client.table(table).update(data)
        
        for key, value in filters.items():
            query = query.eq(key, value)
            
        try:
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to update {table}: {e}")
            raise
            
    async def upsert(
        self,
        table: str,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        on_conflict: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Upsert records into a table."""
        try:
            query = self.client.table(table).upsert(data)
            if on_conflict:
                query = query.on_conflict(on_conflict)
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to upsert into {table}: {e}")
            raise
            
    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete records from a table."""
        query = self.client.table(table).delete()
        
        for key, value in filters.items():
            query = query.eq(key, value)
            
        try:
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to delete from {table}: {e}")
            raise
            
    # =====================================================
    # Bills Operations
    # =====================================================
    
    async def get_bills(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get bills with optional filtering."""
        return await self.select(
            "bills",
            columns="*, parties!bills_party_id_fkey(*), policy_categories!bills_policy_categories(*)",
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="-submitted_date"
        )
        
    async def get_bill_by_id(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Get a bill by ID."""
        results = await self.select(
            "bills",
            columns="*, parties!bills_party_id_fkey(*), policy_categories!bills_policy_categories(*)",
            filters={"id": bill_id},
            limit=1
        )
        return results[0] if results else None
        
    async def get_bill_by_airtable_id(self, airtable_id: str) -> Optional[Dict[str, Any]]:
        """Get a bill by Airtable ID."""
        results = await self.select(
            "bills",
            filters={"airtable_id": airtable_id},
            limit=1
        )
        return results[0] if results else None
        
    async def create_bill(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bill."""
        return await self.insert("bills", bill_data)
        
    async def update_bill(self, bill_id: str, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a bill."""
        results = await self.update("bills", bill_data, {"id": bill_id})
        return results[0] if results else {}
        
    # =====================================================
    # Members Operations
    # =====================================================
    
    async def get_members(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get members with optional filtering."""
        return await self.select(
            "members",
            columns="*, parties!members_party_id_fkey(*)",
            filters=filters,
            limit=limit,
            offset=offset,
            order_by="name"
        )
        
    async def get_member_by_id(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get a member by ID."""
        results = await self.select(
            "members",
            columns="*, parties!members_party_id_fkey(*)",
            filters={"id": member_id},
            limit=1
        )
        return results[0] if results else None
        
    async def get_member_by_airtable_id(self, airtable_id: str) -> Optional[Dict[str, Any]]:
        """Get a member by Airtable ID."""
        results = await self.select(
            "members",
            filters={"airtable_id": airtable_id},
            limit=1
        )
        return results[0] if results else None
        
    # =====================================================
    # Policy Categories Operations
    # =====================================================
    
    async def get_policy_categories(
        self,
        layer: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get policy categories with optional filtering."""
        filters = {}
        if layer:
            filters["layer"] = layer
        if parent_id:
            filters["parent_id"] = parent_id
            
        return await self.select(
            "policy_categories",
            filters=filters,
            order_by="cap_code"
        )
        
    async def get_policy_category_tree(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get complete policy category tree."""
        categories = await self.select("policy_categories", order_by="cap_code")
        
        tree = {"L1": [], "L2": [], "L3": []}
        for category in categories:
            layer = category.get("layer")
            if layer in tree:
                tree[layer].append(category)
                
        return tree
        
    # =====================================================
    # Sync Management Operations
    # =====================================================
    
    async def record_sync_status(
        self,
        table_name: str,
        status: str,
        mode: str = "incremental",
        records_processed: int = 0,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record sync status for a table."""
        data = {
            "table_name": table_name,
            "status": status,
            "sync_mode": mode,
            "records_processed": records_processed,
            "last_sync_at": datetime.utcnow().isoformat(),
        }
        
        if error_message:
            data["error_message"] = error_message
            
        return await self.insert("sync_status", data)
        
    async def get_last_sync_status(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get the last sync status for a table."""
        results = await self.select(
            "sync_status",
            filters={"table_name": table_name},
            order_by="-created_at",
            limit=1
        )
        return results[0] if results else None
        
    async def record_sync_conflict(
        self,
        table_name: str,
        record_id: str,
        airtable_data: Dict[str, Any],
        supabase_data: Dict[str, Any],
        conflict_type: str
    ) -> Dict[str, Any]:
        """Record a sync conflict."""
        data = {
            "table_name": table_name,
            "record_id": record_id,
            "airtable_data": json.dumps(airtable_data),
            "supabase_data": json.dumps(supabase_data),
            "conflict_type": conflict_type,
        }
        
        return await self.insert("sync_conflicts", data)
        
    # =====================================================
    # Health Check and Utilities
    # =====================================================
    
    async def health_check(self) -> bool:
        """Check if Supabase connection is healthy."""
        try:
            # Try a simple query
            await self.select("parties", limit=1)
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False
            
    async def get_table_count(self, table_name: str) -> int:
        """Get the count of records in a table."""
        if self.db_pool:
            # Use direct SQL for better performance
            query = f"SELECT COUNT(*) FROM {table_name}"
            result = await self.execute_query(query)
            return result[0]["count"] if result else 0
        else:
            # Fallback to REST API
            results = await self.select(table_name, columns="id")
            return len(results)
            
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        if self.db_pool:
            query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                )
            """
            result = await self.execute_query(query, table_name)
            return result[0]["exists"] if result else False
        else:
            try:
                await self.select(table_name, limit=1)
                return True
            except:
                return False
                
    # =====================================================
    # Batch Operations for Migration
    # =====================================================
    
    async def batch_upsert_with_mapping(
        self,
        table: str,
        records: List[Dict[str, Any]],
        id_field: str = "airtable_id"
    ) -> Dict[str, Any]:
        """Batch upsert records with ID mapping."""
        success_count = 0
        error_count = 0
        id_mapping = {}
        
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            try:
                results = await self.upsert(table, batch, on_conflict=id_field)
                success_count += len(results)
                
                # Build ID mapping
                for result in results:
                    if id_field in result and "id" in result:
                        id_mapping[result[id_field]] = result["id"]
                        
            except Exception as e:
                error_count += len(batch)
                logger.error(f"Batch upsert failed for {table}: {e}")
                
        return {
            "success_count": success_count,
            "error_count": error_count,
            "id_mapping": id_mapping
        }