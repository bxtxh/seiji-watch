#!/usr/bin/env python3
"""Test Issues table data retrieval."""

import asyncio
import aiohttp

AIRTABLE_PAT = "patzu6qz1qNDVGZqL.7feb60b33535807523001c8ee9d368040fe757652b387f9e333f688583747144"
AIRTABLE_BASE_ID = "appA9UGcgf3NhdnK9"

async def test_issues():
    """Test fetching Issues from Airtable."""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }
    
    print("Testing Issues Table")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Try different table name variations
        table_names = ["Issues", "Issues (課題)", "課題", "issues"]
        
        for table_name in table_names:
            print(f"\nTrying table name: '{table_name}'")
            url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}?maxRecords=5"
            
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        records = data.get('records', [])
                        print(f"✅ Success! Found {len(records)} issues")
                        
                        for i, record in enumerate(records):
                            fields = record.get('fields', {})
                            print(f"\nIssue {i+1}:")
                            print(f"  ID: {record.get('id')}")
                            print(f"  Fields: {list(fields.keys())}")
                            
                            # Print first few fields
                            for key, value in list(fields.items())[:5]:
                                print(f"  {key}: {str(value)[:50]}...")
                        
                        return table_name  # Return successful table name
                    else:
                        print(f"❌ Error {resp.status}: {await resp.text()}")
                        
            except Exception as e:
                print(f"❌ Exception: {e}")
        
        print("\n❌ Could not find Issues table with any name variation")
        return None

if __name__ == "__main__":
    asyncio.run(test_issues())