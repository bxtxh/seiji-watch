#!/usr/bin/env python3
"""
Seed Issue Categories to Airtable
Idempotent script to populate IssueCategories table with CAP-based data.
"""

import asyncio
import csv
import logging
import os
import sys
from pathlib import Path

from shared.clients.airtable import AirtableClient

# Add shared package to path
sys.path.append(str(Path(__file__).parent.parent / "shared" / "src"))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IssueCategorySeedManager:
    """Manager for seeding issue categories to Airtable."""

    def __init__(self, airtable_client: AirtableClient):
        self.client = airtable_client
        self.l1_categories: list[dict] = []
        self.l2_categories: list[dict] = []
        self.existing_categories: dict[str, str] = {}  # cap_code -> record_id

    async def load_csv_data(self, script_dir: Path) -> None:
        """Load L1 and L2 data from CSV files."""
        data_dir = script_dir.parent / "data" / "cap_mapping"

        # Load L1 data
        l1_file = data_dir / "l1_major_topics.csv"
        if not l1_file.exists():
            raise FileNotFoundError(f"L1 file not found: {l1_file}")

        with open(l1_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.l1_categories = list(reader)

        # Load L2 data
        l2_file = data_dir / "l2_sub_topics.csv"
        if not l2_file.exists():
            raise FileNotFoundError(f"L2 file not found: {l2_file}")

        with open(l2_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.l2_categories = list(reader)

        logger.info(
            f"📊 Loaded {len(self.l1_categories)} L1 and {len(self.l2_categories)} L2 categories")

    async def load_existing_categories(self) -> None:
        """Load existing categories from Airtable to enable idempotent operation."""
        try:
            existing = await self.client.list_issue_categories(max_records=1000)
            self.existing_categories = {}

            for record in existing:
                fields = record.get("fields", {})
                cap_code = fields.get("CAP_Code")
                if cap_code:
                    self.existing_categories[cap_code] = record["id"]

            logger.info(
                f"🔍 Found {len(self.existing_categories)} existing categories in Airtable")

        except Exception as e:
            logger.warning(
                f"⚠️  Could not load existing categories (table may not exist): {e}")
            self.existing_categories = {}

    async def seed_l1_categories(self) -> dict[str, str]:
        """Seed L1 categories and return mapping of cap_code -> record_id."""
        l1_mapping = {}
        created_count = 0
        updated_count = 0

        logger.info("🌱 Seeding L1 categories...")

        for category in self.l1_categories:
            cap_code = category["cap_code"]

            category_data = {
                "cap_code": cap_code,
                "layer": "L1",
                "title_ja": category["title_ja"],
                "title_en": category["title_en"],
                "summary_150ja": "",
                "is_seed": True
            }

            try:
                if cap_code in self.existing_categories:
                    # Update existing category
                    record_id = self.existing_categories[cap_code]
                    await self.client.update_issue_category(record_id, {
                        "Title_JA": category_data["title_ja"],
                        "Title_EN": category_data["title_en"],
                        "Is_Seed": True
                    })
                    l1_mapping[cap_code] = record_id
                    updated_count += 1
                    logger.debug(
                        f"✏️  Updated L1 category: {cap_code} - {category['title_ja']}")
                else:
                    # Create new category
                    response = await self.client.create_issue_category(category_data)
                    record_id = response["id"]
                    l1_mapping[cap_code] = record_id
                    created_count += 1
                    logger.debug(
                        f"✨ Created L1 category: {cap_code} - {category['title_ja']}")

                # Small delay to respect rate limits
                await asyncio.sleep(0.25)

            except Exception as e:
                logger.error(f"❌ Failed to process L1 category {cap_code}: {e}")
                continue

        logger.info(
            f"✅ L1 seeding complete: {created_count} created, {updated_count} updated")
        return l1_mapping

    async def seed_l2_categories(self, l1_mapping: dict[str, str]) -> dict[str, str]:
        """Seed L2 categories with parent relationships."""
        l2_mapping = {}
        created_count = 0
        updated_count = 0
        orphaned_count = 0

        logger.info("🌱 Seeding L2 categories...")

        for category in self.l2_categories:
            cap_code = category["cap_code"]
            parent_cap_code = category["parent_cap_code"]

            # Check if parent exists
            if parent_cap_code not in l1_mapping:
                logger.warning(
                    f"⚠️  Orphaned L2 category (parent {parent_cap_code} not found): {cap_code}")
                orphaned_count += 1
                continue

            category_data = {
                "cap_code": cap_code,
                "layer": "L2",
                "title_ja": category["title_ja"],
                "title_en": category["title_en"],
                "summary_150ja": "",
                "parent_category_id": l1_mapping[parent_cap_code],
                "is_seed": True
            }

            try:
                if cap_code in self.existing_categories:
                    # Update existing category
                    record_id = self.existing_categories[cap_code]
                    await self.client.update_issue_category(record_id, {
                        "Title_JA": category_data["title_ja"],
                        "Title_EN": category_data["title_en"],
                        "Parent_Category": [l1_mapping[parent_cap_code]],
                        "Is_Seed": True
                    })
                    l2_mapping[cap_code] = record_id
                    updated_count += 1
                    logger.debug(
                        f"✏️  Updated L2 category: {cap_code} - {category['title_ja']}")
                else:
                    # Create new category
                    response = await self.client.create_issue_category(category_data)
                    record_id = response["id"]
                    l2_mapping[cap_code] = record_id
                    created_count += 1
                    logger.debug(
                        f"✨ Created L2 category: {cap_code} - {category['title_ja']}")

                # Small delay to respect rate limits
                await asyncio.sleep(0.25)

            except Exception as e:
                logger.error(f"❌ Failed to process L2 category {cap_code}: {e}")
                continue

        if orphaned_count > 0:
            logger.warning(f"⚠️  {orphaned_count} L2 categories were orphaned")

        logger.info(
            f"✅ L2 seeding complete: {created_count} created, {updated_count} updated")
        return l2_mapping

    async def validate_relationships(
            self, l1_mapping: dict[str, str], l2_mapping: dict[str, str]) -> None:
        """Validate parent-child relationships in Airtable."""
        logger.info("🔍 Validating relationships...")

        # Get current state from Airtable
        try:
            all_categories = await self.client.list_issue_categories(max_records=1000)

            validation_errors = []
            l1_children_count = {}

            for record in all_categories:
                fields = record.get("fields", {})
                layer = fields.get("Layer")
                cap_code = fields.get("CAP_Code")
                parent_category = fields.get("Parent_Category", [])

                if layer == "L1":
                    l1_children_count[cap_code] = 0
                elif layer == "L2":
                    if not parent_category:
                        validation_errors.append(
                            f"L2 category {cap_code} has no parent")
                    else:
                        # Find parent cap_code
                        parent_id = parent_category[0]
                        parent_cap = None
                        for parent_record in all_categories:
                            if parent_record["id"] == parent_id:
                                parent_cap = parent_record.get(
                                    "fields", {}).get("CAP_Code")
                                break

                        if parent_cap:
                            l1_children_count[parent_cap] = l1_children_count.get(
                                parent_cap, 0) + 1

            if validation_errors:
                logger.warning("⚠️  Validation issues found:")
                for error in validation_errors:
                    logger.warning(f"   - {error}")
            else:
                logger.info("✅ All relationships validated successfully")

            # Show hierarchy statistics
            logger.info("📊 Hierarchy statistics:")
            for l1_cap, child_count in sorted(
                l1_children_count.items(), key=lambda x: int(
                    x[0])):
                logger.info(f"   L1-{l1_cap}: {child_count} children")

        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")

    async def cleanup_non_seed_data(self, dry_run: bool = True) -> None:
        """Remove non-seed categories (optional cleanup)."""
        if dry_run:
            logger.info("🧹 Dry run: Checking for non-seed categories...")
        else:
            logger.info("🧹 Cleaning up non-seed categories...")

        try:
            all_categories = await self.client.list_issue_categories(max_records=1000)
            non_seed_categories = []

            for record in all_categories:
                fields = record.get("fields", {})
                is_seed = fields.get("Is_Seed", False)
                if not is_seed:
                    non_seed_categories.append({
                        "id": record["id"],
                        "cap_code": fields.get("CAP_Code", "unknown"),
                        "title": fields.get("Title_JA", "unknown")
                    })

            if non_seed_categories:
                logger.info(f"🔍 Found {len(non_seed_categories)} non-seed categories:")
                for cat in non_seed_categories:
                    logger.info(f"   - {cat['cap_code']}: {cat['title']}")

                if not dry_run:
                    # Actually delete (not implemented for safety)
                    logger.warning("⚠️  Cleanup deletion not implemented for safety")
            else:
                logger.info("✅ No non-seed categories found")

        except Exception as e:
            logger.error(f"❌ Cleanup check failed: {e}")


async def main():
    """Main seeding function."""
    script_dir = Path(__file__).parent

    # Check environment variables
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not api_key or not base_id:
        logger.error("❌ Missing required environment variables:")
        logger.error("   AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")
        sys.exit(1)

    try:
        # Initialize Airtable client
        logger.info("🔌 Connecting to Airtable...")
        client = AirtableClient(api_key=api_key, base_id=base_id)

        # Test connection
        if not await client.health_check():
            logger.error("❌ Airtable connection failed")
            sys.exit(1)

        logger.info("✅ Airtable connection successful")

        # Initialize seed manager
        seed_manager = IssueCategorySeedManager(client)

        # Load CSV data
        await seed_manager.load_csv_data(script_dir)

        # Load existing categories for idempotent operation
        await seed_manager.load_existing_categories()

        # Seed L1 categories first
        l1_mapping = await seed_manager.seed_l1_categories()

        # Seed L2 categories with parent relationships
        l2_mapping = await seed_manager.seed_l2_categories(l1_mapping)

        # Validate relationships
        await seed_manager.validate_relationships(l1_mapping, l2_mapping)

        # Optional cleanup check
        await seed_manager.cleanup_non_seed_data(dry_run=True)

        # Summary
        total_seeded = len(l1_mapping) + len(l2_mapping)
        logger.info("🎉 Seeding complete!")
        logger.info(f"   L1 categories: {len(l1_mapping)}")
        logger.info(f"   L2 categories: {len(l2_mapping)}")
        logger.info(f"   Total seeded: {total_seeded}")

    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
