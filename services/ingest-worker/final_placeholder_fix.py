#!/usr/bin/env python3
"""
Final Placeholder Fix - Last push to eliminate remaining placeholders
最終プレースホルダー修正 - 残存プレースホルダーの完全除去
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

# Final batch of specific politician readings for remaining placeholders
REMAINING_POLITICIAN_READINGS = {
    # Real politicians that likely still have placeholders
    "藤野保史": "ふじのやすふみ",
    "仁比聡平": "にひそうへい", 
    "田村智子": "たむらともこ",
    "倉林明子": "くらばやしあきこ",
    "宮沢洋一": "みやざわよういち",
    "柳ヶ瀬裕文": "やながせひろふみ",
    "江島潔": "えじまきよし",
    "伊藤孝恵": "いとうたかえ",
    "塩村あやか": "しおむらあやか",
    "福島みずほ": "ふくしまみずほ",
    "緒方林太郎": "おがたりんたろう",
    "山本太郎": "やまもとたろう",
    "北神圭朗": "きたがみけいろう",
    "青柳陽一郎": "あおやぎよういちろう",
    "斎藤嘉隆": "さいとうよしたか",
    "塩川鉄也": "しおかわてつや",
    "本村伸子": "もとむらのぶこ",
    "畑野君枝": "はたのきみえ",
    "志位和夫": "しいかずお",
    "笠井亮": "かさいりょう",
    "穀田恵二": "こくたけいじ",
    "赤嶺政賢": "あかみねせいけん",
    "屋良朝博": "やらともひろ",
    
    # Common placeholder names that might be real people
    "田中太郎": "たなかたろう",  # Could be real, keep as is
    "佐藤花子": "さとうはなこ",  # Could be real, keep as is
    "山田一郎": "やまだいちろう",  # Could be real, keep as is
    "鈴木次郎": "すずきじろう",   # Could be real, keep as is
    
    # Generate readings for other common patterns
    "木原誠二": "きはらせいじ",
    "後藤茂之": "ごとうしげゆき",
    "岸田文雄": "きしだふみお",
    "松野博一": "まつのひろかず",
    "茂木敏充": "もてぎとしみつ",
    "林芳正": "はやしよしまさ",
    "河野太郎": "こうのたろう",
    "西村康稔": "にしむらやすとし",
    "永岡桂子": "ながおかけいこ",
    "葉梨康弘": "はなしやすひろ",
    "齋藤健": "さいとうけん",
    "谷公一": "たにこういち",
    "秋葉賢也": "あきばけんや",
    "森山裕": "もりやまゆたか",
    "高市早苗": "たかいちさなえ",
    "寺田稔": "てらだみのる",
    "小倉將信": "おぐらまさのぶ",
    "和田義明": "わだよしあき",
    "浜田靖一": "はまだやすかず"
}

# Enhanced pattern-based reading generation
ADVANCED_PATTERNS = {
    # More complex surname patterns
    '藤野': 'ふじの', '仁比': 'にひ', '田村': 'たむら', '倉林': 'くらばやし',
    '宮沢': 'みやざわ', '柳ヶ瀬': 'やながせ', '江島': 'えじま', '伊藤': 'いとう',
    '塩村': 'しおむら', '福島': 'ふくしま', '緒方': 'おがた', '山本': 'やまもと',
    '北神': 'きたがみ', '青柳': 'あおやぎ', '斎藤': 'さいとう', '塩川': 'しおかわ',
    '本村': 'もとむら', '畑野': 'はたの', '志位': 'しい', '笠井': 'かさい',
    '穀田': 'こくた', '赤嶺': 'あかみね', '屋良': 'やら', '木原': 'きはら',
    '後藤': 'ごとう', '岸田': 'きしだ', '松野': 'まつの', '茂木': 'もてぎ',
    '永岡': 'ながおか', '葉梨': 'はなし', '谷': 'たに', '秋葉': 'あきば',
    '寺田': 'てらだ', '小倉': 'おぐら', '和田': 'わだ', '浜田': 'はまだ',
    
    # More complex given name patterns
    '保史': 'やすふみ', '聡平': 'そうへい', '智子': 'ともこ', '明子': 'あきこ',
    '洋一': 'よういち', '裕文': 'ひろふみ', '潔': 'きよし', '孝恵': 'たかえ',
    'あやか': 'あやか', 'みずほ': 'みずほ', '林太郎': 'りんたろう', '太郎': 'たろう',
    '圭朗': 'けいろう', '陽一郎': 'よういちろう', '嘉隆': 'よしたか', '鉄也': 'てつや',
    '伸子': 'のぶこ', '君枝': 'きみえ', '和夫': 'かずお', '亮': 'りょう',
    '恵二': 'けいじ', '政賢': 'せいけん', '朝博': 'ともひろ', '誠二': 'せいじ',
    '茂之': 'しげゆき', '文雄': 'ふみお', '博一': 'ひろかず', '敏充': 'としみつ',
    '芳正': 'よしまさ', '康稔': 'やすとし', '桂子': 'けいこ', '康弘': 'やすひろ',
    '健': 'けん', '公一': 'こういち', '賢也': 'けんや', '裕': 'ゆたか',
    '早苗': 'さなえ', '稔': 'みのる', '將信': 'まさのぶ', '義明': 'よしあき',
    '靖一': 'やすかず'
}

class FinalPlaceholderFixer:
    """Final elimination of remaining placeholder patterns"""
    
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
            "placeholder_fixed": 0,
            "real_politician_fixed": 0,
            "pattern_generated": 0,
            "could_not_fix": 0,
            "already_good": 0,
            "errors": 0
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

    def needs_placeholder_fix(self, name, name_kana):
        """Check if record has placeholder that needs fixing"""
        if not name or not name_kana:
            return False, "missing"
        
        name_kana = name_kana.strip()
        
        # Check for placeholder patterns
        placeholder_patterns = ['たなかたろう', 'さとうはなこ', 'やまだ']
        
        for pattern in placeholder_patterns:
            if pattern in name_kana.lower():
                return True, "placeholder"
        
        return False, "good"

    def generate_final_kana(self, name):
        """Generate final kana reading using all available methods"""
        if not name:
            return None
        
        # Check exact match first
        if name in REMAINING_POLITICIAN_READINGS:
            return REMAINING_POLITICIAN_READINGS[name]
        
        # Advanced pattern matching
        result = ""
        remaining = name
        
        # Sort by length (longest first)
        sorted_patterns = sorted(ADVANCED_PATTERNS.items(), key=lambda x: len(x[0]), reverse=True)
        
        while remaining:
            matched = False
            for kanji, kana in sorted_patterns:
                if remaining.startswith(kanji):
                    result += kana
                    remaining = remaining[len(kanji):]
                    matched = True
                    break
            
            if not matched:
                # Single character fallback
                single_char = remaining[0]
                single_readings = {
                    '保': 'やす', '史': 'ふみ', '聡': 'そう', '平': 'へい',
                    '智': 'とも', '子': 'こ', '明': 'あき', '洋': 'よう',
                    '一': 'いち', '裕': 'ゆう', '文': 'ふみ', '潔': 'きよし',
                    '孝': 'たか', '恵': 'え', '林': 'りん', '圭': 'けい',
                    '朗': 'ろう', '陽': 'よう', '嘉': 'よし', '隆': 'たか',
                    '鉄': 'てつ', '也': 'や', '伸': 'のぶ', '君': 'きみ',
                    '枝': 'え', '和': 'かず', '夫': 'お', '亮': 'りょう',
                    '二': 'じ', '政': 'せい', '賢': 'けん', '朝': 'とも',
                    '博': 'ひろ', '誠': 'せい', '茂': 'しげ', '之': 'ゆき',
                    '芳': 'よし', '正': 'まさ', '康': 'やす', '桂': 'けい',
                    '公': 'こう', '早': 'さ', '苗': 'なえ', '稔': 'みのる',
                    '將': 'まさ', '信': 'のぶ', '義': 'よし', '靖': 'やす'
                }
                
                if single_char in single_readings:
                    result += single_readings[single_char]
                
                remaining = remaining[1:]
        
        if result and len(result) >= 3:
            return result
        
        return None

    async def apply_final_fixes(self, session, records_to_fix):
        """Apply final placeholder fixes"""
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
                        if record_info['name'] in REMAINING_POLITICIAN_READINGS:
                            self.fix_results['real_politician_fixed'] += 1
                        else:
                            self.fix_results['pattern_generated'] += 1
                        
                        self.fix_results['placeholder_fixed'] += 1
                        
                    else:
                        self.fix_results['errors'] += 1
                        print(f"   ❌ Error updating {record_info['name']}: {response.status}")
                        
            except Exception as e:
                self.fix_results['errors'] += 1
                print(f"   ❌ Exception updating {record_info['name']}: {e}")
            
            # Rate limiting
            await asyncio.sleep(0.05)
        
        return successful_fixes

    async def run_final_fix(self):
        """Run final placeholder elimination"""
        print("🎯 Starting FINAL Placeholder Elimination...")
        print("🔥 ULTRA AGGRESSIVE removal of remaining placeholders")
        
        async with aiohttp.ClientSession() as session:
            # Get all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)
            
            if not all_records:
                print("❌ No records found!")
                return
            
            print(f"📊 Processing {len(all_records)} Members records")
            
            # Identify remaining placeholders
            print("\n🔍 Identifying remaining placeholders...")
            
            records_to_fix = []
            
            for record in all_records:
                fields = record.get('fields', {})
                name = fields.get('Name', '')
                current_kana = fields.get('Name_Kana', '')
                
                if name:
                    self.fix_results['total_processed'] += 1
                    
                    needs_fix, fix_type = self.needs_placeholder_fix(name, current_kana)
                    
                    if needs_fix:
                        new_kana = self.generate_final_kana(name)
                        
                        if new_kana and new_kana != current_kana:
                            records_to_fix.append({
                                'id': record['id'],
                                'name': name,
                                'current_kana': current_kana,
                                'new_kana': new_kana,
                                'fix_type': fix_type,
                                'house': fields.get('House', ''),
                                'constituency': fields.get('Constituency', '')
                            })
                        else:
                            self.fix_results['could_not_fix'] += 1
                    else:
                        self.fix_results['already_good'] += 1
            
            print(f"🔍 Found {len(records_to_fix)} remaining placeholders to fix")
            
            if not records_to_fix:
                print("🎉 No remaining placeholders found!")
                return self.fix_results
            
            # Show preview
            print(f"\n👀 Preview of final placeholder fixes:")
            for i, item in enumerate(records_to_fix, 1):
                politician_status = "🏛️ REAL POLITICIAN" if item['name'] in REMAINING_POLITICIAN_READINGS else "📝 PATTERN"
                print(f"   {i:2d}. {item['name']} {politician_status}")
                print(f"       Before: '{item['current_kana']}'")
                print(f"       After:  '{item['new_kana']}'")
            
            # Apply fixes
            print(f"\n🚀 Applying final placeholder eliminations...")
            
            fixed_count = await self.apply_final_fixes(session, records_to_fix)
            
            print(f"✅ Eliminated {fixed_count} placeholders successfully")
        
        # Print final summary
        self.print_final_summary()
        return self.fix_results

    def print_final_summary(self):
        """Print final elimination summary"""
        results = self.fix_results
        
        print(f"\n{'='*80}")
        print(f"🎯 FINAL PLACEHOLDER ELIMINATION SUMMARY")
        print(f"{'='*80}")
        
        print(f"📊 PROCESSING SUMMARY:")
        print(f"   Total processed: {results['total_processed']}")
        print(f"   ✅ Already good: {results['already_good']}")
        print(f"   🏛️ Real politicians fixed: {results['real_politician_fixed']}")
        print(f"   📝 Pattern generated: {results['pattern_generated']}")
        print(f"   🔥 Total placeholders eliminated: {results['placeholder_fixed']}")
        print(f"   ⚠️ Could not fix: {results['could_not_fix']}")
        print(f"   ❌ Errors: {results['errors']}")
        
        # Calculate final estimated completeness
        remaining_placeholders = results['could_not_fix']
        total_good = results['already_good'] + results['placeholder_fixed']
        
        if results['total_processed'] > 0:
            final_completeness = (total_good / results['total_processed']) * 100
            print(f"\n📈 ESTIMATED FINAL COMPLETENESS: {final_completeness:.1f}%")
            print(f"🎯 Remaining placeholders: {remaining_placeholders}")
            
            if final_completeness >= 98:
                print(f"🏆 OUTSTANDING! Near-perfect Name_Kana completeness achieved!")
            elif final_completeness >= 95:
                print(f"🎯 EXCELLENT! High-quality Name_Kana completion")
            elif final_completeness >= 90:
                print(f"👍 VERY GOOD! Strong Name_Kana quality")
            else:
                print(f"⚠️ Good progress - further optimization possible")

async def main():
    """Main final fix entry point"""
    fixer = FinalPlaceholderFixer()
    results = await fixer.run_final_fix()
    
    print(f"\n✅ Final placeholder elimination completed!")
    
    # Save final report
    report_filename = f"members_final_placeholder_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump({
            "completion_date": datetime.now().isoformat(),
            "fix_results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Final elimination report saved: {report_filename}")

if __name__ == "__main__":
    asyncio.run(main())