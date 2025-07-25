#!/usr/bin/env python3
"""
Test Airtable connection and table structure
"""

import asyncio
import sys
from pathlib import Path

from shared.clients.airtable import AirtableClient

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))


async def test_airtable_connection():
    """Test Airtable connection and check table structure"""

    try:
        airtable = AirtableClient()
        print("✅ Airtable client initialized successfully")

        # Test Bills table
        print("\n📋 Testing Bills table...")
        bills = await airtable.list_bills()
        print(f"Current bills count: {len(bills.get('records', []))}")

        if bills.get("records"):
            print("Sample bill fields:", list(bills["records"][0]["fields"].keys()))

        # Test Votes table
        print("\n🗳️ Testing Votes table...")
        votes = await airtable.list_votes()
        print(f"Current votes count: {len(votes.get('records', []))}")

        if votes.get("records"):
            print("Sample vote fields:", list(votes["records"][0]["fields"].keys()))

        return True

    except Exception as e:
        print(f"❌ Airtable connection test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_airtable_connection())
