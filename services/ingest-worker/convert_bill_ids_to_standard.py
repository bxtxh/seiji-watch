#!/usr/bin/env python3
"""
Bill ID標準形式変換スクリプト

Legacy形式 (217-1, 217-2, ...) から標準形式 (SC001, SM001, ...) へ変換
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BillRecord:
    """法案レコード構造"""
    bill_id: str | None
    title: str
    status: str
    stage: str
    submitter: str
    category: str
    url: str
    summary: str | None
    submission_date: str | None


class StandardBillIDGenerator:
    """標準形式Bill ID生成器"""

    def __init__(self):
        self.used_ids = set()

        # 法案ID命名規則
        self.HOUSE_CODES = {
            "衆議院": "H",
            "参議院": "S",
            "両院": "B",
            "": "G"  # 政府提出法案
        }

        self.CATEGORY_CODES = {
            "内閣提出": "C",
            "議員提出": "M",
            "予算関連": "B",
            "条約": "T",
            "承認": "A",
            "その他": "O"
        }

        # カテゴリ名マッピング（日本語→英語コード）
        self.CATEGORY_MAPPING = {
            "税制": "C",  # 内閣提出が多い
            "社会保障": "C",
            "経済": "C",
            "外交": "C",
            "行政": "C",
            "法務": "C",
            "防衛": "C",
            "教育": "C",
            "環境": "C",
            "農林": "C",
            "建設": "C",
            "運輸": "C",
            "通信": "C",
            "エネルギー": "C",
            "地方": "M",  # 議員提出が多い
            "選挙": "M",
            "議会": "M",
            "政治": "M",
            "予算": "B",
            "条約": "T",
            "承認": "A",
            "その他": "O"
        }

    def set_existing_ids(self, existing_ids: set):
        """既存IDをセット"""
        self.used_ids = existing_ids.copy()

    def convert_legacy_to_standard(self, bill: BillRecord, house: str = "参議院") -> str:
        """Legacy形式から標準形式へ変換"""

        # 提出者・カテゴリからコード決定
        category_code = self._get_category_code(bill.submitter, bill.category)

        # 議院コード決定
        house_code = self._get_house_code(house, bill.submitter)

        # 連番生成
        sequence = self._generate_sequence(house_code, category_code)

        # 最終ID
        bill_id = f"{house_code}{category_code}{sequence:03d}"

        # 重複チェック
        if bill_id in self.used_ids:
            for i in range(1, 1000):
                alternative_id = f"{house_code}{category_code}{(sequence + i):03d}"
                if alternative_id not in self.used_ids:
                    bill_id = alternative_id
                    break

        self.used_ids.add(bill_id)
        return bill_id

    def _get_category_code(self, submitter: str, category: str) -> str:
        """カテゴリコードを決定"""
        if not submitter:
            return "O"

        # カテゴリマッピングを優先
        if category and category in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[category]

        # カテゴリ名から部分一致で判定
        if category:
            if "予算" in category:
                return "B"
            elif "条約" in category:
                return "T"
            elif "承認" in category:
                return "A"

        # 提出者ベースの判定
        if "内閣" in submitter or "政府" in submitter:
            return "C"
        elif "議員" in submitter:
            return "M"
        else:
            # デフォルト: 内閣提出として扱う
            return "C"

    def _get_house_code(self, house: str, submitter: str) -> str:
        """議院コードを決定"""
        if not house:
            if submitter and "内閣" in submitter:
                return "G"
            return "B"

        return self.HOUSE_CODES.get(house, "S")  # デフォルト: 参議院

    def _generate_sequence(self, house_code: str, category_code: str) -> int:
        """連番を生成"""
        pattern = f"{house_code}{category_code}"
        max_sequence = 0

        for existing_id in self.used_ids:
            if existing_id.startswith(pattern) and len(existing_id) == 6:
                try:
                    sequence = int(existing_id[2:5])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue

        return max_sequence + 1


def load_bills_from_file(file_path: str) -> list[BillRecord]:
    """ファイルからBillsデータを読み込み"""
    with open(file_path, encoding='utf-8') as f:
        data = json.load(f)

    bills = []
    for bill_data in data.get('bills', []):
        bills.append(BillRecord(
            bill_id=bill_data.get('bill_id', ''),
            title=bill_data.get('title', ''),
            status=bill_data.get('status', ''),
            stage=bill_data.get('stage', ''),
            submitter=bill_data.get('submitter', ''),
            category=bill_data.get('category', ''),
            url=bill_data.get('url', ''),
            summary=bill_data.get('summary'),
            submission_date=bill_data.get('submission_date')
        ))

    return bills


def analyze_legacy_ids(bills: list[BillRecord]) -> dict:
    """Legacy ID分析"""
    analysis = {
        "total_bills": len(bills),
        "legacy_format": 0,
        "standard_format": 0,
        "other_format": 0,
        "categories": {},
        "submitters": {}
    }

    for bill in bills:
        if bill.bill_id:
            if re.match(r'^[0-9]+-[0-9]+$', bill.bill_id):
                analysis["legacy_format"] += 1
            elif re.match(r'^[HSBG][CMBTAO][0-9]{3}$', bill.bill_id):
                analysis["standard_format"] += 1
            else:
                analysis["other_format"] += 1

        # カテゴリ統計
        if bill.category:
            analysis["categories"][bill.category] = analysis["categories"].get(bill.category, 0) + 1

        # 提出者統計
        if bill.submitter:
            analysis["submitters"][bill.submitter] = analysis["submitters"].get(bill.submitter, 0) + 1

    return analysis


def convert_all_bills(bills: list[BillRecord]) -> list[dict]:
    """全法案のBill_IDを標準形式に変換"""
    generator = StandardBillIDGenerator()

    results = []
    for bill in bills:
        try:
            new_id = generator.convert_legacy_to_standard(bill)
            results.append({
                "title": bill.title,
                "legacy_id": bill.bill_id,
                "standard_id": new_id,
                "submitter": bill.submitter,
                "category": bill.category,
                "status": bill.status,
                "url": bill.url
            })
        except Exception as e:
            results.append({
                "title": bill.title,
                "legacy_id": bill.bill_id,
                "standard_id": None,
                "error": str(e)
            })

    return results


def main():
    """メイン処理"""
    print("🔄 Bill ID標準形式変換スクリプト")
    print("Legacy形式 (217-1) → 標準形式 (SC001)")
    print("=" * 60)

    # ファイルから読み込み
    file_path = "bills_mvp_collection_20250714_022926.json"

    try:
        print(f"📂 Step 1: {file_path} からデータ読み込み")
        bills = load_bills_from_file(file_path)
        print(f"読み込み完了: {len(bills)}件")

        # 分析
        print("\n📊 Step 2: 現在のID形式分析")
        analysis = analyze_legacy_ids(bills)

        print(f"  総法案数: {analysis['total_bills']}")
        print(f"  Legacy形式: {analysis['legacy_format']}")
        print(f"  標準形式: {analysis['standard_format']}")
        print(f"  その他形式: {analysis['other_format']}")

        # カテゴリ統計
        print("\n  カテゴリ別統計 (上位10件):")
        for category, count in sorted(analysis['categories'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {category}: {count}件")

        # 提出者統計
        print("\n  提出者別統計 (上位10件):")
        for submitter, count in sorted(analysis['submitters'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {submitter}: {count}件")

        # 標準形式への変換
        if analysis['legacy_format'] > 0:
            print(f"\n🔄 Step 3: 標準形式への変換 ({analysis['legacy_format']}件)")

            conversion_results = convert_all_bills(bills)

            # 変換結果統計
            successful = [r for r in conversion_results if r.get('standard_id')]
            failed = [r for r in conversion_results if not r.get('standard_id')]

            print(f"  変換成功: {len(successful)}件")
            print(f"  変換失敗: {len(failed)}件")

            # 変換例表示
            if successful:
                print("\n  変換例 (先頭10件):")
                for i, result in enumerate(successful[:10]):
                    print(f"    {i+1}. {result['legacy_id']} → {result['standard_id']}")
                    print(f"       {result['title']}")
                    print(f"       提出者: {result['submitter']}, カテゴリ: {result['category']}")
                    print()

            # 変換後のパターン分析
            pattern_count = {}
            for result in successful:
                pattern = result['standard_id'][:2]
                pattern_count[pattern] = pattern_count.get(pattern, 0) + 1

            print("  変換後のIDパターン:")
            for pattern, count in sorted(pattern_count.items()):
                print(f"    {pattern}: {count}件")

            # 結果保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"bill_id_conversion_results_{timestamp}.json"

            output_data = {
                "timestamp": timestamp,
                "source_file": file_path,
                "conversion_summary": {
                    "total_bills": len(bills),
                    "legacy_format": analysis['legacy_format'],
                    "conversion_successful": len(successful),
                    "conversion_failed": len(failed)
                },
                "conversion_results": conversion_results,
                "pattern_statistics": pattern_count
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\n📄 結果保存: {output_file}")

            # CSV形式でも出力（Airtableインポート用）
            csv_file = f"bill_id_conversion_mapping_{timestamp}.csv"
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write("legacy_id,standard_id,title,submitter,category\n")
                for result in successful:
                    f.write(f'"{result["legacy_id"]}","{result["standard_id"]}","{result["title"]}","{result["submitter"]}","{result["category"]}"\n')

            print(f"📄 CSV形式保存: {csv_file}")

            # 完了率計算
            if analysis['legacy_format'] > 0:
                completion_rate = (len(successful) / analysis['legacy_format']) * 100
                print("\n📊 Step 4: 変換完了率")
                print(f"  成功率: {completion_rate:.1f}%")

                if completion_rate >= 95:
                    print("🎉 変換が正常に完了しました！")
                else:
                    print("⚠️  一部の変換に失敗しました。")

        else:
            print("✅ 全ての法案が既に標準形式です。")

        return 0

    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {file_path}")
        return 1
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
