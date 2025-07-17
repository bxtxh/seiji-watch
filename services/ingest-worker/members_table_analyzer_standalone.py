#!/usr/bin/env python3
"""
Standalone analysis of Members table in Airtable for:
1. Reality check of records 1-7 (real vs synthetic politicians)
2. Name_Kana field completeness analysis
"""

import json
import os
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from collections import Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')

class SimpleAirtableClient:
    """Simple Airtable client for Members table analysis."""
    
    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }
    
    async def fetch_all_members(self) -> List[Dict[str, Any]]:
        """Fetch all records from the Members table."""
        url = f"{self.base_url}/Members (議員)"
        all_records = []
        
        async with aiohttp.ClientSession() as session:
            offset = None
            
            while True:
                params = {"pageSize": 100}
                if offset:
                    params["offset"] = offset
                
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Error fetching data: {response.status}")
                        print(f"Response: {error_text}")
                        return []
                    
                    data = await response.json()
                    records = data.get("records", [])
                    all_records.extend(records)
                    
                    offset = data.get("offset")
                    if not offset:
                        break
                    
                    # Sleep to respect rate limits
                    await asyncio.sleep(0.2)
        
        return all_records

def analyze_first_seven_records(records: List[Dict[str, Any]]) -> None:
    """Analyze the first 7 records for reality check."""
    print("=== REALITY CHECK: First 7 Records Analysis ===")
    print()
    
    if len(records) < 7:
        print(f"Warning: Only {len(records)} records found, expected at least 7")
        print()
    
    for i, record in enumerate(records[:7], 1):
        fields = record.get("fields", {})
        
        print(f"Record {i}:")
        print(f"  ID: {record.get('id', 'N/A')}")
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
        print(f"  Birth_Date: {fields.get('Birth_Date', 'N/A')}")
        print(f"  First_Elected: {fields.get('First_Elected', 'N/A')}")
        print()

def analyze_name_kana_completeness(records: List[Dict[str, Any]]) -> None:
    """Analyze Name_Kana field completeness."""
    print("=== NAME_KANA COMPLETENESS ANALYSIS ===")
    print()
    
    total_records = len(records)
    missing_kana = []
    present_kana = []
    placeholder_kana = []
    valid_kana = []
    
    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name", "N/A")
        name_kana = fields.get("Name_Kana", "")
        
        if not name_kana or name_kana.strip() == "":
            missing_kana.append(name)
        elif name_kana == "たなかたろう":
            placeholder_kana.append(name)
        else:
            present_kana.append((name, name_kana))
            valid_kana.append((name, name_kana))
    
    missing_count = len(missing_kana)
    placeholder_count = len(placeholder_kana)
    valid_count = len(valid_kana)
    total_present = len(present_kana)
    
    print(f"Total records: {total_records}")
    print(f"Records with ANY Name_Kana: {total_present} ({total_present/total_records*100:.1f}%)")
    print(f"Records with VALID Name_Kana: {valid_count} ({valid_count/total_records*100:.1f}%)")
    print(f"Records with PLACEHOLDER kana (たなかたろう): {placeholder_count} ({placeholder_count/total_records*100:.1f}%)")
    print(f"Records missing Name_Kana: {missing_count} ({missing_count/total_records*100:.1f}%)")
    print()
    
    # Critical finding
    print("🚨 CRITICAL FINDING:")
    total_needing_kana = missing_count + placeholder_count
    print(f"Records needing proper kana: {total_needing_kana}/{total_records} ({total_needing_kana/total_records*100:.1f}%)")
    print()
    
    if placeholder_kana:
        print("Examples of names with placeholder kana (たなかたろう):")
        for i, name in enumerate(placeholder_kana[:10], 1):
            print(f"  {i}. {name} → たなかたろう (NEEDS FIXING)")
        if len(placeholder_kana) > 10:
            print(f"  ... and {len(placeholder_kana) - 10} more")
        print()
    
    if missing_kana:
        print("Examples of names missing kana readings:")
        for i, name in enumerate(missing_kana[:10], 1):  # Show first 10
            print(f"  {i}. {name}")
        
        if len(missing_kana) > 10:
            print(f"  ... and {len(missing_kana) - 10} more")
        print()
    
    if valid_kana:
        print("Examples of names with VALID kana readings:")
        for i, (name, kana) in enumerate(valid_kana[:5], 1):  # Show first 5
            print(f"  {i}. {name} → {kana}")
        print()

def analyze_data_patterns(records: List[Dict[str, Any]]) -> None:
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
        
        # Handle party field - it might be a list of IDs
        if party:
            if isinstance(party, list):
                parties.extend(party)  # Add all party IDs
            else:
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

def analyze_reality_indicators(records: List[Dict[str, Any]]) -> None:
    """Analyze specific indicators of real vs synthetic data."""
    print("=== REALITY INDICATORS ANALYSIS ===")
    print()
    
    # Check for known real politicians
    known_politicians = [
        "赤池誠章", "阿達雅志", "青島健太", "青山繁晴", "秋野公造",
        "麻生太郎", "安倍晋三", "岸田文雄", "菅義偉", "石破茂"
    ]
    
    found_real_politicians = []
    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name", "")
        if name in known_politicians:
            found_real_politicians.append(name)
    
    print("Known real politicians found:")
    if found_real_politicians:
        for politician in found_real_politicians:
            print(f"  ✅ {politician}")
    else:
        print("  ❌ No known politicians found in first batch")
    print()
    
    # Check name patterns (real Japanese names vs synthetic)
    print("Name pattern analysis:")
    kanji_names = 0
    hiragana_names = 0
    katakana_names = 0
    mixed_names = 0
    
    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name", "")
        if not name:
            continue
            
        has_kanji = any('\u4e00' <= c <= '\u9faf' for c in name)
        has_hiragana = any('\u3040' <= c <= '\u309f' for c in name)
        has_katakana = any('\u30a0' <= c <= '\u30ff' for c in name)
        
        if has_kanji and (has_hiragana or has_katakana):
            mixed_names += 1
        elif has_kanji:
            kanji_names += 1
        elif has_hiragana:
            hiragana_names += 1
        elif has_katakana:
            katakana_names += 1
    
    total_analyzed = kanji_names + hiragana_names + katakana_names + mixed_names
    print(f"  Kanji only: {kanji_names}/{total_analyzed} ({kanji_names/total_analyzed*100:.1f}%)")
    print(f"  Mixed (kanji + kana): {mixed_names}/{total_analyzed} ({mixed_names/total_analyzed*100:.1f}%)")
    print(f"  Hiragana only: {hiragana_names}/{total_analyzed}")
    print(f"  Katakana only: {katakana_names}/{total_analyzed}")
    print()

def suggest_kana_strategy(records: List[Dict[str, Any]]) -> None:
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
    print("   - Prompt: 'Provide the hiragana reading for this Japanese politician name: [name]'")
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
    print("Initializing Airtable client...")
    
    # Create Airtable client
    try:
        client = SimpleAirtableClient()
        print("✅ Airtable client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Airtable client: {e}")
        return
    
    print("Fetching Members table data from Airtable...")
    
    # Fetch members data
    records = await client.fetch_all_members()
    
    if not records:
        print("No records found or error occurred.")
        return
    
    print(f"Successfully fetched {len(records)} records from Members table.")
    print("=" * 60)
    print()
    
    # Reality check of first 7 records
    analyze_first_seven_records(records)
    
    # Reality indicators analysis
    analyze_reality_indicators(records)
    
    # Name_Kana completeness analysis
    analyze_name_kana_completeness(records)
    
    # Data pattern analysis
    analyze_data_patterns(records)
    
    # Strategy suggestions
    suggest_kana_strategy(records)
    
    # Save raw data for further analysis
    output_file = f"members_analysis_result_{int(__import__('time').time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"Raw data saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())