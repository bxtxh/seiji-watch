#!/usr/bin/env python3
"""T129.3 Migration script to create Bills-PolicyCategory relationships."""

import asyncio
import json
import os
from datetime import datetime

import aiohttp

# Load environment variables
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


class BillsPolicyCategoryMigrator:
    def __init__(self):
        self.base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
        self.headers = {
            "Authorization": f"Bearer {AIRTABLE_PAT}",
            "Content-Type": "application/json",
        }
        self.session = None
        self.mapping_data = None
        self.bills_data = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def load_mapping_data(self):
        """Load the mapping data from T129.2 analysis."""
        try:
            with open(
                "bills_to_issue_categories_mapping_t129.json", encoding="utf-8"
            ) as f:
                self.mapping_data = json.load(f)
            print("✅ Loaded Bills-to-IssueCategories mapping data")
            return True
        except FileNotFoundError:
            print("❌ Mapping data not found. Please run T129.2 first.")
            return False

    async def fetch_bills_data(self):
        """Fetch all Bills records with categories."""
        print("\n📋 Fetching Bills data...")

        bills_url = f"{self.base_url}/Bills%20(%E6%B3%95%E6%A1%88)"
        all_bills = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with self.session.get(
                bills_url, headers=self.headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_bills.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Failed to fetch Bills data: {response.status}")
                    return None

        print(f"   ✅ Fetched {len(all_bills)} Bills records")
        self.bills_data = all_bills
        return all_bills

    async def check_bills_policy_categories_table(self):
        """Check if Bills_PolicyCategories table exists and is accessible."""
        print("\n🔍 Checking Bills_PolicyCategories table...")

        test_url = f"{self.base_url}/Bills_PolicyCategories?maxRecords=1"
        async with self.session.get(test_url, headers=self.headers) as response:
            if response.status == 200:
                print("✅ Bills_PolicyCategories table is accessible")
                return True
            elif response.status == 404:
                print("❌ Bills_PolicyCategories table does not exist")
                print("   Please create the table first using T127 migration")
                return False
            elif response.status == 403:
                print("❌ Bills_PolicyCategories table is not accessible")
                print("   Please check table permissions")
                return False
            else:
                print(f"❌ Unexpected response: {response.status}")
                return False

    async def create_policy_category_relationships(self, dry_run=True):
        """Create Bills-PolicyCategory relationships."""
        print(
            f"\n🔗 Creating Bills-PolicyCategory relationships (dry_run={dry_run})..."
        )

        if not self.mapping_data or not self.bills_data:
            print("❌ Missing required data")
            return False

        mapping = self.mapping_data.get("bills_to_issue_mapping", {})
        relationships_to_create = []

        # Process each bill
        for bill in self.bills_data:
            fields = bill.get("fields", {})
            bill_id = bill.get("id")
            bill_category = fields.get("Category")

            if not bill_category or bill_category not in mapping:
                continue

            # Get the mapped policy category
            policy_mapping = mapping[bill_category]
            policy_category_id = policy_mapping.get("category_id")

            if not policy_category_id:
                continue

            # Prepare relationship data
            relationship_data = {
                "fields": {
                    "Bill_ID": bill_id,
                    "PolicyCategory_ID": policy_category_id,
                    "Confidence_Score": 0.8,  # Medium confidence for automated migration
                    "Is_Manual": False,
                    "Source": "T129_migration",
                    "Created_At": datetime.now().isoformat(),
                    "Updated_At": datetime.now().isoformat(),
                    "Notes": f"Migrated from Bills.Category '{bill_category}' to PolicyCategory '{policy_mapping.get('title_ja', 'Unknown')}'",
                }
            }

            relationships_to_create.append(relationship_data)

        print(f"   📊 Relationships to create: {len(relationships_to_create)}")

        if not relationships_to_create:
            print("   ⚠️  No relationships to create")
            return True

        # Show preview
        print("   🔍 Sample relationships:")
        for i, rel in enumerate(relationships_to_create[:3]):
            fields = rel["fields"]
            print(
                f"     {i + 1}. Bill: {fields['Bill_ID']} → PolicyCategory: {fields['PolicyCategory_ID']}"
            )
            print(f"        Notes: {fields['Notes']}")

        if dry_run:
            print("   ⚠️  DRY RUN - No actual records created")
            return True

        # Create relationships in batches
        print("   🚀 Creating relationships in batches...")
        created_count = 0
        failed_count = 0

        # Process in batches of 10 (Airtable limit)
        for i in range(0, len(relationships_to_create), 10):
            batch = relationships_to_create[i : i + 10]

            batch_data = {"records": batch}

            try:
                url = f"{self.base_url}/Bills_PolicyCategories"
                async with self.session.post(
                    url, headers=self.headers, json=batch_data
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        created_records = response_data.get("records", [])
                        created_count += len(created_records)
                        print(
                            f"   ✅ Batch {i // 10 + 1}: Created {len(created_records)} relationships"
                        )
                    else:
                        error_data = await response.json()
                        print(f"   ❌ Batch {i // 10 + 1} failed: {response.status}")
                        print(f"      Error: {error_data}")
                        failed_count += len(batch)

                # Rate limiting between batches
                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"   ❌ Batch {i // 10 + 1} error: {e}")
                failed_count += len(batch)

        print("\n📊 Migration results:")
        print(f"   Created: {created_count} relationships")
        print(f"   Failed: {failed_count} relationships")
        print(
            f"   Success rate: {(created_count / (created_count + failed_count)) * 100:.1f}%"
        )

        return created_count > 0

    async def verify_migration(self):
        """Verify the migration was successful."""
        print("\n🔍 Verifying migration results...")

        # Get all relationships
        relationships_url = f"{self.base_url}/Bills_PolicyCategories"
        all_relationships = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with self.session.get(
                relationships_url, headers=self.headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_relationships.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Failed to fetch relationships: {response.status}")
                    return False

        print(f"   ✅ Found {len(all_relationships)} total relationships")

        # Analyze relationships
        source_counts = {}
        confidence_stats = {"high": 0, "medium": 0, "low": 0}

        for rel in all_relationships:
            fields = rel.get("fields", {})
            source = fields.get("Source", "unknown")
            confidence = fields.get("Confidence_Score", 0.0)

            source_counts[source] = source_counts.get(source, 0) + 1

            if confidence >= 0.9:
                confidence_stats["high"] += 1
            elif confidence >= 0.7:
                confidence_stats["medium"] += 1
            else:
                confidence_stats["low"] += 1

        print("   📊 Relationships by source:")
        for source, count in source_counts.items():
            print(f"     {source}: {count}")

        print("   📊 Confidence distribution:")
        for level, count in confidence_stats.items():
            print(f"     {level}: {count}")

        # Check if T129 migration was successful
        t129_count = source_counts.get("T129_migration", 0)
        expected_count = len(
            [b for b in self.bills_data if b.get("fields", {}).get("Category")]
        )

        print("\n🎯 T129 Migration verification:")
        print(f"   Expected relationships: {expected_count}")
        print(f"   T129 relationships created: {t129_count}")
        print(
            f"   Success rate: {(t129_count / expected_count) * 100:.1f}%"
            if expected_count > 0
            else "N/A"
        )

        return t129_count > 0

    async def run_migration(self, dry_run=True):
        """Run the complete migration process."""
        print("🚀 Starting T129.3 Bills-PolicyCategory Migration")
        print("=" * 60)

        # Step 1: Load mapping data
        if not await self.load_mapping_data():
            return False

        # Step 2: Fetch bills data
        if not await self.fetch_bills_data():
            return False

        # Step 3: Check target table
        if not await self.check_bills_policy_categories_table():
            return False

        # Step 4: Create relationships
        if not await self.create_policy_category_relationships(dry_run=dry_run):
            return False

        # Step 5: Verify migration (only if not dry run)
        if not dry_run:
            if not await self.verify_migration():
                return False

        print(
            f"\n✅ T129.3 Migration {'simulation' if dry_run else 'execution'} completed successfully!"
        )

        if dry_run:
            print("\n🎯 To run actual migration:")
            print("   python3 migrate_bills_to_policy_categories.py --execute")

        return True


async def main():
    """Main migration execution."""

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables are required")
        return 1

    # Check command line arguments
    import sys

    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("🧪 Running in DRY RUN mode - no actual records will be created")
        print("   Add --execute flag to run actual migration")
        print()

    async with BillsPolicyCategoryMigrator() as migrator:
        success = await migrator.run_migration(dry_run=dry_run)
        return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
