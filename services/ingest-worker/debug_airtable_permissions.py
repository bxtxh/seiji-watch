#!/usr/bin/env python3
"""
Airtable permissions debugging script based on o3 analysis.
Tests PAT scopes and table-level access systematically.
"""

import asyncio
import os

import aiohttp

AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


async def test_pat_scopes():
    """Test PAT scopes and metadata access."""

    base_url = "https://api.airtable.com/v0"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    print("🔍 PAT Scope & Metadata Analysis")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        # Test 1: Metadata API access (requires schema.bases:read)
        try:
            metadata_url = f"{base_url}/meta/bases/{AIRTABLE_BASE_ID}/tables"
            async with session.get(metadata_url, headers=headers) as response:
                if response.status == 200:
                    print("✅ PAT has schema.bases:read scope")
                    metadata = await response.json()
                    tables = metadata.get("tables", [])
                    print(f"📋 Found {len(tables)} tables in base:")

                    for table in tables:
                        table_id = table.get("id")
                        table_name = table.get("name")
                        print(f"   • {table_name} (ID: {table_id})")

                    return tables
                else:
                    print(f"❌ Metadata API failed: {response.status}")
                    if response.status == 403:
                        print("   → PAT lacks schema.bases:read scope")
                    return []

        except Exception as e:
            print(f"❌ Metadata API error: {e}")
            return []


async def test_individual_table_access(tables):
    """Test access to each table individually using table IDs from metadata."""

    base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    print("\n🔍 Individual Table Access Test")
    print("=" * 50)

    accessible_tables = []
    forbidden_tables = []

    async with aiohttp.ClientSession() as session:
        for table in tables:
            table_id = table.get("id")
            table_name = table.get("name")

            try:
                # Test using table ID (more reliable than name)
                url = f"{base_url}/{table_id}?maxRecords=1"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        record_count = len(data.get("records", []))
                        print(
                            f"✅ {table_name}: Access granted ({record_count} records)"
                        )
                        accessible_tables.append(table_name)
                    elif response.status == 403:
                        print(
                            f"❌ {table_name}: 403 Forbidden (table-level permission issue)"
                        )
                        forbidden_tables.append(table_name)
                    else:
                        print(f"❓ {table_name}: {response.status} {response.reason}")

            except Exception as e:
                print(f"❌ {table_name}: Error - {e}")

    return accessible_tables, forbidden_tables


async def test_write_permissions(accessible_tables):
    """Test write permissions on accessible tables."""

    print("\n🔍 Write Permission Test")
    print("=" * 50)

    if not accessible_tables:
        print("⚠️  No accessible tables to test write permissions")
        return

    # Test with a safe table (Bills)
    test_table = "Bills (法案)"
    if test_table in accessible_tables:
        base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
        headers = {
            "Authorization": f"Bearer {AIRTABLE_PAT}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            # Test creating a test record (we'll delete it immediately)
            test_data = {
    "fields": {
        "Name": "TEST_RECORD_EPIC16_DEBUG",
        "Notes": "This is a test record for debugging EPIC 16 permissions. Safe to delete.",
         } }

            try:
                url = f"{base_url}/{test_table}"
                async with session.post(
                    url, headers=headers, json=test_data
                ) as response:
                    if response.status == 200:
                        print("✅ PAT has data.records:write scope")

                        # Clean up the test record
                        created_record = await response.json()
                        record_id = created_record.get("id")

                        if record_id:
                            # Delete the test record
                            delete_url = f"{base_url}/{test_table}/{record_id}"
                            async with session.delete(
                                delete_url, headers=headers
                            ) as delete_response:
                                if delete_response.status == 200:
                                    print("🧹 Test record cleaned up successfully")
                    else:
                        print(f"❌ Write test failed: {response.status}")
                        if response.status == 403:
                            print(
                                "   → PAT lacks data.records:write scope or table write permissions"
                            )

            except Exception as e:
                print(f"❌ Write test error: {e}")


async def generate_diagnosis_report(accessible_tables, forbidden_tables):
    """Generate a diagnosis report with actionable recommendations."""

    print("\n📋 DIAGNOSIS REPORT")
    print("=" * 50)

    print(f"✅ Accessible Tables ({len(accessible_tables)}):")
    for table in accessible_tables:
        print(f"   • {table}")

    print(f"\n❌ Forbidden Tables ({len(forbidden_tables)}):")
    for table in forbidden_tables:
        print(f"   • {table}")

    print("\n🔧 RECOMMENDED ACTIONS:")

    if forbidden_tables:
        print("1. **Table-Level Permission Issue Detected**")
        print("   → Base owner needs to update table permissions:")
        print(
            "   → Go to each forbidden table → Table dropdown → Edit table permissions"
        )
        print("   → Set 'Who can read records' to 'Editors and up'")
        print("   → Set 'Who can create/delete' to 'Editors and up'")

        print("\n2. **Alternative: Add service account explicitly**")
        print("   → Share each table individually with the PAT owner's email")
        print("   → Grant 'Editor' role minimum")

        print("\n3. **For EPIC 16 Implementation**")
        if "Bills (法案)" in accessible_tables:
            print("   ✅ Can proceed with Bills table integration")
            print(
                "   ⚠️  May need to implement workaround for PolicyCategory relationships"
            )
            print(
                "   → Consider adding PolicyCategory_ID field to Bills table directly"
            )
        else:
            print("   ❌ Cannot proceed - Bills table access required")

    else:
        print("✅ All tables accessible - can proceed with EPIC 16 implementation")


async def main():
    """Main debugging execution."""

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables are required")
        return 1

    print("🚀 Airtable Permission Debugging (Based on o3 Analysis)")
    print(f"Base ID: {AIRTABLE_BASE_ID}")
    print(f"PAT: {AIRTABLE_PAT[:15]}...")
    print("=" * 70)

    # Step 1: Test PAT scopes and get table metadata
    tables = await test_pat_scopes()

    if not tables:
        print("\n❌ Cannot proceed without metadata access")
        print("🔧 IMMEDIATE ACTION: Regenerate PAT with schema.bases:read scope")
        return 1

    # Step 2: Test individual table access
    accessible_tables, forbidden_tables = await test_individual_table_access(tables)

    # Step 3: Test write permissions
    await test_write_permissions(accessible_tables)

    # Step 4: Generate diagnosis report
    await generate_diagnosis_report(accessible_tables, forbidden_tables)

    print(
        "\n✅ Diagnosis complete. Follow recommended actions to resolve EPIC 16 blockers."
    )
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
