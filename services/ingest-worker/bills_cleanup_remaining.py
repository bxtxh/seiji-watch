#!/usr/bin/env python3
"""
Bills Cleanup Remaining Empty Records
残りの空レコードを完全にクリーンアップ
"""

import asyncio
import aiohttp
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def cleanup_remaining_empty_bills():
    """Clean up all remaining empty Bills records"""
    
    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    print("🧹 Starting cleanup of remaining empty Bills records...")
    
    deleted_count = 0
    errors = 0
    
    async with aiohttp.ClientSession() as session:
        # Keep fetching and deleting until no more empty records
        while True:
            # Get current records
            async with session.get(
                f"{base_url}/Bills (法案)?maxRecords=100", 
                headers=headers
            ) as response:
                if response.status != 200:
                    print(f"❌ Error fetching records: {response.status}")
                    break
                
                data = await response.json()
                records = data.get('records', [])
                
                if not records:
                    print("📋 No more records found")
                    break
                
                # Identify empty records in current batch
                empty_records = []
                essential_fields = ["Title", "Bill_Number", "Diet_Session", "House"]
                
                for record in records:
                    fields = record.get('fields', {})
                    filled_essential = sum(1 for field in essential_fields if fields.get(field))
                    
                    if filled_essential == 0:
                        empty_records.append(record)
                
                print(f"📊 Batch: {len(records)} total, {len(empty_records)} empty")
                
                if not empty_records:
                    print("✅ No more empty records found!")
                    break
                
                # Delete empty records
                for record in empty_records:
                    record_id = record['id']
                    
                    try:
                        async with session.delete(
                            f"{base_url}/Bills (法案)/{record_id}",
                            headers=headers
                        ) as delete_response:
                            if delete_response.status == 200:
                                deleted_count += 1
                                if deleted_count % 10 == 0:
                                    print(f"   🗑️ Deleted {deleted_count} empty records...")
                            else:
                                print(f"   ❌ Failed to delete {record_id}: {delete_response.status}")
                                errors += 1
                    except Exception as e:
                        print(f"   ❌ Error deleting {record_id}: {e}")
                        errors += 1
                    
                    await asyncio.sleep(0.05)  # Rate limiting
                
                # If we deleted many records, wait a bit before next batch
                if len(empty_records) > 10:
                    await asyncio.sleep(1)
        
        # Final verification
        print(f"\n📊 Final verification...")
        async with session.get(
            f"{base_url}/Bills (法案)?maxRecords=10", 
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                remaining_records = data.get('records', [])
                
                # Check if any remaining records are empty
                empty_remaining = 0
                for record in remaining_records:
                    fields = record.get('fields', {})
                    filled_essential = sum(1 for field in essential_fields if fields.get(field))
                    if filled_essential == 0:
                        empty_remaining += 1
                
                print(f"📋 Remaining records sample: {len(remaining_records)}")
                print(f"⚠️ Empty records in sample: {empty_remaining}")
    
    # Print final summary
    print(f"\n{'='*60}")
    print(f"📋 BILLS CLEANUP FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"🗑️ Total empty records deleted: {deleted_count}")
    print(f"❌ Errors encountered: {errors}")
    
    if deleted_count > 0:
        print(f"\n📈 Expected Quality Impact:")
        print(f"   Records removed: {deleted_count}")
        print(f"   Completeness should improve significantly")
        print(f"   Recommended: Re-run quality analysis")
    
    return {"deleted": deleted_count, "errors": errors}

if __name__ == "__main__":
    asyncio.run(cleanup_remaining_empty_bills())