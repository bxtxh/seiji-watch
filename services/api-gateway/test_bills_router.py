#!/usr/bin/env python3
"""Test Bills router directly without full server."""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'src'))

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Set environment variables
os.environ["AIRTABLE_PAT"] = os.getenv("AIRTABLE_PAT", "")
os.environ["AIRTABLE_BASE_ID"] = os.getenv("AIRTABLE_BASE_ID", "")

# Import the Bills router
from src.routes.bills import router as bills_router

# Create a test FastAPI app
app = FastAPI()
app.include_router(bills_router)

# Create test client
client = TestClient(app)

def test_bills_router():
    """Test the Bills router directly."""
    print("🧪 Testing Bills Router Directly")
    print("=" * 50)
    
    # Test 1: List bills
    print("\n1. Testing GET /api/bills/")
    response = client.get("/api/bills/")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Bills list: {len(data)} bills found")
        if data:
            print(f"   Sample bill: {data[0].get('fields', {}).get('Name', 'Unknown')}")
    else:
        print(f"   ❌ Error: {response.text}")
    
    # Test 2: Search bills
    print("\n2. Testing POST /api/bills/search")
    search_data = {
        "query": "法案",
        "max_records": 5
    }
    response = client.post("/api/bills/search", json=search_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Search results: {data.get('total_found', 0)} found")
        if data.get('results'):
            print(f"   Sample result: {data['results'][0].get('fields', {}).get('Name', 'Unknown')}")
    else:
        print(f"   ❌ Error: {response.text}")
    
    # Test 3: Statistics
    print("\n3. Testing GET /api/bills/statistics/policy-categories")
    response = client.get("/api/bills/statistics/policy-categories")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Statistics: {data.get('total_relationships', 0)} relationships")
    else:
        print(f"   ❌ Error: {response.text}")

if __name__ == "__main__":
    test_bills_router()