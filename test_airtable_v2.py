#!/usr/bin/env python3
"""Test Airtable connection with proper credentials."""

import os
import asyncio
import aiohttp

# Directly set the credentials from the .env file
AIRTABLE_PAT = "patzu6qz1qNDVGZqL.7feb60b33535807523001c8ee9d368040fe757652b387f9e333f688583747144"
AIRTABLE_BASE_ID = "appA9UGcgf3NhdnK9"

async def test_airtable_direct():
    """Test Airtable API directly."""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }
    
    print("Testing Airtable Connection")
    print("=" * 50)
    print(f"Base ID: {AIRTABLE_BASE_ID}")
    print(f"PAT: {AIRTABLE_PAT[:20]}...")
    print()
    
    async with aiohttp.ClientSession() as session:
        # Test 1: List tables
        print("1. Getting Base Schema...")
        try:
            url = f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tables = data.get('tables', [])
                    print(f"   ✅ Found {len(tables)} tables:")
                    for table in tables[:5]:
                        print(f"      - {table['name']} (ID: {table['id']})")
                else:
                    print(f"   ❌ Error: {resp.status} - {await resp.text()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Try to fetch from Bills table
        print("\n2. Fetching Bills...")
        try:
            # Try different table name variations
            table_names = ["Bills", "Bills (法案)", "法案", "bills"]
            success = False
            
            for table_name in table_names:
                url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}?maxRecords=3"
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        records = data.get('records', [])
                        print(f"   ✅ Found {len(records)} bills in table '{table_name}'")
                        for record in records:
                            fields = record.get('fields', {})
                            name = fields.get('Name', fields.get('名前', fields.get('title', 'No name')))
                            print(f"      - {name[:50]}...")
                        success = True
                        break
            
            if not success:
                print(f"   ❌ Could not find Bills table")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_airtable_direct())