"""Bills and PolicyCategory relationship management API routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

# Import shared models and clients
from shared.clients import AirtableClient

from ..security.validation import InputValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bills", tags=["Bills"])

# Dependency for Airtable client


async def get_airtable_client() -> AirtableClient:
    """Get Airtable client instance."""
    return AirtableClient()


# Request/Response models


class PolicyCategoryRelationshipRequest(BaseModel):
    """Request model for creating/updating Bills-PolicyCategory relationship."""

    bill_id: str = Field(..., description="Bill identifier")
    policy_category_id: str = Field(..., description="PolicyCategory identifier")
    confidence_score: float = Field(
        0.8, ge=0.0, le=1.0, description="Relationship confidence (0.0-1.0)"
    )
    is_manual: bool = Field(
        False, description="Whether manually created vs auto-generated"
    )
    notes: str | None = Field(
        None, description="Additional notes about the relationship"
    )

    @validator("bill_id")
    def validate_bill_id(self, v):
        if not v or not v.strip():
            raise ValueError("Bill ID cannot be empty")
        return InputValidator.sanitize_string(v, 50)

    @validator("policy_category_id")
    def validate_policy_category_id(self, v):
        if not v or not v.strip():
            raise ValueError("PolicyCategory ID cannot be empty")
        return InputValidator.sanitize_string(v, 50)

    @validator("notes")
    def validate_notes(self, v):
        if v and len(v) > 1000:
            raise ValueError("Notes too long (max 1000 characters)")
        return InputValidator.sanitize_string(v, 1000) if v else v


class BillSearchRequest(BaseModel):
    """Request model for searching bills with PolicyCategory filters."""

    query: str | None = Field(None, description="Search query")
    policy_category_ids: list[str] | None = Field(
        None, description="Filter by PolicyCategory IDs"
    )
    policy_category_layer: str | None = Field(
        None, description="Filter by policy layer (L1/L2/L3)"
    )
    status: str | None = Field(None, description="Filter by bill status")
    stage: str | None = Field(None, description="Filter by bill stage")
    max_records: int = Field(100, le=1000, description="Maximum records to return")

    @validator("query")
    def validate_query(self, v):
        if v and len(v) > 200:
            raise ValueError("Query too long (max 200 characters)")
        return InputValidator.sanitize_string(v, 200) if v else v


# Bills endpoints


@router.get("/", response_model=list[dict])
async def list_bills(
    status: str | None = Query(None, description="Filter by status"),
    stage: str | None = Query(None, description="Filter by stage"),
    policy_category_id: str | None = Query(
        None, description="Filter by PolicyCategory ID"
    ),
    max_records: int = Query(100, le=1000),
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """List all bills with optional filtering."""
    try:
        # Build filter formula
        filters = []
        if status:
            filters.append(f"{{Bill_Status}} = '{status}'")
        if stage:
            filters.append(f"{{Stage}} = '{stage}'")

        filter_formula = "AND(" + ", ".join(filters) + ")" if filters else None

        bills = await airtable.list_bills(
            filter_formula=filter_formula, max_records=max_records
        )

        # If PolicyCategory filter is requested, get related bills
        if policy_category_id:
            # Get all Bills-PolicyCategory relationships for this category
            relationships = await airtable.get_bills_by_policy_category(
                policy_category_id
            )
            bill_ids = [
                rel.get("fields", {}).get("Bill_ID", "") for rel in relationships
            ]

            # Filter bills to only include those with relationships
            bills = [bill for bill in bills if bill.get("id") in bill_ids]

        return bills

    except Exception as e:
        logger.error(f"Failed to list bills: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bills")


@router.get("/{bill_id}")
async def get_bill(
    bill_id: str,
    include_policy_categories: bool = Query(
        False, description="Include related PolicyCategories"
    ),
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Get a specific bill by ID with optional PolicyCategory relationships."""
    try:
        bill = await airtable.get_bill(bill_id)

        if include_policy_categories:
            # Get related PolicyCategories for this bill
            relationships = await airtable.get_policy_categories_by_bill(bill_id)

            # Fetch full PolicyCategory data for each relationship
            policy_categories = []
            for rel in relationships:
                rel_fields = rel.get("fields", {})
                category_id = rel_fields.get("PolicyCategory_ID")

                if category_id:
                    try:
                        category = await airtable.get_issue_category(category_id)
                        policy_categories.append(
                            {
                                "category": category,
                                "confidence_score": rel_fields.get(
                                    "Confidence_Score", 0.8
                                ),
                                "is_manual": rel_fields.get("Is_Manual", False),
                                "notes": rel_fields.get("Notes", ""),
                                "relationship_id": rel.get("id"),
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch PolicyCategory {category_id}: {e}"
                        )

            bill["policy_categories"] = policy_categories

        return bill

    except Exception as e:
        logger.error(f"Failed to get bill {bill_id}: {e}")
        raise HTTPException(status_code=404, detail="Bill not found")


@router.post("/search", response_model=dict[str, Any])
async def search_bills(
    request: BillSearchRequest, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Advanced bill search with PolicyCategory filtering."""
    try:
        # Build search filters
        filters = []

        # Text search
        if request.query:
            text_filters = [
                f"SEARCH('{request.query}', {{Name}}) > 0",
                f"SEARCH('{request.query}', {{Bill_Number}}) > 0",
                f"SEARCH('{request.query}', {{Notes}}) > 0",
            ]
            filters.append("OR(" + ", ".join(text_filters) + ")")

        # Status filter
        if request.status:
            filters.append(f"{{Bill_Status}} = '{request.status}'")

        # Stage filter
        if request.stage:
            filters.append(f"{{Stage}} = '{request.stage}'")

        # Build final filter formula
        filter_formula = "AND(" + ", ".join(filters) + ")" if filters else None

        # Get matching bills
        bills = await airtable.list_bills(
            filter_formula=filter_formula,
            max_records=request.max_records
            * 2,  # Get more to account for PolicyCategory filtering
        )

        # Apply PolicyCategory filters if specified
        if request.policy_category_ids or request.policy_category_layer:
            filtered_bills = []

            for bill in bills:
                bill_id = bill.get("id")

                # Get PolicyCategory relationships for this bill
                relationships = await airtable.get_policy_categories_by_bill(bill_id)

                # Check if any relationships match the filter criteria
                matches_filter = False

                for rel in relationships:
                    rel_fields = rel.get("fields", {})
                    category_id = rel_fields.get("PolicyCategory_ID")

                    if category_id:
                        # Check ID filter
                        if (
                            request.policy_category_ids
                            and category_id in request.policy_category_ids
                        ):
                            matches_filter = True
                            break

                        # Check layer filter
                        if request.policy_category_layer:
                            try:
                                category = await airtable.get_issue_category(
                                    category_id
                                )
                                category_layer = category.get("fields", {}).get(
                                    "Layer", ""
                                )
                                if category_layer == request.policy_category_layer:
                                    matches_filter = True
                                    break
                            except Exception as e:
                                logger.warning(
                                    f"Failed to check layer for category {category_id}: {e}"
                                )

                if matches_filter:
                    filtered_bills.append(bill)

            bills = filtered_bills[: request.max_records]

        return {
            "success": True,
            "results": bills,
            "total_found": len(bills),
            "query": request.query,
            "filters": {
                "status": request.status,
                "stage": request.stage,
                "policy_category_ids": request.policy_category_ids,
                "policy_category_layer": request.policy_category_layer,
            },
        }

    except Exception as e:
        logger.error(f"Failed to search bills: {e}")
        raise HTTPException(status_code=500, detail="Failed to search bills")


# Bills-PolicyCategory relationship endpoints


@router.post("/{bill_id}/policy-categories")
async def create_bill_policy_category_relationship(
    bill_id: str,
    request: PolicyCategoryRelationshipRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Create a new Bills-PolicyCategory relationship."""
    try:
        # Validate that the bill_id matches the request
        if bill_id != request.bill_id:
            raise HTTPException(status_code=400, detail="Bill ID mismatch")

        # Validate that both bill and policy category exist
        try:
            await airtable.get_bill(bill_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Bill not found")

        try:
            await airtable.get_issue_category(request.policy_category_id)
        except Exception:
            raise HTTPException(status_code=404, detail="PolicyCategory not found")

        # Check if relationship already exists
        existing_relationships = await airtable.get_policy_categories_by_bill(bill_id)
        for rel in existing_relationships:
            rel_fields = rel.get("fields", {})
            if rel_fields.get("PolicyCategory_ID") == request.policy_category_id:
                raise HTTPException(
                    status_code=409, detail="Relationship already exists"
                )

        # Create the relationship
        relationship_data = {
            "Bill_ID": request.bill_id,
            "PolicyCategory_ID": request.policy_category_id,
            "Confidence_Score": request.confidence_score,
            "Is_Manual": request.is_manual,
            "Notes": request.notes or "",
            "Created_At": "NOW()",
        }

        relationship = await airtable.create_bill_policy_category_relationship(
            relationship_data
        )

        return {
            "success": True,
            "relationship": relationship,
            "message": "Bills-PolicyCategory relationship created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create Bills-PolicyCategory relationship: {e}")
        raise HTTPException(status_code=500, detail="Failed to create relationship")


@router.get("/{bill_id}/policy-categories")
async def get_bill_policy_categories(
    bill_id: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get all PolicyCategories related to a specific bill."""
    try:
        # Validate bill exists
        try:
            await airtable.get_bill(bill_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Bill not found")

        # Get relationships
        relationships = await airtable.get_policy_categories_by_bill(bill_id)

        # Fetch full PolicyCategory data for each relationship
        policy_categories = []
        for rel in relationships:
            rel_fields = rel.get("fields", {})
            category_id = rel_fields.get("PolicyCategory_ID")

            if category_id:
                try:
                    category = await airtable.get_issue_category(category_id)
                    policy_categories.append(
                        {
                            "category": category,
                            "confidence_score": rel_fields.get("Confidence_Score", 0.8),
                            "is_manual": rel_fields.get("Is_Manual", False),
                            "notes": rel_fields.get("Notes", ""),
                            "relationship_id": rel.get("id"),
                            "created_at": rel_fields.get("Created_At", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch PolicyCategory {category_id}: {e}")

        return {
            "bill_id": bill_id,
            "policy_categories": policy_categories,
            "total_count": len(policy_categories),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get policy categories for bill {bill_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch policy categories")


@router.put("/{bill_id}/policy-categories/{relationship_id}")
async def update_bill_policy_category_relationship(
    bill_id: str,
    relationship_id: str,
    request: PolicyCategoryRelationshipRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Update an existing Bills-PolicyCategory relationship."""
    try:
        # Validate that the bill_id matches the request
        if bill_id != request.bill_id:
            raise HTTPException(status_code=400, detail="Bill ID mismatch")

        # Update the relationship
        relationship_data = {
            "Confidence_Score": request.confidence_score,
            "Is_Manual": request.is_manual,
            "Notes": request.notes or "",
            "Updated_At": "NOW()",
        }

        relationship = await airtable.update_bill_policy_category_relationship(
            relationship_id, relationship_data
        )

        return {
            "success": True,
            "relationship": relationship,
            "message": "Bills-PolicyCategory relationship updated successfully",
        }

    except Exception as e:
        logger.error(f"Failed to update Bills-PolicyCategory relationship: {e}")
        raise HTTPException(status_code=500, detail="Failed to update relationship")


@router.delete("/{bill_id}/policy-categories/{relationship_id}")
async def delete_bill_policy_category_relationship(
    bill_id: str,
    relationship_id: str,
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Delete a Bills-PolicyCategory relationship."""
    try:
        # Delete the relationship
        await airtable.delete_bill_policy_category_relationship(relationship_id)

        return {
            "success": True,
            "message": "Bills-PolicyCategory relationship deleted successfully",
        }

    except Exception as e:
        logger.error(f"Failed to delete Bills-PolicyCategory relationship: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete relationship")


# Bulk operations for data migration


@router.post("/policy-categories/bulk-create")
async def bulk_create_bill_policy_category_relationships(
    request: list[PolicyCategoryRelationshipRequest],
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Bulk create Bills-PolicyCategory relationships for data migration."""
    try:
        if len(request) > 100:
            raise HTTPException(
                status_code=400, detail="Bulk operations limited to 100 items"
            )

        created_relationships = []
        failed_relationships = []

        for rel_request in request:
            try:
                # Validate entities exist
                await airtable.get_bill(rel_request.bill_id)
                await airtable.get_issue_category(rel_request.policy_category_id)

                # Create relationship
                relationship_data = {
                    "Bill_ID": rel_request.bill_id,
                    "PolicyCategory_ID": rel_request.policy_category_id,
                    "Confidence_Score": rel_request.confidence_score,
                    "Is_Manual": rel_request.is_manual,
                    "Notes": rel_request.notes or "",
                    "Created_At": "NOW()",
                }

                relationship = await airtable.create_bill_policy_category_relationship(
                    relationship_data
                )
                created_relationships.append(relationship)

            except Exception as e:
                failed_relationships.append(
                    {
                        "bill_id": rel_request.bill_id,
                        "policy_category_id": rel_request.policy_category_id,
                        "error": str(e),
                    }
                )
                logger.warning(
                    f"Failed to create relationship for bill {rel_request.bill_id}: {e}"
                )

        return {
            "success": True,
            "created_count": len(created_relationships),
            "failed_count": len(failed_relationships),
            "created_relationships": created_relationships,
            "failed_relationships": failed_relationships,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk create Bills-PolicyCategory relationships: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to bulk create relationships"
        )


# Statistics endpoints


@router.get("/statistics/policy-categories")
async def get_bills_policy_category_statistics(
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Get statistics about Bills-PolicyCategory relationships."""
    try:
        # Get all relationships
        relationships = await airtable.list_bills_policy_categories()

        # Count by confidence score ranges
        confidence_stats = {
            "high_confidence": len(
                [
                    r
                    for r in relationships
                    if r.get("fields", {}).get("Confidence_Score", 0) >= 0.9
                ]
            ),
            "medium_confidence": len(
                [
                    r
                    for r in relationships
                    if 0.7 <= r.get("fields", {}).get("Confidence_Score", 0) < 0.9
                ]
            ),
            "low_confidence": len(
                [
                    r
                    for r in relationships
                    if r.get("fields", {}).get("Confidence_Score", 0) < 0.7
                ]
            ),
        }

        # Count manual vs automatic
        manual_stats = {
            "manual": len(
                [
                    r
                    for r in relationships
                    if r.get("fields", {}).get("Is_Manual", False)
                ]
            ),
            "automatic": len(
                [
                    r
                    for r in relationships
                    if not r.get("fields", {}).get("Is_Manual", False)
                ]
            ),
        }

        # Get top PolicyCategories by bill count
        category_counts = {}
        for rel in relationships:
            category_id = rel.get("fields", {}).get("PolicyCategory_ID")
            if category_id:
                category_counts[category_id] = category_counts.get(category_id, 0) + 1

        # Sort by count and get top 10
        top_categories = sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_relationships": len(relationships),
            "confidence_distribution": confidence_stats,
            "manual_vs_automatic": manual_stats,
            "top_policy_categories": [
                {"policy_category_id": cat_id, "bill_count": count}
                for cat_id, count in top_categories
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get Bills-PolicyCategory statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")
