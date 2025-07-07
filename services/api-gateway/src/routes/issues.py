"""Issue management API routes."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Header
from pydantic import BaseModel, validator
from ..security.validation import validate_and_sanitize_request, InputValidator

# Import shared models and clients
from shared.models import Issue, IssueTag
from shared.clients import AirtableClient
from shared.utils import IssueExtractor

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
    related_bills: Optional[List[str]] = None
    issue_tags: Optional[List[str]] = None
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        if len(v) > 200:
            raise ValueError('Title too long (max 200 characters)')
        return InputValidator.sanitize_string(v, 200)
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        if len(v) > 2000:
            raise ValueError('Description too long (max 2000 characters)')
        return InputValidator.sanitize_string(v, 2000)
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ['low', 'medium', 'high', 'urgent']
        if v not in allowed_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(allowed_priorities)}')
        return v

class IssueExtractRequest(BaseModel):
    bill_content: str
    bill_title: str = ""
    bill_id: Optional[str] = None
    
    @validator('bill_content')
    def validate_bill_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Bill content cannot be empty')
        if len(v) > 50000:  # 50KB limit for bill content
            raise ValueError('Bill content too long (max 50000 characters)')
        return InputValidator.sanitize_string(v, 50000)
    
    @validator('bill_title')
    def validate_bill_title(cls, v):
        if v and len(v) > 500:
            raise ValueError('Bill title too long (max 500 characters)')
        return InputValidator.sanitize_string(v, 500) if v else v

class IssueTagCreateRequest(BaseModel):
    name: str
    category: str
    color_code: str = "#3B82F6"
    description: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Tag name cannot be empty')
        if len(v) > 100:
            raise ValueError('Tag name too long (max 100 characters)')
        return InputValidator.sanitize_string(v, 100)
    
    @validator('category')
    def validate_category(cls, v):
        allowed_categories = [
            '予算・決算', '税制', '社会保障', '外交・国際', 
            '経済・産業', '教育・文化', '環境・エネルギー', 'その他'
        ]
        if v not in allowed_categories:
            raise ValueError(f'Category must be one of: {", ".join(allowed_categories)}')
        return v
    
    @validator('color_code')
    def validate_color_code(cls, v):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color code must be a valid hex color (e.g., #3B82F6)')
        return v

# Issue endpoints
@router.get("/", response_model=List[dict])
async def list_issues(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
    max_records: int = Query(100, le=1000),
    airtable: AirtableClient = Depends(get_airtable_client)
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
            filter_formula=filter_formula,
            max_records=max_records
        )
        
        return issues
        
    except Exception as e:
        logger.error(f"Failed to list issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch issues")

@router.get("/{issue_id}")
async def get_issue(
    issue_id: str,
    airtable: AirtableClient = Depends(get_airtable_client)
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
    request: IssueCreateRequest,
    airtable: AirtableClient = Depends(get_airtable_client)
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
    airtable: AirtableClient = Depends(get_airtable_client)
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
    extractor: IssueExtractor = Depends(get_issue_extractor)
):
    """Extract issues from bill content using LLM."""
    try:
        # Extract issues using LLM
        extracted_issues = await extractor.extract_issues_from_bill(
            request.bill_content,
            request.bill_title
        )
        
        if not extracted_issues:
            return {"message": "No issues extracted", "issues": []}
        
        # For each extracted issue, suggest tags
        for issue in extracted_issues:
            if "suggested_tags" not in issue:
                issue["suggested_tags"] = []
            
            # Get existing tags for suggestions
            existing_tags = await airtable.list_issue_tags()
            tag_names = [tag["fields"].get("Name", "") for tag in existing_tags if "fields" in tag]
            
            # Add default tags based on category
            default_tags = extractor.generate_default_tags(issue.get("category", "その他"))
            issue["suggested_tags"].extend(default_tags)
            
            # Remove duplicates
            issue["suggested_tags"] = list(set(issue["suggested_tags"]))
        
        return {
            "message": f"Extracted {len(extracted_issues)} issues",
            "issues": extracted_issues,
            "bill_id": request.bill_id
        }
        
    except Exception as e:
        logger.error(f"Failed to extract issues: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract issues")

# Issue Tags endpoints
@router.get("/tags/", response_model=List[dict])
async def list_issue_tags(
    category: Optional[str] = Query(None, description="Filter by category"),
    airtable: AirtableClient = Depends(get_airtable_client)
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
    airtable: AirtableClient = Depends(get_airtable_client)
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
    tag_id: str,
    airtable: AirtableClient = Depends(get_airtable_client)
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
    bill_id: str,
    airtable: AirtableClient = Depends(get_airtable_client)
):
    """Get all issues related to a specific bill."""
    try:
        bill_with_issues = await airtable.get_bills_with_issues(bill_id)
        return bill_with_issues
    except Exception as e:
        logger.error(f"Failed to get issues for bill {bill_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bill issues")