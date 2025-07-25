#!/usr/bin/env python3
"""
Analyze Members table in Airtable for:
1. Reality check of records 1-7 (real vs synthetic politicians)
2. Name_Kana field completeness analysis
"""

import asyncio
import json
import sys
from collections import Counter
from typing import Any

from dotenv import load_dotenv

from shared.clients.airtable import AirtableClient

# Add the shared directory to the path
sys.path.append("/Users/shogen/seiji-watch/shared/src")

# Load environment variables
load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def fetch_all_members(client: AirtableClient) -> list[dict[str, Any]]:
    """Fetch all records from the Members table."""
    all_records = []

    try:
        # First, get initial batch
        response = await client.list_members(max_records=100)
        all_records.extend(response)

        # For now, let's limit to first 100 records for analysis
        # In production, we'd need to implement pagination with offset
        return all_records

    except Exception as e:
        print(f"Error fetching members: {e}")
        return []


def analyze_first_seven_records(records: list[dict[str, Any]]) -> None:
    """Analyze the first 7 records for reality check."""
    print("=== REALITY CHECK: First 7 Records Analysis ===")
    print()

    if len(records) < 7:
        print(f"Warning: Only {len(records)} records found, expected at least 7")
        print()

    for i, record in enumerate(records[:7], 1):
        fields = record.get("fields", {})

        print(f"Record {i}:")
        print(f"  Name: {fields.get('Name', 'N/A')}")
        print(f"  Name_Kana: {fields.get('Name_Kana', 'N/A')}")
        print(f"  Party: {fields.get('Party', 'N/A')}")
        print(f"  House: {fields.get('House', 'N/A')}")
        print(f"  Prefecture: {fields.get('Prefecture', 'N/A')}")
        print(f"  District: {fields.get('District', 'N/A')}")
        print(f"  Election_Type: {fields.get('Election_Type', 'N/A')}")
        print(f"  Term_Start: {fields.get('Term_Start', 'N/A')}")
        print(f"  Term_End: {fields.get('Term_End', 'N/A')}")
        print(f"  Status: {fields.get('Status', 'N/A')}")
        print()


def analyze_name_kana_completeness(records: list[dict[str, Any]]) -> None:
    """Analyze Name_Kana field completeness."""
    print("=== NAME_KANA COMPLETENESS ANALYSIS ===")
    print()

    total_records = len(records)
    missing_kana = []
    present_kana = []

    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name", "N/A")
        name_kana = fields.get("Name_Kana", "")

        if not name_kana or name_kana.strip() == "":
            missing_kana.append(name)
        else:
            present_kana.append((name, name_kana))

    missing_count = len(missing_kana)
    present_count = len(present_kana)

    print(f"Total records: {total_records}")
    print(
        f"Records with Name_Kana: {present_count} ({present_count/total_records*100:.1f}%)"
    )
    print(
        f"Records missing Name_Kana: {missing_count} ({missing_count/total_records*100:.1f}%)"
    )
    print()

    if missing_kana:
        print("Examples of names missing kana readings:")
        for i, name in enumerate(missing_kana[:10], 1):  # Show first 10
            print(f"  {i}. {name}")

        if len(missing_kana) > 10:
            print(f"  ... and {len(missing_kana) - 10} more")
        print()

    if present_kana:
        print("Examples of names with kana readings:")
        for i, (name, kana) in enumerate(present_kana[:5], 1):  # Show first 5
            print(f"  {i}. {name} → {kana}")
        print()


def analyze_data_patterns(records: list[dict[str, Any]]) -> None:
    """Analyze patterns that might indicate real vs synthetic data."""
    print("=== DATA PATTERN ANALYSIS ===")
    print()

    # Analyze party distribution
    parties = []
    houses = []
    prefectures = []
    election_types = []

    for record in records:
        fields = record.get("fields", {})
        party = fields.get("Party", "")
        house = fields.get("House", "")
        prefecture = fields.get("Prefecture", "")
        election_type = fields.get("Election_Type", "")

        if party:
            parties.append(party)
        if house:
            houses.append(house)
        if prefecture:
            prefectures.append(prefecture)
        if election_type:
            election_types.append(election_type)

    print("Party distribution:")
    party_counts = Counter(parties)
    for party, count in party_counts.most_common():
        print(f"  {party}: {count}")
    print()

    print("House distribution:")
    house_counts = Counter(houses)
    for house, count in house_counts.most_common():
        print(f"  {house}: {count}")
    print()

    print("Prefecture distribution (top 10):")
    prefecture_counts = Counter(prefectures)
    for prefecture, count in prefecture_counts.most_common(10):
        print(f"  {prefecture}: {count}")
    print()

    print("Election type distribution:")
    election_type_counts = Counter(election_types)
    for election_type, count in election_type_counts.most_common():
        print(f"  {election_type}: {count}")
    print()


def suggest_kana_strategy(records: list[dict[str, Any]]) -> None:
    """Suggest strategies for filling missing Name_Kana data."""
    print("=== SUGGESTED STRATEGIES FOR FILLING MISSING NAME_KANA ===")
    print()

    print("1. **Automated Kana Generation**:")
    print("   - Use libraries like 'pykakasi' or 'cutlet' for kanji→kana conversion")
    print("   - Install: python3 -m pip install pykakasi")
    print("   - Note: May not be 100% accurate for proper names")
    print()

    print("2. **Manual Verification Database**:")
    print("   - Create a mapping of common politician names to verified kana")
    print("   - Cross-reference with official Diet member lists")
    print("   - Websites like 国会議員白書 often have kana readings")
    print()

    print("3. **Web Scraping Strategy**:")
    print("   - Scrape official Diet member pages")
    print("   - Many official pages include furigana readings")
    print("   - Example: https://www.sangiin.go.jp/japanese/joho1/kousei/giin/profile/")
    print()

    print("4. **LLM-Assisted Generation**:")
    print("   - Use GPT-4 or Claude to generate kana readings")
    print(
        "   - Prompt: 'Provide the hiragana reading for this Japanese politician name: [name]'"
    )
    print("   - Verify against known databases")
    print()

    print("5. **Hybrid Approach (Recommended)**:")
    print("   - Start with automated kana generation for bulk processing")
    print("   - Manually verify and correct high-profile politicians")
    print("   - Use web scraping for official verification")
    print("   - Implement quality checks and validation")
    print()


async def main():
    """Main analysis function."""
    print("Fetching Members table data from Airtable...")

    # Create Airtable client
    try:
        client = AirtableClient()
        print("✅ Airtable client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Airtable client: {e}")
        return

    # Fetch members data
    records = await fetch_all_members(client)

    if not records:
        print("No records found or error occurred.")
        return

    print(f"Successfully fetched {len(records)} records from Members table.")
    print("=" * 60)
    print()

    # Reality check of first 7 records
    analyze_first_seven_records(records)

    # Name_Kana completeness analysis
    analyze_name_kana_completeness(records)

    # Data pattern analysis
    analyze_data_patterns(records)

    # Strategy suggestions
    suggest_kana_strategy(records)

    # Save raw data for further analysis
    output_file = f"members_analysis_result_{int(__import__('time').time())}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Raw data saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
