#!/usr/bin/env python3
"""
Fix Bills table structure - add proper fields for bill details
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')


async def fix_bills_table_structure():
    """Add proper structured fields to Bills table"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    # Get table info
    meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"

    async with aiohttp.ClientSession() as session:
        async with session.get(meta_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                bills_table_id = None

                for table in data.get("tables", []):
                    if table["name"] == "Bills (法案)":
                        bills_table_id = table["id"]
                        print("📋 Current Bills table fields:")
                        for field in table.get("fields", []):
                            print(f"    - {field['name']} ({field['type']})")
                        break

                if not bills_table_id:
                    print("❌ Bills table not found")
                    return False

                print(f"\n🔍 Bills table ID: {bills_table_id}")

                # Proper Bill fields to add
                fields_to_add = [
                    {"name": "Bill_ID", "type": "singleLineText"},
                    {"name": "Diet_Session", "type": "singleLineText"},
                    {"name": "Bill_Number", "type": "singleLineText"},
                    {"name": "Title", "type": "singleLineText"},
                    {"name": "Bill_Status", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "提出"}, {"name": "審議中"}, {"name": "可決"},
                            {"name": "否決"}, {"name": "成立"}, {"name": "廃案"}
                        ]
                    }},
                    {"name": "Stage", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "Backlog"}, {"name": "審議中"},
                            {"name": "採決待ち"}, {"name": "成立"}
                        ]
                    }},
                    {"name": "Submitter", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "政府"}, {"name": "議員"}, {"name": "委員会"}
                        ]
                    }},
                    {"name": "House", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "参議院"}, {"name": "衆議院"}, {"name": "両院"}
                        ]
                    }},
                    {"name": "Bill_Type", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "提出法律案"}, {"name": "予算案"}, {"name": "条約"},
                            {"name": "決議案"}, {"name": "意見書"}
                        ]
                    }},
                    {"name": "Category", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "予算・決算"}, {"name": "税制"}, {"name": "社会保障"},
                            {"name": "外交・国際"}, {"name": "経済・産業"}, {"name": "その他"}
                        ]
                    }},
                    {"name": "Submission_Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
                    {"name": "Committee", "type": "singleLineText"},
                    {"name": "Bill_URL", "type": "url"},
                    {"name": "Summary", "type": "multilineText"},
                    {"name": "Full_Text", "type": "multilineText"},
                    {"name": "Related_Documents", "type": "multilineText"},
                    {"name": "Data_Source", "type": "singleLineText"},
                    {"name": "Collection_Date", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}},
                    {"name": "Process_Method", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "自動スクレイピング"}, {"name": "手動入力"},
                            {"name": "AI処理"}, {"name": "混合"}
                        ]
                    }},
                    {"name": "Quality_Score", "type": "number", "options": {"precision": 2}},
                    {"name": "AI_Analysis", "type": "multilineText"},
                    {"name": "Keywords", "type": "singleLineText"},
                    {"name": "Priority", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "high"}, {"name": "medium"}, {"name": "low"}
                        ]
                    }},
                    {"name": "Created_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}},
                    {"name": "Updated_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}}
                ]

                # Add fields one by one
                success_count = 0
                for field in fields_to_add:
                    try:
                        add_field_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{bills_table_id}/fields"

                        async with session.post(add_field_url, headers=headers, json=field) as add_response:
                            if add_response.status == 200:
                                result = await add_response.json()
                                field_id = result.get("id")
                                print(f"  ✅ Added field: {field['name']} ({field_id})")
                                success_count += 1
                            else:
                                error_text = await add_response.text()
                                print(
                                    f"  ❌ Failed to add {field['name']}: {add_response.status}")
                                if "already exists" in error_text.lower():
                                    print("    (Field already exists, skipping)")
                                    success_count += 1
                                else:
                                    print(f"    Error: {error_text[:100]}...")

                        # Small delay between requests
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        print(f"  ❌ Exception adding {field['name']}: {e}")

                print("\n📊 Summary:")
                print(f"  Total fields to add: {len(fields_to_add)}")
                print(f"  Successfully added: {success_count}")
                print(f"  Success rate: {success_count/len(fields_to_add)*100:.1f}%")

                return success_count >= len(fields_to_add) * 0.8  # 80% success rate

            else:
                print(f"❌ Failed to get table info: {response.status}")
                return False


async def main():
    """Main function"""
    print("🔧 Fix Bills table structure - Adding proper structured fields...")
    print("=" * 60)
    print("❌ Current Problem:")
    print("  All bill details stored in unstructured 'Notes' field")
    print("  - No searchability by bill ID, status, etc.")
    print("  - No relational queries possible")
    print("  - Poor API efficiency")
    print("  - Difficult data validation")
    print("\n✅ Solution:")
    print("  Add proper structured fields for each bill property")
    print("  - Bill_ID, Diet_Session, Bill_Number")
    print("  - Bill_Status, Stage, Submitter, House")
    print("  - Category, Submission_Date, Committee")
    print("  - Structured metadata fields")
    print("=" * 60)
    print()

    success = await fix_bills_table_structure()

    if success:
        print("\n✅ Bills table structure fixed successfully!")
        print("🔄 Next: Migrate existing data from Notes to structured fields")
        print("💡 Recommendation: Create data migration script to parse Notes content")
    else:
        print("\n❌ Failed to add all required fields")

if __name__ == "__main__":
    asyncio.run(main())
