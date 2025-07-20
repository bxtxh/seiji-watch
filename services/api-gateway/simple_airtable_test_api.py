#!/usr/bin/env python3
"""
Simple Airtable API test - EPIC 11 T97 verification
"""
import asyncio
import os
from typing import Any

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv('../../.env.local')

# Initialize FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API - Real Data Test",
    description="Testing real Airtable data integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

class SimpleAirtableClient:
    """Simple Airtable client for testing"""
    
    def __init__(self):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def list_bills(self, max_records: int = 100, filter_formula: str | None = None) -> list[dict[str, Any]]:
        """List bills from Airtable"""
        url = f"{self.base_url}/Bills (法案)"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("records", [])
                else:
                    raise Exception(f"Airtable error: {response.status}")
    
    async def get_bill(self, record_id: str) -> Dict[str, Any]:
        """Get a specific bill"""
        url = f"{self.base_url}/Bills (法案)/{record_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Airtable error: {response.status}")
    
    async def list_votes(self, max_records: int = 100) -> list[dict[str, Any]]:
        """List votes from Airtable"""
        url = f"{self.base_url}/Votes (投票)"
        params = {"maxRecords": max_records}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("records", [])
                else:
                    raise Exception(f"Airtable error: {response.status}")

# Initialize client
airtable = SimpleAirtableClient()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "EPIC 11 T97: API Gateway実データ連携修正 - TEST SERVER",
        "status": "operational",
        "endpoints": {
            "bills": "/api/bills",
            "bills_detail": "/api/bills/{bill_id}",
            "votes": "/api/votes", 
            "search": "/search",
            "stats": "/embeddings/stats"
        }
    }

@app.get("/health")
async def health_check():
    """Health check with Airtable connectivity."""
    try:
        # Test Airtable connection by getting 1 bill
        bills = await airtable.list_bills(max_records=1)
        
        return {
            "status": "healthy",
            "airtable": True,
            "bills_available": len(bills),
            "message": "Real data integration active"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Airtable connection failed"
        }

@app.get("/api/bills")
async def get_bills(max_records: int = Query(100, le=1000), category: Optional[str] = None):
    """Get bills from real Airtable data."""
    try:
        # Build filter for category if specified
        filter_formula = None
        if category:
            filter_formula = f"SEARCH('{category}', {{Notes}}) > 0"
        
        # Get real bills from Airtable
        bills = await airtable.list_bills(
            filter_formula=filter_formula,
            max_records=max_records
        )
        
        # Transform the data to match expected format
        transformed_bills = []
        for bill in bills:
            fields = bill.get("fields", {})
            transformed_bill = {
                "id": bill.get("id"),
                "fields": {
                    "Name": fields.get("Name", ""),
                    "Notes": fields.get("Notes", ""),
                    "Status": "実データ統合済み",
                    "Category": "実データ",
                    "Title": fields.get("Name", "")[:100],
                    "Summary": fields.get("Notes", "")[:200] + "..." if len(fields.get("Notes", "")) > 200 else fields.get("Notes", ""),
                }
            }
            transformed_bills.append(transformed_bill)
        
        return {
            "success": True,
            "data": transformed_bills,
            "count": len(transformed_bills),
            "source": "airtable_real_data",
            "message": "EPIC 11 T97 実データ統合完了"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bills: {str(e)}")

@app.get("/api/bills/{bill_id}")
async def get_bill_detail(bill_id: str):
    """Get detailed information about a specific bill."""
    try:
        # Get bill from Airtable
        bill = await airtable.get_bill(bill_id)
        
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        fields = bill.get("fields", {})
        
        # Transform bill data for frontend
        bill_detail = {
            "id": bill.get("id"),
            "fields": {
                "Name": fields.get("Name", ""),
                "Notes": fields.get("Notes", ""),
                "Title": fields.get("Name", ""),
                "Summary": fields.get("Notes", ""),
                "Status": "実データ統合済み",
                "Category": "実データ",
                "Full_Content": fields.get("Notes", ""),
            },
            "metadata": {
                "source": "airtable",
                "last_updated": bill.get("createdTime", ""),
                "record_id": bill.get("id")
            }
        }
        
        return {
            "success": True,
            "data": bill_detail,
            "source": "airtable_real_data",
            "message": "EPIC 11 T98 個別イシューAPI実装"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bill detail: {str(e)}")

@app.get("/api/votes")
async def get_votes(max_records: int = Query(100, le=1000)):
    """Get votes from real Airtable data."""
    try:
        # Get real votes from Airtable
        votes = await airtable.list_votes(max_records=max_records)
        
        return {
            "success": True,
            "data": votes,
            "count": len(votes),
            "source": "airtable_real_data"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch votes: {str(e)}")

@app.post("/search")
async def search_bills(request: Request):
    """Search bills endpoint using real Airtable data."""
    try:
        # Parse request body
        body = await request.json()
        query = body.get('query', '')
        limit = body.get('limit', 10)
        
        if not query.strip():
            return {
                "success": False,
                "message": "検索クエリが必要です",
                "results": [],
                "total_found": 0
            }
        
        # Search in Airtable using structured fields
        search_formula = f"""OR(
            SEARCH('{query}', {{Name}}) > 0,
            SEARCH('{query}', {{Bill_Status}}) > 0,
            SEARCH('{query}', {{Category}}) > 0,
            SEARCH('{query}', {{Submitter}}) > 0,
            SEARCH('{query}', {{Stage}}) > 0,
            SEARCH('{query}', {{Bill_Number}}) > 0
        )"""
        
        # Get matching bills from Airtable
        matching_bills = await airtable.list_bills(
            filter_formula=search_formula,
            max_records=limit * 2
        )

        # Transform results to expected format
        search_results = []
        for i, bill in enumerate(matching_bills[:limit]):
            fields = bill.get("fields", {})
            name = fields.get("Name", "")
            notes = fields.get("Notes", "")

            result = {
                "bill_id": bill.get("id"),
                "title": name[:100] if name else f"法案 {i+1}",
                "summary": notes[:200] + "..." if len(notes) > 200 else notes,
                "status": "実データ",
                "search_method": "airtable_text",
                "relevance_score": 0.8,
                "category": "実データ統合",
                "stage": "データ確認済み",
                "related_issues": [query]
            }
            search_results.append(result)

        return {
            "success": True,
            "results": search_results,
            "total_found": len(matching_bills),
            "query": query,
            "search_method": "airtable_real_data"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"検索に失敗しました: {str(e)}",
            "results": [],
            "total_found": 0
        }

@app.get("/embeddings/stats")
async def get_embedding_stats():
    """Get embedding statistics from real Airtable data."""
    try:
        # Get real data counts from Airtable
        bills = await airtable.list_bills(max_records=1000)
        votes = await airtable.list_votes(max_records=1000)

        bills_count = len(bills)
        votes_count = len(votes)

        return {
            "status": "healthy",
            "bills": bills_count,
            "votes": votes_count,
            "speeches": 0,  # Not implemented yet
            "message": f"EPIC 11 T97 完了 - {bills_count} bills, {votes_count} votes",
            "source": "airtable_real_data"
        }
    except Exception as e:
        return {
            "status": "error",
            "bills": 0,
            "votes": 0,
            "speeches": 0,
            "message": f"Failed to fetch real data: {str(e)}"
        }

@app.get("/api/issues")
async def get_active_issues(
    status: str | None = Query(
        None, description="Filter by status: 'in_view' for active issues"
    ),
    limit: int = Query(12, le=50, description="Limit number of results")
):
    """Get active issues for TOP page horizontal strip (EPIC 12 T101)."""
    try:
        # Get all bills from Airtable
        bills = await airtable.list_bills(max_records=limit * 2)

        # Transform bills to issue format for TOP page strip
        active_issues = []
        for bill in bills[:limit]:
            fields = bill.get("fields", {})
            name = fields.get("Name", "")
            notes = fields.get("Notes", "")

            # Extract category from notes (looking for カテゴリ: label)
            category = "その他"
            if "税制" in notes:
                category = "税制"
            elif "社会保障" in notes:
                category = "社会保障"
            elif "経済・産業" in notes:
                category = "経済・産業"
            elif "外交・国際" in notes:
                category = "外交・国際"
            elif "環境・エネルギー" in notes:
                category = "環境・エネルギー"

            # Extract bill ID from notes
            bill_id = ""
            if "🏛️ 法案ID:" in notes:
                try:
                    bill_id = notes.split("🏛️ 法案ID:")[1].split("\\n")[0].strip()
                except Exception:
                    bill_id = f"bill-{len(active_issues) + 1}"

            # Determine status (simulate deliberating/vote_pending)
            stage = "審議中" if len(active_issues) % 2 == 0 else "採決待ち"

            issue = {
                "id": bill.get("id"),
                "title": name[:80] + "..." if len(name) > 80 else name,
                "summary": notes[:150] + "..." if len(notes) > 150 else notes,
                "category": category,
                "priority": "medium",
                "stage": stage,
                "status": "deliberating" if stage == "審議中" else "vote_pending",
                "bill_number": bill_id,
                "last_updated": "2025-07-11",
                "urgency": "medium" if len(active_issues) % 3 != 0 else "high",
                "metadata": {
                    "source": "airtable_real_data",
                    "record_id": bill.get("id")
                }
            }
            active_issues.append(issue)

        # Filter by status if specified
        if status == "in_view":
            active_issues = [issue for issue in active_issues if issue["status"] in ["deliberating", "vote_pending"]]

        return {
            "success": True,
            "data": active_issues,
            "count": len(active_issues),
            "message": "EPIC 12 T101 - Active Issues API実装完了",
            "source": "airtable_real_data"
        }

    except Exception as e:
        return {
            "success": False,
            "data": [],
            "count": 0,
            "message": f"Failed to fetch active issues: {str(e)}",
            "source": "error"
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting EPIC 11 T97 + EPIC 12 T101 test server on port {port}")
    print(f"📋 API Gateway実データ連携修正 + Active Issues API")
    print(f"🔗 Testing real Airtable integration")
    uvicorn.run(app, host="0.0.0.0", port=port)