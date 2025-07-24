#!/usr/bin/env python3
"""Test script for Bills-PolicyCategory API endpoints."""

import asyncio
import json
import os

import aiohttp

# Test configuration
API_BASE_URL = "http://localhost:8000"
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_endpoint(self, method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
        """Test an API endpoint and return the response."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        print(f"\n🔍 Testing {method} {endpoint}")
        if params:
            print(f"   Params: {params}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")

        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            ) as response:
                status = response.status
                content = await response.json()

                if 200 <= status < 300:
                    print(f"✅ {status}: Success")
                    return {"success": True, "status": status, "data": content}
                else:
                    print(f"❌ {status}: Error")
                    print(f"   Response: {json.dumps(content, indent=2)}")
                    return {"success": False, "status": status, "data": content}

        except Exception as e:
            print(f"❌ Request failed: {e}")
            return {"success": False, "error": str(e)}

async def test_bills_api():
    """Test the Bills API endpoints."""

    async with APITester(API_BASE_URL) as tester:
        print("🚀 Testing Bills-PolicyCategory API Endpoints")
        print("=" * 60)

        # Test 1: List all bills
        print("\n📋 Test 1: List all bills")
        result = await tester.test_endpoint("GET", "/api/bills/")
        if result["success"]:
            bills = result["data"]
            print(f"   Found {len(bills)} bills")
            if bills:
                sample_bill = bills[0]
                bill_id = sample_bill.get("id", "")
                print(f"   Sample bill ID: {bill_id}")
            else:
                print("   No bills found - may need to add test data")
                return
        else:
            print("   ❌ Failed to list bills")
            return

        # Test 2: Get specific bill
        print("\n🔍 Test 2: Get specific bill")
        if bill_id:
            result = await tester.test_endpoint("GET", f"/api/bills/{bill_id}")
            if result["success"]:
                bill = result["data"]
                print(f"   Retrieved bill: {bill.get('fields', {}).get('Name', 'Unknown')}")
            else:
                print(f"   ❌ Failed to get bill {bill_id}")

        # Test 3: Get bill with policy categories
        print("\n🔗 Test 3: Get bill with policy categories")
        if bill_id:
            result = await tester.test_endpoint("GET", f"/api/bills/{bill_id}", params={"include_policy_categories": True})
            if result["success"]:
                bill = result["data"]
                policy_categories = bill.get("policy_categories", [])
                print(f"   Bill has {len(policy_categories)} policy category relationships")
                for i, rel in enumerate(policy_categories[:3]):  # Show first 3
                    category_name = rel.get("category", {}).get("fields", {}).get("Title_JA", "Unknown")
                    confidence = rel.get("confidence_score", 0.0)
                    print(f"   {i+1}. {category_name} (confidence: {confidence})")
            else:
                print("   ❌ Failed to get bill with policy categories")

        # Test 4: Search bills
        print("\n🔍 Test 4: Search bills")
        search_data = {
            "query": "予算",
            "max_records": 5
        }
        result = await tester.test_endpoint("POST", "/api/bills/search", data=search_data)
        if result["success"]:
            search_result = result["data"]
            bills = search_result.get("results", [])
            print(f"   Found {len(bills)} bills matching '予算'")
            print(f"   Total found: {search_result.get('total_found', 0)}")
        else:
            print("   ❌ Failed to search bills")

        # Test 5: List issue categories (for creating relationships)
        print("\n📂 Test 5: List issue categories")
        result = await tester.test_endpoint("GET", "/api/issues/categories", params={"max_records": 10})
        if result["success"]:
            categories = result["data"]
            print(f"   Found {len(categories)} issue categories")
            if categories:
                sample_category = categories[0]
                category_id = sample_category.get("id", "")
                category_name = sample_category.get("fields", {}).get("Title_JA", "Unknown")
                print(f"   Sample category: {category_name} (ID: {category_id})")

                # Test 6: Create Bills-PolicyCategory relationship
                print("\n🔗 Test 6: Create Bills-PolicyCategory relationship")
                if bill_id and category_id:
                    relationship_data = {
                        "bill_id": bill_id,
                        "policy_category_id": category_id,
                        "confidence_score": 0.9,
                        "is_manual": True,
                        "notes": "Test relationship created by API test script"
                    }
                    result = await tester.test_endpoint("POST", f"/api/bills/{bill_id}/policy-categories", data=relationship_data)
                    if result["success"]:
                        relationship = result["data"]["relationship"]
                        relationship_id = relationship.get("id", "")
                        print(f"   Created relationship: {relationship_id}")

                        # Test 7: Get bill policy categories
                        print("\n📋 Test 7: Get bill policy categories")
                        result = await tester.test_endpoint("GET", f"/api/bills/{bill_id}/policy-categories")
                        if result["success"]:
                            policy_data = result["data"]
                            policy_categories = policy_data.get("policy_categories", [])
                            print(f"   Bill has {len(policy_categories)} policy category relationships")

                            # Test 8: Update relationship (if we have one)
                            if relationship_id:
                                print("\n📝 Test 8: Update Bills-PolicyCategory relationship")
                                update_data = {
                                    "bill_id": bill_id,
                                    "policy_category_id": category_id,
                                    "confidence_score": 0.95,
                                    "is_manual": True,
                                    "notes": "Updated test relationship"
                                }
                                result = await tester.test_endpoint("PUT", f"/api/bills/{bill_id}/policy-categories/{relationship_id}", data=update_data)
                                if result["success"]:
                                    print("   ✅ Relationship updated successfully")
                                else:
                                    print("   ❌ Failed to update relationship")

                            # Test 9: Delete relationship (cleanup)
                            if relationship_id:
                                print("\n🗑️  Test 9: Delete Bills-PolicyCategory relationship")
                                result = await tester.test_endpoint("DELETE", f"/api/bills/{bill_id}/policy-categories/{relationship_id}")
                                if result["success"]:
                                    print("   ✅ Relationship deleted successfully")
                                else:
                                    print("   ❌ Failed to delete relationship")
                        else:
                            print("   ❌ Failed to get bill policy categories")
                    else:
                        print("   ❌ Failed to create relationship")
                else:
                    print("   ⚠️  Skipping relationship tests - missing bill_id or category_id")
            else:
                print("   No categories found - may need to add test data")
        else:
            print("   ❌ Failed to list issue categories")

        # Test 10: Get statistics
        print("\n📊 Test 10: Get Bills-PolicyCategory statistics")
        result = await tester.test_endpoint("GET", "/api/bills/statistics/policy-categories")
        if result["success"]:
            stats = result["data"]
            print(f"   Total relationships: {stats.get('total_relationships', 0)}")
            print(f"   Confidence distribution: {stats.get('confidence_distribution', {})}")
            print(f"   Manual vs Automatic: {stats.get('manual_vs_automatic', {})}")
        else:
            print("   ❌ Failed to get statistics")

        print("\n✅ API Testing Complete!")

async def main():
    """Main test execution."""

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables are required")
        return 1

    print("🧪 Bills-PolicyCategory API Test Suite")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Base ID: {AIRTABLE_BASE_ID}")
    print("=" * 60)

    # Make sure the API server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    print("✅ API server is running")
                else:
                    print(f"❌ API server health check failed: {response.status}")
                    return 1
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("   Make sure the API server is running with: python -m uvicorn src.main:app --reload")
        return 1

    # Run the tests
    try:
        await test_bills_api()
        return 0
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
