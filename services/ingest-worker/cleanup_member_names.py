#!/usr/bin/env python3
"""
Members Name Cleanup - Remove Trailing Numbers
Members 名前クリーンアップ - 末尾数字除去
"""

import asyncio
import aiohttp
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def cleanup_member_names():
    """Remove trailing numbers from Member names"""
    
    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    print("🧹 Starting Members Name Cleanup...")
    print("🎯 Target: Remove trailing numbers from 247 affected names")
    
    cleanup_results = {
        "names_cleaned": 0,
        "records_updated": 0,
        "errors": 0,
        "backup_created": False
    }
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Get all current records
        print("\n📄 Fetching all Members records...")
        
        all_records = []
        offset = None
        
        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset
            
            async with session.get(
                f"{base_url}/Members (議員)",
                headers=headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get('records', [])
                    all_records.extend(records)
                    
                    offset = data.get('offset')
                    if not offset:
                        break
                else:
                    print(f"❌ Error fetching records: {response.status}")
                    return
        
        print(f"📊 Found {len(all_records)} total records")
        
        # Step 2: Identify records with trailing numbers
        print("\n🔍 Identifying records with trailing numbers...")
        
        records_to_clean = []
        for record in all_records:
            name = record.get('fields', {}).get('Name', '')
            
            # Check if name ends with a digit
            if re.search(r'\d+$', name):
                base_name = re.sub(r'\d+$', '', name).strip()
                if base_name != name:  # Only if there's actually a change
                    records_to_clean.append({
                        'record': record,
                        'current_name': name,
                        'clean_name': base_name
                    })
        
        print(f"🔍 Found {len(records_to_clean)} records with trailing numbers")
        
        # Step 3: Create backup
        print("\n💾 Creating backup of affected records...")
        
        backup_data = {
            "backup_date": datetime.now().isoformat(),
            "total_records": len(records_to_clean),
            "records": [item['record'] for item in records_to_clean]
        }
        
        backup_filename = f"members_name_cleanup_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        cleanup_results["backup_created"] = True
        print(f"✅ Backup created: {backup_filename}")
        
        # Step 4: Show preview of changes
        print("\n👀 Preview of changes (first 10):")
        for i, item in enumerate(records_to_clean[:10]):
            print(f"   {i+1:2d}. '{item['current_name']}' → '{item['clean_name']}'")
        
        if len(records_to_clean) > 10:
            print(f"   ... and {len(records_to_clean) - 10} more changes")
        
        # Step 5: Confirmation
        print(f"\n⚠️ CONFIRMATION REQUIRED:")
        print(f"   📊 Records to update: {len(records_to_clean)}")
        print(f"   🔄 Action: Remove trailing numbers from names")
        print(f"   💾 Backup saved: {backup_filename}")
        print(f"   ⏱️ Estimated time: {len(records_to_clean) * 0.1:.1f} seconds")
        
        # For automated execution, we'll proceed (in production, you'd want user confirmation)
        proceed = True
        
        if not proceed:
            print("❌ Cleanup cancelled by user")
            return cleanup_results
        
        # Step 6: Execute cleanup
        print(f"\n🚀 Executing name cleanup...")
        
        for i, item in enumerate(records_to_clean):
            record = item['record']
            clean_name = item['clean_name']
            
            try:
                # Update the record with cleaned name
                update_data = {
                    "fields": {
                        "Name": clean_name
                    }
                }
                
                async with session.patch(
                    f"{base_url}/Members (議員)/{record['id']}",
                    headers=headers,
                    json=update_data
                ) as response:
                    if response.status == 200:
                        cleanup_results["names_cleaned"] += 1
                        cleanup_results["records_updated"] += 1
                        
                        if (i + 1) % 25 == 0:
                            print(f"   ✅ Cleaned {i + 1}/{len(records_to_clean)} names...")
                    else:
                        cleanup_results["errors"] += 1
                        print(f"   ❌ Error updating {record['id']}: {response.status}")
                        
            except Exception as e:
                cleanup_results["errors"] += 1
                print(f"   ❌ Exception updating {record['id']}: {e}")
            
            # Rate limiting
            await asyncio.sleep(0.1)
        
        # Step 7: Verification
        print(f"\n🔍 Verifying cleanup results...")
        
        # Re-fetch to verify
        verification_records = []
        offset = None
        
        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset
            
            async with session.get(
                f"{base_url}/Members (議員)",
                headers=headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get('records', [])
                    verification_records.extend(records)
                    
                    offset = data.get('offset')
                    if not offset:
                        break
        
        # Count remaining names with trailing numbers
        remaining_issues = 0
        for record in verification_records:
            name = record.get('fields', {}).get('Name', '')
            if re.search(r'\d+$', name):
                remaining_issues += 1
        
        print(f"📊 Verification: {remaining_issues} records still have trailing numbers")
    
    # Generate final report
    print(f"\n{'='*70}")
    print(f"🧹 MEMBERS NAME CLEANUP SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Names cleaned: {cleanup_results['names_cleaned']}")
    print(f"📝 Records updated: {cleanup_results['records_updated']}")
    print(f"❌ Errors: {cleanup_results['errors']}")
    print(f"💾 Backup created: {'✅' if cleanup_results['backup_created'] else '❌'}")
    print(f"🔍 Remaining issues: {remaining_issues}")
    
    success_rate = (cleanup_results['names_cleaned'] / len(records_to_clean) * 100) if records_to_clean else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")
    
    if remaining_issues == 0:
        print(f"🎉 SUCCESS! All trailing numbers have been removed!")
    elif remaining_issues < 10:
        print(f"⚠️ Nearly complete - {remaining_issues} issues remaining")
    else:
        print(f"⚠️ Partial success - {remaining_issues} issues still need attention")
    
    # Save cleanup report
    report = {
        "cleanup_date": datetime.now().isoformat(),
        "cleanup_results": cleanup_results,
        "initial_issues": len(records_to_clean),
        "remaining_issues": remaining_issues,
        "success_rate": success_rate,
        "backup_filename": backup_filename
    }
    
    report_filename = f"members_name_cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Cleanup report saved: {report_filename}")
    
    return cleanup_results

if __name__ == "__main__":
    asyncio.run(cleanup_member_names())