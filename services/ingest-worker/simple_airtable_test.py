#!/usr/bin/env python3
"""
Simple Airtable connection test using direct HTTP requests
"""

import aiohttp
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def test_airtable_direct():
    """Test Airtable connection directly"""
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    if not api_key or not base_id:
        print("❌ Airtable credentials not found in environment")
        return False
        
    print(f"🔑 API Key: {api_key[:10]}...")
    print(f"📁 Base ID: {base_id}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test base schema endpoint to see available tables
            print("\n🔍 Testing base schema...")
            schema_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
            async with session.get(schema_url, headers=headers) as response:
                if response.status == 200:
                    schema_data = await response.json()
                    tables = schema_data.get('tables', [])
                    print(f"✅ Base accessible: {len(tables)} tables found")
                    for table in tables:
                        print(f"  📋 Table: {table['name']} (ID: {table['id']})")
                        if table.get('fields'):
                            field_names = [field['name'] for field in table['fields'][:5]]
                            print(f"    Fields: {', '.join(field_names)}...")
                else:
                    print(f"❌ Base schema error: {response.status}")
                    text = await response.text()
                    print(f"Error details: {text[:500]}")
                    
            # Try to access the first available table
            if 'tables' in locals() and tables:
                first_table = tables[0]
                print(f"\n📋 Testing first table: {first_table['name']}")
                async with session.get(f"{base_url}/{first_table['name']}", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Table accessible: {len(data.get('records', []))} records")
                        if data.get('records'):
                            print(f"Sample fields: {list(data['records'][0]['fields'].keys())}")
                    else:
                        print(f"❌ Table access error: {response.status}")
                        text = await response.text()
                        print(f"Error details: {text[:200]}")
                        
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_airtable_direct())