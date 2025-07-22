#!/usr/bin/env python3
"""
Bills Detailed Analysis
Bills テーブルの詳細分析 - 具体的な欠損フィールド特定
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def analyze_bills_detailed():
    """Detailed analysis of Bills table to identify specific missing fields"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    print("🔍 Starting detailed Bills table analysis...")

    async with aiohttp.ClientSession() as session:
        # Get all Bills records
        all_records = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(
                f"{base_url}/Bills (法案)", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_records.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Error fetching records: {response.status}")
                    return

        print(f"📊 Analyzing {len(all_records)} Bills records...")

        # Essential fields for quality calculation
        essential_fields = [
            "Title",
            "Bill_Number",
            "Bill_Status",
            "Diet_Session",
            "House",
            "Category",
            "Priority",
            "Stage",
            "Bill_Type",
            "Submitter",
            "Bill_URL",
            "Data_Source",
        ]

        # Analyze field completeness
        field_analysis = {}

        for field in essential_fields:
            filled_count = 0
            empty_count = 0
            sample_values = []

            for record in all_records:
                value = record.get("fields", {}).get(field)

                if value is None or value == "":
                    empty_count += 1
                else:
                    filled_count += 1
                    if len(sample_values) < 5:
                        sample_values.append(str(value))

            field_analysis[field] = {
                "filled_count": filled_count,
                "empty_count": empty_count,
                "completeness_rate": filled_count / len(all_records)
                if all_records
                else 0,
                "sample_values": sample_values,
            }

        # Print detailed analysis
        print(f"\n{'=' * 80}")
        print("📋 BILLS TABLE DETAILED FIELD ANALYSIS")
        print(f"{'=' * 80}")
        print(f"📊 Total Records: {len(all_records)}")

        for field, analysis in field_analysis.items():
            rate = analysis["completeness_rate"]
            status = "✅" if rate >= 0.9 else "⚠️" if rate >= 0.5 else "❌"

            print(f"\n{status} {field}:")
            print(
                f"   📈 Completeness: {rate:.1%} ({analysis['filled_count']}/{len(all_records)})"
            )
            print(f"   ❌ Missing: {analysis['empty_count']} records")

            if analysis["sample_values"]:
                print(
                    f"   📝 Sample values: {', '.join(analysis['sample_values'][:3])}"
                )

        # Calculate overall completeness for essential fields
        total_completeness = sum(
            analysis["completeness_rate"] for analysis in field_analysis.values()
        ) / len(field_analysis)
        print(f"\n📊 Overall Essential Field Completeness: {total_completeness:.1%}")

        # Identify top priority missing fields
        missing_fields = [
            (field, analysis["empty_count"])
            for field, analysis in field_analysis.items()
            if analysis["completeness_rate"] < 0.9
        ]
        missing_fields.sort(key=lambda x: x[1], reverse=True)

        print("\n🎯 TOP PRIORITY MISSING FIELDS:")
        for field, missing_count in missing_fields[:5]:
            print(f"   📋 {field}: {missing_count} records missing")

        # Check what fields are actually present in records
        print("\n🔍 ACTUAL FIELD PRESENCE ANALYSIS:")
        all_field_names = set()
        for record in all_records[:10]:  # Sample first 10 records
            all_field_names.update(record.get("fields", {}).keys())

        print(f"📋 Fields found in sample records: {sorted(all_field_names)}")

        # Sample record inspection
        print("\n📝 SAMPLE RECORD INSPECTION:")
        for i, record in enumerate(all_records[:3]):
            print(f"\nRecord {i + 1} ({record['id']}):")
            fields = record.get("fields", {})
            for field in essential_fields:
                value = fields.get(field, "❌ MISSING")
                print(f"   {field}: {value}")

        # Generate improvement recommendations
        print("\n💡 IMPROVEMENT RECOMMENDATIONS:")

        if field_analysis.get("Bill_Number", {}).get("empty_count", 0) > 0:
            print("   1. Fill missing Bill_Number fields (critical for uniqueness)")

        if field_analysis.get("Category", {}).get("empty_count", 0) > 0:
            print("   2. Complete category classification for all bills")

        if field_analysis.get("Priority", {}).get("empty_count", 0) > 0:
            print("   3. Assign priority levels to all bills")

        if field_analysis.get("Stage", {}).get("empty_count", 0) > 0:
            print("   4. Determine stage for all bills based on status")

        # Save detailed analysis
        analysis_report = {
            "analysis_date": datetime.now().isoformat(),
            "total_records": len(all_records),
            "essential_fields_analysis": field_analysis,
            "overall_completeness": total_completeness,
            "top_missing_fields": missing_fields,
            "recommendations": [
                "Focus on Bill_Number completion (if missing)",
                "Complete category classification",
                "Assign priority levels",
                "Determine stages based on status",
                "Verify data source and URL fields",
            ],
        }

        filename = (
            f"bills_detailed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Detailed analysis saved: {filename}")

        return analysis_report


if __name__ == "__main__":
    asyncio.run(analyze_bills_detailed())
