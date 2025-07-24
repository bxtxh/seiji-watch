#!/usr/bin/env python3
"""
Debug speech data insertion - test with minimal data
"""

import asyncio
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')


async def debug_speech_insert():
    """Debug minimal speech insertion"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    base_url = f"https://api.airtable.com/v0/{base_id}"

    async with aiohttp.ClientSession() as session:
        # Test 1: Get current Speeches table structure
        print("🔍 Step 1: Get Speeches table structure...")

        meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        async with session.get(meta_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                for table in data.get("tables", []):
                    if table["name"] == "Speeches (発言)":
                        print(f"  Table ID: {table['id']}")
                        print(f"  Fields ({len(table['fields'])}):")
                        for field in table["fields"]:
                            print(f"    - {field['name']} ({field['type']})")
                        break

        # Test 2: Try minimal speech data
        print("\n🧪 Step 2: Test minimal speech insertion...")

        minimal_data = {
            "fields": {
                "Name": "テスト発言"
            }
        }

        async with session.post(
            f"{base_url}/Speeches (発言)",
            headers=headers,
            json=minimal_data
        ) as response:
            print(f"  Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                record_id = result.get('id')
                print(f"  ✅ SUCCESS: {record_id}")

                # Clean up
                async with session.delete(f"{base_url}/Speeches (発言)/{record_id}", headers=headers) as del_response:
                    if del_response.status == 200:
                        print("  🗑️  Cleaned up test record")
            else:
                error_text = await response.text()
                print(f"  ❌ FAILED: {error_text}")

        # Test 3: Try with more fields that should exist
        print("\n🧪 Step 3: Test with multiple safe fields...")

        enhanced_data = {
            "fields": {
                "Name": "テスト発言２",
                "Content": "これはテスト発言です。",
                "Created_At": datetime.now().isoformat()
            }
        }

        async with session.post(
            f"{base_url}/Speeches (発言)",
            headers=headers,
            json=enhanced_data
        ) as response:
            print(f"  Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                record_id = result.get('id')
                print(f"  ✅ SUCCESS: {record_id}")

                # Clean up
                async with session.delete(f"{base_url}/Speeches (発言)/{record_id}", headers=headers) as del_response:
                    if del_response.status == 200:
                        print("  🗑️  Cleaned up test record")
            else:
                error_text = await response.text()
                print(f"  ❌ FAILED: {error_text}")

if __name__ == "__main__":
    asyncio.run(debug_speech_insert())
