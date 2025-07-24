#!/usr/bin/env python3
"""
Analyze Incomplete Name_Kana - Find surname-only readings
不完全Name_Kana分析 - 苗字のみの読み特定
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


class IncompleteKanaAnalyzer:
    """Analyze incomplete kana readings (surname-only cases)"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

        # Known surname patterns for detection
        self.common_surnames = [
            "たなか",
            "さとう",
            "すずき",
            "たかはし",
            "いとう",
            "わたなべ",
            "やまもと",
            "なかむら",
            "こばやし",
            "かとう",
            "よしだ",
            "やまだ",
            "ささき",
            "やまぐち",
            "まつもと",
            "いのうえ",
            "きむら",
            "はやし",
            "さいとう",
            "しみず",
            "やまざき",
            "もり",
            "あべ",
            "いけだ",
            "はしもと",
            "やました",
            "いしかわ",
            "なかじま",
            "まえだ",
            "ふじた",
            "ごとう",
            "おかだ",
            "はせがわ",
            "むらかみ",
            "こんどう",
            "いしだ",
            "にしむら",
            "まつだ",
            "はらだ",
            "わだ",
            "ふくだ",
            "おおた",
            "うえだ",
            "もりた",
            "たむら",
            "たけだ",
            "むらた",
            "にった",
            "おがわ",
            "なかがわ",
            "あおき",
            "きのした",
            "おおしま",
            "しまだ",
            "ふじわら",
            "みうら",
        ]

        self.analysis_results = {
            "total_analyzed": 0,
            "surname_only_cases": [],
            "too_short_cases": [],
            "incomplete_cases": [],
            "good_cases": [],
            "suspicious_cases": [],
        }

    async def get_all_members(self, session):
        """Fetch all Members records"""
        all_records = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(
                f"{self.base_url}/Members (議員)", headers=self.headers, params=params
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
                    return []

        return all_records

    def analyze_kana_completeness(self, name, name_kana):
        """Analyze if kana reading is complete or just surname"""
        if not name or not name_kana:
            return "missing", "Missing name or kana"

        name = name.strip()
        name_kana = name_kana.strip()

        # Skip placeholder patterns
        if any(
            pattern in name_kana.lower()
            for pattern in ["たなかたろう", "さとうはなこ", "やまだ"]
        ):
            return "placeholder", "Known placeholder pattern"

        # Analyze length relationship
        name_len = len(name)
        kana_len = len(name_kana)

        # For Japanese names, typical patterns:
        # 2-character name (田中) should have 3+ kana (たなか)
        # 3-character name (田中太郎) should have 5+ kana (たなかたろう)
        # 4-character name (長谷川太郎) should have 7+ kana (はせがわたろう)

        expected_min_kana = name_len * 1.5  # Rough estimate

        if kana_len < expected_min_kana:
            # Check if it's likely a surname-only reading
            if any(surname in name_kana for surname in self.common_surnames):
                if name_len > 2:  # Multi-character name but short kana
                    return (
                        "surname_only",
                        f"Likely surname-only: {name} → {name_kana} (expected ≥{expected_min_kana:.0f} kana)",
                    )

            return (
                "too_short",
                f"Too short: {kana_len} kana for {name_len} kanji (expected ≥{expected_min_kana:.0f})",
            )

        # Check for specific surname-only patterns
        surname_only_patterns = [
            (
                lambda n, k: len(n) >= 3
                and len(k) <= 4
                and any(s in k for s in self.common_surnames),
                "3+ char name with ≤4 kana",
            ),
            (
                lambda n, k: len(n) >= 4
                and len(k) <= 5
                and any(s in k for s in self.common_surnames),
                "4+ char name with ≤5 kana",
            ),
        ]

        for pattern_func, description in surname_only_patterns:
            if pattern_func(name, name_kana):
                return "surname_only", description

        # Check for suspicious patterns
        if kana_len == name_len:
            return "suspicious", "Kana length equals kanji length (unusual)"

        if kana_len < 3 and name_len > 1:
            return "suspicious", "Very short kana for multi-character name"

        return "good", "Appears to be complete reading"

    async def run_incomplete_analysis(self):
        """Run comprehensive analysis of incomplete kana readings"""
        print("🔍 Starting Incomplete Name_Kana Analysis...")
        print("🎯 Identifying surname-only and incomplete readings")

        async with aiohttp.ClientSession() as session:
            # Get all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)

            if not all_records:
                print("❌ No records found!")
                return

            print(f"📊 Analyzing {len(all_records)} Members records")

            # Analyze each record
            print("\n🔍 Analyzing kana completeness...")

            for record in all_records:
                fields = record.get("fields", {})
                name = fields.get("Name", "")
                name_kana = fields.get("Name_Kana", "")

                if name:
                    self.analysis_results["total_analyzed"] += 1

                    analysis_type, reason = self.analyze_kana_completeness(
                        name, name_kana
                    )

                    record_info = {
                        "id": record["id"],
                        "name": name,
                        "current_kana": name_kana,
                        "house": fields.get("House", ""),
                        "constituency": fields.get("Constituency", ""),
                        "reason": reason,
                        "name_length": len(name),
                        "kana_length": len(name_kana) if name_kana else 0,
                    }

                    if analysis_type == "surname_only":
                        self.analysis_results["surname_only_cases"].append(record_info)
                    elif analysis_type == "too_short":
                        self.analysis_results["too_short_cases"].append(record_info)
                    elif analysis_type == "suspicious":
                        self.analysis_results["suspicious_cases"].append(record_info)
                    elif analysis_type == "good":
                        self.analysis_results["good_cases"].append(record_info)

            # Print detailed analysis
            self.print_incomplete_analysis_report()

            # Save detailed results
            await self.save_incomplete_analysis_results()

            return self.analysis_results

    def print_incomplete_analysis_report(self):
        """Print comprehensive incomplete analysis report"""
        results = self.analysis_results

        print(f"\n{'=' * 80}")
        print("🔍 INCOMPLETE NAME_KANA ANALYSIS REPORT")
        print(f"{'=' * 80}")

        print("📊 ANALYSIS SUMMARY:")
        print(f"   Total analyzed: {results['total_analyzed']}")
        print(f"   ✅ Complete readings: {len(results['good_cases'])}")
        print(f"   ⚠️ Surname-only cases: {len(results['surname_only_cases'])}")
        print(f"   🔤 Too short cases: {len(results['too_short_cases'])}")
        print(f"   ❓ Suspicious cases: {len(results['suspicious_cases'])}")

        total_incomplete = (
            len(results["surname_only_cases"])
            + len(results["too_short_cases"])
            + len(results["suspicious_cases"])
        )
        print(f"   🎯 Total needing fixes: {total_incomplete}")

        # Show surname-only examples
        if results["surname_only_cases"]:
            print("\n⚠️ SURNAME-ONLY CASES (Top 15):")
            for i, item in enumerate(results["surname_only_cases"][:15], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       {item['reason']}")
                print(f"       ({item['house']}, {item['constituency']})")

        # Show too short examples
        if results["too_short_cases"]:
            print("\n🔤 TOO SHORT CASES (Top 10):")
            for i, item in enumerate(results["too_short_cases"][:10], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       {item['reason']}")

        # Show suspicious examples
        if results["suspicious_cases"]:
            print("\n❓ SUSPICIOUS CASES (Top 5):")
            for i, item in enumerate(results["suspicious_cases"][:5], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       {item['reason']}")

        # Calculate completeness rate
        if results["total_analyzed"] > 0:
            completeness_rate = (
                len(results["good_cases"]) / results["total_analyzed"]
            ) * 100
            print("\n📈 COMPLETENESS METRICS:")
            print(f"   Current completeness rate: {completeness_rate:.1f}%")

            if completeness_rate >= 95:
                print("   🏆 EXCELLENT completeness!")
            elif completeness_rate >= 90:
                print("   🎯 VERY GOOD completeness")
            elif completeness_rate >= 80:
                print("   👍 GOOD completeness")
            else:
                print("   ⚠️ NEEDS IMPROVEMENT - many incomplete readings")

    async def save_incomplete_analysis_results(self):
        """Save detailed incomplete analysis results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"members_incomplete_kana_analysis_{timestamp}.json"

        analysis_data = {
            "analysis_date": datetime.now().isoformat(),
            "analysis_results": self.analysis_results,
            "summary": {
                "total_analyzed": self.analysis_results["total_analyzed"],
                "complete_readings": len(self.analysis_results["good_cases"]),
                "surname_only_cases": len(self.analysis_results["surname_only_cases"]),
                "too_short_cases": len(self.analysis_results["too_short_cases"]),
                "suspicious_cases": len(self.analysis_results["suspicious_cases"]),
                "completeness_rate": (
                    (
                        len(self.analysis_results["good_cases"])
                        / self.analysis_results["total_analyzed"]
                        * 100
                    )
                    if self.analysis_results["total_analyzed"] > 0
                    else 0
                ),
            },
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Detailed incomplete analysis saved: {filename}")


async def main():
    """Main incomplete analysis entry point"""
    analyzer = IncompleteKanaAnalyzer()
    results = await analyzer.run_incomplete_analysis()

    print("\n✅ Incomplete Name_Kana analysis completed!")

    total_incomplete = (
        len(results["surname_only_cases"])
        + len(results["too_short_cases"])
        + len(results["suspicious_cases"])
    )

    if total_incomplete > 0:
        print("\n📋 NEXT STEPS:")
        print(f"   1. Fix {len(results['surname_only_cases'])} surname-only readings")
        print(f"   2. Complete {len(results['too_short_cases'])} too-short readings")
        print(f"   3. Review {len(results['suspicious_cases'])} suspicious readings")
        print("\n🎯 Target: Achieve complete full-name kana readings for all records")
    else:
        print("🎉 All Name_Kana readings appear to be complete!")


if __name__ == "__main__":
    asyncio.run(main())
