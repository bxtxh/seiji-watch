#!/usr/bin/env python3
"""
Debug member data insertion - test with minimal data
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def debug_member_insert():
    """Debug minimal member insertion"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    base_url = f"https://api.airtable.com/v0/{base_id}"

    async with aiohttp.ClientSession() as session:
        # Test 1: Get current Members table structure
        print("🔍 Step 1: Get Members table structure...")

        meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        async with session.get(meta_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                for table in data.get("tables", []):
                    if table["name"] == "Members (議員)":
                        print(f"  Table ID: {table['id']}")
                        print(f"  Fields ({len(table['fields'])}):")
                        for field in table["fields"]:
                            print(f"    - {field['name']} ({field['type']})")
                        break

        # Test 2: Try minimal member data
        print("\n🧪 Step 2: Test minimal member insertion...")

        minimal_data = {
            "fields": {
                "Name": "テスト議員"
            }
        }

        async with session.post(
            f"{base_url}/Members (議員)",
            headers=headers,
            json=minimal_data
        ) as response:
            print(f"  Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                record_id = result.get('id')
                print(f"  ✅ SUCCESS: {record_id}")

                # Clean up
                async with session.delete(f"{base_url}/Members (議員)/{record_id}", headers=headers) as del_response:
                    if del_response.status == 200:
                        print("  🗑️  Cleaned up test record")
            else:
                error_text = await response.text()
                print(f"  ❌ FAILED: {error_text}")

        # Test 3: Try with more fields
        print("\n🧪 Step 3: Test with multiple fields...")

        enhanced_data = {
            "fields": {
                "Name": "テスト議員２",
                "House": "参議院",
                "Is_Active": True
            }
        }

        async with session.post(
            f"{base_url}/Members (議員)",
            headers=headers,
            json=enhanced_data
        ) as response:
            print(f"  Status: {response.status}")
            if response.status == 200:
                result = await response.json()
                record_id = result.get('id')
                print(f"  ✅ SUCCESS: {record_id}")

                # Clean up
                async with session.delete(f"{base_url}/Members (議員)/{record_id}", headers=headers) as del_response:
                    if del_response.status == 200:
                        print("  🗑️  Cleaned up test record")
            else:
                error_text = await response.text()
                print(f"  ❌ FAILED: {error_text}")

if __name__ == "__main__":
    asyncio.run(debug_member_insert())
