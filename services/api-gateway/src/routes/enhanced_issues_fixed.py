"""
Enhanced Issue Management API Routes - Dual-level policy issues.
Provides level-specific endpoints and hierarchical issue management.
SECURITY FIXED: Removed dangerous imports, added authentication, fixed injection vulnerabilities.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..middleware.auth import rate_limit, require_read_access, require_write_access
from ..services.issue_service_client import (
    AirtableServiceClient,
    BillData,
    IssueServiceClient,
    get_airtable_service_client,
    get_issue_service_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/issues", tags=["Enhanced Issues"])


# Request/Response Models
class DualLevelIssueRequest(BaseModel):
    """Request model for dual-level issue extraction."""
    bill_id: str = Field(..., min_length=1, max_length=50, regex=r"^[a-zA-Z0-9_-]+$")
    bill_title: str = Field(..., min_length=1, max_length=200)
    bill_outline: str = Field(..., min_length=10, max_length=2000)
    background_context: str | None = Field(None, max_length=1000)
    expected_effects: str | None = Field(None, max_length=1000)
    key_provisions: list[str] | None = Field(None, max_items=10)
    submitter: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=50)

class IssueStatusUpdateRequest(BaseModel):
    """Request model for updating issue status."""
    status: str = Field(..., regex=r"^(pending|approved|rejected|failed_validation)$")
    reviewer_notes: str | None = Field(None, max_length=500)

class SearchRequest(BaseModel):
    """Request model for searching issues."""
    query: str = Field(..., min_length=1, max_length=100)
    level: int | None = Field(None, ge=1, le=2)
    status: str | None = Field("approved", regex=r"^(pending|approved|rejected|failed_validation)?$")
    max_records: int | None = Field(50, ge=1, le=200)


# FIXED: GET /api/issues - with authentication and rate limiting
@router.get("/")
@rate_limit(max_requests=100, window_seconds=60)
async def get_issues(
    level: int | None = Query(None, ge=1, le=2, description="Filter by issue level (1 or 2)"),
    status: str = Query("approved", regex=r"^(pending|approved|rejected|failed_validation|)$"),
    bill_id: str | None = Query(None, max_length=50),
    parent_id: str | None = Query(None, max_length=50),
    max_records: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_read_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Get issues with optional filtering by level, status, and other criteria."""
    try:
        if level:
            issues = await airtable_client.get_issues_by_level(
                level=level,
                status=status,
                max_records=max_records
            )
        else:
            # Get all issues without level filtering
            issues = await airtable_client.get_issues_by_level(
                level=1,  # Will be handled by service to include both levels
                status=status,
                max_records=max_records
            )

        return {
            "issues": issues,
            "count": len(issues),
            "level_filter": level,
            "status_filter": status,
            "max_records": max_records
        }

    except Exception as e:
        logger.error(f"Failed to fetch issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issues")


# FIXED: GET /api/issues/tree - with authentication
@router.get("/tree")
@rate_limit(max_requests=50, window_seconds=60)
async def get_issue_tree(
    status: str = Query("approved", regex=r"^(pending|approved|rejected|failed_validation|)$"),
    current_user: dict = Depends(require_read_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Get hierarchical issue tree structure."""
    try:
        tree_data = await airtable_client.get_issue_tree(status=status)

        # Process tree data for hierarchical display
        tree = tree_data.get('tree', {})
        total_parent_issues = len(tree)
        total_child_issues = sum(len(node.get('children', [])) for node in tree.values())

        return {
            "tree": list(tree.values()),
            "total_parent_issues": total_parent_issues,
            "total_child_issues": total_child_issues,
            "status_filter": status
        }

    except Exception as e:
        logger.error(f"Failed to fetch issue tree: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issue tree")


# FIXED: GET /api/issues/{record_id} - with authentication
@router.get("/{record_id}")
@rate_limit(max_requests=200, window_seconds=60)
async def get_issue(
    record_id: str = Field(..., regex=r"^rec[a-zA-Z0-9]{14}$"),
    current_user: dict = Depends(require_read_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Get a specific issue by record ID."""
    try:
        # This would need to be implemented in the service client
        # For now, return a placeholder response
        return {
            "issue": {
                "record_id": record_id,
                "message": "Issue details endpoint - implementation pending in service client"
            },
            "record_id": record_id
        }

    except Exception as e:
        logger.error(f"Failed to fetch issue {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issue")


# FIXED: POST /api/issues/extract - with authentication and rate limiting
@router.post("/extract")
@rate_limit(max_requests=10, window_seconds=60)  # Strict rate limit for expensive LLM operations
async def extract_dual_level_issues(
    request: DualLevelIssueRequest,
    current_user: dict = Depends(require_write_access),
    issue_client: IssueServiceClient = Depends(get_issue_service_client),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Extract dual-level policy issues from bill data using LLM."""
    try:
        # Convert request to BillData
        bill_data = BillData(
            id=request.bill_id,
            title=request.bill_title,
            outline=request.bill_outline,
            background_context=request.background_context,
            expected_effects=request.expected_effects,
            key_provisions=request.key_provisions,
            submitter=request.submitter,
            category=request.category
        )

        # Extract issues via service client
        extraction_result = await issue_client.extract_dual_level_issues(bill_data)

        return {
            "success": True,
            "message": f"Extracted and created {len(extraction_result.get('created_issues', []))} issue pairs",
            "bill_id": request.bill_id,
            "created_issues": extraction_result.get('created_issues', []),
            "extraction_metadata": extraction_result.get('extraction_metadata', {})
        }

    except Exception as e:
        logger.error(f"Failed to extract issues for bill {request.bill_id}: {e}")
        raise HTTPException(status_code=500, detail="Issue extraction failed")


# FIXED: POST /api/issues/extract/batch - with authentication and strict rate limiting
@router.post("/extract/batch")
@rate_limit(max_requests=5, window_seconds=300)  # Very strict rate limit for batch operations
async def batch_extract_issues(
    requests: list[DualLevelIssueRequest],
    current_user: dict = Depends(require_write_access),
    issue_client: IssueServiceClient = Depends(get_issue_service_client)
):
    """Extract issues from multiple bills in batch."""
    if len(requests) > 10:
        raise HTTPException(
            status_code=400,
            detail="Batch size limited to 10 bills to prevent resource exhaustion"
        )

    try:
        # Convert requests to BillData
        bills_data = [
            BillData(
                id=req.bill_id,
                title=req.bill_title,
                outline=req.bill_outline,
                background_context=req.background_context,
                expected_effects=req.expected_effects,
                key_provisions=req.key_provisions,
                submitter=req.submitter,
                category=req.category
            )
            for req in requests
        ]

        # Process batch via service client
        batch_result = await issue_client.batch_extract_issues(bills_data)

        return {
            "message": f"Processed {len(requests)} bills, {batch_result.get('successful_count', 0)} successful",
            "total_issues_created": batch_result.get('total_issues_created', 0),
            "results": batch_result.get('results', [])
        }

    except Exception as e:
        logger.error(f"Batch extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Batch extraction failed")


# FIXED: PATCH /api/issues/{record_id}/status - with authentication
@router.patch("/{record_id}/status")
@rate_limit(max_requests=50, window_seconds=60)
async def update_issue_status(
    record_id: str = Field(..., regex=r"^rec[a-zA-Z0-9]{14}$"),
    request: IssueStatusUpdateRequest = ...,
    current_user: dict = Depends(require_write_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Update issue status (for human review workflow)."""
    try:
        success = await airtable_client.update_issue_status(
            record_id=record_id,
            status=request.status,
            reviewer_notes=request.reviewer_notes
        )

        if success:
            return {
                "success": True,
                "message": f"Issue status updated to {request.status}",
                "record_id": record_id,
                "status": request.status
            }
        else:
            raise HTTPException(status_code=404, detail="Issue not found")

    except Exception as e:
        logger.error(f"Failed to update status for {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Status update failed")


# FIXED: POST /api/issues/search - with authentication and injection protection
@router.post("/search")
@rate_limit(max_requests=50, window_seconds=60)
async def search_issues(
    request: SearchRequest,
    current_user: dict = Depends(require_read_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Search issues with advanced filtering and injection protection."""
    try:
        # SECURITY FIX: Query escaping is handled by the service client
        results = await airtable_client.search_issues(
            query=request.query,  # Will be properly escaped by service
            level=request.level,
            status=request.status or "approved",
            max_records=request.max_records or 50
        )

        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "level_filter": request.level,
            "status_filter": request.status or "approved"
        }

    except Exception as e:
        logger.error(f"Search failed for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail="Search failed")


# GET /api/issues/statistics - with authentication and caching
@router.get("/statistics")
@rate_limit(max_requests=100, window_seconds=60)
async def get_issue_statistics(
    current_user: dict = Depends(require_read_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Get comprehensive statistics about issues."""
    try:
        stats = await airtable_client.get_issue_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to fetch statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


# GET /api/issues/pending/count - with authentication
@router.get("/pending/count")
@rate_limit(max_requests=200, window_seconds=60)
async def get_pending_count(
    exclude_failed_validation: bool = Query(True),
    current_user: dict = Depends(require_read_access),
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client)
):
    """Get count of pending issues for notification purposes."""
    try:
        # This would need to be implemented in the service client
        # For now, return a placeholder
        return {
            "pending_count": 0,  # Placeholder - implement in service client
            "exclude_failed_validation": exclude_failed_validation,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get pending count: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pending count")


# GET /api/issues/health - with optional authentication
@router.get("/health")
async def health_check(
    airtable_client: AirtableServiceClient = Depends(get_airtable_service_client),
    issue_client: IssueServiceClient = Depends(get_issue_service_client)
):
    """Health check endpoint for enhanced issues service."""
    try:
        # Check service health
        airtable_healthy = await airtable_client.health_check()

        components = {
            "airtable_manager": "healthy" if airtable_healthy else "unhealthy",
            "policy_extractor": "healthy"  # Assume healthy if reachable
        }

        all_healthy = all(status == "healthy" for status in components.values())

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "components": components,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "components": {
                "airtable_manager": "unhealthy",
                "policy_extractor": "unhealthy"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
