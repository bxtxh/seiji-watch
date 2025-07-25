#!/usr/bin/env python3
"""
Create missing Airtable tables with schema.bases:write permission
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def create_airtable_tables():
    """Create missing Airtable tables"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not pat or not base_id:
        print("❌ Missing Airtable credentials")
        return False

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    # Table schemas to create
    tables_to_create = [
        {
            "name": "Parties (政党)",
            "description": "Political parties data for Diet Issue Tracker",
            "fields": [
                {"name": "Name", "type": "singleLineText"},
                {"name": "Name_EN", "type": "singleLineText"},
                {"name": "Abbreviation", "type": "singleLineText"},
                {"name": "Description", "type": "multilineText"},
                {"name": "Website_URL", "type": "url"},
                {"name": "Color_Code", "type": "singleLineText"},
                {
                    "name": "Is_Active",
                    "type": "checkbox",
                    "options": {"icon": "check", "color": "greenBright"},
                },
                {
                    "name": "Created_At",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
                {
                    "name": "Updated_At",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
            ],
        },
        {
            "name": "Meetings (会議)",
            "description": "Diet meetings and sessions data",
            "fields": [
                {"name": "Meeting_ID", "type": "singleLineText"},
                {"name": "Title", "type": "singleLineText"},
                {
                    "name": "Meeting_Type",
                    "type": "singleSelect",
                    "options": {
                        "choices": [
                            {"name": "本会議"},
                            {"name": "委員会"},
                            {"name": "分科会"},
                        ]
                    },
                },
                {"name": "Committee_Name", "type": "singleLineText"},
                {"name": "Diet_Session", "type": "singleLineText"},
                {
                    "name": "House",
                    "type": "singleSelect",
                    "options": {"choices": [{"name": "衆議院"}, {"name": "参議院"}]},
                },
                {
                    "name": "Session_Number",
                    "type": "number",
                    "options": {"precision": 0},
                },
                {
                    "name": "Meeting_Date",
                    "type": "date",
                    "options": {"dateFormat": {"name": "iso"}},
                },
                {
                    "name": "Start_Time",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
                {
                    "name": "End_Time",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
                {"name": "Summary", "type": "multilineText"},
                {"name": "Video_URL", "type": "url"},
                {"name": "Audio_URL", "type": "url"},
                {"name": "Transcript_URL", "type": "url"},
                {
                    "name": "Participant_Count",
                    "type": "number",
                    "options": {"precision": 0},
                },
                {
                    "name": "Is_Public",
                    "type": "checkbox",
                    "options": {"icon": "check", "color": "greenBright"},
                },
                {
                    "name": "Is_Processed",
                    "type": "checkbox",
                    "options": {"icon": "check", "color": "blueBright"},
                },
                {
                    "name": "Is_Cancelled",
                    "type": "checkbox",
                    "options": {"icon": "check", "color": "redBright"},
                },
                {
                    "name": "Created_At",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
                {
                    "name": "Updated_At",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
            ],
        },
        {
            "name": "IssueCategories (課題カテゴリ)",
            "description": "Hierarchical issue categories based on CAP classification",
            "fields": [
                {"name": "CAP_Code", "type": "singleLineText"},
                {
                    "name": "Layer",
                    "type": "singleSelect",
                    "options": {
                        "choices": [{"name": "L1"}, {"name": "L2"}, {"name": "L3"}]
                    },
                },
                {"name": "Title_JA", "type": "singleLineText"},
                {"name": "Title_EN", "type": "singleLineText"},
                {"name": "Summary_150JA", "type": "multilineText"},
                {
                    "name": "Is_Seed",
                    "type": "checkbox",
                    "options": {"icon": "check", "color": "yellowBright"},
                },
                {
                    "name": "Created_At",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
                {
                    "name": "Updated_At",
                    "type": "dateTime",
                    "options": {
                        "dateFormat": {"name": "iso"},
                        "timeFormat": {"name": "24hour"},
                        "timeZone": "Asia/Tokyo",
                    },
                },
            ],
        },
    ]

    async with aiohttp.ClientSession() as session:
        print("🚀 Creating missing Airtable tables...")
        print("=" * 60)

        success_count = 0

        for table_schema in tables_to_create:
            table_name = table_schema["name"]

            try:
                print(f"\n📋 Creating table: {table_name}")

                # Create table via meta API
                create_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"

                async with session.post(
                    create_url, headers=headers, json=table_schema
                ) as response:

                    print(f"  Status: {response.status}")

                    if response.status == 200:
                        result = await response.json()
                        table_id = result.get("id")
                        print(f"  ✅ SUCCESS: Table created with ID {table_id}")
                        print(
                            f"  Fields: {len(table_schema['fields'])} fields configured"
                        )
                        success_count += 1

                    elif response.status == 422:
                        error_data = await response.json()
                        error_msg = error_data.get("error", {}).get(
                            "message", "Unknown error"
                        )
                        if "already exists" in error_msg.lower():
                            print("  ⚠️  Table already exists, skipping...")
                            success_count += 1
                        else:
                            print(f"  ❌ VALIDATION ERROR: {error_msg}")

                    else:
                        error_text = await response.text()
                        print(f"  ❌ ERROR: {error_text[:200]}...")

            except Exception as e:
                print(f"  ❌ EXCEPTION: {e}")

        # Verify all tables exist
        print("\n🔍 Verifying table creation...")

        # Get current table list
        meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        async with session.get(meta_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                existing_tables = [table["name"] for table in data.get("tables", [])]

                print("\n📊 Current tables in base:")
                for table_name in sorted(existing_tables):
                    print(f"  ✅ {table_name}")

                # Check if all required tables exist
                required_tables = [
                    "Bills (法案)",
                    "Members (議員)",
                    "Speeches (発言)",
                    "Issues (課題)",
                    "Votes (投票)",
                    "IssueTags (課題タグ)",
                    "Parties (政党)",
                    "Meetings (会議)",
                    "IssueCategories (課題カテゴリ)",
                ]

                missing_tables = [
                    t for t in required_tables if t not in existing_tables
                ]

                print("\n🎯 Table Status Summary:")
                print(f"  Total required: {len(required_tables)}")
                print(f"  Currently exist: {len(existing_tables)}")
                print(f"  Missing: {len(missing_tables)}")

                if missing_tables:
                    print(f"  Missing tables: {', '.join(missing_tables)}")
                else:
                    print("  ✅ ALL REQUIRED TABLES EXIST!")

                return len(missing_tables) == 0

            else:
                print(f"❌ Could not verify tables: {response.status}")
                return False


async def main():
    """Main function"""
    print("🚀 EPIC 13: Airtable テーブル作成")
    print("🎯 目標: 不足している3テーブルの作成")
    print()

    try:
        success = await create_airtable_tables()

        if success:
            print("\n🎉 SUCCESS: All required tables created!")
            print("✅ Ready for data collection phase")
            print("🔄 Next: T108 議員データ収集実行")
        else:
            print("\n⚠️  PARTIAL SUCCESS: Some tables may need manual creation")

    except Exception as e:
        print(f"💥 Table creation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
