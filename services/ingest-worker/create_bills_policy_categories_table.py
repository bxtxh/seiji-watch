#!/usr/bin/env python3
"""
EPIC 16 T127 - Create Bills_PolicyCategories relationship table in Airtable

This script creates the intermediate table for managing Bills ↔ PolicyCategory relationships,
replacing the vulnerable string matching approach with a proper relational system.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "shared" / "src"))

# Direct import to avoid SQLAlchemy dependencies
sys.path.append(str(project_root / "shared" / "src" / "shared" / "clients"))
import logging

from airtable import AirtableClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_bills_policy_categories_table():
    """
    Create Bills_PolicyCategories table in Airtable for EPIC 16.

    Note: This script assumes the table structure will be created manually in Airtable UI
    with the following fields:

    Fields:
    - Bill_ID (Single line text) - Bill identifier for reference
    - PolicyCategory_ID (Single line text) - PolicyCategory identifier
    - Bill (Link to Bills 法案) - Actual relationship to Bills table
    - PolicyCategory (Link to IssueCategories) - Actual relationship to IssueCategories table
    - Confidence_Score (Number, decimal) - Relationship confidence (0.0-1.0)
    - Is_Manual (Checkbox) - Whether manually created vs auto-generated
    - Source (Single select: auto_migration, llm_analysis, manual_curation) - Origin of relationship
    - Created_At (Date) - Creation timestamp
    - Updated_At (Date) - Last update timestamp
    """

    try:
        # Initialize Airtable client
        client = AirtableClient()

        # Test connection
        health_ok = await client.health_check()
        if not health_ok:
            logger.error("❌ Airtable connection failed. Check PAT and base ID.")
            return False

        logger.info("✅ Airtable connection successful")

        # Check if Bills_PolicyCategories table already exists by trying to list records
        try:
            test_records = await client.list_bill_policy_category_relationships(
                max_records=1
            )
            logger.info("✅ Bills_PolicyCategories table already exists")
            logger.info(f"Current record count: {len(test_records)}")
            return True

        except Exception as e:
            if "NOT_FOUND" in str(e) or "Table not found" in str(e):
                logger.warning("⚠️  Bills_PolicyCategories table does not exist")
                logger.info(
                    "📋 Please create the table manually in Airtable with the following structure:"
                )
                print_table_schema()
                return False
            else:
                logger.error(f"❌ Error checking table: {e}")
                return False

    except Exception as e:
        logger.error(f"❌ Failed to create/check Bills_PolicyCategories table: {e}")
        return False


def print_table_schema():
    """Print the required table schema for manual creation."""

    schema = """
📋 AIRTABLE TABLE CREATION INSTRUCTIONS
=====================================

Table Name: Bills_PolicyCategories

FIELDS TO CREATE:
1. Bill_ID
   - Type: Single line text
   - Description: Bill identifier for reference

2. PolicyCategory_ID
   - Type: Single line text
   - Description: PolicyCategory identifier

3. Bill
   - Type: Link to another record
   - Linked Table: Bills (法案)
   - Description: Link to actual Bill record

4. PolicyCategory
   - Type: Link to another record
   - Linked Table: IssueCategories
   - Description: Link to actual PolicyCategory record

5. Confidence_Score
   - Type: Number
   - Format: Decimal (0.0-1.0)
   - Description: Relationship confidence score

6. Is_Manual
   - Type: Checkbox
   - Description: Whether manually created vs auto-generated

7. Source
   - Type: Single select
   - Options: auto_migration, llm_analysis, manual_curation
   - Description: Origin of relationship

8. Created_At
   - Type: Date
   - Include time: Yes
   - Description: Creation timestamp

9. Updated_At
   - Type: Date
   - Include time: Yes
   - Description: Last update timestamp

AFTER CREATING THE TABLE:
- Run this script again to verify the table structure
- Proceed with T128 (API endpoints) and T129 (data migration)
"""

    print(schema)


async def verify_related_tables():
    """Verify that required tables (Bills, IssueCategories) exist."""

    client = AirtableClient()

    try:
        # Check Bills table
        bills = await client.list_bills(max_records=1)
        logger.info(f"✅ Bills table found with {len(bills)} records (showing first 1)")

        # Check IssueCategories table
        categories = await client.list_issue_categories(max_records=1)
        logger.info(
            f"✅ IssueCategories table found with {len(categories)} records (showing first 1)"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Error verifying related tables: {e}")
        return False


async def main():
    """Main execution function."""

    logger.info("🚀 EPIC 16 T127 - Bills_PolicyCategories Table Creation")
    logger.info("=" * 60)

    # Verify related tables exist first
    logger.info("1. Verifying related tables...")
    if not await verify_related_tables():
        logger.error("❌ Required tables not found. Cannot proceed.")
        return 1

    # Create/verify Bills_PolicyCategories table
    logger.info("2. Creating/verifying Bills_PolicyCategories table...")
    success = await create_bills_policy_categories_table()

    if success:
        logger.info("✅ T127 completed successfully!")
        logger.info("📋 Next steps:")
        logger.info("   - Proceed with T128 (API endpoints)")
        logger.info("   - Proceed with T129 (data migration)")
        return 0
    else:
        logger.error("❌ T127 failed. Please create the table manually and try again.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
