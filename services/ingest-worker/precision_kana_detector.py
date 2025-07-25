#!/usr/bin/env python3
"""
Precision Name_Kana Detector - Zero-defect surname-only detection
精密Name_Kana検出器 - 苗字のみ読みの完全検出
Based on o3 recommendations for critical political data systems
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


class PrecisionKanaDetector:
    """Precision detection system for incomplete kana readings"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

        # Common Japanese surnames for perfect-match detection
        self.common_surnames = {
            "たなか": "田中",
            "さとう": "佐藤",
            "すずき": "鈴木",
            "たかはし": "高橋",
            "いとう": "伊藤",
            "わたなべ": "渡辺",
            "やまもと": "山本",
            "なかむら": "中村",
            "こばやし": "小林",
            "かとう": "加藤",
            "よしだ": "吉田",
            "やまだ": "山田",
            "ささき": "佐々木",
            "やまぐち": "山口",
            "まつもと": "松本",
            "いのうえ": "井上",
            "きむら": "木村",
            "はやし": "林",
            "さいとう": "斎藤",
            "しみず": "清水",
            "やまざき": "山崎",
            "もり": "森",
            "あべ": "阿部",
            "いけだ": "池田",
            "はしもと": "橋本",
            "やました": "山下",
            "いしかわ": "石川",
            "なかじま": "中島",
            "まえだ": "前田",
            "ふじた": "藤田",
            "ごとう": "後藤",
            "おかだ": "岡田",
            "はせがわ": "長谷川",
            "むらかみ": "村上",
            "こんどう": "近藤",
            "いしだ": "石田",
            "にしむら": "西村",
            "まつだ": "松田",
            "はらだ": "原田",
            "わだ": "和田",
            "ふくだ": "福田",
            "おおた": "太田",
            "うえだ": "上田",
            "もりた": "森田",
            "たむら": "田村",
            "たけだ": "武田",
            "むらた": "村田",
            "にった": "新田",
            "おがわ": "小川",
            "なかがわ": "中川",
            "あおき": "青木",
            "きのした": "木下",
            "おおしま": "大島",
            "しまだ": "島田",
            "ふじわら": "藤原",
            "みうら": "三浦",
            "まるやま": "丸山",
            "かねこ": "金子",
            "やすだ": "安田",
            "ほんだ": "本田",
            "たにぐち": "谷口",
            "みやざき": "宮崎",
            "おおの": "大野",
            "なかの": "中野",
            "おの": "小野",
            "のぐち": "野口",
            "のだ": "野田",
            "おおつか": "大塚",
            "こまつ": "小松",
            "まつお": "松尾",
            "みやもと": "宮本",
        }

        self.detection_results = {
            "total_analyzed": 0,
            "length_ratio_flags": [],
            "perfect_match_flags": [],
            "morpheme_count_flags": [],
            "fuzzy_length_flags": [],
            "combined_high_confidence": [],
            "already_complete": [],
            "critical_issues": [],
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

    def normalize_kana(self, kana_text):
        """Normalize kana text for comparison"""
        if not kana_text:
            return ""

        # Convert to hiragana, strip spaces, normalize
        normalized = kana_text.strip().lower()

        # Convert katakana to hiragana (basic conversion)
        katakana_to_hiragana = str.maketrans(
            "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンー",
            "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんー",
        )
        normalized = normalized.translate(katakana_to_hiragana)

        return normalized

    def apply_length_ratio_rule(self, name, name_kana):
        """Rule A: Length-ratio detection (kana_len < kanji_len × 1.3)"""
        if not name or not name_kana:
            return False, "Missing data"

        kanji_len = len(name)
        kana_len = len(self.normalize_kana(name_kana))

        # For politicians, expect at least 1.3x length ratio
        expected_min = kanji_len * 1.3

        if kana_len < expected_min:
            return True, f"Length ratio: {kana_len}/{kanji_len} < {expected_min:.1f}"

        return False, "Length ratio OK"

    def apply_perfect_match_rule(self, name, name_kana):
        """Rule B: Perfect surname match detection"""
        if not name or not name_kana:
            return False, "Missing data"

        normalized_kana = self.normalize_kana(name_kana)

        # Check if kana exactly matches a known surname AND name starts with that
        # surname kanji
        for surname_kana, surname_kanji in self.common_surnames.items():
            if normalized_kana == surname_kana and name.startswith(surname_kanji):
                return True, f"Perfect surname match: {surname_kana} = {surname_kanji}"

        return False, "No perfect surname match"

    def apply_morpheme_count_rule(self, name_kana):
        """Rule C: Morpheme count analysis (simplified)"""
        if not name_kana:
            return False, "Missing kana"

        normalized = self.normalize_kana(name_kana)

        # Simplified morpheme detection - look for common patterns
        # Politicians typically have 2 morphemes (surname + given name)

        # Common surname endings that suggest this is surname-only
        surname_only_patterns = [
            "たなか",
            "さとう",
            "やまだ",
            "すずき",
            "たかはし",
            "おかだ",
            "まつもと",
            "なかがわ",
            "わたなべ",
            "たかはし",
            "おおた",
            "はやし",
            "やまぐち",
            "いとう",
        ]

        # If the entire kana matches a common surname pattern exactly
        if normalized in surname_only_patterns:
            return True, f"Morpheme analysis: '{normalized}' appears to be surname-only"

        # Additional check: very short kana (≤4 chars) for names with 3+ kanji
        if len(normalized) <= 4 and len(normalized) > 0:
            return (
                True,
                f"Morpheme analysis: {len(normalized)} chars too short for full name",
            )

        return False, "Morpheme count OK"

    def apply_fuzzy_length_check(self, name, name_kana):
        """Rule D: Fuzzy length guard for edge cases"""
        if not name or not name_kana:
            return False, "Missing data"

        kanji_len = len(name)
        kana_len = len(self.normalize_kana(name_kana))

        if kanji_len == 0:
            return False, "No kanji"

        ratio = kana_len / kanji_len

        # If ratio is very low, flag for manual review
        if ratio < 1.8:
            return True, f"Fuzzy check: ratio {ratio:.2f} < 1.8 threshold"

        return False, "Fuzzy length OK"

    def comprehensive_detection(self, name, name_kana):
        """Apply all detection rules and determine confidence level"""
        flags = []
        scores = []

        # Apply each rule
        flag_a, reason_a = self.apply_length_ratio_rule(name, name_kana)
        if flag_a:
            flags.append(f"A: {reason_a}")
            scores.append(3)  # High confidence

        flag_b, reason_b = self.apply_perfect_match_rule(name, name_kana)
        if flag_b:
            flags.append(f"B: {reason_b}")
            scores.append(4)  # Very high confidence

        flag_c, reason_c = self.apply_morpheme_count_rule(name_kana)
        if flag_c:
            flags.append(f"C: {reason_c}")
            scores.append(2)  # Medium confidence

        flag_d, reason_d = self.apply_fuzzy_length_check(name, name_kana)
        if flag_d:
            flags.append(f"D: {reason_d}")
            scores.append(1)  # Low confidence, manual review

        # Calculate confidence level
        total_score = sum(scores)
        flag_count = len(flags)

        if total_score >= 6 or flag_count >= 3:
            confidence = "CRITICAL"
        elif total_score >= 4 or flag_count >= 2:
            confidence = "HIGH"
        elif total_score >= 2:
            confidence = "MEDIUM"
        elif flag_count >= 1:
            confidence = "LOW"
        else:
            confidence = "COMPLETE"

        return flags, confidence, total_score

    async def run_precision_detection(self):
        """Run comprehensive precision detection analysis"""
        print("🔍 Starting PRECISION Name_Kana Detection...")
        print("🎯 Zero-defect detection for critical political data")

        async with aiohttp.ClientSession() as session:
            # Get all records
            print("\n📄 Fetching Members records...")
            all_records = await self.get_all_members(session)

            if not all_records:
                print("❌ No records found!")
                return

            print(
                f"📊 Analyzing {len(all_records)} Members records with precision rules"
            )

            # Apply precision detection to each record
            for record in all_records:
                fields = record.get("fields", {})
                name = fields.get("Name", "")
                name_kana = fields.get("Name_Kana", "")

                if name:
                    self.detection_results["total_analyzed"] += 1

                    flags, confidence, score = self.comprehensive_detection(
                        name, name_kana
                    )

                    record_info = {
                        "id": record["id"],
                        "name": name,
                        "current_kana": name_kana,
                        "house": fields.get("House", ""),
                        "constituency": fields.get("Constituency", ""),
                        "flags": flags,
                        "confidence": confidence,
                        "score": score,
                        "kanji_length": len(name),
                        "kana_length": len(self.normalize_kana(name_kana)),
                    }

                    # Categorize by confidence level
                    if confidence == "CRITICAL":
                        self.detection_results["critical_issues"].append(record_info)
                    elif confidence == "HIGH":
                        self.detection_results["combined_high_confidence"].append(
                            record_info
                        )
                    elif confidence == "MEDIUM":
                        self.detection_results["fuzzy_length_flags"].append(record_info)
                    elif confidence == "LOW":
                        self.detection_results["morpheme_count_flags"].append(
                            record_info
                        )
                    else:
                        self.detection_results["already_complete"].append(record_info)

            # Print detailed detection report
            self.print_precision_report()

            # Save detailed results
            await self.save_precision_results()

            return self.detection_results

    def print_precision_report(self):
        """Print comprehensive precision detection report"""
        results = self.detection_results

        print(f"\n{'='*80}")
        print("🔍 PRECISION NAME_KANA DETECTION REPORT")
        print(f"{'='*80}")

        print("📊 DETECTION SUMMARY:")
        print(f"   Total analyzed: {results['total_analyzed']}")
        print(f"   🚨 CRITICAL issues: {len(results['critical_issues'])}")
        print(f"   ⚠️ HIGH confidence flags: {len(results['combined_high_confidence'])}")
        print(f"   📝 MEDIUM confidence: {len(results['fuzzy_length_flags'])}")
        print(f"   💡 LOW confidence: {len(results['morpheme_count_flags'])}")
        print(f"   ✅ Complete readings: {len(results['already_complete'])}")

        total_flagged = (
            len(results["critical_issues"])
            + len(results["combined_high_confidence"])
            + len(results["fuzzy_length_flags"])
            + len(results["morpheme_count_flags"])
        )

        print(f"   🎯 Total requiring fixes: {total_flagged}")

        # Show critical issues
        if results["critical_issues"]:
            print("\n🚨 CRITICAL ISSUES (Definite surname-only):")
            for i, item in enumerate(results["critical_issues"][:10], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       Flags: {'; '.join(item['flags'])}")
                print(
                    f"       Confidence: {item['confidence']} (Score: {item['score']})"
                )
                print(f"       ({item['house']}, {item['constituency']})")

        # Show high confidence issues
        if results["combined_high_confidence"]:
            print("\n⚠️ HIGH CONFIDENCE ISSUES (Very likely surname-only):")
            for i, item in enumerate(results["combined_high_confidence"][:10], 1):
                print(f"   {i:2d}. {item['name']} → '{item['current_kana']}'")
                print(f"       Flags: {'; '.join(item['flags'])}")
                print(
                    f"       Confidence: {item['confidence']} (Score: {item['score']})"
                )

        # Calculate precision metrics
        if results["total_analyzed"] > 0:
            critical_rate = (
                len(results["critical_issues"]) / results["total_analyzed"]
            ) * 100
            flagged_rate = (total_flagged / results["total_analyzed"]) * 100
            complete_rate = (
                len(results["already_complete"]) / results["total_analyzed"]
            ) * 100

            print("\n📈 PRECISION METRICS:")
            print(f"   Critical issues rate: {critical_rate:.1f}%")
            print(f"   Total flagged rate: {flagged_rate:.1f}%")
            print(f"   Complete readings rate: {complete_rate:.1f}%")

            if critical_rate == 0:
                print("   🏆 NO CRITICAL ISSUES DETECTED!")
            elif critical_rate < 2:
                print("   🎯 Low critical rate - excellent baseline")
            elif critical_rate < 5:
                print("   ⚠️ Moderate critical rate - needs attention")
            else:
                print("   🚨 HIGH CRITICAL RATE - immediate action required")

    async def save_precision_results(self):
        """Save detailed precision detection results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"precision_kana_detection_report_{timestamp}.json"

        detection_data = {
            "detection_date": datetime.now().isoformat(),
            "detection_results": self.detection_results,
            "methodology": {
                "rules_applied": [
                    "A: Length-ratio rule (kana_len < kanji_len × 1.3)",
                    "B: Perfect surname match detection",
                    "C: Morpheme count analysis",
                    "D: Fuzzy length guard (ratio < 1.8)",
                ],
                "confidence_levels": {
                    "CRITICAL": "Score ≥6 or flags ≥3 - Definite surname-only",
                    "HIGH": "Score ≥4 or flags ≥2 - Very likely surname-only",
                    "MEDIUM": "Score ≥2 - Possibly incomplete",
                    "LOW": "Score ≥1 - Manual review recommended",
                    "COMPLETE": "No flags - Reading appears complete",
                },
            },
            "summary": {
                "total_analyzed": self.detection_results["total_analyzed"],
                "critical_issues": len(self.detection_results["critical_issues"]),
                "high_confidence": len(
                    self.detection_results["combined_high_confidence"]
                ),
                "total_flagged": (
                    len(self.detection_results["critical_issues"])
                    + len(self.detection_results["combined_high_confidence"])
                    + len(self.detection_results["fuzzy_length_flags"])
                    + len(self.detection_results["morpheme_count_flags"])
                ),
                "complete_readings": len(self.detection_results["already_complete"]),
            },
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(detection_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Precision detection report saved: {filename}")


async def main():
    """Main precision detection entry point"""
    detector = PrecisionKanaDetector()
    results = await detector.run_precision_detection()

    print("\n✅ Precision Name_Kana detection completed!")

    total_flagged = (
        len(results["critical_issues"])
        + len(results["combined_high_confidence"])
        + len(results["fuzzy_length_flags"])
        + len(results["morpheme_count_flags"])
    )

    if total_flagged > 0:
        print("\n📋 NEXT STEPS FOR ZERO-DEFECT QUALITY:")
        print(
            f"   1. 🚨 Fix {len(results['critical_issues'])} CRITICAL surname-only issues"
        )
        print(
            f"   2. ⚠️ Fix {len(results['combined_high_confidence'])} HIGH confidence issues"
        )
        print(
            f"   3. 📝 Review {len(results['fuzzy_length_flags'])} MEDIUM confidence cases"
        )
        print(
            f"   4. 💡 Manual review {len(results['morpheme_count_flags'])} LOW confidence cases"
        )
        print(
            "\n🎯 Target: Achieve 100% complete full-name readings for national political database"
        )
    else:
        print("🎉 All Name_Kana readings passed precision detection!")


if __name__ == "__main__":
    asyncio.run(main())
