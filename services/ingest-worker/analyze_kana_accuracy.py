#!/usr/bin/env python3
"""
Members Name_Kana Accuracy Analysis
議員Name_Kana精度分析 - 間違った読み方の特定と修正
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

# Known correct readings for prominent Japanese politicians
CORRECT_POLITICIAN_READINGS = {
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
    
    # Current party leaders and prominent figures
    "枝野幸男": "えだのゆきお",
    "志位和夫": "しいかずお", 
    "山口那津男": "やまぐちなつお",
    "玉木雄一郎": "たまきゆういちろう",
    "福島みずほ": "ふくしまみずほ",
    "立憲民主": "りっけんみんしゅ",
    
    # Cabinet ministers and key figures
    "河野太郎": "こうのたろう",
    "茂木敏充": "もてぎとしみつ",
    "加藤勝信": "かとうかつのぶ",
    "田村憲久": "たむらのりひさ",
    "西村康稔": "にしむらやすとし",
    "丸川珠代": "まるかわたまよ",
    
    # Other known politicians with specific readings
    "羽田雄一郎": "はたゆういちろう",
    "蓮舫": "れんほう",
    "辻元清美": "つじもときよみ",
    "福山哲郎": "ふくやまてつろう",
    "杉尾秀哉": "すぎおひでや",
    "音喜多駿": "おときたしゅん",
    "今井絵理子": "いまいえりこ",
    "川田龍平": "かわだりゅうへい",
    "浜田昌良": "はまだまさよし",
    "吉田忠智": "よしだただとも",
    
    # Names that are commonly mispronounced
    "畑野君枝": "はたのきみえ",
    "桝屋敬悟": "ますやけいご", 
    "松山政司": "まつやままさし",
    "森山裕": "もりやまゆたか",
    "逢沢一郎": "あいざわいちろう",
    "二階俊博": "にかいとしひろ",
    "甘利明": "あまりあきら",
    "下村博文": "しもむらはくぶん",
    "稲田朋美": "いなだともみ",
    "高市早苗": "たかいちさなえ",
    "野田聖子": "のだせいこ",
    "萩生田光一": "はぎうだこういち",
    "世耕弘成": "せこうひろしげ",
    "菅原一秀": "すがわらいっしゅう",
    "梶山弘志": "かじやまひろし",
    "竹本直一": "たけもとなおかず",
    "橋本聖子": "はしもとせいこ",
    "平井卓也": "ひらいたくや",
    "坂本哲志": "さかもとてつし",
    "井上信治": "いのうえしんじ",
    "小此木八郎": "おこのぎはちろう"
}

class KanaAccuracyAnalyzer:
    """Name_Kana accuracy analysis and correction system"""
    
    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }
        
        self.analysis_results = {
            "total_analyzed": 0,
            "definitely_wrong": [],
            "probably_wrong": [],
            "placeholder_issues": [],
            "verified_correct": [],
            "corrections_needed": 0
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

    def analyze_kana_accuracy(self, name, name_kana):
        """Analyze the accuracy of a kana reading"""
        if not name or not name_kana:
            return "missing", "Missing name or kana"
        
        name_kana = name_kana.strip()
        
        # Check for known correct readings
        if name in CORRECT_POLITICIAN_READINGS:
            expected = CORRECT_POLITICIAN_READINGS[name]
            if name_kana == expected:
                return "verified_correct", f"Matches known reading: {expected}"
            else:
                return "definitely_wrong", f"Should be '{expected}', not '{name_kana}'"
        
        # Check for obvious placeholder patterns
        placeholder_patterns = [
            "たなかたろう", "さとうはなこ", "やまだ", "田中太郎", "佐藤花子"
        ]
        if any(pattern in name_kana.lower() for pattern in placeholder_patterns):
            return "placeholder", f"Placeholder pattern detected: {name_kana}"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            (len(name_kana) < 3, "Too short for Japanese name"),
            (len(name_kana) > 12, "Too long for typical Japanese name"),
            (name_kana == name, "Kana same as kanji name"),
            (any(char in name_kana for char in "0123456789"), "Contains numbers"),
            (any(char in name_kana for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "Contains English"),
        ]
        
        for condition, reason in suspicious_patterns:
            if condition:
                return "probably_wrong", reason
        
        # Check for common misreadings based on patterns
        common_mistakes = [
            ("太郎", "たろう", "tarō ending"),
            ("一郎", "いちろう", "ichirō ending"),
            ("次郎", "じろう", "jirō ending"),
            ("三郎", "さぶろう", "saburō ending"),
        ]
        
        for kanji_part, expected_kana, description in common_mistakes:
            if kanji_part in name and expected_kana not in name_kana:
                return "probably_wrong", f"Missing expected {description}"
        
        return "unknown", "Cannot determine accuracy"

    async def run_accuracy_analysis(self):
        """Run comprehensive kana accuracy analysis"""
        print("🔍 Starting Members Name_Kana Accuracy Analysis...")
        print("🎯 Identifying incorrect readings and generating corrections")
        
        async with aiohttp.ClientSession() as session:
            # Get all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)
            
            if not all_records:
                print("❌ No records found!")
                return
            
            print(f"📊 Analyzing {len(all_records)} Members records")
            
            # Analyze each record
            print("\n🔍 Analyzing Name_Kana accuracy...")
            
            for record in all_records:
                fields = record.get('fields', {})
                name = fields.get('Name', '')
                name_kana = fields.get('Name_Kana', '')
                constituency = fields.get('Constituency', '')
                house = fields.get('House', '')
                
                if name:
                    self.analysis_results["total_analyzed"] += 1
                    
                    accuracy_type, reason = self.analyze_kana_accuracy(name, name_kana)
                    
                    record_info = {
                        'id': record['id'],
                        'name': name,
                        'current_kana': name_kana,
                        'house': house,
                        'constituency': constituency,
                        'reason': reason
                    }
                    
                    if accuracy_type == "definitely_wrong":
                        self.analysis_results["definitely_wrong"].append(record_info)
                        self.analysis_results["corrections_needed"] += 1
                    elif accuracy_type == "probably_wrong":
                        self.analysis_results["probably_wrong"].append(record_info)
                        self.analysis_results["corrections_needed"] += 1
                    elif accuracy_type == "placeholder":
                        self.analysis_results["placeholder_issues"].append(record_info)
                        self.analysis_results["corrections_needed"] += 1
                    elif accuracy_type == "verified_correct":
                        self.analysis_results["verified_correct"].append(record_info)
            
            # Print detailed analysis
            self.print_analysis_report()
            
            # Save detailed results
            await self.save_analysis_results()
            
            return self.analysis_results

    def print_analysis_report(self):
        """Print comprehensive analysis report"""
        results = self.analysis_results
        
        print(f"\n{'='*80}")
        print(f"🔍 MEMBERS NAME_KANA ACCURACY ANALYSIS REPORT")
        print(f"{'='*80}")
        
        print(f"📊 ANALYSIS SUMMARY:")
        print(f"   Total analyzed: {results['total_analyzed']}")
        print(f"   ✅ Verified correct: {len(results['verified_correct'])}")
        print(f"   ❌ Definitely wrong: {len(results['definitely_wrong'])}")
        print(f"   ⚠️ Probably wrong: {len(results['probably_wrong'])}")
        print(f"   🔄 Placeholder issues: {len(results['placeholder_issues'])}")
        print(f"   🎯 Total corrections needed: {results['corrections_needed']}")
        
        # Show definitely wrong examples
        if results['definitely_wrong']:
            print(f"\n❌ DEFINITELY WRONG READINGS (Top 10):")
            for i, item in enumerate(results['definitely_wrong'][:10], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       {item['reason']}")
                print(f"       ({item['house']}, {item['constituency']})")
        
        # Show probably wrong examples
        if results['probably_wrong']:
            print(f"\n⚠️ PROBABLY WRONG READINGS (Top 5):")
            for i, item in enumerate(results['probably_wrong'][:5], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       {item['reason']}")
        
        # Show verified correct examples
        if results['verified_correct']:
            print(f"\n✅ VERIFIED CORRECT READINGS (Sample):")
            for i, item in enumerate(results['verified_correct'][:5], 1):
                print(f"   {i:2d}. {item['name']} → {item['current_kana']} ✓")
        
        # Calculate accuracy percentage
        total_checked = len(results['verified_correct']) + results['corrections_needed']
        if total_checked > 0:
            accuracy_rate = (len(results['verified_correct']) / total_checked) * 100
            print(f"\n📈 ACCURACY METRICS:")
            print(f"   Current accuracy rate: {accuracy_rate:.1f}%")
            
            if accuracy_rate >= 90:
                print(f"   🏆 EXCELLENT accuracy!")
            elif accuracy_rate >= 80:
                print(f"   👍 GOOD accuracy")
            elif accuracy_rate >= 70:
                print(f"   ⚠️ MODERATE accuracy - improvements needed")
            else:
                print(f"   ❌ LOW accuracy - significant corrections required")

    async def save_analysis_results(self):
        """Save detailed analysis results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"members_kana_accuracy_analysis_{timestamp}.json"
        
        analysis_data = {
            "analysis_date": datetime.now().isoformat(),
            "analysis_results": self.analysis_results,
            "summary": {
                "total_analyzed": self.analysis_results["total_analyzed"],
                "corrections_needed": self.analysis_results["corrections_needed"],
                "verified_correct": len(self.analysis_results["verified_correct"]),
                "accuracy_rate": (len(self.analysis_results["verified_correct"]) / 
                                (len(self.analysis_results["verified_correct"]) + self.analysis_results["corrections_needed"]) * 100)
                                if (len(self.analysis_results["verified_correct"]) + self.analysis_results["corrections_needed"]) > 0 else 0
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed analysis saved: {filename}")

async def main():
    """Main analysis entry point"""
    analyzer = KanaAccuracyAnalyzer()
    results = await analyzer.run_accuracy_analysis()
    
    print(f"\n✅ Name_Kana accuracy analysis completed!")
    
    if results["corrections_needed"] > 0:
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Review {results['corrections_needed']} identified issues")
        print(f"   2. Apply corrections for definitely wrong readings")
        print(f"   3. Research and verify probably wrong readings")
        print(f"   4. Replace remaining placeholder patterns")
        print(f"\n🎯 Target: Achieve >95% Name_Kana accuracy")
    else:
        print(f"🎉 All Name_Kana readings appear to be accurate!")

if __name__ == "__main__":
    asyncio.run(main())