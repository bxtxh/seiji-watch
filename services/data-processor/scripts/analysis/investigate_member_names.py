#!/usr/bin/env python3
"""
Investigation script for Members table to identify names with trailing numbers.
"""

import json
import os
import re
from collections import defaultdict
from typing import Any

import requests


def get_airtable_records(
    base_id: str, table_name: str, pat: str
) -> list[dict[str, Any]]:
    """Fetch all records from Airtable table."""
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    all_records = []
    offset = None

    while True:
        params = {}
        if offset:
            params["offset"] = offset

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            print(f"Response: {response.text}")
            return []

        data = response.json()
        all_records.extend(data.get("records", []))

        offset = data.get("offset")
        if not offset:
            break

    return all_records


def analyze_member_names(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze member names for trailing numbers."""

    # Pattern to match names with trailing numbers
    # This will match Japanese names followed by one or more digits
    trailing_number_pattern = re.compile(r"^(.+?)(\d+)$")

    results = {
        "total_records": len(records),
        "records_with_trailing_numbers": [],
        "clean_records": [],
        "pattern_analysis": defaultdict(int),
        "number_distribution": defaultdict(int),
    }

    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name", "").strip()

        if not name:
            continue

        match = trailing_number_pattern.match(name)

        if match:
            base_name = match.group(1)
            number = match.group(2)

            results["records_with_trailing_numbers"].append(
                {
                    "record_id": record["id"],
                    "full_name": name,
                    "base_name": base_name,
                    "trailing_number": number,
                    "fields": fields,
                }
            )

            # Track patterns
            results["pattern_analysis"][f"ends_with_{number}"] += 1
            results["number_distribution"][number] += 1

        else:
            results["clean_records"].append(
                {"record_id": record["id"], "name": name, "fields": fields}
            )

    return results


def print_analysis_report(analysis: dict[str, Any]):
    """Print detailed analysis report."""

    print("=" * 80)
    print("MEMBERS TABLE NAME ANALYSIS REPORT")
    print("=" * 80)

    print(f"\nTOTAL RECORDS: {analysis['total_records']}")
    print(
        f"RECORDS WITH TRAILING NUMBERS: {len(analysis['records_with_trailing_numbers'])}"
    )
    print(f"CLEAN RECORDS: {len(analysis['clean_records'])}")

    if analysis["records_with_trailing_numbers"]:
        print(
            f"\nPERCENTAGE AFFECTED: {len(analysis['records_with_trailing_numbers']) / analysis['total_records'] * 100:.1f}%"
        )

        print("\n" + "=" * 40)
        print("EXAMPLES OF PROBLEMATIC NAMES")
        print("=" * 40)

        # Show first 10 examples
        for i, record in enumerate(analysis["records_with_trailing_numbers"][:10]):
            print(
                f"{i + 1:2d}. '{record['full_name']}' -> '{record['base_name']}' (number: {record['trailing_number']})"
            )

        if len(analysis["records_with_trailing_numbers"]) > 10:
            print(
                f"    ... and {len(analysis['records_with_trailing_numbers']) - 10} more"
            )

        print("\n" + "=" * 40)
        print("NUMBER DISTRIBUTION")
        print("=" * 40)

        for number, count in sorted(analysis["number_distribution"].items()):
            print(f"Number '{number}': {count} occurrences")

        print("\n" + "=" * 40)
        print("PATTERN ANALYSIS")
        print("=" * 40)

        for pattern, count in sorted(analysis["pattern_analysis"].items()):
            print(f"{pattern}: {count} records")

        print("\n" + "=" * 40)
        print("DETAILED RECORD ANALYSIS")
        print("=" * 40)

        # Group by base name to identify potential duplicates
        base_name_groups = defaultdict(list)
        for record in analysis["records_with_trailing_numbers"]:
            base_name_groups[record["base_name"]].append(record)

        print(f"\nUNIQUE BASE NAMES: {len(base_name_groups)}")

        # Show potential duplicates
        duplicates = {k: v for k, v in base_name_groups.items() if len(v) > 1}
        if duplicates:
            print(f"POTENTIAL DUPLICATES (same base name): {len(duplicates)}")
            for base_name, records in list(duplicates.items())[:5]:
                print(f"  '{base_name}' appears as:")
                for record in records:
                    print(f"    - '{record['full_name']}'")
        else:
            print("NO APPARENT DUPLICATES FOUND")

    else:
        print("\n✅ NO RECORDS WITH TRAILING NUMBERS FOUND!")

    print("\n" + "=" * 40)
    print("CLEANUP RECOMMENDATIONS")
    print("=" * 40)

    if analysis["records_with_trailing_numbers"]:
        print("RECOMMENDED ACTIONS:")
        print("1. Review examples above to confirm pattern")
        print("2. Create backup of current data")
        print("3. Implement bulk update to remove trailing numbers")
        print("4. Check for actual duplicates after cleanup")
        print("5. Verify no legitimate numbers are removed")

        print("\nSUGGESTED CLEANUP QUERY:")
        print(
            "UPDATE records SET Name = REGEX_REPLACE(Name, r'(\\d+)$', '') WHERE Name REGEXP '\\d+$'"
        )

    else:
        print("✅ No cleanup needed - all names are clean!")


def main():
    """Main investigation function."""

    # Load environment variables
    airtable_pat = os.getenv("AIRTABLE_PAT")
    airtable_base_id = os.getenv("AIRTABLE_BASE_ID")

    if not airtable_pat or not airtable_base_id:
        print("Error: Missing AIRTABLE_PAT or AIRTABLE_BASE_ID environment variables")
        print("Please ensure these are set in your environment or .env.local file")
        return

    table_name = "Members (議員)"

    print("Fetching data from Airtable...")
    print(f"Base ID: {airtable_base_id}")
    print(f"Table: {table_name}")
    print()

    # Fetch data
    records = get_airtable_records(airtable_base_id, table_name, airtable_pat)

    if not records:
        print("No records found or error occurred")
        return

    # Analyze data
    analysis = analyze_member_names(records)

    # Print report
    print_analysis_report(analysis)

    # Save detailed results to file
    output_file = f"member_name_analysis_{analysis['total_records']}_records.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
