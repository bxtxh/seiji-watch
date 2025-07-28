#!/usr/bin/env python3
"""Simplified API server for testing."""

import logging
import os
from typing import Any

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment variables with validation
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

if not AIRTABLE_PAT:
    raise ValueError("AIRTABLE_PAT environment variable is required")
if not AIRTABLE_BASE_ID:
    raise ValueError("AIRTABLE_BASE_ID environment variable is required")

app = FastAPI(title="Diet Issue Tracker API (Simplified)")

# CORS設定 - More restrictive configuration
cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")
cors_methods = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
cors_headers = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)


# Airtable helper
async def fetch_airtable(
    table_name: str, max_records: int = 100
) -> list[dict[str, Any]]:
    """Fetch data from Airtable."""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}?maxRecords={max_records}"

    # Configure timeout
    timeout = aiohttp.ClientTimeout(total=30)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("records", [])
                else:
                    logger.error(
                        f"Airtable API error: {resp.status} - {await resp.text()}"
                    )
                    raise HTTPException(
                        status_code=resp.status, detail="Failed to fetch data"
                    )
    except TimeoutError:
        logger.error(f"Timeout while fetching from Airtable table: {table_name}")
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        logger.error(f"Unexpected error fetching from Airtable: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway-simplified",
        "version": "1.0.0",
    }


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway-simplified",
        "version": "1.0.0",
    }


@app.get("/api/bills")
async def get_bills(max_records: int = 100):
    """Get bills from Airtable."""
    try:
        bills = await fetch_airtable("Bills (法案)", max_records)
        return bills
    except Exception as e:
        logger.error(f"Error in get_bills: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/bills/search")
async def search_bills_get(
    q: str = "", limit: int = 20, offset: int = 0, status: str = None
):
    """Search bills (GET)."""
    try:
        # Get all bills
        bills = await fetch_airtable("Bills (法案)", 100)

        # Simple filtering
        query = q.lower()

        filtered_bills = []
        for bill in bills:
            fields = bill.get("fields", {})
            name = fields.get("Name", "").lower()
            bill_status = fields.get("Bill_Status", "")

            # Apply filters
            if query and query not in name:
                continue
            if status and status != bill_status:
                continue

            filtered_bills.append(bill)

        # Apply pagination
        paginated = filtered_bills[offset : offset + limit]

        return {
            "success": True,
            "results": paginated,
            "total_found": len(filtered_bills),
            "query": q,
            "filters": {"status": status},
        }
    except Exception as e:
        logger.error(f"Error in search_bills_get: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/bills/search")
async def search_bills(request: dict):
    """Search bills."""
    try:
        # Get all bills
        bills = await fetch_airtable("Bills (法案)", request.get("max_records", 100))

        # Simple filtering
        query = request.get("query", "").lower()
        status = request.get("status", "")

        filtered_bills = []
        for bill in bills:
            fields = bill.get("fields", {})
            name = fields.get("Name", "").lower()
            bill_status = fields.get("Bill_Status", "")

            # Apply filters
            if query and query not in name:
                continue
            if status and status != bill_status:
                continue

            filtered_bills.append(bill)

        return {
            "success": True,
            "results": filtered_bills,
            "total_found": len(filtered_bills),
            "query": request.get("query", ""),
            "filters": {"status": status},
        }
    except Exception as e:
        logger.error(f"Error in search_bills: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/issues/categories")
async def get_categories(max_records: int = 100):
    """Get issue categories."""
    try:
        categories = await fetch_airtable("IssueCategories", max_records)
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        # Return empty array if table doesn't exist
        return []


@app.get("/api/issues/categories/{category_id}")
async def get_category(category_id: str):
    """Get specific category."""
    try:
        categories = await fetch_airtable("IssueCategories", 1000)
        for cat in categories:
            if cat.get("id") == category_id:
                return cat
        raise HTTPException(status_code=404, detail="Category not found")
    except Exception as e:
        logger.error(f"Error in get_category: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/issues/categories/tree")
async def get_categories_tree():
    """Get categories in tree structure."""
    try:
        # For now, return a simple tree structure
        # In production, this would fetch from IssueCategories table and build hierarchy
        return [
            {
                "id": "1",
                "name": "社会保障",
                "children": [
                    {"id": "11", "name": "医療・健康保険", "children": []},
                    {"id": "12", "name": "年金", "children": []},
                    {"id": "13", "name": "介護", "children": []},
                ],
            },
            {
                "id": "2",
                "name": "経済・産業",
                "children": [
                    {"id": "21", "name": "金融", "children": []},
                    {"id": "22", "name": "貿易", "children": []},
                    {"id": "23", "name": "中小企業", "children": []},
                ],
            },
            {
                "id": "3",
                "name": "環境・エネルギー",
                "children": [
                    {"id": "31", "name": "気候変動", "children": []},
                    {"id": "32", "name": "再生可能エネルギー", "children": []},
                    {"id": "33", "name": "原子力", "children": []},
                ],
            },
            {
                "id": "4",
                "name": "教育・文化",
                "children": [
                    {"id": "41", "name": "学校教育", "children": []},
                    {"id": "42", "name": "高等教育", "children": []},
                    {"id": "43", "name": "文化振興", "children": []},
                ],
            },
            {
                "id": "5",
                "name": "外交・防衛",
                "children": [
                    {"id": "51", "name": "外交政策", "children": []},
                    {"id": "52", "name": "防衛・安全保障", "children": []},
                    {"id": "53", "name": "国際協力", "children": []},
                ],
            },
        ]
    except Exception as e:
        logger.error(f"Error in get_categories_tree: {str(e)}")
        return []


@app.get("/api/members/{member_id}")
async def get_member(member_id: str):
    """Get specific member details."""
    try:
        members = await fetch_airtable("Members (議員)", 1000)

        # Fetch parties to resolve party names
        parties = await fetch_airtable("Parties (政党)", 100)
        party_map = {p["id"]: p["fields"].get("Name", "無所属") for p in parties}

        for member in members:
            if member.get("id") == member_id:
                # Add party name to fields
                if member.get("fields", {}).get("Party"):
                    party_id = (
                        member["fields"]["Party"][0]
                        if isinstance(member["fields"]["Party"], list)
                        else member["fields"]["Party"]
                    )
                    member["fields"]["Party_Name"] = party_map.get(party_id, "無所属")
                else:
                    member["fields"]["Party_Name"] = "無所属"

                return {"success": True, "member": member}

        raise HTTPException(status_code=404, detail="Member not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_member: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/members/{member_id}/voting-stats")
async def get_member_voting_stats(member_id: str):
    """Get member voting statistics."""
    # In a real implementation, this would fetch actual voting data from Airtable
    # For MVP, return mock data
    return {
        "success": True,
        "stats": {
            "total_votes": 127,
            "attendance_rate": 0.94,
            "party_alignment_rate": 0.87,
            "voting_pattern": {
                "yes_votes": 89,
                "no_votes": 28,
                "abstentions": 5,
                "absences": 5,
            },
        },
    }


@app.get("/api/policy/member/{member_id}/analysis")
async def get_member_policy_analysis(member_id: str):
    """Get member policy analysis."""
    # In a real implementation, this would analyze actual voting data and speeches
    # For MVP, return mock data
    return {
        "success": True,
        "analysis": {
            "member_id": member_id,
            "analysis_timestamp": "2025-01-28T10:00:00Z",
            "overall_activity_level": 0.75,
            "party_alignment_rate": 0.87,
            "data_completeness": 0.82,
            "stance_distribution": {
                "strong_support": 15,
                "support": 25,
                "neutral": 10,
                "oppose": 8,
                "strong_oppose": 3,
            },
            "strongest_positions": [
                {
                    "issue_tag": "環境政策",
                    "issue_name": "カーボンニュートラル2050目標",
                    "stance": "strong_support",
                    "confidence": 0.92,
                    "vote_count": 8,
                    "supporting_evidence": [
                        "環境委員会で積極的に発言",
                        "関連法案に全て賛成票を投じている",
                        "再生可能エネルギー推進議連のメンバー",
                    ],
                    "last_updated": "2025-01-15T00:00:00Z",
                },
                {
                    "issue_tag": "社会保障",
                    "issue_name": "高齢者医療費負担の見直し",
                    "stance": "oppose",
                    "confidence": 0.85,
                    "vote_count": 5,
                    "supporting_evidence": [
                        "厚生労働委員会で負担増に反対の立場を表明",
                        "関連法案修正案を提出",
                    ],
                    "last_updated": "2025-01-20T00:00:00Z",
                },
                {
                    "issue_tag": "経済政策",
                    "issue_name": "中小企業支援強化",
                    "stance": "support",
                    "confidence": 0.78,
                    "vote_count": 6,
                    "supporting_evidence": [
                        "経済産業委員会で支援策拡充を提言",
                        "地元企業との意見交換会を定期開催",
                    ],
                    "last_updated": "2025-01-10T00:00:00Z",
                },
            ],
            "total_issues_analyzed": 61,
            "policy_interests": ["環境政策", "社会保障", "経済政策", "教育"],
            "voting_patterns": {
                "環境関連": {"support": 12, "oppose": 1, "abstain": 0},
                "社会保障関連": {"support": 8, "oppose": 5, "abstain": 2},
                "経済関連": {"support": 15, "oppose": 3, "abstain": 1},
            },
            "stance_summary": {"progressive": 0.65, "conservative": 0.35},
        },
    }


@app.get("/api/members")
async def get_members(max_records: int = 100):
    """Get members."""
    try:
        members = await fetch_airtable("Members (議員)", max_records)

        # Fetch parties to resolve party names
        parties = await fetch_airtable("Parties (政党)", 100)
        party_map = {p["id"]: p["fields"].get("Name", "無所属") for p in parties}

        # Add party names to members
        for member in members:
            if member.get("fields", {}).get("Party"):
                party_id = (
                    member["fields"]["Party"][0]
                    if isinstance(member["fields"]["Party"], list)
                    else member["fields"]["Party"]
                )
                member["fields"]["Party_Name"] = party_map.get(party_id, "無所属")
            else:
                member["fields"]["Party_Name"] = "無所属"

        return members
    except Exception as e:
        logger.error(f"Error in get_members: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/speeches")
async def get_speeches(max_records: int = 100):
    """Get speeches."""
    try:
        speeches = await fetch_airtable("Speeches (発言)", max_records)
        return speeches
    except Exception as e:
        logger.error(f"Error in get_speeches: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/issues/kanban")
async def get_issues_kanban(range: str = "30d", max_per_stage: int = 8):
    """Get issues in kanban format."""
    try:
        # Fetch issues from Airtable
        issues = await fetch_airtable("Issues (課題)", 100)

        # Group issues by stage (Priority field seems to exist)
        stages = {"backlog": [], "in_progress": [], "in_review": [], "completed": []}

        for issue in issues:
            fields = issue.get("fields", {})
            priority = fields.get("Priority", "").lower()

            # Map priority to stages (adjust based on actual data)
            if priority in ["high", "高"]:
                stage = "in_progress"
            elif priority in ["medium", "中"]:
                stage = "in_review"
            elif priority in ["low", "低"]:
                stage = "completed"
            else:
                stage = "backlog"

            # Transform to expected format
            # Extract tags from the Tags field or Related_Keywords
            tags = []
            if fields.get("Tags"):
                # If Tags is a string, split it
                if isinstance(fields.get("Tags"), str):
                    tags = [t.strip() for t in fields.get("Tags").split(",")][:3]
                elif isinstance(fields.get("Tags"), list):
                    tags = fields.get("Tags")[:3]
            elif fields.get("Related_Keywords"):
                # Use Related_Keywords as fallback
                if isinstance(fields.get("Related_Keywords"), str):
                    tags = [
                        t.strip() for t in fields.get("Related_Keywords").split(",")
                    ][:3]

            issue_data = {
                "id": issue.get("id"),
                "title": fields.get("Title", ""),
                "description": fields.get("Description", ""),
                "category": fields.get("Category_L1", ""),
                "priority": fields.get("Priority", ""),
                "created_at": fields.get("Created_At", ""),
                "updated_at": fields.get("Updated_At", ""),
                "schedule": {"from": "2025-07-01", "to": "2025-07-28"},
                "tags": tags,
                "related_bills": [],  # Empty array for now since we don't have bill relationships
            }

            stages[stage].append(issue_data)

        # Limit items per stage
        for stage in stages:
            stages[stage] = stages[stage][:max_per_stage]

        total_issues = sum(len(items) for items in stages.values())

        return {
            "success": True,
            "data": {"stages": stages},
            "metadata": {
                "total_issues": total_issues,
                "last_updated": "2025-07-28T00:00:00Z",
                "date_range": {"from": "2025-07-01", "to": "2025-07-28"},
            },
        }
    except Exception as e:
        logger.error(f"Error fetching kanban data: {str(e)}")
        return {
            "success": True,
            "data": {
                "stages": {
                    "backlog": [],
                    "in_progress": [],
                    "in_review": [],
                    "completed": [],
                }
            },
            "metadata": {
                "total_issues": 0,
                "last_updated": "2025-07-28T00:00:00Z",
                "date_range": {"from": "2025-07-01", "to": "2025-07-28"},
            },
        }


@app.get("/api/issues")
async def get_issues(
    limit: int = 20, offset: int = 0, category: str = None, tag: str = None
):
    """Get issues with pagination."""
    try:
        all_issues = await fetch_airtable("Issues (課題)", 1000)

        # Transform issues to expected format
        transformed_issues = []
        for issue in all_issues:
            fields = issue.get("fields", {})

            # Parse tags from comma-separated string
            tags_str = fields.get("Tags", "")
            tags = (
                [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                if tags_str
                else []
            )

            transformed = {
                "id": issue.get("id"),
                "title": fields.get("Title", ""),
                "description": fields.get("Description", ""),
                "category": fields.get("Category_L1", ""),
                "subcategory": fields.get("Category_L2", ""),
                "status": fields.get("Status", ""),
                "priority": fields.get("Priority", ""),
                "tags": tags,
                "issue_tags": [
                    {"id": f"tag-{i}", "name": tag, "color": "#94a3b8"}
                    for i, tag in enumerate(tags)
                ],
                "created_at": fields.get("Created_At", ""),
                "updated_at": fields.get("Updated_At", ""),
                "schedule": {"from": "2025-07-01", "to": "2025-07-28"},
                "related_bills": [],
            }

            # Apply filters
            if category and transformed["category"] != category:
                continue
            if tag and tag not in transformed["tags"]:
                continue

            transformed_issues.append(transformed)

        # Apply pagination
        total = len(transformed_issues)
        paginated = transformed_issues[offset : offset + limit]

        return {
            "success": True,
            "issues": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Error in get_issues: {str(e)}")
        return {
            "success": False,
            "issues": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/issues/{issue_id}")
async def get_issue(issue_id: str):
    """Get specific issue."""
    try:
        issues = await fetch_airtable("Issues (課題)", 1000)

        for issue in issues:
            if issue.get("id") == issue_id:
                fields = issue.get("fields", {})

                # Parse tags from comma-separated string
                tags_str = fields.get("Tags", "")
                tags = (
                    [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                    if tags_str
                    else []
                )

                transformed = {
                    "id": issue.get("id"),
                    "title": fields.get("Title", ""),
                    "description": fields.get("Description", ""),
                    "category": fields.get("Category_L1", ""),
                    "subcategory": fields.get("Category_L2", ""),
                    "status": fields.get("Status", ""),
                    "priority": fields.get("Priority", ""),
                    "tags": tags,
                    "issue_tags": [
                        {"id": f"tag-{i}", "name": tag, "color": "#94a3b8"}
                        for i, tag in enumerate(tags)
                    ],
                    "created_at": fields.get("Created_At", ""),
                    "updated_at": fields.get("Updated_At", ""),
                    "schedule": {"from": "2025-07-01", "to": "2025-07-28"},
                    "related_bills": [],
                    "bills": [],  # For compatibility
                    "timeline": [],  # For timeline component
                    "watch_count": 0,
                }

                return {"success": True, "issue": transformed}

        raise HTTPException(status_code=404, detail="Issue not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_issue: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/issues/{issue_id}/bills")
async def get_issue_bills(issue_id: str):
    """Get bills related to specific issue."""
    try:
        # For now, return empty array
        # In production, this would fetch related bills
        return {"success": True, "bills": []}
    except Exception as e:
        logger.error(f"Error in get_issue_bills: {str(e)}")
        return {"success": False, "bills": [], "error": "Internal server error"}


@app.get("/api/issues/tags")
async def get_issue_tags():
    """Get all unique issue tags."""
    try:
        issues = await fetch_airtable("Issues (課題)", 1000)
        all_tags = set()

        for issue in issues:
            fields = issue.get("fields", {})
            tags_str = fields.get("Tags", "")
            if tags_str:
                tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
                all_tags.update(tags)

        # Convert to list of tag objects
        tag_list = [{"name": tag, "count": 0} for tag in sorted(all_tags)]

        # Count occurrences
        for tag_obj in tag_list:
            count = 0
            for issue in issues:
                fields = issue.get("fields", {})
                tags_str = fields.get("Tags", "")
                if tags_str and tag_obj["name"] in tags_str:
                    count += 1
            tag_obj["count"] = count

        return {"success": True, "tags": tag_list}
    except Exception as e:
        logger.error(f"Error in get_issue_tags: {str(e)}")
        return {"success": False, "tags": []}


if __name__ == "__main__":
    import uvicorn

    print("Starting simplified API server on port 8081...")
    print(f"Airtable Base ID: {AIRTABLE_BASE_ID}")
    uvicorn.run(app, host="0.0.0.0", port=8081)
