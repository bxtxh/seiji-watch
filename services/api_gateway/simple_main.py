#!/usr/bin/env python3
"""
Simple API Gateway for staging deployment
"""

import os
from typing import Any, List, Optional

import aiohttp
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Initialize FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API Gateway - Staging",
    description="API Gateway for staging environment with real Airtable data",
    version="1.0.0",
)

# Add CORS middleware
# Get allowed origins from environment variable with defaults
allowed_origins = os.getenv("ALLOWED_CORS_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == ['']:
    # Default origins for staging environment
    allowed_origins = [
        "https://seiji-watch-web-frontend-staging-496359339214.asia-northeast1.run.app",
        "https://staging.politics-watch.jp"
    ]

# Add localhost only for local development
if os.getenv("ENVIRONMENT", "staging") == "development":
    allowed_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class AirtableClient:
    """Simple Airtable client for staging environment"""

    def __init__(self):
        self.api_key = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        if not self.api_key or not self.base_id:
            raise ValueError("AIRTABLE_PAT and AIRTABLE_BASE_ID must be set")
        
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_bills(self, limit: int = 100, offset: Optional[str] = None) -> dict:
        """List bills from Airtable"""
        params = {"pageSize": min(limit, 100)}
        if offset:
            params["offset"] = offset

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/Bills%20(%E6%B3%95%E6%A1%88)",
                headers=self.headers,
                params=params,
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Airtable API error: {await response.text()}",
                    )
                return await response.json()

    async def search_bills(self, query: str, filters: dict = None) -> dict:
        """Search bills with query and filters"""
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

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/Bills%20(%E6%B3%95%E6%A1%88)",
                headers=self.headers,
                params=params,
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Airtable API error: {await response.text()}",
                    )
                return await response.json()

    async def list_members(self, limit: int = 100) -> dict:
        """List members from Airtable"""
        params = {"pageSize": min(limit, 100)}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/Members%20(%E8%AD%B0%E5%93%A1)",
                headers=self.headers,
                params=params,
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Airtable API error: {await response.text()}",
                    )
                return await response.json()


# Initialize Airtable client lazily
_airtable_client = None

def get_airtable_client():
    global _airtable_client
    if _airtable_client is None:
        _airtable_client = AirtableClient()
    return _airtable_client


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api-gateway", "environment": "staging"}

@app.get("/api/health")
async def api_health_check():
    """API Health check endpoint"""
    return {"status": "healthy", "service": "api-gateway", "environment": "staging"}

@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables"""
    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    return {
        "airtable_pat_present": bool(pat),
        "airtable_pat_prefix": pat[:10] if pat else None,
        "airtable_base_id_present": bool(base_id),
        "airtable_base_id": base_id if base_id else None,
        "env_vars_count": len([k for k in os.environ.keys() if k.startswith("AIRTABLE")])
    }


@app.get("/api/bills/search")
async def search_bills(
    q: Optional[str] = Query(None, description="Search query"),
    status: Optional[str] = Query(None, description="Bill status filter"),
    stage: Optional[str] = Query(None, description="Bill stage filter"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
):
    """Search bills with query and filters"""
    try:
        filters = {}
        if status:
            filters["status"] = status
        if stage:
            filters["stage"] = stage

        if q:
            result = await get_airtable_client().search_bills(q, filters)
        else:
            result = await get_airtable_client().list_bills(limit)

        # Transform Airtable response to frontend format
        bills = []
        for record in result.get("records", []):
            fields = record.get("fields", {})
            bills.append({
                "id": record["id"],
                "fields": {
                    "Bill_Number": fields.get("Bill_Number", ""),
                    "Name": fields.get("Name", ""),
                    "Bill_Status": fields.get("Bill_Status", ""),
                    "Category": fields.get("Category", ""),
                    "Diet_Session": fields.get("Diet_Session", ""),
                    "Submitted_Date": fields.get("Submitted_Date", ""),
                    "Summary": fields.get("Summary", ""),
                    "Stage": fields.get("Stage", ""),
                }
            })

        return {
            "success": True,
            "results": bills,
            "total_found": len(bills),
            "query": q,
            "filters": filters,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.get("/api/bills/{bill_id}")
async def get_bill(bill_id: str):
    """Get bill details by ID"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{get_airtable_client().base_url}/Bills/{bill_id}",
                headers=get_airtable_client().headers,
            ) as response:
                if response.status == 404:
                    raise HTTPException(status_code=404, detail="Bill not found")
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Airtable API error: {await response.text()}",
                    )
                
                result = await response.json()
                return {
                    "success": True,
                    "result": {
                        "id": result["id"],
                        "fields": result.get("fields", {}),
                    }
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bill: {str(e)}")


@app.get("/api/members")
async def list_members(
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
):
    """List members"""
    try:
        result = await get_airtable_client().list_members(limit)

        # Transform Airtable response to frontend format
        members = []
        for record in result.get("records", []):
            fields = record.get("fields", {})
            members.append({
                "id": record["id"],
                "fields": {
                    "Name": fields.get("Name", ""),
                    "Name_Kana": fields.get("Name_Kana", ""),
                    "Party": fields.get("Party", ""),
                    "House": fields.get("House", ""),
                    "Constituency": fields.get("Constituency", ""),
                }
            })

        return {
            "success": True,
            "results": members,
            "total_found": len(members),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching members: {str(e)}")


@app.get("/api/members/{member_id}")
async def get_member(member_id: str):
    """Get member details by ID"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{get_airtable_client().base_url}/Members/{member_id}",
                headers=get_airtable_client().headers,
            ) as response:
                if response.status == 404:
                    raise HTTPException(status_code=404, detail="Member not found")
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Airtable API error: {await response.text()}",
                    )
                
                result = await response.json()
                return {
                    "success": True,
                    "result": {
                        "id": result["id"],
                        "fields": result.get("fields", {}),
                    }
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching member: {str(e)}")


@app.get("/api/issues/kanban")
async def get_issues_kanban(
    range: str = Query("30d", description="Time range for issues"),
    max_per_stage: int = Query(8, description="Maximum issues per stage"),
):
    """Get issues in kanban format"""
    try:
        # Return structure that matches frontend expectations
        return {
            "success": True,
            "data": {
                "stages": {
                    "backlog": [],
                    "in_progress": [],
                    "in_review": [],
                    "completed": []
                }
            },
            "metadata": {
                "total_issues": 0,
                "range": range,
                "max_per_stage": max_per_stage,
                "last_updated": "2025-07-26T00:00:00Z"
            },
            "message": "Kanban data structure ready"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching kanban data: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)