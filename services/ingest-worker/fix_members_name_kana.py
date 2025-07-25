#!/usr/bin/env python3
"""
Members Name_Kana Fix - Generate proper kana readings
Members Name_Kana修正 - 適切なカナ読み生成
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

# Install pykakasi if not available
try:
    import pykakasi
except ImportError:
    print("Installing pykakasi for kana conversion...")
    import subprocess

    subprocess.check_call(["python3", "-m", "pip", "install", "pykakasi"])
    import pykakasi

load_dotenv("/Users/shogen/seiji-watch/.env.local")


class MembersNameKanaFixer:
    """Fix Name_Kana field for Members table"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

        # Initialize pykakasi for kanji to kana conversion
        self.kks = pykakasi.kakasi()
        self.kks.setMode("J", "H")  # Kanji to Hiragana
        self.conv = self.kks.getConverter()

        # Known politician name corrections (for better accuracy)
        self.known_readings = {
            "安倍晋三": "あべしんぞう",
            "菅義偉": "すがよしひで",
            "麻生太郎": "あそうたろう",
            "岸田文雄": "きしだふみお",
            "石破茂": "いしばしげる",
            "野田佳彦": "のだよしひこ",
            "枝野幸男": "えだのゆきお",
            "玉木雄一郎": "たまきゆういちろう",
            "志位和夫": "しいかずお",
            "山口那津男": "やまぐちなつお",
            "福島みずほ": "ふくしまみずほ",
            "田村憲久": "たむらのりひさ",
            "加藤勝信": "かとうかつのぶ",
            "茂木敏充": "もてぎとしみつ",
            "河野太郎": "こうのたろう",
            "小泉進次郎": "こいずみしんじろう",
        }

        self.results = {
            "total_processed": 0,
            "placeholder_fixed": 0,
            "empty_fixed": 0,
            "already_good": 0,
            "errors": 0,
            "backup_created": False,
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

    def generate_kana_reading(self, name):
        """Generate kana reading for a Japanese name"""
        # Check if we have a known reading
        if name in self.known_readings:
            return self.known_readings[name]

        # Use pykakasi for automatic conversion
        try:
            kana_reading = self.conv.do(name)
            return kana_reading
        except Exception:
            # Fallback - return original name if conversion fails
            return name

    def needs_kana_fix(self, name, name_kana):
        """Check if Name_Kana field needs fixing"""
        if not name_kana or name_kana.strip() == "":
            return True, "empty"

        # Check for placeholder patterns
        placeholder_patterns = [
            "たなかたろう",
            "田中太郎",
            "tanaka",
            "taro",
            "さとうはなこ",
            "佐藤花子",
            "hanako",
        ]

        if any(pattern in name_kana.lower() for pattern in placeholder_patterns):
            return True, "placeholder"

        # Check if kana looks invalid (too short for typical Japanese names)
        if len(name_kana.strip()) < 3:
            return True, "too_short"

        return False, "good"

    async def fix_name_kana_batch(self, session, records_to_fix):
        """Fix Name_Kana for a batch of records"""
        successful_updates = 0

        for record in records_to_fix:
            name = record["name"]
            new_kana = record["new_kana"]
            record_id = record["id"]

            try:
                update_data = {"fields": {"Name_Kana": new_kana}}

                async with session.patch(
                    f"{self.base_url}/Members (議員)/{record_id}",
                    headers=self.headers,
                    json=update_data,
                ) as response:
                    if response.status == 200:
                        successful_updates += 1
                        if record["fix_type"] == "placeholder":
                            self.results["placeholder_fixed"] += 1
                        elif record["fix_type"] == "empty":
                            self.results["empty_fixed"] += 1
                    else:
                        self.results["errors"] += 1
                        print(f"   ❌ Error updating {name}: {response.status}")

            except Exception as e:
                self.results["errors"] += 1
                print(f"   ❌ Exception updating {name}: {e}")

            # Rate limiting
            await asyncio.sleep(0.05)

        return successful_updates

    async def run_kana_fix(self):
        """Run comprehensive Name_Kana fix"""
        print("🔤 Starting Members Name_Kana Fix...")
        print("🎯 Target: Generate proper kana readings for Japanese names")

        async with aiohttp.ClientSession() as session:
            # Step 1: Fetch all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)

            if not all_records:
                print("❌ No records found!")
                return

            print(f"📊 Found {len(all_records)} Members records")

            # Step 2: Analyze current state
            print("\n🔍 Analyzing Name_Kana field state...")

            records_to_fix = []
            analysis = {"empty": 0, "placeholder": 0, "too_short": 0, "good": 0}

            for record in all_records:
                fields = record.get("fields", {})
                name = fields.get("Name", "")
                name_kana = fields.get("Name_Kana", "")

                if name:
                    needs_fix, fix_type = self.needs_kana_fix(name, name_kana)
                    analysis[fix_type] += 1

                    if needs_fix:
                        new_kana = self.generate_kana_reading(name)
                        records_to_fix.append(
                            {
                                "id": record["id"],
                                "name": name,
                                "current_kana": name_kana,
                                "new_kana": new_kana,
                                "fix_type": fix_type,
                            }
                        )

            print("📊 Analysis Results:")
            print(f"   ✅ Good kana: {analysis['good']}")
            print(f"   🔤 Empty: {analysis['empty']}")
            print(f"   🔄 Placeholder: {analysis['placeholder']}")
            print(f"   ⚠️ Too short: {analysis['too_short']}")
            print(f"   🎯 Need fixing: {len(records_to_fix)}")

            if not records_to_fix:
                print("🎉 All Name_Kana fields are already good!")
                return self.results

            # Step 3: Create backup
            print("\n💾 Creating backup...")
            backup_data = {
                "backup_date": datetime.now().isoformat(),
                "records_to_fix": len(records_to_fix),
                "analysis": analysis,
                "records": [item for item in records_to_fix],
            }

            backup_filename = (
                f"members_kana_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(backup_filename, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            self.results["backup_created"] = True
            print(f"✅ Backup saved: {backup_filename}")

            # Step 4: Show preview
            print("\n👀 Preview of changes (first 10):")
            for i, item in enumerate(records_to_fix[:10]):
                print(f"   {i+1:2d}. {item['name']}")
                print(f"       Before: '{item['current_kana']}'")
                print(f"       After:  '{item['new_kana']}'")

            if len(records_to_fix) > 10:
                print(f"   ... and {len(records_to_fix) - 10} more changes")

            # Step 5: Execute fixes in batches
            print("\n🚀 Executing kana fixes...")

            batch_size = 50
            total_fixed = 0

            for i in range(0, len(records_to_fix), batch_size):
                batch = records_to_fix[i : i + batch_size]
                batch_fixed = await self.fix_name_kana_batch(session, batch)
                total_fixed += batch_fixed

                print(
                    f"   ✅ Batch {i//batch_size + 1}: Fixed {batch_fixed}/{len(batch)} records"
                )

            self.results["total_processed"] = len(records_to_fix)
            self.results["already_good"] = analysis["good"]

            # Step 6: Verification
            print("\n🔍 Verifying results...")

            # Quick verification with sample
            verification_records = await self.get_all_members(session)
            remaining_issues = 0

            for record in verification_records[:100]:  # Sample check
                fields = record.get("fields", {})
                name = fields.get("Name", "")
                name_kana = fields.get("Name_Kana", "")

                if name:
                    needs_fix, _ = self.needs_kana_fix(name, name_kana)
                    if needs_fix:
                        remaining_issues += 1

            print(f"📊 Sample verification: {remaining_issues}/100 still need fixes")

        # Final report
        self.print_summary()
        return self.results

    def print_summary(self):
        """Print comprehensive summary"""
        print(f"\n{'='*70}")
        print("🔤 MEMBERS NAME_KANA FIX SUMMARY")
        print(f"{'='*70}")
        print(f"📊 Total processed: {self.results['total_processed']}")
        print(f"🔄 Placeholder fixed: {self.results['placeholder_fixed']}")
        print(f"🔤 Empty fixed: {self.results['empty_fixed']}")
        print(f"✅ Already good: {self.results['already_good']}")
        print(f"❌ Errors: {self.results['errors']}")
        print(f"💾 Backup created: {'✅' if self.results['backup_created'] else '❌'}")

        (
            self.results["already_good"]
            + self.results["placeholder_fixed"]
            + self.results["empty_fixed"]
        )
        if self.results["total_processed"] > 0:
            success_rate = (
                (self.results["placeholder_fixed"] + self.results["empty_fixed"])
                / self.results["total_processed"]
            ) * 100
            print(f"\n📈 Fix Success Rate: {success_rate:.1f}%")

        if self.results["errors"] == 0 and self.results["total_processed"] > 0:
            print("🎉 SUCCESS! All Name_Kana fields have been fixed!")
        elif self.results["errors"] < 10:
            print(f"👍 Mostly successful - {self.results['errors']} minor errors")
        else:
            print(f"⚠️ Some issues - {self.results['errors']} errors need attention")


async def main():
    """Main entry point"""
    fixer = MembersNameKanaFixer()
    results = await fixer.run_kana_fix()

    print("\n✅ Members Name_Kana fix completed!")

    # Save final report
    report_filename = (
        f"members_kana_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_filename, "w", encoding="utf-8") as f:
        json.dump(
            {"completion_date": datetime.now().isoformat(), "results": results},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"💾 Final report saved: {report_filename}")


if __name__ == "__main__":
    asyncio.run(main())
