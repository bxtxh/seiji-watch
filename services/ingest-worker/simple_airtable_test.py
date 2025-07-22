# \!/usr/bin/env python3
"""Simple Airtable connection test without SQLAlchemy dependencies."""

import asyncio
import os

import aiohttp

AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


async def test_airtable_tables():
    """Test access to different Airtable tables."""

    base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    # Tables to test
    tables_to_test = [
        "Bills (法案)",
        "Bills",
        "IssueCategories",
        "Issues",
        "IssueTags",
        "Members",
        "Parties",
        "Speeches",
        "Votes (投票)",
        "Bills_PolicyCategories",  # Our target table
    ]

    async with aiohttp.ClientSession() as session:
        for table_name in tables_to_test:
            try:
                url = f"{base_url}/{table_name}?maxRecords=1"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        record_count = len(data.get("records", []))
                        print(f"✅ {table_name}: {record_count} records (showing 1)")
                    elif response.status == 403:
                        print(f"❌ {table_name}: 403 Forbidden (permission denied)")
                    elif response.status == 404:
                        print(f"⚠️  {table_name}: 404 Not Found (table doesn't exist)")
                    else:
                        print(f"❓ {table_name}: {response.status} {response.reason}")

            except Exception as e:
                print(f"❌ {table_name}: Error - {e}")


async def main():
    """Main execution."""

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables are required")
        return 1

    print("🔍 Testing Airtable table access...")
    print(f"Base ID: {AIRTABLE_BASE_ID}")
    print(f"PAT: {AIRTABLE_PAT[:15]}...")
    print("=" * 50)

    await test_airtable_tables()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
