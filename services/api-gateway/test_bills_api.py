#!/usr/bin/env python3
"""Test script for Bills API endpoints."""

import asyncio
import os

import aiohttp

# Set environment variables
os.environ["AIRTABLE_PAT"] = os.getenv("AIRTABLE_PAT", "")
os.environ["AIRTABLE_BASE_ID"] = os.getenv("AIRTABLE_BASE_ID", "")

API_BASE_URL = "http://localhost:8000"


async def test_bills_endpoints():
    """Test all Bills API endpoints."""

    print("🧪 Testing Bills API Endpoints")
    print("=" * 50)

    # Test data

    async with aiohttp.ClientSession() as session:
        # Test 1: List bills
        print("\n1. Testing GET /api/bills/")
        try:
            async with session.get(f"{API_BASE_URL}/api/bills/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Bills list: {len(data)} bills found")
                    if data:
                        print(
                            f"   Sample bill: {data[0].get('fields', {}).get('Name', 'Unknown')}"
                        )
                else:
                    print(f"❌ Bills list failed: {response.status}")
        except Exception as e:
            print(f"❌ Bills list error: {e}")

        # Test 2: List bills with filters
        print("\n2. Testing GET /api/bills/?status=進行中")
        try:
            async with session.get(
                f"{API_BASE_URL}/api/bills/?status=進行中"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Filtered bills: {len(data)} bills found")
                else:
                    print(f"❌ Filtered bills failed: {response.status}")
        except Exception as e:
            print(f"❌ Filtered bills error: {e}")

        # Test 3: Get specific bill (need to get a real bill ID first)
        print("\n3. Testing GET /api/bills/{bill_id}")
        try:
            # Get a real bill ID first
            async with session.get(
                f"{API_BASE_URL}/api/bills/?max_records=1"
            ) as response:
                if response.status == 200:
                    bills = await response.json()
                    if bills:
                        real_bill_id = bills[0].get("id")
                        print(f"   Using real bill ID: {real_bill_id}")

                        # Test getting the specific bill
                        async with session.get(
                            f"{API_BASE_URL}/api/bills/{real_bill_id}"
                        ) as bill_response:
                            if bill_response.status == 200:
                                bill_data = await bill_response.json()
                                print(
                                    f"✅ Bill details: {bill_data.get('fields', {}).get('Name', 'Unknown')}"
                                )
                            else:
                                print(f"❌ Bill details failed: {bill_response.status}")
                    else:
                        print("⚠️  No bills found to test with")
                else:
                    print(f"❌ Could not get bill for testing: {response.status}")
        except Exception as e:
            print(f"❌ Bill details error: {e}")

        # Test 4: Search bills
        print("\n4. Testing POST /api/bills/search")
        try:
            search_data = {"query": "法案", "max_records": 5}
            async with session.post(
                f"{API_BASE_URL}/api/bills/search", json=search_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Bill search: {data.get('total_found', 0)} results found")
                    if data.get("results"):
                        print(
                            f"   Sample result: {data['results'][0].get('fields', {}).get('Name', 'Unknown')}"
                        )
                else:
                    print(f"❌ Bill search failed: {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"❌ Bill search error: {e}")

        # Test 5: Test PolicyCategory relationship endpoints (need real IDs)
        print("\n5. Testing Bills-PolicyCategory relationship endpoints")
        try:
            # Get real bill and policy category IDs
            async with session.get(
                f"{API_BASE_URL}/api/bills/?max_records=1"
            ) as bills_response:
                if bills_response.status == 200:
                    bills = await bills_response.json()
                    if bills:
                        real_bill_id = bills[0].get("id")
                        print(f"   Using real bill ID: {real_bill_id}")

                        # Test getting policy categories for this bill
                        async with session.get(
                            f"{API_BASE_URL}/api/bills/{real_bill_id}/policy-categories"
                        ) as rel_response:
                            if rel_response.status == 200:
                                rel_data = await rel_response.json()
                                print(
                                    f"✅ Bill policy categories: {rel_data.get('total_count', 0)} relationships found"
                                )
                            else:
                                print(
                                    f"❌ Bill policy categories failed: {rel_response.status}"
                                )
                                print(f"   Response: {await rel_response.text()}")
                    else:
                        print("⚠️  No bills found to test relationships with")
                else:
                    print(
                        f"❌ Could not get bills for relationship testing: {bills_response.status}"
                    )
        except Exception as e:
            print(f"❌ Bills-PolicyCategory relationship error: {e}")

        # Test 6: Statistics endpoint
        print("\n6. Testing GET /api/bills/statistics/policy-categories")
        try:
            async with session.get(
                f"{API_BASE_URL}/api/bills/statistics/policy-categories"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"✅ Statistics: {data.get('total_relationships', 0)} total relationships"
                    )
                    print(
                        f"   High confidence: {data.get('confidence_distribution', {}).get('high_confidence', 0)}"
                    )
                    print(
                        f"   Manual entries: {data.get('manual_vs_automatic', {}).get('manual', 0)}"
                    )
                else:
                    print(f"❌ Statistics failed: {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"❌ Statistics error: {e}")

        # Test 7: Test issues endpoints (existing)
        print("\n7. Testing GET /api/issues/categories")
        try:
            async with session.get(f"{API_BASE_URL}/api/issues/categories") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Issue categories: {len(data)} categories found")
                    if data:
                        print(
                            f"   Sample category: {data[0].get('fields', {}).get('Title_JA', 'Unknown')}"
                        )
                else:
                    print(f"❌ Issue categories failed: {response.status}")
        except Exception as e:
            print(f"❌ Issue categories error: {e}")


async def test_server_connection():
    """Test if API server is running."""
    print("🔍 Testing API Server Connection")
    print("=" * 50)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API server running: {data.get('message', 'Unknown')}")
                    return True
                else:
                    print(f"❌ API server not responding: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ API server connection error: {e}")
        return False


async def test_airtable_connection():
    """Test direct Airtable connection."""
    print("\n🔍 Testing Direct Airtable Connection")
    print("=" * 50)

    AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables required")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {AIRTABLE_PAT}",
                "Content-Type": "application/json",
            }

            # Test Bills table
            url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Bills%20%28%E6%B3%95%E6%A1%88%29?maxRecords=1"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"✅ Bills table: {len(data.get('records', []))} records accessible"
                    )
                else:
                    print(f"❌ Bills table failed: {response.status}")
                    return False

            # Test IssueCategories table (use table ID for reliable access)
            url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/tbl6wK8L9K5ny1dDm?maxRecords=1"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"✅ IssueCategories table: {len(data.get('records', []))} records accessible"
                    )
                else:
                    print(f"❌ IssueCategories table failed: {response.status}")
                    return False

            return True

    except Exception as e:
        print(f"❌ Airtable connection error: {e}")
        return False


async def main():
    """Main test execution."""
    print("🚀 Bills API Testing Suite")
    print("=" * 70)

    # Test 1: Airtable connection
    if not await test_airtable_connection():
        print("\n❌ Cannot proceed without Airtable connection")
        return 1

    # Test 2: API server connection
    if not await test_server_connection():
        print("\n❌ Cannot proceed without API server")
        print("💡 Start the API server with: python -m uvicorn src.main:app --reload")
        return 1

    # Test 3: Bills API endpoints
    await test_bills_endpoints()

    print("\n✅ Bills API testing complete!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
