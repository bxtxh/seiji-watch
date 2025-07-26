"""
Airtable caching and connection pooling for API Gateway
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientTimeout


class CachedAirtableClient:
    """Airtable client with connection pooling and response caching"""

    def __init__(
        self,
        api_key: str,
        base_id: str,
        cache_ttl: int = 300,  # 5 minutes default
        max_connections: int = 10,
        connection_timeout: int = 30,
    ):
        self.api_key = api_key
        self.base_id = base_id
        self.base_url = f"https://api.airtable.com/v0/{base_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Cache configuration
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Connection pool configuration
        self.timeout = ClientTimeout(total=connection_timeout)
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections,
            ttl_dns_cache=300,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session with connection pooling"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._session

    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from endpoint and parameters"""
        cache_data = {
            "endpoint": endpoint,
            "params": params or {},
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cached_time = cache_entry.get("timestamp", 0)
        current_time = time.time()
        return (current_time - cached_time) < self.cache_ttl

    async def _get_cached_or_fetch(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Get data from cache or fetch from Airtable"""
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache
        cache_entry = self._cache.get(cache_key)
        if cache_entry and self._is_cache_valid(cache_entry):
            return cache_entry["data"]
        
        # Fetch from Airtable
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Update cache
                self._cache[cache_key] = {
                    "data": data,
                    "timestamp": time.time(),
                }
                
                return data
                
        except aiohttp.ClientError as e:
            # If we have stale cache data, return it on error
            if cache_entry:
                return cache_entry["data"]
            raise

    async def list_bills(
        self,
        limit: int = 100,
        offset: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List bills with caching"""
        params = {"pageSize": min(limit, 100)}
        if offset:
            params["offset"] = offset
        
        return await self._get_cached_or_fetch(
            "Bills%20(%E6%B3%95%E6%A1%88)",
            params,
        )

    async def search_bills(
        self,
        query: str,
        filters: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Search bills with caching"""
        formula_parts = []
        
        if query:
            formula_parts.append(f"SEARCH(LOWER('{query}'), LOWER({{Name}}))")
        
        if filters:
            if filters.get("status"):
                formula_parts.append(f"{{Bill_Status}} = '{filters['status']}'")
            if filters.get("stage"):
                formula_parts.append(f"{{Stage}} = '{filters['stage']}'")
        
        formula = "AND(" + ", ".join(formula_parts) + ")" if formula_parts else ""
        
        params = {"pageSize": 100}
        if formula:
            params["filterByFormula"] = formula
        
        return await self._get_cached_or_fetch(
            "Bills%20(%E6%B3%95%E6%A1%88)",
            params,
        )

    async def get_bill(self, bill_id: str) -> Dict[str, Any]:
        """Get single bill with caching"""
        return await self._get_cached_or_fetch(f"Bills/{bill_id}")

    async def list_members(self, limit: int = 100) -> Dict[str, Any]:
        """List members with caching"""
        params = {"pageSize": min(limit, 100)}
        return await self._get_cached_or_fetch(
            "Members%20(%E8%AD%B0%E5%93%A1)",
            params,
        )

    async def get_member(self, member_id: str) -> Dict[str, Any]:
        """Get single member with caching"""
        return await self._get_cached_or_fetch(f"Members/{member_id}")

    async def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()

    async def close(self):
        """Close the connection pool"""
        if self._session and not self._session.closed:
            await self._session.close()
        
        # Wait a bit for the connection to close properly
        await asyncio.sleep(0.25)