#!/usr/bin/env python3
"""
Simple API Gateway server focused on Issue Categories functionality for testing.
This bypasses complex shared dependencies and directly implements the category APIs.
"""

import os
import sys
import json
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Mock Airtable client for category data
class MockAirtableClient:
    """Mock Airtable client with sample category data."""
    
    def __init__(self):
        self.categories = self._load_mock_categories()
    
    def _load_mock_categories(self) -> List[Dict[str, Any]]:
        """Load mock category data based on CAP classification."""
        return [
            {
                "id": "cat_001",
                "fields": {
                    "CAP_Code": "1",
                    "Layer": "L1", 
                    "Title_JA": "社会保障・医療",
                    "Title_EN": "Social Welfare & Healthcare",
                    "Description": "社会保障制度、医療制度、年金制度に関する政策分野",
                    "Is_Seed": True
                }
            },
            {
                "id": "cat_002", 
                "fields": {
                    "CAP_Code": "2",
                    "Layer": "L1",
                    "Title_JA": "経済・産業政策",
                    "Title_EN": "Economic & Industrial Policy", 
                    "Description": "経済政策、産業振興、規制緩和に関する政策分野",
                    "Is_Seed": True
                }
            },
            {
                "id": "cat_003",
                "fields": {
                    "CAP_Code": "3", 
                    "Layer": "L1",
                    "Title_JA": "外交・国際関係",
                    "Title_EN": "Foreign Affairs & International Relations",
                    "Description": "外交政策、国際協力、通商政策に関する政策分野", 
                    "Is_Seed": True
                }
            },
            {
                "id": "cat_101",
                "fields": {
                    "CAP_Code": "1.1",
                    "Layer": "L2",
                    "Title_JA": "健康保険制度改革", 
                    "Title_EN": "Health Insurance Reform",
                    "Parent_Category": ["cat_001"],
                    "Description": "健康保険制度の改革に関する具体的な政策項目",
                    "Is_Seed": True
                }
            },
            {
                "id": "cat_102",
                "fields": {
                    "CAP_Code": "1.2",
                    "Layer": "L2", 
                    "Title_JA": "高齢者介護サービス",
                    "Title_EN": "Elderly Care Services",
                    "Parent_Category": ["cat_001"],
                    "Description": "高齢者介護サービスの拡充に関する政策項目",
                    "Is_Seed": True
                }
            },
            {
                "id": "cat_201",
                "fields": {
                    "CAP_Code": "2.1", 
                    "Layer": "L2",
                    "Title_JA": "中小企業支援",
                    "Title_EN": "SME Support",
                    "Parent_Category": ["cat_002"],
                    "Description": "中小企業の経営支援、融資制度に関する政策項目",
                    "Is_Seed": True
                }
            },
            {
                "id": "cat_301",
                "fields": {
                    "CAP_Code": "3.1",
                    "Layer": "L2",
                    "Title_JA": "アジア太平洋戦略",
                    "Title_EN": "Asia-Pacific Strategy", 
                    "Parent_Category": ["cat_003"],
                    "Description": "アジア太平洋地域における外交戦略",
                    "Is_Seed": True
                }
            }
        ]
    
    async def get_issue_categories(self, max_records: int = 100) -> Dict[str, Any]:
        """Get all issue categories."""
        filtered_categories = self.categories[:max_records]
        return {
            "records": filtered_categories,
            "offset": None
        }
    
    async def get_category_tree(self) -> Dict[str, Any]:
        """Get category tree structure."""
        # Build tree structure
        l1_categories = []
        
        for cat in self.categories:
            if cat["fields"]["Layer"] == "L1":
                # Find children
                children = [
                    child for child in self.categories 
                    if (child["fields"]["Layer"] == "L2" and 
                        "Parent_Category" in child["fields"] and
                        cat["id"] in child["fields"]["Parent_Category"])
                ]
                
                l1_cat = {
                    "id": cat["id"],
                    "title_ja": cat["fields"]["Title_JA"],
                    "title_en": cat["fields"].get("Title_EN"),
                    "cap_code": cat["fields"]["CAP_Code"],
                    "description": cat["fields"].get("Description"),
                    "children": [
                        {
                            "id": child["id"],
                            "title_ja": child["fields"]["Title_JA"], 
                            "title_en": child["fields"].get("Title_EN"),
                            "cap_code": child["fields"]["CAP_Code"],
                            "description": child["fields"].get("Description")
                        }
                        for child in children
                    ]
                }
                l1_categories.append(l1_cat)
        
        return {
            "tree": l1_categories,
            "total_l1": len([c for c in self.categories if c["fields"]["Layer"] == "L1"]),
            "total_l2": len([c for c in self.categories if c["fields"]["Layer"] == "L2"])
        }
    
    async def get_issue_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get specific category details."""
        for cat in self.categories:
            if cat["id"] == category_id:
                return cat
        return None
    
    async def get_category_children(self, category_id: str) -> Dict[str, Any]:
        """Get child categories."""
        children = [
            cat for cat in self.categories
            if (cat["fields"]["Layer"] == "L2" and 
                "Parent_Category" in cat["fields"] and
                category_id in cat["fields"]["Parent_Category"])
        ]
        
        return {
            "records": children,
            "parent_id": category_id
        }
    
    async def search_categories(self, query: str, max_records: int = 50) -> Dict[str, Any]:
        """Search categories by title."""
        matching_categories = []
        
        for cat in self.categories:
            title_ja = cat["fields"]["Title_JA"].lower()
            title_en = cat["fields"].get("Title_EN", "").lower()
            
            if (query.lower() in title_ja or 
                query.lower() in title_en):
                matching_categories.append(cat)
                
                if len(matching_categories) >= max_records:
                    break
        
        return {
            "records": matching_categories,
            "query": query,
            "total_matches": len(matching_categories)
        }

# Create FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API - Category Test Server",
    description="Simple API Gateway for testing Issue Category functionality", 
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "accept", "accept-language", "authorization",
        "content-language", "content-type", "x-requested-with",
        "x-csrf-token", "x-request-id"
    ],
    expose_headers=["X-Total-Count"],
    max_age=600
)

# Initialize mock client
airtable_client = MockAirtableClient()

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "api-gateway-category-test",
        "version": "1.0.0",
        "categories_loaded": len(airtable_client.categories)
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Diet Issue Tracker API Gateway - Category Test Server",
        "docs": "/docs",
        "health": "/health",
        "features": ["issue_categories", "category_tree", "category_search"]
    }

# Issue Category API endpoints
@app.get("/api/issues/categories")
async def get_categories(max_records: int = 100):
    """Get all issue categories."""
    try:
        categories = await airtable_client.get_issue_categories(max_records=max_records)
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

@app.get("/api/issues/categories/tree")
async def get_category_tree():
    """Get category tree structure."""
    try:
        tree = await airtable_client.get_category_tree()
        return tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category tree: {str(e)}")

@app.get("/api/issues/categories/{category_id}")
async def get_category_detail(category_id: str):
    """Get specific category details."""
    try:
        category = await airtable_client.get_issue_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category: {str(e)}")

@app.get("/api/issues/categories/{category_id}/children")
async def get_category_children(category_id: str):
    """Get child categories."""
    try:
        children = await airtable_client.get_category_children(category_id)
        return children
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch category children: {str(e)}")

@app.get("/api/issues/categories/search")
async def search_categories(query: str, max_records: int = 50):
    """Search categories by title."""
    try:
        results = await airtable_client.search_categories(query, max_records=max_records)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search categories: {str(e)}")

# Mock bills endpoint for category testing
@app.get("/api/bills")
async def get_bills(max_records: int = 100, category: Optional[str] = None):
    """Get bills, optionally filtered by category."""
    try:
        # Mock bills data that matches our categories
        mock_bills = [
            {
                "id": f"bill_00{i}",
                "fields": {
                    "Bill_Number": f"第213回国会第{i}号",
                    "Title": f"サンプル法案{i} - 社会保障制度改革",
                    "Summary": f"これは法案{i}の要約です。社会保障制度の重要な改革に関する内容が含まれています。",
                    "Status": "審議中" if i % 3 == 0 else "成立" if i % 3 == 1 else "否決",
                    "Category": "社会保障・医療",
                    "Category_ID": "cat_001",
                    "Diet_Session": f"第213回国会",
                    "Submitted_Date": "2024-01-15"
                }
            }
            for i in range(1, 6)
        ] + [
            {
                "id": f"bill_01{i}",
                "fields": {
                    "Bill_Number": f"第213回国会第{i+5}号",
                    "Title": f"経済政策法案{i} - 中小企業支援",
                    "Summary": f"これは経済政策法案{i}の要約です。中小企業支援に関する重要な内容が含まれています。",
                    "Status": "審議中" if i % 2 == 0 else "成立",
                    "Category": "経済・産業政策", 
                    "Category_ID": "cat_002",
                    "Diet_Session": f"第213回国会",
                    "Submitted_Date": "2024-02-01"
                }
            }
            for i in range(1, 4)
        ]
        
        # Filter by category if specified
        if category:
            mock_bills = [
                bill for bill in mock_bills 
                if category in bill["fields"].get("Category", "") or 
                   category == bill["fields"].get("Category_ID", "")
            ]
        
        # Limit results
        mock_bills = mock_bills[:max_records]
        
        return mock_bills
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bills: {str(e)}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Category Test API Gateway on port {port}")
    print("Available endpoints:")
    print("- GET /health")
    print("- GET /api/issues/categories") 
    print("- GET /api/issues/categories/tree")
    print("- GET /api/issues/categories/{id}")
    print("- GET /api/issues/categories/{id}/children")
    print("- GET /api/issues/categories/search?query=...")
    print("- GET /api/bills?category=...")
    
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)