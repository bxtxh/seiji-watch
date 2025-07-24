#!/usr/bin/env python3
"""
Debug issue data insertion - test with minimal data
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def debug_issue_insert():
    """Debug minimal issue insertion"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    base_url = f"https://api.airtable.com/v0/{base_id}"

    async with aiohttp.ClientSession() as session:
        # Test 1: Try minimal issue data
        print("🧪 Step 1: Test minimal issue insertion...")

        minimal_data = {
            "fields": {
                "Name": "テストイシュー"
            }
        }

        async with session.post(
            f"{base_url}/Issues (課題)",
            headers=headers,
            json=minimal_data
        ) as response:
            print(f"  Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                record_id = result.get('id')
                print(f"  ✅ SUCCESS: {record_id}")

                # Clean up
                async with session.delete(f"{base_url}/Issues (課題)/{record_id}", headers=headers) as del_response:
                    if del_response.status == 200:
                        print("  🗑️  Cleaned up test record")
            else:
                error_text = await response.text()
                print(f"  ❌ FAILED: {error_text}")

        # Test 2: Try with proper issue fields (excluding original template fields)
        print("\n🧪 Step 2: Test with issue-specific fields...")

        enhanced_data = {
            "fields": {
                "Title": "テストイシュー２",
                "Description": "これはテストイシューの説明です。",
                "Category_L1": "社会保障",
                "Priority": "medium"
            }
        }

        async with session.post(
            f"{base_url}/Issues (課題)",
            headers=headers,
            json=enhanced_data
        ) as response:
            print(f"  Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                record_id = result.get('id')
                print(f"  ✅ SUCCESS: {record_id}")

                # Clean up
                async with session.delete(f"{base_url}/Issues (課題)/{record_id}", headers=headers) as del_response:
                    if del_response.status == 200:
                        print("  🗑️  Cleaned up test record")
            else:
                error_text = await response.text()
                print(f"  ❌ FAILED: {error_text}")

if __name__ == "__main__":
    asyncio.run(debug_issue_insert())
