#!/usr/bin/env python3
"""
Quick completeness improvement test
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def test_improvements():
    """Test basic improvements on a few records"""
    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Get a few Bills records
        async with session.get(
            f"{base_url}/Bills (法案)?maxRecords=3",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                records = data.get('records', [])
                
                print(f"📄 Found {len(records)} Bills records")
                
                for record in records[:1]:  # Test just one record
                    record_id = record['id']
                    fields = record.get('fields', {})
                    
                    print(f"\n🔍 Testing record {record_id}")
                    print(f"Current fields: {list(fields.keys())}")
                    
                    # Simple test update
                    updates = {}
                    if not fields.get('Priority') or fields.get('Priority') == 'medium':
                        updates['Priority'] = 'high'
                    
                    if updates:
                        update_data = {"fields": updates}
                        print(f"📝 Updating with: {updates}")
                        
                        async with session.patch(
                            f"{base_url}/Bills (法案)/{record_id}",
                            headers=headers,
                            json=update_data
                        ) as update_response:
                            if update_response.status == 200:
                                print("✅ Update successful!")
                            else:
                                error_text = await update_response.text()
                                print(f"❌ Update failed: {update_response.status} - {error_text}")
                    else:
                        print("⚠️ No updates needed")
                        
            else:
                print(f"❌ Failed to fetch records: {response.status}")

if __name__ == "__main__":
    asyncio.run(test_improvements())