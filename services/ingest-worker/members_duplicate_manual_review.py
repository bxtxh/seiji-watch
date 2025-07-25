#!/usr/bin/env python3
"""
Members Duplicate Manual Review
議員重複データの手動レビュー・統合システム
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


class MembersDuplicateReviewer:
    """Members table duplicate detection and manual review system"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.table_name = "Members (議員)"
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

        # Key fields for duplicate detection
        self.duplicate_keys = ["Name", "Name_Kana", "Constituency", "House"]

        # Quality scoring weights
        self.quality_weights = {
            "Name": 0.25,
            "Name_Kana": 0.20,
            "Constituency": 0.20,
            "House": 0.15,
            "Party": 0.10,
            "Terms_Served": 0.10,
        }

    async def get_all_members_records(
        self, session: aiohttp.ClientSession
    ) -> list[dict]:
        """Fetch all Members records"""
        all_records = []
        offset = None

        while True:
            try:
                params = {"pageSize": 100}
                if offset:
                    params["offset"] = offset

                async with session.get(
                    f"{self.base_url}/{self.table_name}",
                    headers=self.headers,
                    params=params,
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get("records", [])
                        all_records.extend(records)

                        offset = data.get("offset")
                        if not offset:
                            break

                        print(f"📄 Fetched {len(all_records)} members so far...")
                        await asyncio.sleep(0.2)
                    else:
                        print(f"❌ Error fetching records: {response.status}")
                        return []

            except Exception as e:
                print(f"❌ Error in pagination: {e}")
                return []

        print(f"✅ Total members fetched: {len(all_records)}")
        return all_records

    def calculate_record_quality_score(self, fields: dict) -> float:
        """Calculate quality score for a record"""
        score = 0.0

        for field, weight in self.quality_weights.items():
            value = fields.get(field)
            if value and value != "":
                if isinstance(value, list) and len(value) > 0:
                    score += weight
                elif isinstance(value, str) and len(value.strip()) > 0:
                    score += weight
                elif isinstance(value, int | float) and value > 0:
                    score += weight

        return round(score, 3)

    def detect_exact_duplicates(self, records: list[dict]) -> dict[str, list[dict]]:
        """Detect exact duplicates by name"""
        name_groups = {}

        for record in records:
            fields = record.get("fields", {})
            name = fields.get("Name", "").strip()

            if name:
                if name not in name_groups:
                    name_groups[name] = []
                name_groups[name].append(record)

        # Keep only groups with multiple records
        exact_duplicates = {
            name: group for name, group in name_groups.items() if len(group) > 1
        }

        return exact_duplicates

    def detect_potential_duplicates(self, records: list[dict]) -> dict[str, list[dict]]:
        """Detect potential duplicates by multiple criteria"""
        potential_groups = {}

        for record in records:
            fields = record.get("fields", {})

            # Create composite key from multiple fields
            name = fields.get("Name", "").strip()
            name_kana = fields.get("Name_Kana", "").strip()
            constituency = fields.get("Constituency", "").strip()
            house = fields.get("House", "").strip()

            # Skip if essential data is missing
            if not name or not house:
                continue

            # Create multiple potential keys
            keys = []

            # Key 1: Name + House (same person, different constituencies)
            if name and house:
                keys.append(f"name_house:{name}|{house}")

            # Key 2: Name_Kana + House (same reading, same house)
            if name_kana and house:
                keys.append(f"kana_house:{name_kana}|{house}")

            # Key 3: Name + Constituency (same person, same district)
            if name and constituency:
                keys.append(f"name_const:{name}|{constituency}")

            for key in keys:
                if key not in potential_groups:
                    potential_groups[key] = []
                potential_groups[key].append(record)

        # Keep only groups with multiple records
        potential_duplicates = {
            key: group for key, group in potential_groups.items() if len(group) > 1
        }

        return potential_duplicates

    def analyze_duplicate_group(self, group: list[dict]) -> dict:
        """Analyze a group of duplicate records"""
        analysis = {
            "group_size": len(group),
            "records": [],
            "recommended_action": "manual_review",
            "quality_scores": [],
            "suggested_keep": None,
            "merge_conflicts": [],
        }

        for record in group:
            fields = record.get("fields", {})
            quality_score = self.calculate_record_quality_score(fields)

            record_info = {
                "id": record["id"],
                "fields": fields,
                "quality_score": quality_score,
                "created_at": fields.get("Created_At", ""),
                "updated_at": fields.get("Updated_At", ""),
            }

            analysis["records"].append(record_info)
            analysis["quality_scores"].append(quality_score)

        # Sort by quality score (highest first)
        analysis["records"].sort(key=lambda x: x["quality_score"], reverse=True)

        # Suggest which record to keep
        if analysis["records"]:
            analysis["suggested_keep"] = analysis["records"][0]["id"]

        # Detect merge conflicts
        field_values = {}
        for record_info in analysis["records"]:
            for field, value in record_info["fields"].items():
                if field not in field_values:
                    field_values[field] = set()
                if value:
                    field_values[field].add(str(value))

        for field, values in field_values.items():
            if len(values) > 1:
                analysis["merge_conflicts"].append(
                    {"field": field, "values": list(values)}
                )

        # Determine recommended action
        if len(analysis["merge_conflicts"]) == 0:
            analysis["recommended_action"] = "auto_merge"
        elif len(analysis["merge_conflicts"]) <= 2:
            analysis["recommended_action"] = "simple_merge"
        else:
            analysis["recommended_action"] = "complex_merge"

        return analysis

    def print_duplicate_analysis(
        self, duplicate_type: str, groups: dict[str, list[dict]]
    ):
        """Print detailed duplicate analysis"""
        print(f"\n{'='*80}")
        print(f"🔍 {duplicate_type.upper()} ANALYSIS")
        print(f"{'='*80}")

        if not groups:
            print("✅ No duplicates found!")
            return

        total_duplicates = sum(len(group) - 1 for group in groups.values())
        print(f"📊 Groups found: {len(groups)}")
        print(f"📊 Total duplicate records: {total_duplicates}")

        for i, (key, group) in enumerate(groups.items(), 1):
            print(f"\n🔍 Group {i}: {key}")
            print(f"{'─'*60}")

            analysis = self.analyze_duplicate_group(group)

            print(f"📋 Records: {analysis['group_size']}")
            print(f"🎯 Recommended: {analysis['recommended_action']}")
            print(f"⚠️ Conflicts: {len(analysis['merge_conflicts'])}")

            # Show each record in group
            for j, record_info in enumerate(analysis["records"]):
                marker = (
                    "🟢 KEEP"
                    if record_info["id"] == analysis["suggested_keep"]
                    else "🔴 REMOVE"
                )
                print(
                    f"   {marker} Record {j+1} (Q:{record_info['quality_score']}): {record_info['id']}"
                )

                fields = record_info["fields"]
                print(f"      Name: {fields.get('Name', 'N/A')}")
                print(f"      House: {fields.get('House', 'N/A')}")
                print(f"      Constituency: {fields.get('Constituency', 'N/A')}")
                print(f"      Party: {fields.get('Party', 'N/A')}")

            # Show conflicts
            if analysis["merge_conflicts"]:
                print("   ⚠️ Merge Conflicts:")
                for conflict in analysis["merge_conflicts"]:
                    print(f"      {conflict['field']}: {', '.join(conflict['values'])}")

    async def save_duplicate_analysis_report(
        self, exact_groups: dict, potential_groups: dict
    ):
        """Save comprehensive duplicate analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Analyze all groups
        exact_analyses = {}
        for key, group in exact_groups.items():
            exact_analyses[key] = self.analyze_duplicate_group(group)

        potential_analyses = {}
        for key, group in potential_groups.items():
            potential_analyses[key] = self.analyze_duplicate_group(group)

        report = {
            "analysis_date": datetime.now().isoformat(),
            "table_name": self.table_name,
            "summary": {
                "exact_duplicate_groups": len(exact_groups),
                "potential_duplicate_groups": len(potential_groups),
                "total_exact_duplicates": sum(
                    len(group) - 1 for group in exact_groups.values()
                ),
                "total_potential_duplicates": sum(
                    len(group) - 1 for group in potential_groups.values()
                ),
            },
            "exact_duplicates": {
                "groups": exact_analyses,
                "action_summary": {
                    "auto_merge": sum(
                        1
                        for a in exact_analyses.values()
                        if a["recommended_action"] == "auto_merge"
                    ),
                    "simple_merge": sum(
                        1
                        for a in exact_analyses.values()
                        if a["recommended_action"] == "simple_merge"
                    ),
                    "complex_merge": sum(
                        1
                        for a in exact_analyses.values()
                        if a["recommended_action"] == "complex_merge"
                    ),
                    "manual_review": sum(
                        1
                        for a in exact_analyses.values()
                        if a["recommended_action"] == "manual_review"
                    ),
                },
            },
            "potential_duplicates": {
                "groups": potential_analyses,
                "action_summary": {
                    "auto_merge": sum(
                        1
                        for a in potential_analyses.values()
                        if a["recommended_action"] == "auto_merge"
                    ),
                    "simple_merge": sum(
                        1
                        for a in potential_analyses.values()
                        if a["recommended_action"] == "simple_merge"
                    ),
                    "complex_merge": sum(
                        1
                        for a in potential_analyses.values()
                        if a["recommended_action"] == "complex_merge"
                    ),
                    "manual_review": sum(
                        1
                        for a in potential_analyses.values()
                        if a["recommended_action"] == "manual_review"
                    ),
                },
            },
            "recommendations": [
                "Review exact duplicates first (higher confidence)",
                "Auto-merge records with no conflicts",
                "Manually review complex merges",
                "Use quality scores to select best records",
            ],
        }

        filename = f"members_duplicate_analysis_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Duplicate analysis report saved: {filename}")
        return report

    async def run_duplicate_analysis(self):
        """Run comprehensive duplicate analysis"""
        print("🔍 Starting Members duplicate analysis...")

        async with aiohttp.ClientSession() as session:
            # Fetch all records
            all_records = await self.get_all_members_records(session)
            if not all_records:
                print("❌ No records found or fetch failed")
                return

            # Detect exact duplicates
            exact_duplicates = self.detect_exact_duplicates(all_records)
            self.print_duplicate_analysis("exact duplicates", exact_duplicates)

            # Detect potential duplicates
            potential_duplicates = self.detect_potential_duplicates(all_records)
            self.print_duplicate_analysis("potential duplicates", potential_duplicates)

            # Save comprehensive report
            report = await self.save_duplicate_analysis_report(
                exact_duplicates, potential_duplicates
            )

            # Summary
            print(f"\n{'='*80}")
            print("📋 MEMBERS DUPLICATE ANALYSIS SUMMARY")
            print(f"{'='*80}")
            print(f"📊 Total Members: {len(all_records)}")
            print(f"🔍 Exact Duplicate Groups: {len(exact_duplicates)}")
            print(f"🔍 Potential Duplicate Groups: {len(potential_duplicates)}")
            print(
                f"🗑️ Total Records to Review: {report['summary']['total_exact_duplicates'] + report['summary']['total_potential_duplicates']}"
            )

            print("\n🎯 RECOMMENDED ACTIONS:")
            exact_summary = report["exact_duplicates"]["action_summary"]
            potential_summary = report["potential_duplicates"]["action_summary"]

            print(
                f"   ✅ Auto-merge ready: {exact_summary['auto_merge']} exact + {potential_summary['auto_merge']} potential"
            )
            print(
                f"   🔧 Simple merge needed: {exact_summary['simple_merge']} exact + {potential_summary['simple_merge']} potential"
            )
            print(
                f"   🧠 Complex review needed: {exact_summary['complex_merge']} exact + {potential_summary['complex_merge']} potential"
            )
            print(
                f"   👥 Manual review: {exact_summary['manual_review']} exact + {potential_summary['manual_review']} potential"
            )


async def main():
    """Main entry point"""
    reviewer = MembersDuplicateReviewer()
    await reviewer.run_duplicate_analysis()

    print("\n✅ Members duplicate analysis completed!")
    print("📋 Next steps:")
    print("   1. Review the generated analysis report")
    print("   2. Start with auto-merge candidates")
    print("   3. Manually review complex cases")
    print("   4. Implement merge operations")


if __name__ == "__main__":
    asyncio.run(main())
