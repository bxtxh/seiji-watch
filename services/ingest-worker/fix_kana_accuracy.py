#!/usr/bin/env python3
"""
Members Name_Kana Accuracy Fix
議員Name_Kana精度修正 - 正確な読み方への修正
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

# Comprehensive correct readings database for Japanese politicians
CORRECT_POLITICIAN_READINGS = {
    # Definitely wrong cases identified in analysis
    "杉尾秀哉": "すぎおひでや",  # Was: すぎおしゅうや
    "西村康稔": "にしむらやすとし",  # Was: にしむらやすしみのる
    "森山裕": "もりやまゆたか",  # Was: もりやまひろし
    "甘利明": "あまりあきら",  # Was: あまりめい
    "羽田雄一郎": "はたゆういちろう",  # Was: たなかたろう
    "今井絵理子": "いまいえりこ",  # Was: たなかたろう
    "稲田朋美": "いなだともみ",  # Was: たなかたろう
    "橋本聖子": "はしもとせいこ",  # Was: たなかたろう
    "高市早苗": "たかいちさなえ",  # Was: たなかたろう

    # Prime Ministers and major political figures
    "安倍晋三": "あべしんぞう",
    "菅義偉": "すがよしひで",
    "岸田文雄": "きしだふみお",
    "麻生太郎": "あそうたろう",
    "石破茂": "いしばしげる",
    "野田佳彦": "のだよしひこ",
    "鳩山由紀夫": "はとやまゆきお",
    "福田康夫": "ふくだやすお",
    "小泉純一郎": "こいずみじゅんいちろう",
    "小泉進次郎": "こいずみしんじろう",

    # Current party leaders
    "枝野幸男": "えだのゆきお",
    "志位和夫": "しいかずお",
    "山口那津男": "やまぐちなつお",
    "玉木雄一郎": "たまきゆういちろう",
    "福島みずほ": "ふくしまみずほ",

    # Cabinet ministers and key figures
    "河野太郎": "こうのたろう",
    "茂木敏充": "もてぎとしみつ",
    "加藤勝信": "かとうかつのぶ",
    "田村憲久": "たむらのりひさ",
    "丸川珠代": "まるかわたまよ",
    "野田聖子": "のだせいこ",
    "萩生田光一": "はぎうだこういち",
    "世耕弘成": "せこうひろしげ",
    "菅原一秀": "すがわらいっしゅう",
    "梶山弘志": "かじやまひろし",
    "竹本直一": "たけもとなおかず",
    "平井卓也": "ひらいたくや",
    "坂本哲志": "さかもとてつし",
    "井上信治": "いのうえしんじ",
    "小此木八郎": "おこのぎはちろう",

    # Opposition party leaders and prominent figures
    "蓮舫": "れんほう",
    "辻元清美": "つじもときよみ",
    "福山哲郎": "ふくやまてつろう",
    "音喜多駿": "おときたしゅん",
    "川田龍平": "かわだりゅうへい",
    "浜田昌良": "はまだまさよし",
    "吉田忠智": "よしだただとも",

    # Other important politicians
    "逢沢一郎": "あいざわいちろう",
    "二階俊博": "にかいとしひろ",
    "下村博文": "しもむらはくぶん",

    # Common name patterns corrections
    "田中太郎": "たなかたろう",
    "佐藤花子": "さとうはなこ",
    "山田一郎": "やまだいちろう",
    "鈴木次郎": "すずきじろう",
    "森次郎": "もりじろう",  # Fix the "つぐろう" error

    # Additional corrections based on common patterns
    "中村明": "なかむらあきら",
    "西村誠": "にしむらまこと",
    "清水宏": "しみずひろし",
    "林博": "はやしひろし",
    "池田三郎": "いけださぶろう",
    "前田誠": "まえだまこと",
    "吉田太郎": "よしだたろう",
    "井上博": "いのうえひろし",
    "斎藤正": "さいとうただし",
    "木村明": "きむらあきら"
}


class KanaAccuracyFixer:
    """Fix Name_Kana accuracy issues"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }

        self.fix_results = {
            "total_processed": 0,
            "definitely_wrong_fixed": 0,
            "placeholder_fixed": 0,
            "pattern_fixed": 0,
            "already_correct": 0,
            "errors": 0,
            "corrections_applied": []
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
                f"{self.base_url}/Members (議員)",
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get('records', [])
                    all_records.extend(records)

                    offset = data.get('offset')
                    if not offset:
                        break
                else:
                    print(f"❌ Error fetching records: {response.status}")
                    return []

        return all_records

    def determine_correction(self, name, current_kana):
        """Determine if and how to correct a kana reading"""
        if not name or not current_kana:
            return None, "missing_data"

        current_kana = current_kana.strip()

        # Check for known correct readings
        if name in CORRECT_POLITICIAN_READINGS:
            correct_reading = CORRECT_POLITICIAN_READINGS[name]
            if current_kana != correct_reading:
                return correct_reading, "known_correction"
            else:
                return None, "already_correct"

        # Check for placeholder patterns that need generic fixes
        placeholder_patterns = [
            ("たなかたろう", "Unknown politician reading needed"),
            ("さとうはなこ", "Unknown politician reading needed"),
            ("やまだ", "Unknown politician reading needed")
        ]

        for pattern, reason in placeholder_patterns:
            if pattern in current_kana.lower():
                # Try to generate a better reading based on name parts
                better_reading = self.generate_better_reading(name)
                if better_reading and better_reading != current_kana:
                    return better_reading, "placeholder_fix"

        return None, "no_correction_needed"

    def generate_better_reading(self, name):
        """Generate a better kana reading for unknown names"""
        # Common surname readings
        surname_readings = {
            '田中': 'たなか', '佐藤': 'さとう', '鈴木': 'すずき', '高橋': 'たかはし',
            '伊藤': 'いとう', '渡辺': 'わたなべ', '山本': 'やまもと', '中村': 'なかむら',
            '小林': 'こばやし', '加藤': 'かとう', '吉田': 'よしだ', '山田': 'やまだ',
            '佐々木': 'ささき', '山口': 'やまぐち', '松本': 'まつもと', '井上': 'いのうえ',
            '木村': 'きむら', '林': 'はやし', '斎藤': 'さいとう', '清水': 'しみず',
            '山崎': 'やまざき', '森': 'もり', '阿部': 'あべ', '池田': 'いけだ',
            '橋本': 'はしもと', '山下': 'やました', '石川': 'いしかわ', '中島': 'なかじま',
            '前田': 'まえだ', '藤田': 'ふじた', '後藤': 'ごとう', '岡田': 'おかだ',
            '長谷川': 'はせがわ', '村上': 'むらかみ', '近藤': 'こんどう', '石田': 'いしだ',
            '西村': 'にしむら', '松田': 'まつだ', '原田': 'はらだ', '和田': 'わだ'
        }

        # Common given name readings
        given_name_readings = {
            '太郎': 'たろう', '次郎': 'じろう', '三郎': 'さぶろう', '一郎': 'いちろう',
            '花子': 'はなこ', '美穂': 'みほ', '恵子': 'けいこ', '由美': 'ゆみ',
            '明': 'あきら', '誠': 'まこと', '宏': 'ひろし', '健一': 'けんいち',
            '正': 'ただし', '博': 'ひろし', '和夫': 'かずお', '幸男': 'ゆきお',
            '裕': 'ゆたか', '守': 'まもる', '薫': 'かおる', '茂': 'しげる'
        }

        # Try to construct reading from parts
        result = ""
        remaining = name

        # First try surnames
        for kanji, kana in surname_readings.items():
            if remaining.startswith(kanji):
                result += kana
                remaining = remaining[len(kanji):]
                break

        # Then try given names
        for kanji, kana in given_name_readings.items():
            if kanji in remaining:
                result += kana
                remaining = remaining.replace(kanji, "", 1)
                break

        # If we got a complete reading, return it
        if result and not remaining:
            return result

        # Otherwise return None to indicate we can't generate a good reading
        return None

    async def apply_kana_corrections(self, session, records_to_fix):
        """Apply kana corrections to records"""
        successful_fixes = 0

        for record_info in records_to_fix:
            try:
                update_data = {
                    "fields": {
                        "Name_Kana": record_info['new_kana']
                    }
                }

                async with session.patch(
                    f"{self.base_url}/Members (議員)/{record_info['id']}",
                    headers=self.headers,
                    json=update_data
                ) as response:
                    if response.status == 200:
                        successful_fixes += 1

                        # Track fix type
                        if record_info['fix_type'] == 'known_correction':
                            self.fix_results['definitely_wrong_fixed'] += 1
                        elif record_info['fix_type'] == 'placeholder_fix':
                            self.fix_results['placeholder_fixed'] += 1
                        else:
                            self.fix_results['pattern_fixed'] += 1

                        self.fix_results['corrections_applied'].append(record_info)

                    else:
                        self.fix_results['errors'] += 1
                        print(
                            f"   ❌ Error updating {record_info['name']}: {response.status}")

            except Exception as e:
                self.fix_results['errors'] += 1
                print(f"   ❌ Exception updating {record_info['name']}: {e}")

            # Rate limiting
            await asyncio.sleep(0.05)

        return successful_fixes

    async def run_accuracy_fix(self):
        """Run comprehensive kana accuracy fix"""
        print("🔧 Starting Members Name_Kana Accuracy Fix...")
        print("🎯 Applying corrections to known incorrect readings")

        async with aiohttp.ClientSession() as session:
            # Get all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)

            if not all_records:
                print("❌ No records found!")
                return

            print(f"📊 Processing {len(all_records)} Members records")

            # Identify corrections needed
            print("\n🔍 Identifying corrections needed...")

            records_to_fix = []

            for record in all_records:
                fields = record.get('fields', {})
                name = fields.get('Name', '')
                current_kana = fields.get('Name_Kana', '')

                if name:
                    self.fix_results['total_processed'] += 1

                    correction, fix_type = self.determine_correction(name, current_kana)

                    if correction:
                        records_to_fix.append({
                            'id': record['id'],
                            'name': name,
                            'current_kana': current_kana,
                            'new_kana': correction,
                            'fix_type': fix_type,
                            'house': fields.get('House', ''),
                            'constituency': fields.get('Constituency', '')
                        })
                    elif fix_type == 'already_correct':
                        self.fix_results['already_correct'] += 1

            print(f"🔍 Found {len(records_to_fix)} records requiring corrections")

            if not records_to_fix:
                print("🎉 All Name_Kana readings are already accurate!")
                return self.fix_results

            # Create backup
            print("\n💾 Creating backup...")
            backup_data = {
                "backup_date": datetime.now().isoformat(),
                "records_to_fix": len(records_to_fix),
                "corrections": records_to_fix
            }

            backup_filename = f"members_kana_accuracy_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Backup saved: {backup_filename}")

            # Show preview of major corrections
            print("\n👀 Preview of corrections (first 10):")
            for i, item in enumerate(records_to_fix[:10], 1):
                print(f"   {i:2d}. {item['name']}")
                print(f"       Before: '{item['current_kana']}'")
                print(f"       After:  '{item['new_kana']}'")
                print(f"       ({item['fix_type']})")

            if len(records_to_fix) > 10:
                print(f"   ... and {len(records_to_fix) - 10} more corrections")

            # Apply corrections
            print("\n🚀 Applying corrections...")

            fixed_count = await self.apply_kana_corrections(session, records_to_fix)

            print(f"✅ Applied {fixed_count} corrections successfully")

        # Print final summary
        self.print_fix_summary()
        return self.fix_results

    def print_fix_summary(self):
        """Print comprehensive fix summary"""
        results = self.fix_results

        print(f"\n{'='*70}")
        print("🔧 MEMBERS NAME_KANA ACCURACY FIX SUMMARY")
        print(f"{'='*70}")

        print("📊 PROCESSING SUMMARY:")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   ✅ Already correct: {results['already_correct']}")
        print(f"   🔧 Definitely wrong fixed: {results['definitely_wrong_fixed']}")
        print(f"   🔄 Placeholder fixed: {results['placeholder_fixed']}")
        print(f"   📝 Pattern fixed: {results['pattern_fixed']}")
        print(f"   ❌ Errors: {results['errors']}")

        total_fixed = results['definitely_wrong_fixed'] + \
            results['placeholder_fixed'] + results['pattern_fixed']
        print(f"\n📈 TOTAL CORRECTIONS APPLIED: {total_fixed}")

        # Show key corrections
        if results['corrections_applied']:
            print("\n🎯 KEY CORRECTIONS APPLIED:")
            for correction in results['corrections_applied'][:10]:
                if correction['fix_type'] == 'known_correction':
                    print(
                        f"   ✅ {correction['name']}: '{correction['current_kana']}' → '{correction['new_kana']}'")

        # Calculate new accuracy estimate
        total_analyzed = results['total_processed']
        estimated_correct = results['already_correct'] + total_fixed
        if total_analyzed > 0:
            estimated_accuracy = (estimated_correct / total_analyzed) * 100
            print(f"\n📈 ESTIMATED NEW ACCURACY RATE: {estimated_accuracy:.1f}%")

            if estimated_accuracy >= 95:
                print("🏆 EXCELLENT! Target accuracy achieved!")
            elif estimated_accuracy >= 90:
                print("🎯 VERY GOOD! Close to target accuracy")
            elif estimated_accuracy >= 80:
                print("👍 GOOD! Significant improvement made")
            else:
                print("⚠️ Further improvements still needed")


async def main():
    """Main fix entry point"""
    fixer = KanaAccuracyFixer()
    results = await fixer.run_accuracy_fix()

    print("\n✅ Name_Kana accuracy fix completed!")

    # Save final report
    report_filename = f"members_kana_accuracy_fix_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump({
            "completion_date": datetime.now().isoformat(),
            "fix_results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"💾 Final report saved: {report_filename}")

if __name__ == "__main__":
    asyncio.run(main())
