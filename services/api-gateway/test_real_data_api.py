#!/usr/bin/env python3
"""
Test API server for real Airtable data integration - EPIC 11 T97
"""
import os
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent / "shared" / "src"
sys.path.insert(0, str(shared_path))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

# Import our Airtable client
from shared.clients.airtable import AirtableClient

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

# Initialize Airtable client
airtable_client = AirtableClient()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Diet Issue Tracker API - Real Data Integration Test",
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
        # Test Airtable connection
        airtable_health = await airtable_client.health_check()

        return {
            "status": "healthy" if airtable_health else "degraded",
            "airtable": airtable_health,
            "message": "Real data integration active"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Airtable connection failed"
        }

@app.get("/api/bills")
async def get_bills(max_records: int = Query(100, le=1000), category: str | None = None):
    """Get bills from real Airtable data."""
    try:
        # Build filter for category if specified
        filter_formula = None
        if category:
            filter_formula = f"SEARCH('{category}', {{Notes}}) > 0"

        # Get real bills from Airtable
        bills = await airtable_client.list_bills(
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
            "source": "airtable_real_data"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bills: {str(e)}")

@app.get("/api/bills/{bill_id}")
async def get_bill_detail(bill_id: str):
    """Get detailed information about a specific bill."""
    try:
        # Get bill from Airtable
        bill = await airtable_client.get_bill(bill_id)

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
            "source": "airtable_real_data"
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
        votes = await airtable_client.list_votes(max_records=max_records)

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
        matching_bills = await airtable_client.list_bills(
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
        bills = await airtable_client.list_bills(max_records=1000)
        votes = await airtable_client.list_votes(max_records=1000)

        bills_count = len(bills)
        votes_count = len(votes)

        return {
            "status": "healthy",
            "bills": bills_count,
            "votes": votes_count,
            "speeches": 0,  # Not implemented yet
            "message": f"Real data integration complete - {bills_count} bills, {votes_count} votes",
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting real data API server on port {port}")
    print("📋 Testing EPIC 11 T97: API Gateway実データ連携修正")
    uvicorn.run(app, host="0.0.0.0", port=port)
