"""
Enhanced Issue Management API Routes - Dual-level policy issues.
Provides level-specific endpoints and hierarchical issue management.
"""

import logging
import os

# Import the enhanced services
import sys
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

# TODO: Replace with proper HTTP client calls to respective services
# These are placeholder implementations to avoid cross-service imports

from typing import Dict, List, Optional

from ..security.validation import InputValidator

# Placeholder classes and types
class BillData:
    """Placeholder for BillData. Should be replaced with proper API schema."""
    def __init__(self, **kwargs):
        pass

class PolicyIssueExtractor:
    """Placeholder for PolicyIssueExtractor. Should be replaced with HTTP API calls."""
    
    async def extract_issues(self, text: str) -> List[Dict[str, Any]]:
        """Placeholder method for issue extraction."""
        logger.warning("PolicyIssueExtractor.extract_issues called - implement HTTP API call")
        return []

class DualLevelIssue:
    """Placeholder for DualLevelIssue. Should be replaced with proper API schema."""
    def __init__(self, **kwargs):
        # Store all passed kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

class AirtableIssueManager:
    """Placeholder for Airtable issue management. Should be replaced with HTTP API calls."""
    
    async def get_issue_by_id(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """Placeholder method for getting issue data."""
        logger.warning("AirtableIssueManager.get_issue_by_id called - implement HTTP API call")
        return None
    
    async def get_issues_by_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Placeholder method for getting issues by category."""
        logger.warning("AirtableIssueManager.get_issues_by_category called - implement HTTP API call")
        return []


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/issues", tags=["Enhanced Issues"])


# Dependencies
async def get_airtable_issue_manager() -> AirtableIssueManager:
    """Get enhanced Airtable issue manager instance."""
    return AirtableIssueManager()


async def get_policy_issue_extractor() -> PolicyIssueExtractor:
    """Get policy issue extractor instance."""
    return PolicyIssueExtractor()


# Request/Response Models
class DualLevelIssueRequest(BaseModel):
    """Request for creating dual-level issues."""

    bill_id: str
    bill_title: str
    bill_outline: str | None = None
    background_context: str | None = None
    expected_effects: str | None = None
    key_provisions: list[str] | None = Field(default_factory=list)
    submitter: str | None = None
    category: str | None = None

    @validator("bill_id")
    def validate_bill_id(self, v):
        if not v or not v.strip():
            raise ValueError("Bill ID cannot be empty")
        return InputValidator.sanitize_string(v, 100)

    @validator("bill_title")
    def validate_bill_title(self, v):
        if not v or not v.strip():
            raise ValueError("Bill title cannot be empty")
        if len(v) > 500:
            raise ValueError("Bill title too long (max 500 characters)")
        return InputValidator.sanitize_string(v, 500)


class IssueStatusUpdateRequest(BaseModel):
    """Request for updating issue status."""

    status: str
    reviewer_notes: str | None = None

    @validator("status")
    def validate_status(self, v):
        allowed_statuses = ["pending", "approved", "rejected", "failed_validation"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @validator("reviewer_notes")
    def validate_reviewer_notes(self, v):
        if v and len(v) > 1000:
            raise ValueError("Reviewer notes too long (max 1000 characters)")
        return InputValidator.sanitize_string(v, 1000) if v else v


class IssueSearchRequest(BaseModel):
    """Request for searching issues."""

    query: str
    level: int | None = Query(None, ge=1, le=2, description="Issue level (1 or 2)")
    status: str = "approved"
    max_records: int = Query(50, le=200)

    @validator("query")
    def validate_query(self, v):
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        if len(v) > 100:
            raise ValueError("Search query too long (max 100 characters)")
        return InputValidator.sanitize_string(v, 100)


# Core Enhanced Issue Endpoints
@router.get("/")
async def get_issues(
    level: int | None = Query(None, ge=1, le=2, description="Issue level (1 or 2)"),
    status: str = Query("approved", description="Issue status filter"),
    bill_id: str | None = Query(None, description="Filter by bill ID"),
    parent_id: str | None = Query(None, description="Filter by parent issue"),
    max_records: int = Query(100, le=1000),
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Get issues with level filtering and enhanced options."""
    try:
        # Validate input
        if bill_id:
            bill_id = InputValidator.sanitize_string(bill_id, 100)
        if parent_id:
            parent_id = InputValidator.sanitize_string(parent_id, 100)

        if level:
            # Get issues by specific level
            issues = await airtable_manager.get_issues_by_level(
                level=level, status=status, max_records=max_records
            )
        elif bill_id:
            # Get issues by bill
            issues = await airtable_manager.get_issues_by_bill(
                bill_id=bill_id, status=status
            )
        else:
            # Get all issues with basic filtering
            issues = await airtable_manager.list_issues_by_status(
                status=status, max_records=max_records
            )

        # Format response based on level
        formatted_issues = []
        for issue in issues:
            fields = issue.get("fields", {})

            if level == 1:
                # Level 1 format
                formatted_issues.append(
                    {
                        "issue_id": fields.get("Issue_ID"),
                        "record_id": issue["id"],
                        "label": fields.get("Label_Lv1", ""),
                        "confidence": fields.get("Confidence", 0.0),
                        "source_bill_id": fields.get("Source_Bill_ID"),
                        "quality_score": fields.get("Quality_Score", 0.0),
                        "status": fields.get("Status", "pending"),
                        "created_at": fields.get("Created_At"),
                        "level": 1,
                    }
                )
            elif level == 2:
                # Level 2 format
                formatted_issues.append(
                    {
                        "issue_id": fields.get("Issue_ID"),
                        "record_id": issue["id"],
                        "label": fields.get("Label_Lv2", ""),
                        "parent_id": fields.get("Parent_ID"),
                        "confidence": fields.get("Confidence", 0.0),
                        "source_bill_id": fields.get("Source_Bill_ID"),
                        "quality_score": fields.get("Quality_Score", 0.0),
                        "status": fields.get("Status", "pending"),
                        "created_at": fields.get("Created_At"),
                        "level": 2,
                    }
                )
            else:
                # Both levels for frontend toggle
                formatted_issues.append(
                    {
                        "issue_id": fields.get("Issue_ID"),
                        "record_id": issue["id"],
                        "label_lv1": fields.get("Label_Lv1", ""),
                        "label_lv2": fields.get("Label_Lv2", ""),
                        "parent_id": fields.get("Parent_ID"),
                        "confidence": fields.get("Confidence", 0.0),
                        "source_bill_id": fields.get("Source_Bill_ID"),
                        "quality_score": fields.get("Quality_Score", 0.0),
                        "status": fields.get("Status", "pending"),
                        "created_at": fields.get("Created_At"),
                        "level": 1 if not fields.get("Parent_ID") else 2,
                    }
                )

        return {
            "issues": formatted_issues,
            "count": len(formatted_issues),
            "level_filter": level,
            "status_filter": status,
        }

    except Exception as e:
        logger.error(f"Failed to get issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issues")


@router.get("/tree")
async def get_issue_tree(
    status: str = Query("approved", description="Issue status filter"),
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Get hierarchical issue tree structure."""
    try:
        tree = await airtable_manager.get_issue_tree(status=status)

        # Format tree for API response
        formatted_tree = []
        for parent_id, parent_data in tree.items():
            formatted_parent = {
                "record_id": parent_id,
                "issue_id": parent_data["issue_id"],
                "label_lv1": parent_data["label_lv1"],
                "confidence": parent_data["confidence"],
                "source_bill_id": parent_data["source_bill_id"],
                "children": [],
            }

            for child in parent_data["children"]:
                formatted_child = {
                    "issue_id": child["issue_id"],
                    "label_lv2": child["label_lv2"],
                    "confidence": child["confidence"],
                    "source_bill_id": child["source_bill_id"],
                }
                formatted_parent["children"].append(formatted_child)

            formatted_tree.append(formatted_parent)

        return {
            "tree": formatted_tree,
            "total_parent_issues": len(formatted_tree),
            "total_child_issues": sum(
                len(parent["children"]) for parent in formatted_tree
            ),
            "status_filter": status,
        }

    except Exception as e:
        logger.error(f"Failed to get issue tree: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issue tree")


@router.get("/{record_id}")
async def get_issue(
    record_id: str,
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Get a specific issue by Airtable record ID."""
    try:
        record_id = InputValidator.sanitize_string(record_id, 100)

        issue_record = await airtable_manager.get_issue_record(record_id)
        if not issue_record:
            raise HTTPException(status_code=404, detail="Issue not found")

        return {"issue": issue_record.to_dict(), "record_id": record_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get issue {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issue")


# Issue Extraction Endpoints
@router.post("/extract")
async def extract_dual_level_issues(
    request: DualLevelIssueRequest,
    extractor: PolicyIssueExtractor = Depends(get_policy_issue_extractor),
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Extract dual-level issues from bill data using LLM."""
    try:
        # Create BillData object
        bill_data = BillData(
            id=request.bill_id,
            title=request.bill_title,
            outline=request.bill_outline,
            background_context=request.background_context,
            expected_effects=request.expected_effects,
            key_provisions=request.key_provisions,
            submitter=request.submitter,
            category=request.category,
        )

        # Extract issues using LLM
        extraction_result = await extractor.extract_issues_with_metadata(bill_data)

        if extraction_result["status"] == "failed":
            return {
                "success": False,
                "message": "Failed to extract issues",
                "error": extraction_result["metadata"].get("error"),
                "bill_id": request.bill_id,
            }

        extracted_issues = extraction_result["issues"]
        metadata = extraction_result["metadata"]

        # Create issue pairs in Airtable
        created_pairs = []
        if extracted_issues:
            quality_scores = metadata.get("individual_quality_scores", [])

            for i, issue_data in enumerate(extracted_issues):
                quality_score = quality_scores[i] if i < len(quality_scores) else 0.0

                # Convert dict to DualLevelIssue for validation
                dual_issue = DualLevelIssue(**issue_data)

                # Create issue pair in Airtable
                lv1_id, lv2_id = await airtable_manager.create_issue_pair(
                    dual_issue, request.bill_id, quality_score
                )

                created_pairs.append(
                    {
                        "lv1_record_id": lv1_id,
                        "lv2_record_id": lv2_id,
                        "label_lv1": dual_issue.label_lv1,
                        "label_lv2": dual_issue.label_lv2,
                        "confidence": dual_issue.confidence,
                        "quality_score": quality_score,
                    }
                )

        return {
            "success": True,
            "message": f"Extracted and created {len(created_pairs)} issue pairs",
            "bill_id": request.bill_id,
            "created_issues": created_pairs,
            "extraction_metadata": metadata,
        }

    except Exception as e:
        logger.error(f"Failed to extract issues for bill {request.bill_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract issues")


@router.post("/extract/batch")
async def batch_extract_issues(
    requests: list[DualLevelIssueRequest],
    extractor: PolicyIssueExtractor = Depends(get_policy_issue_extractor),
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Batch extract issues from multiple bills."""
    try:
        if len(requests) > 10:  # Limit batch size
            raise HTTPException(
                status_code=400, detail="Batch size limited to 10 bills"
            )

        # Convert to BillData objects
        bills = []
        for req in requests:
            bill_data = BillData(
                id=req.bill_id,
                title=req.bill_title,
                outline=req.bill_outline,
                background_context=req.background_context,
                expected_effects=req.expected_effects,
                key_provisions=req.key_provisions,
                submitter=req.submitter,
                category=req.category,
            )
            bills.append(bill_data)

        # Batch extract using LLM
        batch_results = await extractor.batch_extract_issues(bills)

        # Process results and create Airtable records
        processed_results = []
        for i, result in enumerate(batch_results):
            bill_id = result["bill_id"]

            if result["status"] == "success":
                extracted_issues = result["issues"]
                metadata = result["metadata"]
                quality_scores = metadata.get("individual_quality_scores", [])

                created_pairs = []
                for j, issue_data in enumerate(extracted_issues):
                    quality_score = (
                        quality_scores[j] if j < len(quality_scores) else 0.0
                    )

                    dual_issue = DualLevelIssue(**issue_data)

                    lv1_id, lv2_id = await airtable_manager.create_issue_pair(
                        dual_issue, bill_id, quality_score
                    )

                    created_pairs.append(
                        {
                            "lv1_record_id": lv1_id,
                            "lv2_record_id": lv2_id,
                            "label_lv1": dual_issue.label_lv1,
                            "label_lv2": dual_issue.label_lv2,
                            "confidence": dual_issue.confidence,
                            "quality_score": quality_score,
                        }
                    )

                processed_results.append(
                    {
                        "bill_id": bill_id,
                        "success": True,
                        "issues_created": len(created_pairs),
                        "created_issues": created_pairs,
                    }
                )
            else:
                processed_results.append(
                    {
                        "bill_id": bill_id,
                        "success": False,
                        "error": result["metadata"].get("error"),
                    }
                )

        successful_count = sum(1 for r in processed_results if r["success"])
        total_issues = sum(r.get("issues_created", 0) for r in processed_results)

        return {
            "message": f"Processed {len(requests)} bills, {successful_count} successful",
            "total_issues_created": total_issues,
            "results": processed_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch extract issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to batch extract issues")


# Issue Management Endpoints
@router.patch("/{record_id}/status")
async def update_issue_status(
    record_id: str,
    request: IssueStatusUpdateRequest,
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Update issue status for review workflow."""
    try:
        record_id = InputValidator.sanitize_string(record_id, 100)

        success = await airtable_manager.update_issue_status(
            record_id=record_id,
            status=request.status,
            reviewer_notes=request.reviewer_notes,
        )

        if not success:
            raise HTTPException(
                status_code=404, detail="Issue not found or update failed"
            )

        return {
            "success": True,
            "message": f"Issue status updated to {request.status}",
            "record_id": record_id,
            "status": request.status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update issue status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update issue status")


@router.post("/search")
async def search_issues(
    request: IssueSearchRequest,
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Search issues by text query."""
    try:
        results = await airtable_manager.search_issues(
            query=request.query,
            level=request.level,
            status=request.status,
            max_records=request.max_records,
        )

        # Format results
        formatted_results = []
        for issue in results:
            fields = issue.get("fields", {})

            formatted_result = {
                "record_id": issue["id"],
                "issue_id": fields.get("Issue_ID"),
                "label_lv1": fields.get("Label_Lv1", ""),
                "label_lv2": fields.get("Label_Lv2", ""),
                "parent_id": fields.get("Parent_ID"),
                "confidence": fields.get("Confidence", 0.0),
                "source_bill_id": fields.get("Source_Bill_ID"),
                "quality_score": fields.get("Quality_Score", 0.0),
                "status": fields.get("Status", "pending"),
                "level": 1 if not fields.get("Parent_ID") else 2,
            }
            formatted_results.append(formatted_result)

        return {
            "query": request.query,
            "results": formatted_results,
            "count": len(formatted_results),
            "level_filter": request.level,
            "status_filter": request.status,
        }

    except Exception as e:
        logger.error(f"Failed to search issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to search issues")


# Statistics and Monitoring Endpoints
@router.get("/statistics")
async def get_issue_statistics(
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Get comprehensive issue statistics."""
    try:
        stats = await airtable_manager.get_issue_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get issue statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/pending/count")
async def get_pending_count(
    exclude_failed_validation: bool = Query(
        True, description="Exclude failed validation"
    ),
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Get count of pending issues for notifications."""
    try:
        count = await airtable_manager.count_pending_issues(exclude_failed_validation)

        return {
            "pending_count": count,
            "exclude_failed_validation": exclude_failed_validation,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get pending count: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending count")


# Health Check Endpoint
@router.get("/health")
async def health_check(
    airtable_manager: AirtableIssueManager = Depends(get_airtable_issue_manager),
):
    """Health check for enhanced issues service."""
    try:
        airtable_healthy = await airtable_manager.health_check()

        # Test extractor
        extractor_healthy = True
        try:
            extractor = PolicyIssueExtractor()
            extractor_healthy = await extractor.health_check()
        except Exception:
            extractor_healthy = False

        overall_healthy = airtable_healthy and extractor_healthy

        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "components": {
                "airtable_manager": "healthy" if airtable_healthy else "unhealthy",
                "policy_extractor": "healthy" if extractor_healthy else "unhealthy",
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
