#!/usr/bin/env python3
"""
Fix Members table schema - delete and recreate with proper fields
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def fix_members_table():
    """Delete and recreate Members table with proper schema"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    # Get table ID for Members (議員)
    meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"

    async with aiohttp.ClientSession() as session:
        # Get current table ID
        async with session.get(meta_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                members_table_id = None

                for table in data.get("tables", []):
                    if table["name"] == "Members (議員)":
                        members_table_id = table["id"]
                        break

                if not members_table_id:
                    print("❌ Members table not found")
                    return False

                print(f"🔍 Found Members table: {members_table_id}")

                # Delete existing table
                delete_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{members_table_id}"
                async with session.delete(delete_url, headers=headers) as delete_response:
                    if delete_response.status == 200:
                        print("✅ Deleted old Members table")
                    else:
                        print(f"❌ Failed to delete table: {delete_response.status}")
                        return False

                # Wait a moment
                await asyncio.sleep(2)

                # Create new Members table with proper schema
                new_table_schema = {
                    "name": "Members (議員)",
                    "description": "Diet members data with complete information",
                    "fields": [
                        {"name": "Name", "type": "singleLineText"},
                        {"name": "Name_Kana", "type": "singleLineText"},
                        {"name": "Name_EN", "type": "singleLineText"},
                        {"name": "House", "type": "singleSelect", "options": {
                            "choices": [
                                {"name": "衆議院"},
                                {"name": "参議院"}
                            ]
                        }},
                        {"name": "Constituency", "type": "singleLineText"},
                        {"name": "Diet_Member_ID", "type": "singleLineText"},
                        {"name": "Birth_Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
                        {"name": "Gender", "type": "singleSelect", "options": {
                            "choices": [
                                {"name": "男性"},
                                {"name": "女性"},
                                {"name": "その他"}
                            ]
                        }},
                        {"name": "First_Elected", "type": "singleLineText"},
                        {"name": "Terms_Served", "type": "number", "options": {"precision": 0}},
                        {"name": "Previous_Occupations", "type": "multilineText"},
                        {"name": "Education", "type": "multilineText"},
                        {"name": "Website_URL", "type": "url"},
                        {"name": "Twitter_Handle", "type": "singleLineText"},
                        {"name": "Facebook_URL", "type": "url"},
                        {"name": "Is_Active", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
                        {"name": "Status", "type": "singleSelect", "options": {
                            "choices": [
                                {"name": "active"},
                                {"name": "inactive"},
                                {"name": "deceased"}
                            ]
                        }},
                        {"name": "Party", "type": "multipleRecordLinks", "options": {"linkedTableId": None}},  # Will be updated
                        {"name": "Created_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}},
                        {"name": "Updated_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}}
                    ]
                }

                # Get Parties table ID for linking
                parties_table_id = None
                for table in data.get("tables", []):
                    if table["name"] == "Parties (政党)":
                        parties_table_id = table["id"]
                        break

                if parties_table_id:
                    # Update Party field with correct linkedTableId
                    for field in new_table_schema["fields"]:
                        if field["name"] == "Party":
                            field["options"]["linkedTableId"] = parties_table_id

                # Create new table
                create_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
                async with session.post(create_url, headers=headers, json=new_table_schema) as create_response:
                    if create_response.status == 200:
                        result = await create_response.json()
                        new_table_id = result.get("id")
                        print(f"✅ Created new Members table: {new_table_id}")
                        print(f"📋 Fields: {len(new_table_schema['fields'])} configured")
                        return True
                    else:
                        error_text = await create_response.text()
                        print(f"❌ Failed to create table: {create_response.status}")
                        print(f"Error: {error_text}")
                        return False
            else:
                print(f"❌ Failed to get table info: {response.status}")
                return False

async def main():
    """Main function"""
    print("🔧 Fixing Members (議員) table schema...")

    success = await fix_members_table()

    if success:
        print("\n✅ Members table fixed successfully!")
        print("🔄 Ready to retry T108 member data collection")
    else:
        print("\n❌ Failed to fix Members table")

if __name__ == "__main__":
    asyncio.run(main())
