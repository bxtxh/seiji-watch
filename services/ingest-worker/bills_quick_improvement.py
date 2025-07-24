#!/usr/bin/env python3
"""
Bills Quick Improvement
高速Bills改善システム - バッチ処理アプローチ
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')


async def quick_bills_improvement():
    """Quick Bills table improvement with batch processing"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    print("🚀 Starting Quick Bills Improvement...")

    improvements = {
        "status_standardized": 0,
        "categories_filled": 0,
        "priorities_assigned": 0,
        "stages_filled": 0,
        "errors": 0
    }

    async with aiohttp.ClientSession() as session:
        # Get Bills records in small batches
        print("📄 Fetching Bills records...")

        async with session.get(
            f"{base_url}/Bills (法案)?maxRecords=50",
            headers=headers
        ) as response:
            if response.status != 200:
                print(f"❌ Failed to fetch records: {response.status}")
                return

            data = await response.json()
            records = data.get('records', [])
            print(f"📊 Processing {len(records)} Bills records...")

            # Process each record with improvements
            for i, record in enumerate(records):
                if i >= 20:  # Limit to first 20 for quick improvement
                    break

                record_id = record['id']
                fields = record.get('fields', {})
                updates = {}

                print(f"\n🔧 Processing record {i+1}/20: {record_id}")

                # 1. Status standardization
                status = fields.get('Bill_Status', '')
                if status == '議案要旨':
                    updates['Bill_Status'] = '提出'
                    improvements["status_standardized"] += 1
                elif not status:
                    updates['Bill_Status'] = '提出'
                    improvements["status_standardized"] += 1

                # 2. Category classification based on title
                if not fields.get('Category') or fields.get('Category') == 'その他':
                    title = fields.get('Title', '').lower()
                    if '経済' in title or '産業' in title:
                        updates['Category'] = '経済・産業'
                    elif '社会' in title or '保障' in title or '年金' in title:
                        updates['Category'] = '社会保障'
                    elif '外交' in title or '国際' in title or '条約' in title:
                        updates['Category'] = '外交・国際'
                    elif '教育' in title or '学校' in title:
                        updates['Category'] = '教育・文化'
                    elif '環境' in title or 'エネルギー' in title:
                        updates['Category'] = '環境・エネルギー'
                    else:
                        updates['Category'] = 'その他'
                    improvements["categories_filled"] += 1

                # 3. Priority assignment
                if not fields.get('Priority'):
                    title = fields.get('Title', '').lower()
                    if '重要' in title or '基本' in title:
                        updates['Priority'] = 'high'
                    elif '一部改正' in title or '整備' in title:
                        updates['Priority'] = 'low'
                    else:
                        updates['Priority'] = 'medium'
                    improvements["priorities_assigned"] += 1

                # 4. Stage filling
                if not fields.get('Stage'):
                    bill_status = updates.get(
                        'Bill_Status', fields.get(
                            'Bill_Status', ''))
                    if bill_status == '提出':
                        updates['Stage'] = 'Backlog'
                    elif bill_status == '審議中':
                        updates['Stage'] = '審議中'
                    elif bill_status == '成立':
                        updates['Stage'] = '成立'
                    else:
                        updates['Stage'] = 'Backlog'
                    improvements["stages_filled"] += 1

                # Apply updates if any
                if updates:
                    print(f"   📝 Updating: {list(updates.keys())}")

                    try:
                        update_data = {"fields": updates}
                        async with session.patch(
                            f"{base_url}/Bills (法案)/{record_id}",
                            headers=headers,
                            json=update_data
                        ) as update_response:
                            if update_response.status == 200:
                                print("   ✅ Update successful")
                            else:
                                await update_response.text()
                                print(f"   ❌ Update failed: {update_response.status}")
                                improvements["errors"] += 1
                    except Exception as e:
                        print(f"   ❌ Update error: {e}")
                        improvements["errors"] += 1
                else:
                    print("   ℹ️ No updates needed")

                await asyncio.sleep(0.2)  # Rate limiting

        # Final verification - check one record to see improvements
        print("\n📊 Verifying improvements...")
        async with session.get(
            f"{base_url}/Bills (法案)?maxRecords=5",
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                verification_records = data.get('records', [])

                # Calculate completeness
                essential_fields = [
                    "Title",
                    "Bill_Status",
                    "Category",
                    "Priority",
                    "Stage"]
                total_completeness = 0

                for record in verification_records:
                    fields = record.get('fields', {})
                    filled_count = sum(
                        1 for field in essential_fields if fields.get(field))
                    completeness = filled_count / len(essential_fields)
                    total_completeness += completeness

                avg_completeness = total_completeness / \
                    len(verification_records) if verification_records else 0

                print(f"📈 Sample completeness: {avg_completeness:.1%}")

    # Print summary
    print(f"\n{'='*60}")
    print("📋 QUICK BILLS IMPROVEMENT SUMMARY")
    print(f"{'='*60}")
    print(f"🔧 Status standardized: {improvements['status_standardized']}")
    print(f"🏷️ Categories filled: {improvements['categories_filled']}")
    print(f"⭐ Priorities assigned: {improvements['priorities_assigned']}")
    print(f"📊 Stages filled: {improvements['stages_filled']}")
    print(f"❌ Errors: {improvements['errors']}")

    total_improvements = sum(v for k, v in improvements.items() if k != "errors")
    print(f"\n✅ Total improvements: {total_improvements}")

    # Save quick report
    report = {
        "improvement_date": datetime.now().isoformat(),
        "type": "quick_improvement_batch_1",
        "records_processed": 20,
        "improvements": improvements,
        "notes": "First batch of quick improvements focusing on essential field completion"}

    filename = f"bills_quick_improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 Report saved: {filename}")

    return improvements

if __name__ == "__main__":
    asyncio.run(quick_bills_improvement())
