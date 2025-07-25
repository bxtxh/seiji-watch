#!/usr/bin/env python3
"""
Complete Name_Kana Fix - Thorough correction of incomplete readings
完全Name_Kana修正 - 不完全読みの徹底修正
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")

# Comprehensive database of correct politician readings
COMPLETE_POLITICIAN_READINGS = {
    # Cases identified as surname-only from analysis
    "岡田克也": "おかだかつや",  # Was: おかだ
    "松本豊": "まつもとゆたか",  # Was: まつもと
    "中川貴": "なかがわたかし",  # Was: なかがわ
    "渡辺喜美": "わたなべよしみ",  # Was: わたなべ
    "高橋光男": "たかはしみつお",  # Was: たかはし
    "太田房江": "おおたふさえ",  # Was: おおた
    # Major political figures - complete readings
    "山口那津男": "やまぐちなつお",  # Already correct but flagged
    "高橋はるみ": "たかはしはるみ",  # Already correct but flagged
    "佐々木さやか": "ささきさやか",  # Already correct but flagged
    "高橋千鶴子": "たかはしちづこ",  # Already correct but flagged
    "佐々木三郎": "ささきさぶろう",  # Already correct but flagged
    # Too short cases - complete readings
    "吉良佳子": "きらよしこ",  # Was: きらけいこ
    "那谷屋正義": "なたやまさよし",  # Was: なたやせいぎ
    "海老原真二": "えびはらしんじ",  # Correct
    "嘉田由紀子": "かだゆきこ",  # Correct
    "志位和夫": "しいかずお",  # Correct
    "吉川ゆうみ": "よしかわゆうみ",  # Correct
    "金子恵美": "かねこえみ",  # Correct but could be かねこめぐみ
    "山谷えり子": "やまたにえりこ",  # Correct
    "大門実紀史": "だいもんみきし",  # Correct
    "野田聖子": "のだせいこ",  # Correct
    # Additional complete readings for major politicians
    "安倍晋三": "あべしんぞう",
    "菅義偉": "すがよしひで",
    "岸田文雄": "きしだふみお",
    "麻生太郎": "あそうたろう",
    "石破茂": "いしばしげる",
    "野田佳彦": "のだよしひこ",
    "枝野幸男": "えだのゆきお",
    "玉木雄一郎": "たまきゆういちろう",
    "福島みずほ": "ふくしまみずほ",
    "河野太郎": "こうのたろう",
    "小泉進次郎": "こいずみしんじろう",
    "加藤勝信": "かとうかつのぶ",
    "茂木敏充": "もてぎとしみつ",
    "田村憲久": "たむらのりひさ",
    "杉尾秀哉": "すぎおひでや",
    "西村康稔": "にしむらやすとし",
    "森山裕": "もりやまゆたか",
    "甘利明": "あまりあきら",
    "羽田雄一郎": "はたゆういちろう",
    "今井絵理子": "いまいえりこ",
    "稲田朋美": "いなだともみ",
    "橋本聖子": "はしもとせいこ",
    "高市早苗": "たかいちさなえ",
    "蓮舫": "れんほう",
    "辻元清美": "つじもときよみ",
    "福山哲郎": "ふくやまてつろう",
    "音喜多駿": "おときたしゅん",
    "川田龍平": "かわだりゅうへい",
    "浜田昌良": "はまだまさよし",
    "吉田忠智": "よしだただとも",
    # Additional common names that might need fixing
    "田中太郎": "たなかたろう",
    "佐藤花子": "さとうはなこ",
    "山田一郎": "やまだいちろう",
    "鈴木次郎": "すずきじろう",
    "森次郎": "もりじろう",
    "中村明": "なかむらあきら",
    "西村誠": "にしむらまこと",
    "清水宏": "しみずひろし",
    "林博": "はやしひろし",
    "池田三郎": "いけださぶろう",
    "前田誠": "まえだまこと",
    "吉田太郎": "よしだたろう",
    "井上博": "いのうえひろし",
    "斎藤正": "さいとうただし",
    "木村明": "きむらあきら",
    # Additional politicians based on common patterns
    "松本龍": "まつもとりゅう",
    "中川正春": "なかがわまさはる",
    "渡辺周": "わたなべしゅう",
    "高橋千秋": "たかはしちあき",
    "太田昭宏": "おおたあきひろ",
    "金子原二郎": "かねこげんじろう",
    "佐藤正久": "さとうまさひさ",
    "山田宏": "やまだひろし",
    "鈴木宗男": "すずきむねお",
    "森喜朗": "もりよしろう",
}

# Enhanced pattern-based kana generation
ENHANCED_KANJI_PATTERNS = {
    # Extended surname patterns
    "田中": "たなか",
    "佐藤": "さとう",
    "鈴木": "すずき",
    "高橋": "たかはし",
    "伊藤": "いとう",
    "渡辺": "わたなべ",
    "山本": "やまもと",
    "中村": "なかむら",
    "小林": "こばやし",
    "加藤": "かとう",
    "吉田": "よしだ",
    "山田": "やまだ",
    "佐々木": "ささき",
    "山口": "やまぐち",
    "松本": "まつもと",
    "井上": "いのうえ",
    "木村": "きむら",
    "林": "はやし",
    "斎藤": "さいとう",
    "清水": "しみず",
    "山崎": "やまざき",
    "森": "もり",
    "阿部": "あべ",
    "池田": "いけだ",
    "橋本": "はしもと",
    "山下": "やました",
    "石川": "いしかわ",
    "中島": "なかじま",
    "前田": "まえだ",
    "藤田": "ふじた",
    "後藤": "ごとう",
    "岡田": "おかだ",
    "長谷川": "はせがわ",
    "村上": "むらかみ",
    "近藤": "こんどう",
    "石田": "いしだ",
    "西村": "にしむら",
    "松田": "まつだ",
    "原田": "はらだ",
    "和田": "わだ",
    "中田": "なかた",
    "平田": "ひらた",
    "小川": "おがわ",
    "中川": "なかがわ",
    "福田": "ふくだ",
    "太田": "おおた",
    "上田": "うえだ",
    "森田": "もりた",
    "那谷屋": "なたや",
    "海老原": "えびはら",
    "嘉田": "かだ",
    "金子": "かねこ",
    "山谷": "やまたに",
    "大門": "だいもん",
    "吉良": "きら",
    # Extended given name patterns
    "太郎": "たろう",
    "次郎": "じろう",
    "三郎": "さぶろう",
    "一郎": "いちろう",
    "四郎": "しろう",
    "五郎": "ごろう",
    "六郎": "ろくろう",
    "七郎": "しちろう",
    "花子": "はなこ",
    "美穂": "みほ",
    "恵子": "けいこ",
    "由美": "ゆみ",
    "直子": "なおこ",
    "真理": "まり",
    "明美": "あけみ",
    "裕子": "ゆうこ",
    "明": "あきら",
    "誠": "まこと",
    "宏": "ひろし",
    "健一": "けんいち",
    "正": "ただし",
    "博": "ひろし",
    "和夫": "かずお",
    "幸男": "ゆきお",
    "裕": "ゆたか",
    "守": "まもる",
    "薫": "かおる",
    "茂": "しげる",
    "克也": "かつや",
    "豊": "ゆたか",
    "貴": "たかし",
    "喜美": "よしみ",
    "光男": "みつお",
    "房江": "ふさえ",
    "佳子": "よしこ",
    "正義": "まさよし",
    "真二": "しんじ",
    "由紀子": "ゆきこ",
    "ゆうみ": "ゆうみ",
    "恵美": "えみ",
    "えり子": "えりこ",
    "実紀史": "みきし",
    "聖子": "せいこ",
    "千鶴子": "ちづこ",
    "はるみ": "はるみ",
    "さやか": "さやか",
    "那津男": "なつお",
    # Single character readings
    "大": "だい",
    "小": "しょう",
    "高": "たか",
    "新": "しん",
    "古": "ふる",
    "東": "ひがし",
    "西": "にし",
    "南": "みなみ",
    "北": "きた",
    "中": "なか",
    "上": "うえ",
    "下": "した",
    "内": "うち",
    "外": "そと",
    "山": "やま",
    "川": "かわ",
    "田": "た",
    "野": "の",
    "原": "はら",
    "沢": "さわ",
    "島": "しま",
    "橋": "はし",
    "本": "もと",
    "元": "もと",
    "末": "すえ",
}


class CompleteKanaFixer:
    """Complete and thorough Name_Kana fixing system"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

        self.fix_results = {
            "total_processed": 0,
            "incomplete_fixed": 0,
            "surname_only_fixed": 0,
            "pattern_improved": 0,
            "already_complete": 0,
            "could_not_improve": 0,
            "errors": 0,
            "corrections_applied": [],
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

    def needs_complete_fix(self, name, name_kana):
        """Determine if kana needs to be completed"""
        if not name or not name_kana:
            return True, "missing"

        name = name.strip()
        name_kana = name_kana.strip()

        # Check for known correct readings first
        if name in COMPLETE_POLITICIAN_READINGS:
            correct_reading = COMPLETE_POLITICIAN_READINGS[name]
            if name_kana != correct_reading:
                return True, "known_correction"

        # Check for placeholder patterns
        if any(
            pattern in name_kana.lower()
            for pattern in ["たなかたろう", "さとうはなこ", "やまだ"]
        ):
            return True, "placeholder"

        # Check length relationship - more sophisticated analysis
        name_len = len(name)
        kana_len = len(name_kana)

        # Expected minimum kana length based on name structure
        if name_len >= 4:  # Like 岡田克也
            expected_min = 6
        elif name_len == 3:  # Like 田中太郎
            expected_min = 5
        else:  # 2 characters
            expected_min = 4

        if kana_len < expected_min:
            return True, "too_short"

        # Check for specific surname-only patterns
        common_surnames = [
            "たなか",
            "さとう",
            "おかだ",
            "まつもと",
            "なかがわ",
            "わたなべ",
            "たかはし",
            "おおた",
        ]
        if any(
            surname in name_kana and len(name_kana) <= len(surname) + 1
            for surname in common_surnames
        ):
            if name_len > 2:
                return True, "surname_only"

        return False, "complete"

    def generate_complete_kana(self, name):
        """Generate complete kana reading for a name"""
        if not name:
            return None

        # Check for exact match first
        if name in COMPLETE_POLITICIAN_READINGS:
            return COMPLETE_POLITICIAN_READINGS[name]

        # Pattern-based generation
        result = ""
        remaining = name

        # Sort patterns by length (longest first)
        sorted_patterns = sorted(
            ENHANCED_KANJI_PATTERNS.items(), key=lambda x: len(x[0]), reverse=True
        )

        # Try to match patterns
        while remaining:
            matched = False
            for kanji, kana in sorted_patterns:
                if remaining.startswith(kanji):
                    result += kana
                    remaining = remaining[len(kanji) :]
                    matched = True
                    break

            if not matched:
                # Try single character
                single_char = remaining[0]
                if single_char in ENHANCED_KANJI_PATTERNS:
                    result += ENHANCED_KANJI_PATTERNS[single_char]
                    remaining = remaining[1:]
                else:
                    # Unknown character - try common readings
                    common_single_readings = {
                        "龍": "りゅう",
                        "周": "しゅう",
                        "春": "はる",
                        "秋": "あき",
                        "夏": "なつ",
                        "冬": "ふゆ",
                        "朝": "あさ",
                        "夜": "よる",
                        "金": "きん",
                        "銀": "ぎん",
                        "鉄": "てつ",
                        "石": "いし",
                        "水": "みず",
                        "火": "ひ",
                        "土": "つち",
                        "木": "き",
                        "花": "はな",
                        "鳥": "とり",
                        "魚": "さかな",
                        "犬": "いぬ",
                        "猫": "ねこ",
                        "馬": "うま",
                        "牛": "うし",
                        "豚": "ぶた",
                    }

                    if single_char in common_single_readings:
                        result += common_single_readings[single_char]
                    else:
                        # Skip unknown character
                        pass
                    remaining = remaining[1:]

        # If we generated a meaningful result, return it
        if result and len(result) >= 4:
            return result

        return None

    async def apply_complete_fixes(self, session, records_to_fix):
        """Apply complete kana fixes"""
        successful_fixes = 0

        for record_info in records_to_fix:
            try:
                update_data = {"fields": {"Name_Kana": record_info["new_kana"]}}

                async with session.patch(
                    f"{self.base_url}/Members (議員)/{record_info['id']}",
                    headers=self.headers,
                    json=update_data,
                ) as response:
                    if response.status == 200:
                        successful_fixes += 1

                        # Track fix type
                        if record_info["fix_type"] == "known_correction":
                            self.fix_results["surname_only_fixed"] += 1
                        elif record_info["fix_type"] in ["too_short", "surname_only"]:
                            self.fix_results["incomplete_fixed"] += 1
                        else:
                            self.fix_results["pattern_improved"] += 1

                        self.fix_results["corrections_applied"].append(record_info)

                    else:
                        self.fix_results["errors"] += 1
                        print(
                            f"   ❌ Error updating {record_info['name']}: {response.status}"
                        )

            except Exception as e:
                self.fix_results["errors"] += 1
                print(f"   ❌ Exception updating {record_info['name']}: {e}")

            # Rate limiting
            await asyncio.sleep(0.05)

        return successful_fixes

    async def run_complete_fix(self):
        """Run complete and thorough kana fix"""
        print("🔧 Starting Complete Members Name_Kana Fix...")
        print("🎯 ULTRA THOROUGH correction of all incomplete readings")

        async with aiohttp.ClientSession() as session:
            # Get all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)

            if not all_records:
                print("❌ No records found!")
                return

            print(f"📊 Processing {len(all_records)} Members records")

            # Identify records needing complete fix
            print("\n🔍 Identifying records needing complete kana fix...")

            records_to_fix = []

            for record in all_records:
                fields = record.get("fields", {})
                name = fields.get("Name", "")
                current_kana = fields.get("Name_Kana", "")

                if name:
                    self.fix_results["total_processed"] += 1

                    needs_fix, fix_type = self.needs_complete_fix(name, current_kana)

                    if needs_fix:
                        if fix_type == "known_correction":
                            new_kana = COMPLETE_POLITICIAN_READINGS[name]
                        else:
                            new_kana = self.generate_complete_kana(name)

                        if new_kana and new_kana != current_kana:
                            records_to_fix.append(
                                {
                                    "id": record["id"],
                                    "name": name,
                                    "current_kana": current_kana,
                                    "new_kana": new_kana,
                                    "fix_type": fix_type,
                                    "house": fields.get("House", ""),
                                    "constituency": fields.get("Constituency", ""),
                                }
                            )
                        else:
                            self.fix_results["could_not_improve"] += 1
                    else:
                        self.fix_results["already_complete"] += 1

            print(f"🔍 Found {len(records_to_fix)} records requiring complete fix")

            if not records_to_fix:
                print("🎉 All Name_Kana readings are already complete!")
                return self.fix_results

            # Create backup
            print("\n💾 Creating backup...")
            backup_data = {
                "backup_date": datetime.now().isoformat(),
                "records_to_fix": len(records_to_fix),
                "corrections": records_to_fix,
            }

            backup_filename = f"members_complete_kana_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Backup saved: {backup_filename}")

            # Show preview of major corrections
            print("\n👀 Preview of complete corrections (first 20):")
            for i, item in enumerate(records_to_fix[:20], 1):
                print(f"   {i:2d}. {item['name']}")
                print(f"       Before: '{item['current_kana']}'")
                print(f"       After:  '{item['new_kana']}'")
                print(f"       ({item['fix_type']})")

            if len(records_to_fix) > 20:
                print(
                    f"   ... and {len(records_to_fix) - 20} more complete corrections"
                )

            # Apply fixes
            print("\n🚀 Applying complete kana corrections...")

            fixed_count = await self.apply_complete_fixes(session, records_to_fix)

            print(f"✅ Applied {fixed_count} complete corrections successfully")

        # Print final summary
        self.print_complete_summary()
        return self.fix_results

    def print_complete_summary(self):
        """Print complete fix summary"""
        results = self.fix_results

        print(f"\n{'=' * 80}")
        print("🔧 COMPLETE NAME_KANA FIX SUMMARY - ULTRA THOROUGH")
        print(f"{'=' * 80}")

        print("📊 PROCESSING SUMMARY:")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   ✅ Already complete: {results['already_complete']}")
        print(f"   🔧 Surname-only fixed: {results['surname_only_fixed']}")
        print(f"   📝 Incomplete fixed: {results['incomplete_fixed']}")
        print(f"   🎯 Pattern improved: {results['pattern_improved']}")
        print(f"   ⚠️ Could not improve: {results['could_not_improve']}")
        print(f"   ❌ Errors: {results['errors']}")

        total_fixed = (
            results["surname_only_fixed"]
            + results["incomplete_fixed"]
            + results["pattern_improved"]
        )
        print(f"\n📈 TOTAL COMPLETE CORRECTIONS APPLIED: {total_fixed}")

        # Show key corrections
        if results["corrections_applied"]:
            print("\n🎯 KEY COMPLETE CORRECTIONS APPLIED:")
            for correction in results["corrections_applied"][:15]:
                print(
                    f"   ✅ {correction['name']}: '{correction['current_kana']}' → '{correction['new_kana']}'"
                )

        # Calculate final completeness estimate
        total_complete = results["already_complete"] + total_fixed
        if results["total_processed"] > 0:
            completeness_rate = (total_complete / results["total_processed"]) * 100
            print(f"\n📈 ESTIMATED FINAL COMPLETENESS RATE: {completeness_rate:.1f}%")

            if completeness_rate >= 98:
                print("🏆 EXCELLENT! Near-perfect completeness achieved!")
            elif completeness_rate >= 95:
                print("🎯 OUTSTANDING! Excellent completeness")
            elif completeness_rate >= 90:
                print("👍 VERY GOOD! High completeness achieved")
            else:
                print("⚠️ Good progress but more improvements needed")


async def main():
    """Main complete fix entry point"""
    fixer = CompleteKanaFixer()
    results = await fixer.run_complete_fix()

    print("\n✅ Complete Name_Kana fix completed!")

    # Save final report
    report_filename = f"members_complete_kana_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, "w", encoding="utf-8") as f:
        json.dump(
            {"completion_date": datetime.now().isoformat(), "fix_results": results},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"💾 Complete fix report saved: {report_filename}")


if __name__ == "__main__":
    asyncio.run(main())
