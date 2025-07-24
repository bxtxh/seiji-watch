#!/usr/bin/env python3
"""
Bill ID修正スクリプト (ファイルベース)

既存のJSONファイルからBillsデータを読み込み、Bill_IDを修正して
結果を確認します。
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


class BillIDGenerator:
    """Bill ID生成器"""

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

    def set_existing_ids(self, existing_ids: set):
        """既存IDをセット"""
        self.used_ids = existing_ids.copy()

    def generate_bill_id(self, bill: BillRecord, house: str = "参議院") -> str:
        """法案に対してBill_IDを生成"""

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

        # カテゴリを優先してチェック
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
            return "O"

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


def analyze_bill_ids(bills: list[BillRecord]) -> dict:
    """Bill IDの分析"""
    analysis = {
        "total_bills": len(bills),
        "has_bill_id": 0,
        "missing_bill_id": 0,
        "invalid_format": 0,
        "existing_ids": set(),
        "missing_bills": [],
        "id_patterns": {}
    }

    for bill in bills:
        if bill.bill_id and bill.bill_id.strip():
            analysis["has_bill_id"] += 1
            analysis["existing_ids"].add(bill.bill_id)

            # フォーマット分析
            if re.match(r'^[HSBG][CMBTAO][0-9]{3}$', bill.bill_id):
                analysis["id_patterns"]["standard"] = analysis["id_patterns"].get(
                    "standard", 0) + 1
            elif re.match(r'^[0-9]+-[0-9]+$', bill.bill_id):
                analysis["id_patterns"]["legacy"] = analysis["id_patterns"].get(
                    "legacy", 0) + 1
            else:
                analysis["id_patterns"]["other"] = analysis["id_patterns"].get(
                    "other", 0) + 1
                analysis["invalid_format"] += 1
        else:
            analysis["missing_bill_id"] += 1
            analysis["missing_bills"].append(bill)

    return analysis


def generate_bill_ids_for_missing(
        bills: list[BillRecord],
        existing_ids: set) -> list[dict]:
    """欠損Bill_IDを生成"""
    generator = BillIDGenerator()
    generator.set_existing_ids(existing_ids)

    results = []
    for bill in bills:
        if not bill.bill_id or not bill.bill_id.strip():
            try:
                new_id = generator.generate_bill_id(bill)
                results.append({
                    "title": bill.title,
                    "original_id": bill.bill_id,
                    "new_id": new_id,
                    "submitter": bill.submitter,
                    "category": bill.category,
                    "status": bill.status
                })
            except Exception as e:
                results.append({
                    "title": bill.title,
                    "original_id": bill.bill_id,
                    "new_id": None,
                    "error": str(e)
                })

    return results


def main():
    """メイン処理"""
    print("🔧 Bill ID修正スクリプト (ファイルベース)")
    print("=" * 50)

    # ファイルから読み込み
    file_path = "bills_mvp_collection_20250714_022926.json"

    try:
        print(f"📂 Step 1: {file_path} からデータ読み込み")
        bills = load_bills_from_file(file_path)
        print(f"読み込み完了: {len(bills)}件")

        # 分析
        print("\n📊 Step 2: Bill ID分析")
        analysis = analyze_bill_ids(bills)

        print(f"  総法案数: {analysis['total_bills']}")
        print(f"  Bill_ID有り: {analysis['has_bill_id']}")
        print(f"  Bill_ID無し: {analysis['missing_bill_id']}")
        print(f"  不正フォーマット: {analysis['invalid_format']}")
        print(
            f"  欠損率: {(analysis['missing_bill_id']/analysis['total_bills'])*100:.1f}%")

        if analysis['id_patterns']:
            print("\n  既存IDパターン:")
            for pattern, count in analysis['id_patterns'].items():
                print(f"    {pattern}: {count}件")

        # 欠損データのサンプル表示
        if analysis['missing_bills']:
            print("\n  欠損データ例 (先頭10件):")
            for i, bill in enumerate(analysis['missing_bills'][:10]):
                print(f"    {i+1}. {bill.title}")
                print(f"       提出者: {bill.submitter}, カテゴリ: {bill.category}")

        # Bill ID生成
        if analysis['missing_bill_id'] > 0:
            print(f"\n🔨 Step 3: Bill ID生成 ({analysis['missing_bill_id']}件)")

            generated_results = generate_bill_ids_for_missing(
                analysis['missing_bills'],
                analysis['existing_ids']
            )

            # 結果表示
            successful = [r for r in generated_results if r.get('new_id')]
            failed = [r for r in generated_results if not r.get('new_id')]

            print(f"  生成成功: {len(successful)}件")
            print(f"  生成失敗: {len(failed)}件")

            if successful:
                print("\n  生成されたID例 (先頭10件):")
                for i, result in enumerate(successful[:10]):
                    print(f"    {i+1}. {result['new_id']}: {result['title']}")
                    print(
                        f"       提出者: {result['submitter']}, カテゴリ: {result['category']}")

            if failed:
                print("\n  ⚠️  生成失敗例:")
                for result in failed[:5]:
                    print(
                        f"    - {result['title']}: {result.get('error', 'Unknown error')}")

            # 結果を保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"bill_id_generation_results_{timestamp}.json"

            output_data = {
                "timestamp": timestamp,
                "source_file": file_path,
                "analysis": {
                    "total_bills": analysis['total_bills'],
                    "has_bill_id": analysis['has_bill_id'],
                    "missing_bill_id": analysis['missing_bill_id'],
                    "invalid_format": analysis['invalid_format'],
                    "id_patterns": analysis['id_patterns']
                },
                "generated_results": generated_results
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\n📄 結果保存: {output_file}")

            # 統計サマリー
            print("\n📊 Step 4: 統計サマリー")

            # 生成されたIDのパターン分析
            pattern_count = {}
            for result in successful:
                pattern = result['new_id'][:2]
                pattern_count[pattern] = pattern_count.get(pattern, 0) + 1

            print("  生成IDパターン:")
            for pattern, count in sorted(pattern_count.items()):
                print(f"    {pattern}: {count}件")

            # 提出者別統計
            submitter_count = {}
            for result in successful:
                submitter = result['submitter']
                submitter_count[submitter] = submitter_count.get(submitter, 0) + 1

            print("\n  提出者別統計:")
            for submitter, count in sorted(
                    submitter_count.items(), key=lambda x: x[1], reverse=True)[
                    :10]:
                print(f"    {submitter}: {count}件")

        print("\n🎉 Bill ID修正処理が完了しました！")

        if analysis['missing_bill_id'] == 0:
            print("✅ 全ての法案にBill_IDが設定されています。")
        else:
            completion_rate = (len(successful) / analysis['missing_bill_id']) * 100
            print(f"📊 修正完了率: {completion_rate:.1f}%")

        return 0

    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {file_path}")
        return 1
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
