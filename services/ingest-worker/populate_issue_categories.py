#!/usr/bin/env python3
"""
Populate IssueCategories table with CAP-based policy categories.
This is a prerequisite for T129 migration.
"""

import asyncio
import os
from datetime import datetime

import aiohttp

# Set environment variables
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# CAP-based policy categories for Japan
# Based on Comparative Agendas Project (CAP) classification
CAP_CATEGORIES = [
    # Layer 1 (Major Topics)
    {
        "CAP_Code": "1",
        "Layer": "L1",
        "Title_JA": "経済・財政",
        "Title_EN": "Economy and Finance",
        "Description": "経済政策、財政政策、予算、税制に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "2",
        "Layer": "L1",
        "Title_JA": "教育・文化",
        "Title_EN": "Education and Culture",
        "Description": "教育制度、文化政策、科学技術に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "3",
        "Layer": "L1",
        "Title_JA": "地方自治・行政",
        "Title_EN": "Local Government and Administration",
        "Description": "地方自治体、行政組織、公務員制度に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "4",
        "Layer": "L1",
        "Title_JA": "農林水産",
        "Title_EN": "Agriculture, Forestry and Fisheries",
        "Description": "農業、林業、水産業に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "5",
        "Layer": "L1",
        "Title_JA": "労働・雇用",
        "Title_EN": "Labor and Employment",
        "Description": "労働政策、雇用制度、労働者保護に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "6",
        "Layer": "L1",
        "Title_JA": "運輸・通信",
        "Title_EN": "Transportation and Communications",
        "Description": "交通政策、通信政策、インフラ整備に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "7",
        "Layer": "L1",
        "Title_JA": "環境・エネルギー",
        "Title_EN": "Environment and Energy",
        "Description": "環境保護、エネルギー政策、気候変動対策に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "8",
        "Layer": "L1",
        "Title_JA": "住宅・都市計画",
        "Title_EN": "Housing and Urban Planning",
        "Description": "住宅政策、都市計画、地域開発に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "10",
        "Layer": "L1",
        "Title_JA": "司法・法務",
        "Title_EN": "Justice and Legal Affairs",
        "Description": "司法制度、法務行政、人権保護に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "12",
        "Layer": "L1",
        "Title_JA": "社会保障",
        "Title_EN": "Social Security",
        "Description": "社会保障制度、医療保険、年金に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "13",
        "Layer": "L1",
        "Title_JA": "医療・健康",
        "Title_EN": "Healthcare and Health",
        "Description": "医療制度、公衆衛生、健康増進に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "14",
        "Layer": "L1",
        "Title_JA": "商業・産業",
        "Title_EN": "Commerce and Industry",
        "Description": "商業政策、産業振興、中小企業支援に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "15",
        "Layer": "L1",
        "Title_JA": "防衛・安全保障",
        "Title_EN": "Defense and Security",
        "Description": "国防政策、安全保障、軍事に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "16",
        "Layer": "L1",
        "Title_JA": "外交・国際関係",
        "Title_EN": "Foreign Affairs and International Relations",
        "Description": "外交政策、国際協力、対外関係に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "17",
        "Layer": "L1",
        "Title_JA": "科学・技術",
        "Title_EN": "Science and Technology",
        "Description": "科学技術政策、研究開発、イノベーションに関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "18",
        "Layer": "L1",
        "Title_JA": "貿易・通商",
        "Title_EN": "Trade and Commerce",
        "Description": "貿易政策、通商政策、経済連携に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "19",
        "Layer": "L1",
        "Title_JA": "国土・地域",
        "Title_EN": "Territory and Regional Development",
        "Description": "国土政策、地域開発、災害対策に関する政策分野",
        "Parent_Category": None,
    },
    {
        "CAP_Code": "20",
        "Layer": "L1",
        "Title_JA": "その他",
        "Title_EN": "Others",
        "Description": "その他の政策分野",
        "Parent_Category": None,
    },
    # Layer 2 (Sub-topics) - Selected important subcategories
    {
        "CAP_Code": "1.1",
        "Layer": "L2",
        "Title_JA": "予算・決算",
        "Title_EN": "Budget and Settlement",
        "Description": "国家予算、決算、財政収支に関する政策",
        "Parent_Category": "1",
    },
    {
        "CAP_Code": "1.2",
        "Layer": "L2",
        "Title_JA": "税制",
        "Title_EN": "Tax Policy",
        "Description": "税制改革、税率、税収に関する政策",
        "Parent_Category": "1",
    },
    {
        "CAP_Code": "13.1",
        "Layer": "L2",
        "Title_JA": "社会保障制度",
        "Title_EN": "Social Security System",
        "Description": "年金制度、生活保護、社会保険に関する政策",
        "Parent_Category": "12",
    },
    {
        "CAP_Code": "13.2",
        "Layer": "L2",
        "Title_JA": "医療保険",
        "Title_EN": "Health Insurance",
        "Description": "健康保険制度、医療費、保険制度に関する政策",
        "Parent_Category": "13",
    },
    {
        "CAP_Code": "15.1",
        "Layer": "L2",
        "Title_JA": "産業振興",
        "Title_EN": "Industrial Development",
        "Description": "産業政策、企業支援、経済振興に関する政策",
        "Parent_Category": "14",
    },
    {
        "CAP_Code": "7.1",
        "Layer": "L2",
        "Title_JA": "環境保護",
        "Title_EN": "Environmental Protection",
        "Description": "環境規制、公害対策、生態系保護に関する政策",
        "Parent_Category": "7",
    },
    {
        "CAP_Code": "7.2",
        "Layer": "L2",
        "Title_JA": "エネルギー政策",
        "Title_EN": "Energy Policy",
        "Description": "エネルギー供給、再生可能エネルギー、省エネルギーに関する政策",
        "Parent_Category": "7",
    },
    {
        "CAP_Code": "19.1",
        "Layer": "L2",
        "Title_JA": "国際協力",
        "Title_EN": "International Cooperation",
        "Description": "国際援助、多国間協力、国際機関に関する政策",
        "Parent_Category": "16",
    },
    {
        "CAP_Code": "16.1",
        "Layer": "L2",
        "Title_JA": "国防政策",
        "Title_EN": "Defense Policy",
        "Description": "自衛隊、軍事力、防衛装備に関する政策",
        "Parent_Category": "15",
    },
    {
        "CAP_Code": "2.1",
        "Layer": "L2",
        "Title_JA": "教育制度",
        "Title_EN": "Education System",
        "Description": "学校教育、高等教育、教育改革に関する政策",
        "Parent_Category": "2",
    },
    {
        "CAP_Code": "4.1",
        "Layer": "L2",
        "Title_JA": "農業政策",
        "Title_EN": "Agricultural Policy",
        "Description": "農業振興、食料安全保障、農地に関する政策",
        "Parent_Category": "4",
    },
    {
        "CAP_Code": "12.1",
        "Layer": "L2",
        "Title_JA": "司法改革",
        "Title_EN": "Judicial Reform",
        "Description": "司法制度改革、裁判員制度、法曹制度に関する政策",
        "Parent_Category": "10",
    },
    {
        "CAP_Code": "11.1",
        "Layer": "L2",
        "Title_JA": "憲法・統治",
        "Title_EN": "Constitution and Governance",
        "Description": "憲法改正、統治機構、政治制度に関する政策",
        "Parent_Category": "10",
    },
    {
        "CAP_Code": "20.1",
        "Layer": "L2",
        "Title_JA": "その他政策",
        "Title_EN": "Other Policies",
        "Description": "分類されない政策分野",
        "Parent_Category": "20",
    },
]


async def populate_issue_categories():
    """Populate IssueCategories table with CAP-based categories."""

    print("🚀 Populating IssueCategories Table")
    print("=" * 60)

    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables required")
        return False

    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    # Use table ID for reliable access
    issue_categories_url = (
        f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/tbl6wK8L9K5ny1dDm"
    )

    async with aiohttp.ClientSession() as session:
        # Check if table exists and is accessible
        try:
            async with session.get(issue_categories_url, headers=headers) as response:
                if response.status != 200:
                    print(f"❌ Cannot access IssueCategories table: {response.status}")
                    return False

                data = await response.json()
                existing_records = data.get("records", [])
                print(f"📋 Found {len(existing_records)} existing records")

                if existing_records:
                    print("⚠️  Table already has data. Proceeding to add new records...")

        except Exception as e:
            print(f"❌ Error accessing IssueCategories table: {e}")
            return False

        # Create records in batches
        created_count = 0
        error_count = 0

        print(f"\n🔄 Creating {len(CAP_CATEGORIES)} category records...")

        for i in range(0, len(CAP_CATEGORIES), 10):
            batch = CAP_CATEGORIES[i : i + 10]

            # Prepare batch data
            records_data = []
            for category in batch:
                record_data = {
                    "fields": {
                        "CAP_Code": category["CAP_Code"],
                        "Layer": category["Layer"],
                        "Title_JA": category["Title_JA"],
                        "Title_EN": category["Title_EN"],
                        "Summary_150JA": category["Description"],
                        "Is_Seed": True,
                        "Created_At": datetime.now().isoformat(),
                        "Updated_At": datetime.now().isoformat(),
                    }
                }

                # Note: Parent_Category field doesn't exist in current schema

                records_data.append(record_data)

            batch_data = {"records": records_data}

            try:
                async with session.post(
                    issue_categories_url, headers=headers, json=batch_data
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        batch_created = len(response_data.get("records", []))
                        created_count += batch_created
                        print(
                            f"✅ Batch {i // 10 + 1}: Created {batch_created} categories"
                        )

                        # Show created categories
                        for record in response_data.get("records", []):
                            fields = record.get("fields", {})
                            cap_code = fields.get("CAP_Code", "")
                            title_ja = fields.get("Title_JA", "")
                            layer = fields.get("Layer", "")
                            print(f"   • {cap_code} ({layer}): {title_ja}")

                    else:
                        error_text = await response.text()
                        print(f"❌ Batch {i // 10 + 1} failed: {response.status}")
                        print(f"   Error: {error_text}")
                        error_count += len(batch)

                # Rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"❌ Batch {i // 10 + 1} error: {e}")
                error_count += len(batch)

        print("\n🎉 Population Complete!")
        print(f"   Successfully created: {created_count} categories")
        print(f"   Errors: {error_count}")

        return created_count > 0


async def verify_population():
    """Verify the populated categories."""

    print("\n🔍 Verifying IssueCategories Population")
    print("=" * 60)

    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json",
    }

    issue_categories_url = (
        f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/tbl6wK8L9K5ny1dDm"
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(issue_categories_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    categories = data.get("records", [])

                    print(f"✅ Total categories in table: {len(categories)}")

                    # Organize by layer
                    layer_counts = {"L1": 0, "L2": 0, "L3": 0}
                    cap_codes = []

                    for category in categories:
                        fields = category.get("fields", {})
                        layer = fields.get("Layer", "")
                        cap_code = fields.get("CAP_Code", "")

                        if layer in layer_counts:
                            layer_counts[layer] += 1

                        cap_codes.append(cap_code)

                    print("\n📊 Layer Distribution:")
                    for layer, count in layer_counts.items():
                        print(f"   {layer}: {count} categories")

                    print("\n📋 CAP Codes Available:")
                    for cap_code in sorted(cap_codes):
                        print(f"   {cap_code}")

                    return True

                else:
                    print(f"❌ Verification failed: {response.status}")
                    return False

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False


async def main():
    """Main execution."""

    print("🚀 IssueCategories Population Script")
    print("=" * 70)

    # Step 1: Populate IssueCategories
    population_success = await populate_issue_categories()
    if not population_success:
        return 1

    # Step 2: Verify population
    verification_success = await verify_population()
    if not verification_success:
        return 1

    print("\n✅ IssueCategories populated successfully!")
    print("🔧 Ready for T129 migration: python t129_data_migration.py")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
