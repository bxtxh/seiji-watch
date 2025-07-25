"""Issue management API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, validator

from shared.clients import AirtableClient

# Import shared models and clients
from shared.utils import IssueExtractor

from ..security.validation import InputValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/issues", tags=["Issues"])

# Dependency for Airtable client


async def get_airtable_client() -> AirtableClient:
    """Get Airtable client instance."""
    return AirtableClient()


# Dependency for Issue Extractor


async def get_issue_extractor() -> IssueExtractor:
    """Get Issue Extractor instance."""
    return IssueExtractor()


# Request/Response models with validation


class IssueCreateRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    related_bills: list[str] | None = None
    issue_tags: list[str] | None = None

    @validator("title")
    def validate_title(self, v):
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        if len(v) > 200:
            raise ValueError("Title too long (max 200 characters)")
        return InputValidator.sanitize_string(v, 200)

    @validator("description")
    def validate_description(self, v):
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        if len(v) > 2000:
            raise ValueError("Description too long (max 2000 characters)")
        return InputValidator.sanitize_string(v, 2000)

    @validator("priority")
    def validate_priority(self, v):
        allowed_priorities = ["low", "medium", "high", "urgent"]
        if v not in allowed_priorities:
            raise ValueError(
                f"Priority must be one of: {', '.join(allowed_priorities)}"
            )
        return v


class IssueExtractRequest(BaseModel):
    bill_content: str
    bill_title: str = ""
    bill_id: str | None = None

    @validator("bill_content")
    def validate_bill_content(self, v):
        if not v or not v.strip():
            raise ValueError("Bill content cannot be empty")
        if len(v) > 50000:  # 50KB limit for bill content
            raise ValueError("Bill content too long (max 50000 characters)")
        return InputValidator.sanitize_string(v, 50000)

    @validator("bill_title")
    def validate_bill_title(self, v):
        if v and len(v) > 500:
            raise ValueError("Bill title too long (max 500 characters)")
        return InputValidator.sanitize_string(v, 500) if v else v


class IssueTagCreateRequest(BaseModel):
    name: str
    category: str
    color_code: str = "#3B82F6"
    description: str | None = None

    @validator("name")
    def validate_name(self, v):
        if not v or not v.strip():
            raise ValueError("Tag name cannot be empty")
        if len(v) > 100:
            raise ValueError("Tag name too long (max 100 characters)")
        return InputValidator.sanitize_string(v, 100)

    @validator("category")
    def validate_category(self, v):
        allowed_categories = [
            "予算・決算",
            "税制",
            "社会保障",
            "外交・国際",
            "経済・産業",
            "教育・文化",
            "環境・エネルギー",
            "その他",
        ]
        if v not in allowed_categories:
            raise ValueError(
                f"Category must be one of: {', '.join(allowed_categories)}"
            )
        return v

    @validator("color_code")
    def validate_color_code(self, v):
        import re

        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color code must be a valid hex color (e.g., #3B82F6)")
        return v


# Issue endpoints


@router.get("/", response_model=list[dict])
async def list_issues(
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status"),
    max_records: int = Query(100, le=1000),
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """List all issues with optional filtering."""
    try:
        # Build filter formula
        filters = []
        if category:
            filters.append(f"{{Category}} = '{category}'")
        if status:
            filters.append(f"{{Status}} = '{status}'")

        filter_formula = "AND(" + ", ".join(filters) + ")" if filters else None

        issues = await airtable.list_issues(
            filter_formula=filter_formula, max_records=max_records
        )

        return issues

    except Exception as e:
        logger.error(f"Failed to list issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issues")


@router.get("/{issue_id}")
async def get_issue(
    issue_id: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get a specific issue by ID."""
    try:
        issue = await airtable.get_issue(issue_id)
        return issue
    except Exception as e:
        logger.error(f"Failed to get issue {issue_id}: {e}")
        raise HTTPException(status_code=404, detail="Issue not found")


@router.post("/")
async def create_issue(
    request: IssueCreateRequest, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Create a new issue."""
    try:
        issue_data = request.model_dump()
        issue = await airtable.create_issue(issue_data)
        return issue
    except Exception as e:
        logger.error(f"Failed to create issue: {e}")
        raise HTTPException(status_code=500, detail="Failed to create issue")


@router.put("/{issue_id}")
async def update_issue(
    issue_id: str,
    request: IssueCreateRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Update an existing issue."""
    try:
        issue_data = request.model_dump()
        issue = await airtable.update_issue(issue_id, issue_data)
        return issue
    except Exception as e:
        logger.error(f"Failed to update issue {issue_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update issue")


# LLM extraction endpoint


@router.post("/extract")
async def extract_issues(
    request: IssueExtractRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
    extractor: IssueExtractor = Depends(get_issue_extractor),
):
    """Extract issues from bill content using LLM."""
    try:
        # Extract issues using LLM
        extracted_issues = await extractor.extract_issues_from_bill(
            request.bill_content, request.bill_title
        )

        if not extracted_issues:
            return {"message": "No issues extracted", "issues": []}

        # For each extracted issue, suggest tags
        for issue in extracted_issues:
            if "suggested_tags" not in issue:
                issue["suggested_tags"] = []

            # Get existing tags for suggestions
            existing_tags = await airtable.list_issue_tags()
            [tag["fields"].get("Name", "") for tag in existing_tags if "fields" in tag]

            # Add default tags based on category
            default_tags = extractor.generate_default_tags(
                issue.get("category", "その他")
            )
            issue["suggested_tags"].extend(default_tags)

            # Remove duplicates
            issue["suggested_tags"] = list(set(issue["suggested_tags"]))

        return {
            "message": f"Extracted {len(extracted_issues)} issues",
            "issues": extracted_issues,
            "bill_id": request.bill_id,
        }

    except Exception as e:
        logger.error(f"Failed to extract issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract issues")


# Issue Tags endpoints


@router.get("/tags/", response_model=list[dict])
async def list_issue_tags(
    category: str | None = Query(None, description="Filter by category"),
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """List all issue tags."""
    try:
        filter_formula = f"{{Category}} = '{category}'" if category else None
        tags = await airtable.list_issue_tags(filter_formula=filter_formula)
        return tags
    except Exception as e:
        logger.error(f"Failed to list issue tags: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issue tags")


@router.post("/tags/")
async def create_issue_tag(
    request: IssueTagCreateRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Create a new issue tag."""
    try:
        tag_data = request.model_dump()
        tag = await airtable.create_issue_tag(tag_data)
        return tag
    except Exception as e:
        logger.error(f"Failed to create issue tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to create issue tag")


@router.get("/tags/{tag_id}")
async def get_issue_tag(
    tag_id: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get a specific issue tag by ID."""
    try:
        tag = await airtable.get_issue_tag(tag_id)
        return tag
    except Exception as e:
        logger.error(f"Failed to get issue tag {tag_id}: {e}")
        raise HTTPException(status_code=404, detail="Issue tag not found")


# Bills with issues


@router.get("/bills/{bill_id}/issues")
async def get_bill_issues(
    bill_id: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get all issues related to a specific bill."""
    try:
        bill_with_issues = await airtable.get_bills_with_issues(bill_id)
        return bill_with_issues
    except Exception as e:
        logger.error(f"Failed to get issues for bill {bill_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bill issues")


# Issue Categories endpoints


@router.get("/categories", response_model=list[dict])
async def list_issue_categories(
    layer: str | None = Query(None, description="Filter by layer (L1/L2/L3)"),
    parent_id: str | None = Query(None, description="Filter by parent category"),
    max_records: int = Query(1000, le=1000),
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """List issue categories with hierarchical filtering."""
    try:
        if layer:
            # Filter by layer
            categories = await airtable.get_categories_by_layer(layer)
        elif parent_id:
            # Filter by parent
            categories = await airtable.get_category_children(parent_id)
        else:
            # Get all categories
            categories = await airtable.list_issue_categories(max_records=max_records)

        return categories

    except Exception as e:
        logger.error(f"Failed to list issue categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issue categories")


@router.get("/categories/tree")
async def get_category_tree(airtable: AirtableClient = Depends(get_airtable_client)):
    """Get full category tree structure."""
    try:
        tree = await airtable.get_category_tree()
        return tree
    except Exception as e:
        logger.error(f"Failed to get category tree: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category tree")


@router.get("/categories/{category_id}")
async def get_issue_category(
    category_id: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get a specific issue category by ID."""
    try:
        category = await airtable.get_issue_category(category_id)
        return category
    except Exception as e:
        logger.error(f"Failed to get issue category {category_id}: {e}")
        raise HTTPException(status_code=404, detail="Issue category not found")


@router.get("/categories/{category_id}/children")
async def get_category_children(
    category_id: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get child categories for a specific category."""
    try:
        children = await airtable.get_category_children(category_id)
        return children
    except Exception as e:
        logger.error(f"Failed to get children for category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category children")


@router.get("/categories/search")
async def search_categories(
    q: str = Query(..., description="Search query"),
    layer: str | None = Query(None, description="Filter by layer"),
    max_records: int = Query(100, le=1000),
    airtable: AirtableClient = Depends(get_airtable_client),
):
    """Search issue categories by title."""
    try:
        # Build search filter
        search_filters = []

        # Search in both Japanese and English titles
        search_filters.append(f"SEARCH('{q}', {{Title_JA}}) > 0")
        search_filters.append(f"SEARCH('{q}', {{Title_EN}}) > 0")

        # Combine search filters with OR
        search_formula = "OR(" + ", ".join(search_filters) + ")"

        # Add layer filter if specified
        if layer:
            filter_formula = f"AND({search_formula}, {{Layer}} = '{layer}')"
        else:
            filter_formula = search_formula

        categories = await airtable.list_issue_categories(
            filter_formula=filter_formula, max_records=max_records
        )

        return categories

    except Exception as e:
        logger.error(f"Failed to search categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to search categories")


@router.get("/categories/cap/{cap_code}")
async def get_category_by_cap_code(
    cap_code: str, airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get category by CAP code."""
    try:
        category = await airtable.find_category_by_cap_code(cap_code)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except Exception as e:
        logger.error(f"Failed to get category by CAP code {cap_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category")
