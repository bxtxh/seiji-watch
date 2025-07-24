#!/usr/bin/env python3
"""
CAP Mapping Data Validation Script
Validates L1 and L2 data integrity and relationships.
"""

import csv
import sys
from pathlib import Path


def load_csv_data(file_path: Path) -> list[dict]:
    """Load CSV data into list of dictionaries."""
    with open(file_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def validate_l1_data(l1_data: list[dict]) -> list[str]:
    """Validate L1 data integrity."""
    errors = []
    cap_codes = set()

    for row in l1_data:
        cap_code = row['cap_code']
        layer = row['layer']
        title_en = row['title_en']
        title_ja = row['title_ja']

        # Check required fields
        if not cap_code:
            errors.append(f"Missing cap_code in row: {row}")
        if not title_en:
            errors.append(f"Missing title_en for cap_code {cap_code}")
        if not title_ja:
            errors.append(f"Missing title_ja for cap_code {cap_code}")
        if layer != 'L1':
            errors.append(f"Invalid layer '{layer}' for L1 data, cap_code {cap_code}")

        # Check for duplicates
        if cap_code in cap_codes:
            errors.append(f"Duplicate cap_code: {cap_code}")
        cap_codes.add(cap_code)

    return errors

def validate_l2_data(l2_data: list[dict], l1_cap_codes: set[str]) -> list[str]:
    """Validate L2 data integrity and parent relationships."""
    errors = []
    cap_codes = set()

    for row in l2_data:
        cap_code = row['cap_code']
        layer = row['layer']
        parent_cap_code = row['parent_cap_code']
        title_en = row['title_en']
        title_ja = row['title_ja']

        # Check required fields
        if not cap_code:
            errors.append(f"Missing cap_code in row: {row}")
        if not parent_cap_code:
            errors.append(f"Missing parent_cap_code for cap_code {cap_code}")
        if not title_en:
            errors.append(f"Missing title_en for cap_code {cap_code}")
        if not title_ja:
            errors.append(f"Missing title_ja for cap_code {cap_code}")
        if layer != 'L2':
            errors.append(f"Invalid layer '{layer}' for L2 data, cap_code {cap_code}")

        # Check parent relationship
        if parent_cap_code not in l1_cap_codes:
            errors.append(f"Invalid parent_cap_code '{parent_cap_code}' for cap_code {cap_code}")

        # Check for duplicates
        if cap_code in cap_codes:
            errors.append(f"Duplicate cap_code: {cap_code}")
        cap_codes.add(cap_code)

    return errors

def check_translation_quality(data: list[dict]) -> list[str]:
    """Check translation quality and consistency."""
    warnings = []

    for row in data:
        cap_code = row['cap_code']
        title_ja = row['title_ja']

        # Check for common translation issues
        if not title_ja:
            continue

        # Check for inconsistent terminology
        if 'Health' in row.get('title_en', '') and '保健' not in title_ja and '医療' not in title_ja:
            warnings.append(f"Potential translation inconsistency for {cap_code}: {row['title_en']} -> {title_ja}")

        # Check for overly long translations
        if len(title_ja) > 20:
            warnings.append(f"Long translation for {cap_code}: {title_ja} ({len(title_ja)} chars)")

    return warnings

def main():
    """Main validation function."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data" / "cap_mapping"

    l1_file = data_dir / "l1_major_topics.csv"
    l2_file = data_dir / "l2_sub_topics.csv"

    if not l1_file.exists():
        print(f"❌ L1 file not found: {l1_file}")
        sys.exit(1)

    if not l2_file.exists():
        print(f"❌ L2 file not found: {l2_file}")
        sys.exit(1)

    # Load data
    print("📊 Loading CAP mapping data...")
    l1_data = load_csv_data(l1_file)
    l2_data = load_csv_data(l2_file)

    print(f"   L1 records: {len(l1_data)}")
    print(f"   L2 records: {len(l2_data)}")

    # Validate L1 data
    print("\n🔍 Validating L1 data...")
    l1_errors = validate_l1_data(l1_data)
    l1_cap_codes = {row['cap_code'] for row in l1_data}

    # Validate L2 data
    print("🔍 Validating L2 data...")
    l2_errors = validate_l2_data(l2_data, l1_cap_codes)

    # Check translation quality
    print("🌐 Checking translation quality...")
    l1_warnings = check_translation_quality(l1_data)
    l2_warnings = check_translation_quality(l2_data)

    # Report results
    total_errors = len(l1_errors) + len(l2_errors)
    total_warnings = len(l1_warnings) + len(l2_warnings)

    print("\n📋 Validation Results:")
    print(f"   Errors: {total_errors}")
    print(f"   Warnings: {total_warnings}")

    if l1_errors:
        print("\n❌ L1 Errors:")
        for error in l1_errors:
            print(f"   - {error}")

    if l2_errors:
        print("\n❌ L2 Errors:")
        for error in l2_errors:
            print(f"   - {error}")

    if l1_warnings:
        print("\n⚠️  L1 Warnings:")
        for warning in l1_warnings:
            print(f"   - {warning}")

    if l2_warnings:
        print("\n⚠️  L2 Warnings:")
        for warning in l2_warnings:
            print(f"   - {warning}")

    if total_errors == 0:
        print("\n✅ Data validation passed! Ready for Airtable seeding.")
    else:
        print(f"\n❌ Data validation failed with {total_errors} errors.")
        sys.exit(1)

    # Coverage report
    print("\n📈 Coverage Report:")
    print(f"   L1 categories: {len(l1_cap_codes)}")
    print(f"   L2 categories: {len(l2_data)}")
    print(f"   Avg L2 per L1: {len(l2_data) / len(l1_cap_codes):.1f}")

    # Show parent coverage
    parent_coverage = {}
    for row in l2_data:
        parent = row['parent_cap_code']
        parent_coverage[parent] = parent_coverage.get(parent, 0) + 1

    print(f"   L1 categories with L2 children: {len(parent_coverage)}/{len(l1_cap_codes)}")

    uncovered_l1 = l1_cap_codes - set(parent_coverage.keys())
    if uncovered_l1:
        print(f"   L1 categories without L2 children: {sorted(uncovered_l1)}")

if __name__ == "__main__":
    main()
