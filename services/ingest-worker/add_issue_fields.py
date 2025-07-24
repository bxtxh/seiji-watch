#!/usr/bin/env python3
"""
Add required fields to existing Issues table
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def add_issue_fields():
    """Add required fields to Issues table"""

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
                issues_table_id = None
                bills_table_id = None

                for table in data.get("tables", []):
                    if table["name"] == "Issues (課題)":
                        issues_table_id = table["id"]
                        print("  Current Issues table fields:")
                        for field in table.get("fields", []):
                            print(f"    - {field['name']} ({field['type']})")
                    elif table["name"] == "Bills (法案)":
                        bills_table_id = table["id"]

                if not issues_table_id:
                    print("❌ Issues table not found")
                    return False

                print(f"🔍 Issues table ID: {issues_table_id}")
                print(f"🔍 Bills table ID: {bills_table_id}")

                # Fields to add
                fields_to_add = [
                    {"name": "Title", "type": "singleLineText"},
                    {"name": "Description", "type": "multilineText"},
                    {"name": "Category_L1", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "社会保障"},
                            {"name": "経済・産業"},
                            {"name": "外交・国際"},
                            {"name": "教育・文化"},
                            {"name": "環境・エネルギー"},
                            {"name": "司法・行政"},
                            {"name": "インフラ・交通"}
                        ]
                    }},
                    {"name": "Category_L2", "type": "singleLineText"},
                    {"name": "Category_L3", "type": "singleLineText"},
                    {"name": "Priority", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "high"}, {"name": "medium"}, {"name": "low"}
                        ]
                    }},
                    {"name": "Status", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "active"},
                            {"name": "inactive"},
                            {"name": "resolved"}
                        ]
                    }},
                    {"name": "Source_Bill_ID", "type": "singleLineText"},
                    {"name": "Impact_Level", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "high"}, {"name": "medium"}, {"name": "low"}
                        ]
                    }},
                    {"name": "Stakeholders", "type": "multilineText"},
                    {"name": "Estimated_Timeline", "type": "singleLineText"},
                    {
                        "name": "AI_Confidence", "type": "number",
                        "options": {"precision": 2}
                    },
                    {"name": "Tags", "type": "singleLineText"},
                    {"name": "Related_Keywords", "type": "singleLineText"},
                    {
                        "name": "Created_At", "type": "dateTime",
                        "options": {
                            "dateFormat": {"name": "iso"},
                            "timeFormat": {"name": "24hour"},
                            "timeZone": "Asia/Tokyo"
                        }
                    },
                    {
                        "name": "Updated_At", "type": "dateTime",
                        "options": {
                            "dateFormat": {"name": "iso"},
                            "timeFormat": {"name": "24hour"},
                            "timeZone": "Asia/Tokyo"
                        }
                    }
                ]

                # Add Bill link field if Bills table exists
                if bills_table_id:
                    fields_to_add.append({
                        "name": "Source_Bills",
                        "type": "multipleRecordLinks",
                        "options": {"linkedTableId": bills_table_id}
                    })

                # Add fields one by one
                success_count = 0
                for field in fields_to_add:
                    try:
                        add_field_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{issues_table_id}/fields"

                        async with session.post(
                            add_field_url, headers=headers, json=field
                        ) as add_response:
                            if add_response.status == 200:
                                result = await add_response.json()
                                field_id = result.get("id")
                                print(f"  ✅ Added field: {field['name']} ({field_id})")
                                success_count += 1
                            else:
                                error_text = await add_response.text()
                                print(
                            f"  ❌ Failed to add {field['name']}: "
                            f"{add_response.status}"
                        )
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
    print("🔧 Adding fields to Issues (課題) table...")

    success = await add_issue_fields()

    if success:
        print("\n✅ Issues table fields added successfully!")
        print("🔄 Ready to execute T110 issue data generation")
    else:
        print("\n❌ Failed to add all required fields")

if __name__ == "__main__":
    asyncio.run(main())
