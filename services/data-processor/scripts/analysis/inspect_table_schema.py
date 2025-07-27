#!/usr/bin/env python3
"""
Inspect Airtable table schema to understand field structure.
"""

import asyncio
import json
import os

import aiohttp

AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


async def inspect_table_schema(table_name: str, table_id: str):
    """Inspect table schema using metadata API."""

    print(f"🔍 Inspecting {table_name} Schema")
    print("=" * 60)

    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        # Use metadata API to get table schema
        metadata_url = (
            f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables"
        )

        try:
            async with session.get(metadata_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    tables = data.get("tables", [])

                    # Find the target table
                    target_table = None
                    for table in tables:
                        if table.get("id") == table_id:
                            target_table = table
                            break

                    if not target_table:
                        print(f"❌ Table {table_name} not found in metadata")
                        return False

                    print(f"📋 Table: {target_table.get('name', 'Unknown')}")
                    print(f"   ID: {target_table.get('id', 'Unknown')}")

                    # Show fields
                    fields = target_table.get("fields", [])
                    print(f"\n📊 Fields ({len(fields)} total):")

                    for field in fields:
                        field_name = field.get("name", "Unknown")
                        field_type = field.get("type", "Unknown")
                        field_id = field.get("id", "Unknown")

                        print(f"   • {field_name} ({field_type}) - ID: {field_id}")

                        # Show field options if available
                        options = field.get("options", {})
                        if options:
                            print(f"     Options: {json.dumps(options, indent=8)}")

                    return fields

                else:
                    print(f"❌ Metadata API failed: {response.status}")
                    return False

        except Exception as e:
            print(f"❌ Error inspecting schema: {e}")
            return False


async def main():
    """Main execution."""

    print("🚀 Airtable Schema Inspector")
    print("=" * 70)

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables required")
        return 1

    # Inspect key tables
    tables_to_inspect = [
        ("IssueCategories", "tbl6wK8L9K5ny1dDm"),
        ("Bills", "tblQjh6zvKLYa9fPn"),
        ("Issues", "tbllqAfZMz6QNaMfF"),
    ]

    for table_name, table_id in tables_to_inspect:
        await inspect_table_schema(table_name, table_id)
        print()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
