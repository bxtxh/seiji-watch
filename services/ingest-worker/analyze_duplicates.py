#!/usr/bin/env python3
"""
Detailed analysis of duplicate member names and their distribution.
"""

import json
import re
from collections import defaultdict, Counter


def analyze_duplicates():
    """Analyze the duplicate patterns in detail."""
    
    # Load the analysis data
    with open('member_name_analysis_567_records.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    problematic_records = data['records_with_trailing_numbers']
    
    # Group by base name
    base_name_groups = defaultdict(list)
    for record in problematic_records:
        base_name_groups[record['base_name']].append(record)
    
    print("=" * 80)
    print("DETAILED DUPLICATE ANALYSIS")
    print("=" * 80)
    
    # Analyze group sizes
    group_sizes = Counter(len(group) for group in base_name_groups.values())
    
    print(f"TOTAL BASE NAMES WITH NUMBERS: {len(base_name_groups)}")
    print(f"TOTAL RECORDS WITH NUMBERS: {len(problematic_records)}")
    print()
    
    print("GROUP SIZE DISTRIBUTION:")
    for size, count in sorted(group_sizes.items()):
        print(f"  {size} variants: {count} base names")
    print()
    
    # Show detailed examples of each group size
    print("DETAILED EXAMPLES BY GROUP SIZE:")
    print("-" * 50)
    
    for target_size in sorted(group_sizes.keys()):
        print(f"\nGROUPS WITH {target_size} VARIANTS:")
        examples = [name for name, group in base_name_groups.items() if len(group) == target_size]
        
        for i, base_name in enumerate(examples[:5]):  # Show first 5 examples
            group = base_name_groups[base_name]
            numbers = [record['trailing_number'] for record in group]
            print(f"  {i+1}. '{base_name}' -> numbers: {sorted(numbers)}")
            
            # Show some additional details for the first few
            if i < 2:
                for record in group[:3]:  # Show first 3 records
                    fields = record['fields']
                    house = fields.get('House', 'Unknown')
                    constituency = fields.get('Constituency', 'Unknown')
                    party = fields.get('Party', [])
                    print(f"     '{record['full_name']}': {house}, {constituency}")
        
        if len(examples) > 5:
            print(f"  ... and {len(examples) - 5} more")
    
    # Analyze if these look like actual duplicates or different people
    print("\n" + "=" * 50)
    print("DUPLICATE PATTERN ANALYSIS")
    print("=" * 50)
    
    # Sample some groups to check for actual duplicates vs different people
    suspicious_duplicates = []
    likely_different_people = []
    
    for base_name, group in base_name_groups.items():
        if len(group) > 1:
            # Check if they have identical or very similar other fields
            houses = set(record['fields'].get('House', '') for record in group)
            constituencies = set(record['fields'].get('Constituency', '') for record in group)
            first_elected = set(record['fields'].get('First_Elected', '') for record in group)
            
            # If same house and constituency, likely duplicate
            if len(houses) == 1 and len(constituencies) == 1:
                suspicious_duplicates.append((base_name, group))
            else:
                likely_different_people.append((base_name, group))
    
    print(f"SUSPICIOUS DUPLICATES (same house/constituency): {len(suspicious_duplicates)}")
    print(f"LIKELY DIFFERENT PEOPLE (different house/constituency): {len(likely_different_people)}")
    print()
    
    if suspicious_duplicates:
        print("SUSPICIOUS DUPLICATES EXAMPLES:")
        for i, (base_name, group) in enumerate(suspicious_duplicates[:5]):
            print(f"{i+1}. '{base_name}' ({len(group)} records):")
            for record in group:
                fields = record['fields']
                house = fields.get('House', 'Unknown')
                constituency = fields.get('Constituency', 'Unknown')
                first_elected = fields.get('First_Elected', 'Unknown')
                print(f"   '{record['full_name']}': {house}, {constituency}, elected {first_elected}")
            print()
    
    if likely_different_people:
        print("LIKELY DIFFERENT PEOPLE EXAMPLES:")
        for i, (base_name, group) in enumerate(likely_different_people[:3]):
            print(f"{i+1}. '{base_name}' ({len(group)} records):")
            for record in group:
                fields = record['fields']
                house = fields.get('House', 'Unknown')
                constituency = fields.get('Constituency', 'Unknown')
                first_elected = fields.get('First_Elected', 'Unknown')
                print(f"   '{record['full_name']}': {house}, {constituency}, elected {first_elected}")
            print()
    
    # Check for patterns in the numbers
    print("=" * 50)
    print("NUMBER PATTERN ANALYSIS")
    print("=" * 50)
    
    all_numbers = [record['trailing_number'] for record in problematic_records]
    number_counter = Counter(all_numbers)
    
    print("NUMBER FREQUENCY:")
    for number, count in sorted(number_counter.items(), key=lambda x: int(x[0])):
        print(f"  {number}: {count} times ({count/len(all_numbers)*100:.1f}%)")
    
    # Check if numbers are sequential within groups
    sequential_groups = 0
    non_sequential_groups = 0
    
    for base_name, group in base_name_groups.items():
        if len(group) > 1:
            numbers = sorted([int(record['trailing_number']) for record in group])
            is_sequential = all(numbers[i] == numbers[i-1] + 1 for i in range(1, len(numbers)))
            starts_from_one = numbers[0] == 1
            
            if is_sequential and starts_from_one:
                sequential_groups += 1
            else:
                non_sequential_groups += 1
    
    print(f"\nSEQUENTIAL NUMBERING ANALYSIS:")
    print(f"Groups with sequential 1,2,3... numbering: {sequential_groups}")
    print(f"Groups with non-sequential numbering: {non_sequential_groups}")
    
    return {
        'total_problematic': len(problematic_records),
        'unique_base_names': len(base_name_groups),
        'suspicious_duplicates': len(suspicious_duplicates),
        'likely_different_people': len(likely_different_people),
        'group_sizes': dict(group_sizes),
        'number_distribution': dict(number_counter)
    }


if __name__ == "__main__":
    result = analyze_duplicates()
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    for key, value in result.items():
        print(f"{key}: {value}")