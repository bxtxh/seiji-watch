#!/usr/bin/env python3
"""Analyze Bills table categories for T129 migration."""

import asyncio
import json
import os
from collections import defaultdict

import aiohttp

# Load environment variables
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


async def analyze_bills_categories():
    """Analyze the Bills table category distribution."""

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables are required")
        return

    base_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    print("🔍 Analyzing Bills table categories for T129 migration")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:

        # Get all Bills records
        print("\n📋 Step 1: Fetching all Bills records...")
        bills_url = f"{base_url}/Bills%20(%E6%B3%95%E6%A1%88)"
        all_bills = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(
                bills_url, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_bills.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Failed to fetch Bills data: {response.status}")
                    return

        print(f"   ✅ Fetched {len(all_bills)} Bills records")

        # Analyze category distribution
        print("\n📊 Step 2: Analyzing category distribution...")
        categories = defaultdict(int)
        total_with_category = 0

        # Sample record structure
        sample_record = None

        for record in all_bills:
            fields = record.get("fields", {})
            category = fields.get("Category")

            if not sample_record:
                sample_record = fields

            if category:
                categories[category] += 1
                total_with_category += 1

        print(f"   Records with Category: {total_with_category}/{len(all_bills)}")
        print(f"   Records without Category: {len(all_bills) - total_with_category}")

        # Show sample record structure
        if sample_record:
            print("\n🔍 Step 3: Sample Bills record structure:")
            for field_name, field_value in sample_record.items():
                if isinstance(field_value, str) and len(field_value) > 80:
                    print(f"   {field_name}: {field_value[:80]}...")
                elif isinstance(field_value, list):
                    print(f"   {field_name}: [list with {len(field_value)} items]")
                else:
                    print(f"   {field_name}: {field_value}")

        # Show category distribution
        print("\n📈 Step 4: Current category distribution:")
        print(f"   Total unique categories: {len(categories)}")
        print("   Category breakdown:")

        for category, count in sorted(
            categories.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / len(all_bills)) * 100
            print(f"   {category}: {count} bills ({percentage:.1f}%)")

        # Generate mapping candidates
        print("\n🔗 Step 5: Generating mapping candidates...")
        mapping_candidates = {
            "予算・決算": ["予算", "決算", "budget", "財政"],
            "税制": ["税", "tax", "租税", "課税"],
            "社会保障": ["社会保障", "年金", "医療", "介護", "福祉", "保険"],
            "外交・国際": ["外交", "国際", "条約", "防衛", "安全保障"],
            "経済・産業": ["経済", "産業", "商工", "農業", "漁業", "林業", "貿易"],
            "教育・文化": ["教育", "文化", "学校", "大学", "研究", "スポーツ"],
            "環境・エネルギー": ["環境", "エネルギー", "原発", "再生可能", "温暖化"],
            "法務・司法": ["法務", "司法", "裁判", "検察", "弁護士"],
            "行政・地方": ["行政", "地方", "自治体", "公務員", "議員"],
            "交通・通信": ["交通", "通信", "道路", "鉄道", "航空", "港湾"],
            "労働・雇用": ["労働", "雇用", "働き方", "賃金", "労災"],
            "その他": ["その他", "一般", "雑則"],
        }

        print("   📋 Suggested mapping structure:")
        for target_category, keywords in mapping_candidates.items():
            print(f"   {target_category}: {keywords}")

        # Try to match existing categories to candidates
        print("\n🎯 Step 6: Automatic mapping suggestions:")
        suggested_mappings = {}

        for existing_category in categories.keys():
            if existing_category and existing_category != "":
                # Try to find best match
                best_match = None
                best_score = 0

                for target_category, keywords in mapping_candidates.items():
                    score = 0
                    for keyword in keywords:
                        if keyword.lower() in existing_category.lower():
                            score += 1

                    if score > best_score:
                        best_score = score
                        best_match = target_category

                if best_match:
                    suggested_mappings[existing_category] = best_match
                else:
                    suggested_mappings[existing_category] = "その他"

        for existing_category, suggested_target in suggested_mappings.items():
            count = categories[existing_category]
            print(f"   '{existing_category}' ({count} bills) → '{suggested_target}'")

        # Save results for T129.2
        results = {
            "total_bills": len(all_bills),
            "bills_with_category": total_with_category,
            "category_distribution": dict(categories),
            "suggested_mappings": suggested_mappings,
            "mapping_candidates": mapping_candidates,
            "sample_record": (
                {k: str(v)[:100] for k, v in sample_record.items()}
                if sample_record
                else None
            ),
        }

        output_file = "bills_category_analysis_t129.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Results saved to: {output_file}")
        print("✅ T129.1 Analysis complete!")
        print("\n🎯 Next steps for T129.2:")
        print("   1. Review suggested mappings")
        print("   2. Verify against IssueCategories table")
        print("   3. Create migration script for T129.3")


if __name__ == "__main__":
    asyncio.run(analyze_bills_categories())
