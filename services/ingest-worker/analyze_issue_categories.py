#!/usr/bin/env python3
"""Analyze IssueCategories table for T129.2 mapping."""

import asyncio
import json
import os
from collections import defaultdict

import aiohttp

# Load environment variables
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

async def analyze_issue_categories():
    """Analyze the IssueCategories table for Bills category mapping."""

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables are required")
        return

    base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json"
    }

    print("🔍 Analyzing IssueCategories table for T129.2 mapping")
    print("=" * 60)

    # Load Bills analysis results
    try:
        with open("bills_category_analysis_t129.json", encoding='utf-8') as f:
            bills_analysis = json.load(f)
        print("✅ Loaded Bills analysis results from T129.1")
    except FileNotFoundError:
        print("❌ Bills analysis results not found. Please run T129.1 first.")
        return

    bills_categories = bills_analysis.get("category_distribution", {})

    async with aiohttp.ClientSession() as session:

        # First check if IssueCategories table exists
        print("\n📋 Step 1: Checking IssueCategories table access...")

        test_url = f"{base_url}/IssueCategories?maxRecords=1"
        async with session.get(test_url, headers=headers) as response:
            if response.status == 403:
                print("❌ IssueCategories table not accessible")
                print("   This table may not exist or have proper permissions")
                print("   Proceeding with fallback analysis...")

                # Fallback: Create mapping based on Bills categories
                await create_fallback_mapping(bills_categories)
                return
            elif response.status != 200:
                print(f"❌ Failed to access IssueCategories table: {response.status}")
                return

        print("✅ IssueCategories table is accessible")

        # Get all IssueCategories records
        print("\n📋 Step 2: Fetching all IssueCategories records...")
        categories_url = f"{base_url}/IssueCategories"
        all_categories = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(categories_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_categories.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Failed to fetch IssueCategories data: {response.status}")
                    return

        print(f"   ✅ Fetched {len(all_categories)} IssueCategories records")

        # Analyze category structure
        print("\n📊 Step 3: Analyzing IssueCategories structure...")

        # Sample record structure
        sample_record = all_categories[0].get("fields", {}) if all_categories else {}

        print("   📋 Sample IssueCategories record structure:")
        for field_name, field_value in sample_record.items():
            if isinstance(field_value, str) and len(field_value) > 80:
                print(f"   {field_name}: {field_value[:80]}...")
            elif isinstance(field_value, list):
                print(f"   {field_name}: [list with {len(field_value)} items]")
            else:
                print(f"   {field_name}: {field_value}")

        # Analyze by layer
        layers = defaultdict(list)
        for record in all_categories:
            fields = record.get("fields", {})
            layer = fields.get("Layer", "Unknown")
            layers[layer].append(record)

        print("\n   📈 Categories by layer:")
        for layer, records in sorted(layers.items()):
            print(f"   {layer}: {len(records)} categories")

        # Find matching categories for Bills categories
        print("\n🔗 Step 4: Mapping Bills categories to IssueCategories...")

        bills_to_issue_mapping = {}

        for bills_category, count in bills_categories.items():
            if not bills_category:
                continue

            print(f"\n   🔍 Finding matches for '{bills_category}' ({count} bills):")

            # Look for exact matches first
            exact_matches = []
            partial_matches = []

            for record in all_categories:
                fields = record.get("fields", {})
                title_ja = fields.get("Title_JA", "")
                fields.get("Title_EN", "")

                # Check exact match
                if bills_category == title_ja:
                    exact_matches.append(record)
                # Check partial match
                elif (bills_category.lower() in title_ja.lower() or
                      title_ja.lower() in bills_category.lower()):
                    partial_matches.append(record)

            # Report matches
            if exact_matches:
                print(f"   ✅ Exact matches found: {len(exact_matches)}")
                best_match = exact_matches[0]
                bills_to_issue_mapping[bills_category] = {
                    "category_id": best_match.get("id"),
                    "title_ja": best_match.get("fields", {}).get("Title_JA", ""),
                    "title_en": best_match.get("fields", {}).get("Title_EN", ""),
                    "layer": best_match.get("fields", {}).get("Layer", ""),
                    "cap_code": best_match.get("fields", {}).get("CAP_Code", ""),
                    "match_type": "exact",
                    "bills_count": count
                }
                print(f"   → Selected: {best_match.get('fields', {}).get('Title_JA', 'Unknown')}")

            elif partial_matches:
                print(f"   ⚠️  Partial matches found: {len(partial_matches)}")
                for match in partial_matches[:3]:  # Show first 3
                    title = match.get("fields", {}).get("Title_JA", "Unknown")
                    layer = match.get("fields", {}).get("Layer", "Unknown")
                    print(f"     - {title} ({layer})")

                # Use the first partial match
                best_match = partial_matches[0]
                bills_to_issue_mapping[bills_category] = {
                    "category_id": best_match.get("id"),
                    "title_ja": best_match.get("fields", {}).get("Title_JA", ""),
                    "title_en": best_match.get("fields", {}).get("Title_EN", ""),
                    "layer": best_match.get("fields", {}).get("Layer", ""),
                    "cap_code": best_match.get("fields", {}).get("CAP_Code", ""),
                    "match_type": "partial",
                    "bills_count": count
                }
                print(f"   → Selected: {best_match.get('fields', {}).get('Title_JA', 'Unknown')}")

            else:
                print("   ❌ No matches found")
                # Check if it's "その他" - use a generic category
                if bills_category == "その他":
                    bills_to_issue_mapping[bills_category] = {
                        "category_id": "GENERIC_OTHER",
                        "title_ja": "その他",
                        "title_en": "Other",
                        "layer": "L1",
                        "cap_code": "99",
                        "match_type": "fallback",
                        "bills_count": count
                    }
                    print("   → Using fallback category for 'その他'")

        # Summary
        print("\n📊 Step 5: Mapping summary:")
        print(f"   Bills categories to map: {len(bills_categories)}")
        print(f"   Successful mappings: {len(bills_to_issue_mapping)}")
        print(f"   Failed mappings: {len(bills_categories) - len(bills_to_issue_mapping)}")

        # Save results
        results = {
            "bills_categories": bills_categories,
            "issue_categories_total": len(all_categories),
            "issue_categories_by_layer": {layer: len(records) for layer, records in layers.items()},
            "bills_to_issue_mapping": bills_to_issue_mapping,
            "sample_issue_category": {k: str(v)[:100] for k, v in sample_record.items()} if sample_record else None
        }

        output_file = "bills_to_issue_categories_mapping_t129.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Results saved to: {output_file}")
        print("✅ T129.2 Analysis complete!")
        print("\n🎯 Next steps for T129.3:")
        print("   1. Review the mapping results")
        print("   2. Create Bills-PolicyCategory relationship records")
        print("   3. Verify the migration worked correctly")

async def create_fallback_mapping(bills_categories):
    """Create fallback mapping when IssueCategories table is not accessible."""

    print("\n🔄 Creating fallback mapping...")

    # Define fallback IssueCategories based on typical CAP structure
    fallback_categories = {
        "予算・決算": {
            "category_id": "FALLBACK_BUDGET",
            "title_ja": "予算・決算",
            "title_en": "Budget and Finance",
            "layer": "L1",
            "cap_code": "1",
            "match_type": "fallback"
        },
        "税制": {
            "category_id": "FALLBACK_TAX",
            "title_ja": "税制",
            "title_en": "Taxation",
            "layer": "L1",
            "cap_code": "2",
            "match_type": "fallback"
        },
        "社会保障": {
            "category_id": "FALLBACK_SOCIAL",
            "title_ja": "社会保障",
            "title_en": "Social Security",
            "layer": "L1",
            "cap_code": "3",
            "match_type": "fallback"
        },
        "外交・国際": {
            "category_id": "FALLBACK_FOREIGN",
            "title_ja": "外交・国際",
            "title_en": "Foreign Affairs",
            "layer": "L1",
            "cap_code": "19",
            "match_type": "fallback"
        },
        "経済・産業": {
            "category_id": "FALLBACK_ECONOMY",
            "title_ja": "経済・産業",
            "title_en": "Economy and Industry",
            "layer": "L1",
            "cap_code": "4",
            "match_type": "fallback"
        },
        "その他": {
            "category_id": "FALLBACK_OTHER",
            "title_ja": "その他",
            "title_en": "Other",
            "layer": "L1",
            "cap_code": "99",
            "match_type": "fallback"
        }
    }

    # Map Bills categories to fallback categories
    bills_to_issue_mapping = {}

    for bills_category, count in bills_categories.items():
        if bills_category in fallback_categories:
            mapping = fallback_categories[bills_category].copy()
            mapping["bills_count"] = count
            bills_to_issue_mapping[bills_category] = mapping
            print(f"   ✅ Mapped '{bills_category}' ({count} bills) to fallback category")
        else:
            # Use "その他" as fallback
            mapping = fallback_categories["その他"].copy()
            mapping["bills_count"] = count
            bills_to_issue_mapping[bills_category] = mapping
            print(f"   ⚠️  Mapped '{bills_category}' ({count} bills) to fallback 'その他'")

    # Save fallback results
    results = {
        "bills_categories": bills_categories,
        "issue_categories_total": len(fallback_categories),
        "issue_categories_by_layer": {"L1": len(fallback_categories)},
        "bills_to_issue_mapping": bills_to_issue_mapping,
        "is_fallback": True,
        "note": "IssueCategories table not accessible - using fallback mapping"
    }

    output_file = "bills_to_issue_categories_mapping_t129.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Fallback mapping saved to: {output_file}")
    print("✅ T129.2 Fallback analysis complete!")

if __name__ == "__main__":
    asyncio.run(analyze_issue_categories())
