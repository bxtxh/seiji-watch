#!/usr/bin/env python3
"""
Check current Airtable status and data counts
"""

import aiohttp
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def check_airtable_status():
    """Check current status of Airtable tables"""
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    async with aiohttp.ClientSession() as session:
        try:
            print("🔍 Checking current Airtable status...")
            
            # Check Bills table
            print("\n📋 Bills (法案) table:")
            async with session.get(f"{base_url}/Bills (法案)", headers=headers) as response:
                if response.status == 200:
                    bills_data = await response.json()
                    bills_count = len(bills_data.get('records', []))
                    print(f"  Current records: {bills_count}")
                    
                    if bills_count > 0:
                        sample_bill = bills_data['records'][0]
                        print(f"  Sample fields: {list(sample_bill['fields'].keys())}")
                        if 'Name' in sample_bill['fields']:
                            print(f"  Sample title: {sample_bill['fields']['Name'][:50]}...")
                else:
                    print(f"  ❌ Error accessing Bills: {response.status}")
                    bills_count = 0
            
            # Check Votes table
            print("\n🗳️ Votes (投票) table:")
            async with session.get(f"{base_url}/Votes (投票)", headers=headers) as response:
                if response.status == 200:
                    votes_data = await response.json()
                    votes_count = len(votes_data.get('records', []))
                    print(f"  Current records: {votes_count}")
                    
                    if votes_count > 0:
                        sample_vote = votes_data['records'][0]
                        print(f"  Sample fields: {list(sample_vote['fields'].keys())}")
                        if 'Name' in sample_vote['fields']:
                            print(f"  Sample name: {sample_vote['fields']['Name'][:50]}...")
                else:
                    print(f"  ❌ Error accessing Votes: {response.status}")
                    votes_count = 0
            
            # Assessment
            print(f"\n📊 EPIC 11 T96 Status Assessment:")
            print(f"📋 Bills: {bills_count} records")
            print(f"🗳️ Votes: {votes_count} records")
            
            if bills_count >= 150:
                print(f"✅ SUFFICIENT DATA FOR MVP!")
                print(f"🎯 EPIC 11 T96 already has enough bills for functionality")
                print(f"✅ Ready to proceed to T97: API Gateway実データ連携修正")
                return True, bills_count, votes_count
            elif bills_count >= 50:
                print(f"⚠️ PARTIAL DATA - may be sufficient for basic testing")
                print(f"💡 Consider proceeding with T97 for basic functionality")
                return "partial", bills_count, votes_count
            else:
                print(f"❌ INSUFFICIENT DATA - need more records for MVP")
                return False, bills_count, votes_count
                
        except Exception as e:
            print(f"❌ Error checking Airtable status: {e}")
            return False, 0, 0

async def main():
    """Check Airtable status"""
    
    print("=" * 50)
    print("🔍 EPIC 11 T96: AIRTABLE STATUS CHECK")
    print("=" * 50)
    
    try:
        status, bills_count, votes_count = await check_airtable_status()
        
        if status == True:
            print(f"\n🎉 EPIC 11 T96 DATA INTEGRATION COMPLETE!")
            print(f"📊 Current state sufficient for MVP")
            print(f"🔄 Ready for next task: T97")
        elif status == "partial":
            print(f"\n⚠️ EPIC 11 T96 PARTIALLY COMPLETE")
            print(f"📊 May proceed with available data")
        else:
            print(f"\n❌ EPIC 11 T96 NEEDS MORE DATA")
            
    except Exception as e:
        print(f"💥 Status check failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())