#!/usr/bin/env python3
"""
Expand L2 Coverage for CAP Mapping
Add missing L2 sub-topics for uncovered L1 categories.
"""

import csv
from pathlib import Path

# Additional L2 categories for better coverage
ADDITIONAL_L2_CATEGORIES = [
    # Civil Rights and Liberties (2)
    {"cap_code": "200", "parent_cap_code": "2", "title_en": "General Civil Rights", "title_ja": "一般市民権"},
    {"cap_code": "201", "parent_cap_code": "2", "title_en": "Freedom of Speech and Press", "title_ja": "言論・報道の自由"},
    {"cap_code": "202", "parent_cap_code": "2", "title_en": "Privacy Rights", "title_ja": "プライバシー権"},
    
    # Agriculture (4)
    {"cap_code": "400", "parent_cap_code": "4", "title_en": "General Agriculture", "title_ja": "一般農業政策"},
    {"cap_code": "401", "parent_cap_code": "4", "title_en": "Agricultural Trade", "title_ja": "農産物貿易"},
    {"cap_code": "402", "parent_cap_code": "4", "title_en": "Food Safety", "title_ja": "食品安全"},
    
    # Labor and Employment (5)
    {"cap_code": "500", "parent_cap_code": "5", "title_en": "General Labor Issues", "title_ja": "一般労働問題"},
    {"cap_code": "501", "parent_cap_code": "5", "title_en": "Worker Safety and Protection", "title_ja": "労働安全・保護"},
    {"cap_code": "502", "parent_cap_code": "5", "title_en": "Employment Training", "title_ja": "雇用訓練"},
    
    # Education (6)
    {"cap_code": "600", "parent_cap_code": "6", "title_en": "Elementary and Secondary Education", "title_ja": "初等・中等教育"},
    {"cap_code": "601", "parent_cap_code": "6", "title_en": "Higher Education", "title_ja": "高等教育"},
    {"cap_code": "602", "parent_cap_code": "6", "title_en": "Vocational Education", "title_ja": "職業教育"},
    
    # Environment (7)
    {"cap_code": "700", "parent_cap_code": "7", "title_en": "General Environmental Issues", "title_ja": "一般環境問題"},
    {"cap_code": "701", "parent_cap_code": "7", "title_en": "Air and Water Quality", "title_ja": "大気・水質"},
    {"cap_code": "702", "parent_cap_code": "7", "title_en": "Climate Change", "title_ja": "気候変動"},
    
    # Energy (8)
    {"cap_code": "800", "parent_cap_code": "8", "title_en": "General Energy Policy", "title_ja": "一般エネルギー政策"},
    {"cap_code": "801", "parent_cap_code": "8", "title_en": "Renewable Energy", "title_ja": "再生可能エネルギー"},
    {"cap_code": "802", "parent_cap_code": "8", "title_en": "Nuclear Energy", "title_ja": "原子力エネルギー"},
    
    # Transportation (10)
    {"cap_code": "1000", "parent_cap_code": "10", "title_en": "General Transportation", "title_ja": "一般交通政策"},
    {"cap_code": "1001", "parent_cap_code": "10", "title_en": "Highway and Road Construction", "title_ja": "道路・高速道路建設"},
    {"cap_code": "1002", "parent_cap_code": "10", "title_en": "Public Transportation", "title_ja": "公共交通"},
    
    # Law and Crime (12)
    {"cap_code": "1200", "parent_cap_code": "12", "title_en": "General Law and Crime", "title_ja": "一般法務・犯罪"},
    {"cap_code": "1201", "parent_cap_code": "12", "title_en": "Police and Law Enforcement", "title_ja": "警察・法執行"},
    {"cap_code": "1202", "parent_cap_code": "12", "title_en": "Judicial System", "title_ja": "司法制度"},
    
    # Community Development (14)
    {"cap_code": "1400", "parent_cap_code": "14", "title_en": "Urban Development", "title_ja": "都市開発"},
    {"cap_code": "1401", "parent_cap_code": "14", "title_en": "Rural Development", "title_ja": "地方開発"},
    {"cap_code": "1402", "parent_cap_code": "14", "title_en": "Housing Policy", "title_ja": "住宅政策"},
    
    # Banking and Finance (15)
    {"cap_code": "1500", "parent_cap_code": "15", "title_en": "General Banking", "title_ja": "一般銀行業"},
    {"cap_code": "1501", "parent_cap_code": "15", "title_en": "Financial Regulation", "title_ja": "金融規制"},
    {"cap_code": "1502", "parent_cap_code": "15", "title_en": "Insurance", "title_ja": "保険"},
    
    # Space Science and Technology (17)
    {"cap_code": "1700", "parent_cap_code": "17", "title_en": "Space Research", "title_ja": "宇宙研究"},
    {"cap_code": "1701", "parent_cap_code": "17", "title_en": "Technology Development", "title_ja": "技術開発"},
    {"cap_code": "1702", "parent_cap_code": "17", "title_en": "Information Technology", "title_ja": "情報技術"},
    
    # Foreign Trade (18)
    {"cap_code": "1800", "parent_cap_code": "18", "title_en": "General Trade Policy", "title_ja": "一般貿易政策"},
    {"cap_code": "1801", "parent_cap_code": "18", "title_en": "Trade Agreements", "title_ja": "貿易協定"},
    {"cap_code": "1802", "parent_cap_code": "18", "title_en": "Import and Export", "title_ja": "輸出入"},
    
    # Government Operations (20)
    {"cap_code": "2000", "parent_cap_code": "20", "title_en": "General Government Operations", "title_ja": "一般政府運営"},
    {"cap_code": "2001", "parent_cap_code": "20", "title_en": "Public Administration", "title_ja": "行政管理"},
    {"cap_code": "2002", "parent_cap_code": "20", "title_en": "Government Procurement", "title_ja": "政府調達"},
    
    # Public Lands and Water (21)
    {"cap_code": "2100", "parent_cap_code": "21", "title_en": "Natural Resource Management", "title_ja": "天然資源管理"},
    {"cap_code": "2101", "parent_cap_code": "21", "title_en": "Water Resources", "title_ja": "水資源"},
    {"cap_code": "2102", "parent_cap_code": "21", "title_en": "National Parks", "title_ja": "国立公園"},
    
    # Culture and Arts (23)
    {"cap_code": "2300", "parent_cap_code": "23", "title_en": "Cultural Policy", "title_ja": "文化政策"},
    {"cap_code": "2301", "parent_cap_code": "23", "title_en": "Arts Funding", "title_ja": "芸術支援"},
    {"cap_code": "2302", "parent_cap_code": "23", "title_en": "Cultural Heritage", "title_ja": "文化遺産"},
    
    # Other (99)
    {"cap_code": "9900", "parent_cap_code": "99", "title_en": "Miscellaneous Issues", "title_ja": "その他の課題"},
]

def main():
    """Expand L2 coverage by adding new categories."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data" / "cap_mapping"
    
    l2_file = data_dir / "l2_sub_topics.csv"
    
    # Load existing L2 data
    existing_l2 = []
    if l2_file.exists():
        with open(l2_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_l2 = list(reader)
    
    existing_cap_codes = {row['cap_code'] for row in existing_l2}
    
    # Add new categories (avoiding duplicates)
    new_categories = []
    for category in ADDITIONAL_L2_CATEGORIES:
        if category['cap_code'] not in existing_cap_codes:
            new_categories.append({
                "cap_code": category['cap_code'],
                "layer": "L2",
                "parent_cap_code": category['parent_cap_code'],
                "title_en": category['title_en'],
                "title_ja": category['title_ja']
            })
    
    # Combine existing and new categories
    all_l2_categories = existing_l2 + new_categories
    
    # Sort by cap_code for consistent ordering
    all_l2_categories.sort(key=lambda x: int(x['cap_code']))
    
    # Write updated L2 file
    with open(l2_file, 'w', encoding='utf-8', newline='') as f:
        if all_l2_categories:
            fieldnames = ['cap_code', 'layer', 'parent_cap_code', 'title_en', 'title_ja']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_l2_categories)
    
    print(f"✅ L2 coverage expanded:")
    print(f"   Existing categories: {len(existing_l2)}")
    print(f"   New categories: {len(new_categories)}")
    print(f"   Total categories: {len(all_l2_categories)}")
    
    # Show coverage by parent
    parent_coverage = {}
    for category in all_l2_categories:
        parent = category['parent_cap_code']
        parent_coverage[parent] = parent_coverage.get(parent, 0) + 1
    
    print(f"\n📊 Coverage by L1 category:")
    for parent, count in sorted(parent_coverage.items(), key=lambda x: int(x[0])):
        print(f"   L1-{parent}: {count} sub-topics")

if __name__ == "__main__":
    main()