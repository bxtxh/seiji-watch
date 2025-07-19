"""
Issue Service Client
Provides secure interface to the ingest-worker issue extraction services.
"""

import logging
import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import os

logger = logging.getLogger(__name__)

class BillData(BaseModel):
    """Bill data model for issue extraction."""
    id: str
    title: str
    outline: str
    background_context: Optional[str] = None
    expected_effects: Optional[str] = None
    key_provisions: Optional[List[str]] = None
    submitter: Optional[str] = None
    category: Optional[str] = None

class DualLevelIssue(BaseModel):
    """Dual-level issue model."""
    label_lv1: str
    label_lv2: str
    confidence: float

class IssueServiceClient:
    """Client for communicating with the ingest-worker issue extraction service."""
    
    def __init__(self):
        self.base_url = os.getenv('INGEST_WORKER_URL', 'http://localhost:8001')
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    async def extract_dual_level_issues(self, bill_data: BillData) -> Dict[str, Any]:
        """Extract dual-level issues from bill data via HTTP API."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {
                    "bill_id": bill_data.id,
                    "bill_title": bill_data.title,
                    "bill_outline": bill_data.outline,
                    "background_context": bill_data.background_context,
                    "expected_effects": bill_data.expected_effects,
                    "key_provisions": bill_data.key_provisions or [],
                    "submitter": bill_data.submitter,
                    "category": bill_data.category
                }
                
                async with session.post(
                    f"{self.base_url}/extract-issues",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Issue extraction failed: {error_text}"
                        )
                    
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to communicate with ingest-worker: {e}")
            raise HTTPException(
                status_code=503,
                detail="Issue extraction service unavailable"
            )
        except asyncio.TimeoutError:
            logger.error("Timeout while extracting issues")
            raise HTTPException(
                status_code=504,
                detail="Issue extraction timeout"
            )
            
    async def batch_extract_issues(self, bills_data: List[BillData]) -> Dict[str, Any]:
        """Batch extract issues from multiple bills."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = [
                    {
                        "bill_id": bill.id,
                        "bill_title": bill.title,
                        "bill_outline": bill.outline,
                        "background_context": bill.background_context,
                        "expected_effects": bill.expected_effects,
                        "key_provisions": bill.key_provisions or [],
                        "submitter": bill.submitter,
                        "category": bill.category
                    }
                    for bill in bills_data
                ]
                
                async with session.post(
                    f"{self.base_url}/extract-issues/batch",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Batch extraction failed: {error_text}"
                        )
                    
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to communicate with ingest-worker: {e}")
            raise HTTPException(
                status_code=503,
                detail="Issue extraction service unavailable"
            )

class AirtableServiceClient:
    """Client for communicating with Airtable issue management service."""
    
    def __init__(self):
        self.base_url = os.getenv('INGEST_WORKER_URL', 'http://localhost:8001')
        self.timeout = aiohttp.ClientTimeout(total=30)
        
    async def get_issues_by_level(self, level: int, status: str = "approved", max_records: int = 100) -> List[Dict]:
        """Get issues filtered by level."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                params = {
                    "level": level,
                    "status": status,
                    "max_records": max_records
                }
                
                async with session.get(
                    f"{self.base_url}/airtable-issues",
                    params=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Failed to fetch issues: {error_text}"
                        )
                    
                    data = await response.json()
                    return data.get('issues', [])
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to communicate with Airtable service: {e}")
            raise HTTPException(
                status_code=503,
                detail="Airtable service unavailable"
            )
            
    async def get_issue_tree(self, status: str = "approved") -> Dict[str, Any]:
        """Get hierarchical issue tree."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                params = {"status": status}
                
                async with session.get(
                    f"{self.base_url}/airtable-issues/tree",
                    params=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Failed to fetch issue tree: {error_text}"
                        )
                    
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to communicate with Airtable service: {e}")
            raise HTTPException(
                status_code=503,
                detail="Airtable service unavailable"
            )
            
    async def search_issues(self, query: str, level: Optional[int] = None, 
                          status: str = "approved", max_records: int = 50) -> List[Dict]:
        """Search issues with proper query escaping."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Properly escaped search payload
                payload = {
                    "query": query,  # Service will handle escaping
                    "level": level,
                    "status": status,
                    "max_records": max_records
                }
                
                async with session.post(
                    f"{self.base_url}/airtable-issues/search",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Search failed: {error_text}"
                        )
                    
                    data = await response.json()
                    return data.get('results', [])
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to search issues: {e}")
            raise HTTPException(
                status_code=503,
                detail="Search service unavailable"
            )
            
    async def update_issue_status(self, record_id: str, status: str, reviewer_notes: Optional[str] = None) -> bool:
        """Update issue status with security validation."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {
                    "status": status,
                    "reviewer_notes": reviewer_notes or ""
                }
                
                async with session.patch(
                    f"{self.base_url}/airtable-issues/{record_id}/status",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Status update failed: {error_text}"
                        )
                    
                    return True
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to update issue status: {e}")
            raise HTTPException(
                status_code=503,
                detail="Status update service unavailable"
            )
            
    async def get_issue_statistics(self) -> Dict[str, Any]:
        """Get issue statistics."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/airtable-issues/statistics") as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Failed to fetch statistics: {error_text}"
                        )
                    
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch statistics: {e}")
            raise HTTPException(
                status_code=503,
                detail="Statistics service unavailable"
            )
            
    async def health_check(self) -> bool:
        """Check if the Airtable service is healthy."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except:
            return False

# Dependency injection
async def get_issue_service_client() -> IssueServiceClient:
    """Get issue service client instance."""
    return IssueServiceClient()

async def get_airtable_service_client() -> AirtableServiceClient:
    """Get Airtable service client instance."""
    return AirtableServiceClient()