#!/usr/bin/env python3
"""Test Airtable connection directly."""

import os
import sys
import asyncio
from pathlib import Path

# Add shared module to path
project_root = Path(__file__).parent
shared_src = project_root / "shared" / "src"
sys.path.insert(0, str(shared_src))

# Load environment variables
env_file = project_root / "services" / "api-gateway" / ".env.development"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    value = value.split("#")[0].strip()
                    os.environ[key.strip()] = value

async def test_airtable():
    """Test Airtable connection and data retrieval."""
    try:
        from shared.clients.airtable import AirtableClient
        
        # Initialize client
        client = AirtableClient()
        
        print("Testing Airtable connection...")
        print(f"PAT: {'*' * 10 if os.getenv('AIRTABLE_PAT') else 'NOT SET'}")
        print(f"Base ID: {os.getenv('AIRTABLE_BASE_ID', 'NOT SET')}")
        print()
        
        # Test 1: List Bills
        print("1. Fetching Bills...")
        try:
            bills = await client.list_bills(max_records=5)
            print(f"   ✅ Found {len(bills)} bills")
            if bills:
                first_bill = bills[0]
                fields = first_bill.get('fields', {})
                print(f"   First bill: {fields.get('Name', 'No name')[:50]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: List Categories
        print("\n2. Fetching Issue Categories...")
        try:
            categories = await client.get_issue_categories(max_records=5)
            print(f"   ✅ Found {len(categories)} categories")
            if categories:
                first_cat = categories[0]
                fields = first_cat.get('fields', {})
                print(f"   First category: {fields.get('Title_JA', 'No title')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: List Votes
        print("\n3. Fetching Votes...")
        try:
            votes = await client.list_votes(max_records=5)
            print(f"   ✅ Found {len(votes)} votes")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n✅ Airtable connection test complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_airtable())