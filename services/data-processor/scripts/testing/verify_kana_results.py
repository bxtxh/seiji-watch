#!/usr/bin/env python3
"""
Verify Name_Kana Fix Results
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def verify_kana_results():
    """Verify the results of Name_Kana fixes"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    print("🔍 Verifying Name_Kana Fix Results...")

    async with aiohttp.ClientSession() as session:
        # Get all records
        all_records = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(
                f"{base_url}/Members (議員)", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_records.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Error: {response.status}")
                    return

        print(f"📊 Total records: {len(all_records)}")

        # Analyze final state
        analysis = {"good_kana": 0, "empty": 0, "placeholder": 0, "total_with_name": 0}

        good_examples = []
        problem_examples = []

        for record in all_records:
            fields = record.get("fields", {})
            name = fields.get("Name", "")
            name_kana = fields.get("Name_Kana", "")

            if name:
                analysis["total_with_name"] += 1

                if not name_kana or name_kana.strip() == "":
                    analysis["empty"] += 1
                    problem_examples.append(
                        {"name": name, "kana": name_kana, "issue": "empty"}
                    )
                elif "たなかたろう" in name_kana.lower():
                    analysis["placeholder"] += 1
                    problem_examples.append(
                        {"name": name, "kana": name_kana, "issue": "placeholder"}
                    )
                else:
                    analysis["good_kana"] += 1
                    if len(good_examples) < 10:
                        good_examples.append({"name": name, "kana": name_kana})

        # Calculate quality metrics
        total_good = analysis["good_kana"]
        analysis["empty"] + analysis["placeholder"]
        completeness = (
            (total_good / analysis["total_with_name"]) * 100
            if analysis["total_with_name"] > 0
            else 0
        )

        print("\n📊 Final Analysis:")
        print(f"   ✅ Good Name_Kana: {analysis['good_kana']}")
        print(f"   🔤 Empty: {analysis['empty']}")
        print(f"   🔄 Placeholder: {analysis['placeholder']}")
        print(f"   📈 Completeness: {completeness:.1f}%")

        # Show examples
        if good_examples:
            print("\n✅ Good Examples:")
            for i, ex in enumerate(good_examples[:5], 1):
                print(f"   {i}. {ex['name']} → {ex['kana']}")

        if problem_examples:
            print("\n⚠️ Remaining Issues (first 5):")
            for i, ex in enumerate(problem_examples[:5], 1):
                print(f"   {i}. {ex['name']} → '{ex['kana']}' ({ex['issue']})")

        # Quality assessment
        print("\n📈 Quality Assessment:")
        if completeness >= 95:
            print(f"🏆 EXCELLENT! {completeness:.1f}% Name_Kana completeness")
        elif completeness >= 90:
            print(f"🎯 VERY GOOD! {completeness:.1f}% Name_Kana completeness")
        elif completeness >= 80:
            print(f"👍 GOOD! {completeness:.1f}% Name_Kana completeness")
        else:
            print(f"⚠️ Needs improvement - {completeness:.1f}% completeness")

        return {
            "total_records": len(all_records),
            "good_kana": analysis["good_kana"],
            "empty": analysis["empty"],
            "placeholder": analysis["placeholder"],
            "completeness": completeness,
        }


if __name__ == "__main__":
    asyncio.run(verify_kana_results())
