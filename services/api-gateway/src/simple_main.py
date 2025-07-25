"""Simplified FastAPI application for Diet Issue Tracker API Gateway - MVP Demo."""

import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API",
    description="API Gateway for Diet Issue Tracker MVP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "accept",
        "accept-language",
        "authorization",
        "content-language",
        "content-type",
        "x-requested-with",
        "x-csrf-token",
        "x-request-id",
    ],
    expose_headers=["X-Total-Count"],
    max_age=600,
)

# Root endpoint


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Diet Issue Tracker API Gateway - MVP Demo",
        "docs": "/docs",
        "health": "/health",
    }


# Health check endpoint


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
        "timestamp": time.time(),
    }


# Mock Issue Category API endpoints


@app.get("/api/issues/categories")
async def get_categories(max_records: int = 100):
    """Get all issue categories (mock data)."""
    try:
        # Mock data based on CAP classification
        mock_categories = [
            {
                "id": "rec_l1_macroeconomics",
                "fields": {
                    "CAP_Code": "1",
                    "Layer": "L1",
                    "Title_JA": "マクロ経済学",
                    "Title_EN": "Macroeconomics",
                    "Summary_150JA": "経済全体の動向、財政政策、金融政策、経済成長に関する政策分野",
                    "Is_Seed": True,
                },
            },
            {
                "id": "rec_l1_civil_rights",
                "fields": {
                    "CAP_Code": "2",
                    "Layer": "L1",
                    "Title_JA": "市民権・自由・少数者問題",
                    "Title_EN": "Civil Rights, Minority Issues and Civil Liberties",
                    "Summary_150JA": "基本的人権、差別問題、個人の自由、少数者の権利保護に関する政策分野",
                    "Is_Seed": True,
                },
            },
            {
                "id": "rec_l1_health",
                "fields": {
                    "CAP_Code": "3",
                    "Layer": "L1",
                    "Title_JA": "健康",
                    "Title_EN": "Health",
                    "Summary_150JA": "医療制度、公衆衛生、健康保険、医療研究に関する政策分野",
                    "Is_Seed": True,
                },
            },
        ]
        return mock_categories[:max_records]
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


@app.get("/api/issues/categories/tree")
async def get_category_tree():
    """Get category tree structure (mock data)."""
    try:
        return {
            "L1": [
                {
                    "id": "rec_l1_macroeconomics",
                    "fields": {
                        "CAP_Code": "1",
                        "Layer": "L1",
                        "Title_JA": "マクロ経済学",
                        "Title_EN": "Macroeconomics",
                        "Is_Seed": True,
                    },
                },
                {
                    "id": "rec_l1_civil_rights",
                    "fields": {
                        "CAP_Code": "2",
                        "Layer": "L1",
                        "Title_JA": "市民権・自由・少数者問題",
                        "Title_EN": "Civil Rights, Minority Issues and Civil Liberties",
                        "Is_Seed": True,
                    },
                },
                {
                    "id": "rec_l1_health",
                    "fields": {
                        "CAP_Code": "3",
                        "Layer": "L1",
                        "Title_JA": "健康",
                        "Title_EN": "Health",
                        "Is_Seed": True,
                    },
                },
            ],
            "L2": [
                {
                    "id": "rec_l2_general_domestic_macro",
                    "fields": {
                        "CAP_Code": "105",
                        "Layer": "L2",
                        "Title_JA": "国内マクロ経済問題",
                        "Title_EN": "General Domestic Macroeconomic Issues",
                        "Parent_Category": ["rec_l1_macroeconomics"],
                        "Is_Seed": True,
                    },
                },
                {
                    "id": "rec_l2_general_civil_rights",
                    "fields": {
                        "CAP_Code": "200",
                        "Layer": "L2",
                        "Title_JA": "一般的市民権・自由",
                        "Title_EN": "General Civil Rights and Liberties",
                        "Parent_Category": ["rec_l1_civil_rights"],
                        "Is_Seed": True,
                    },
                },
            ],
            "L3": [],
        }
    except Exception as e:
        logger.error(f"Failed to get category tree: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category tree")


@app.get("/api/issues/categories/{category_id}")
async def get_category_detail(category_id: str):
    """Get specific category details (mock data)."""
    try:
        # Mock data for specific category
        mock_category = {
            "id": category_id,
            "fields": {
                "CAP_Code": "1",
                "Layer": "L1",
                "Title_JA": "マクロ経済学",
                "Title_EN": "Macroeconomics",
                "Summary_150JA": "経済全体の動向、財政政策、金融政策、経済成長に関する政策分野です。GDP、インフレ、雇用率などの主要経済指標と関連する政策を含みます。",
                "Is_Seed": True,
            },
        }
        return mock_category
    except Exception as e:
        logger.error(f"Failed to get category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category")


@app.get("/api/issues/categories/{category_id}/children")
async def get_category_children(category_id: str):
    """Get child categories (mock data)."""
    try:
        # Mock child categories
        mock_children = [
            {
                "id": "rec_l2_general_domestic_macro",
                "fields": {
                    "CAP_Code": "105",
                    "Layer": "L2",
                    "Title_JA": "国内マクロ経済問題",
                    "Title_EN": "General Domestic Macroeconomic Issues",
                    "Parent_Category": [category_id],
                    "Is_Seed": True,
                },
            },
            {
                "id": "rec_l2_inflation_prices",
                "fields": {
                    "CAP_Code": "106",
                    "Layer": "L2",
                    "Title_JA": "インフレ・物価・デフレ",
                    "Title_EN": "Inflation, Prices, and Deflation",
                    "Parent_Category": [category_id],
                    "Is_Seed": True,
                },
            },
        ]
        return mock_children
    except Exception as e:
        logger.error(f"Failed to get children for category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch category children")


@app.get("/api/bills")
async def get_bills(max_records: int = 100, category: str | None = None):
    """Get bills, optionally filtered by category (mock data)."""
    try:
        # Mock bills data
        mock_bills = [
            {
                "id": f"bill_00{i}",
                "fields": {
                    "Bill_Number": f"第213回国会第{i}号",
                    "Title": f"経済政策関連法案{i}",
                    "Summary": f"これは法案{i}の要約です。マクロ経済学に関する重要な政策が含まれています。",
                    "Status": (
                        "審議中" if i % 3 == 0 else "成立" if i % 3 == 1 else "否決"
                    ),
                    "Category": "マクロ経済学",
                    "Diet_Session": "第213回国会",
                    "Submitted_Date": "2024-01-15",
                },
            }
            for i in range(1, min(max_records + 1, 11))
        ]

        # Filter by category if specified
        if category:
            mock_bills = [
                bill
                for bill in mock_bills
                if category in bill["fields"].get("Category", "")
            ]

        return mock_bills
    except Exception as e:
        logger.error(f"Failed to get bills: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bills")


# Global exception handler


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8081))  # Use 8081 to avoid conflicts
    # Bind to all interfaces (covers both IPv4 and IPv6)
    uvicorn.run(app, host="::", port=port)
