#!/usr/bin/env python3
"""
Bill ID生成ロジックのテスト

実際のAirtable接続なしで、Bill ID生成アルゴリズムをテストします。
"""

import re
from dataclasses import dataclass


@dataclass
class BillRecord:
    """法案レコード構造"""
    record_id: str
    bill_id: str | None
    title: str
    submission_date: str | None
    status: str
    stage: str
    submitter: str
    category: str
    diet_session: str | None
    house: str | None


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

    def generate_bill_id(self, bill: BillRecord, session: str = "217") -> str:
        """法案に対してBill_IDを生成"""

        # 提出者・カテゴリからコード決定
        category_code = self._get_category_code(bill.submitter, bill.category)

        # 議院コード決定
        house_code = self._get_house_code(bill.house, bill.submitter)

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

        return self.HOUSE_CODES.get(house, "B")

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


def create_test_data() -> list[BillRecord]:
    """テスト用のサンプルデータを作成"""
    return [

        # 既存IDがある法案
        BillRecord(
            "rec1",
            "HC001",
            "デジタル庁設置法案",
            "2025-01-24",
            "成立",
            "成立",
            "内閣",
            "デジタル",
            "217",
            "衆議院"),
        BillRecord(
            "rec2",
            "SM001",
            "議員報酬改正法案",
            "2025-02-15",
            "審議中",
            "委員会",
            "田中議員",
            "制度",
            "217",
            "参議院"),

        # Bill_IDが欠損している法案
        BillRecord(
            "rec3",
            "",
            "予算関連法案",
            "2025-03-01",
            "審議中",
            "委員会",
            "内閣",
            "予算",
            "217",
            "衆議院"),
        BillRecord(
            "rec4",
            None,
            "地方創生推進法案",
            "2025-03-15",
            "審議中",
            "委員会",
            "山田議員",
            "地方",
            "217",
            "参議院"),
        BillRecord(
            "rec5",
            "  ",
            "環境保護法案",
            "2025-04-01",
            "審議中",
            "委員会",
            "内閣",
            "環境",
            "217",
            ""),
        BillRecord(
            "rec6",
            "",
            "条約批准案",
            "2025-04-15",
            "審議中",
            "委員会",
            "外務大臣",
            "条約",
            "217",
            "両院"),
        BillRecord(
            "rec7",
            "",
            "承認案件",
            "2025-05-01",
            "審議中",
            "委員会",
            "内閣",
            "承認",
            "217",
            "衆議院"),
        BillRecord(
            "rec8",
            "",
            "その他の法案",
            "2025-05-15",
            "審議中",
            "委員会",
            "佐藤議員",
            "その他",
            "217",
            "参議院"),
        BillRecord(
            "rec9",
            "",
            "政府提出法案",
            "2025-06-01",
            "審議中",
            "委員会",
            "内閣",
            "制度",
            "217",
            ""),
        BillRecord(
            "rec10",
            "",
            "無所属議員提出",
            "2025-06-15",
            "審議中",
            "委員会",
            "無所属議員",
            "制度",
            "217",
            "衆議院"),

    ]


def test_bill_id_generation():
    """Bill ID生成ロジックのテスト"""
    print("🧪 Bill ID生成ロジックテスト")
    print("=" * 50)

    # テストデータ準備
    test_bills = create_test_data()

    # 既存IDを抽出
    existing_ids = set()
    missing_bills = []

    for bill in test_bills:
        if bill.bill_id and bill.bill_id.strip():
            existing_ids.add(bill.bill_id.strip())
        else:
            missing_bills.append(bill)

    print("📊 テストデータ:")
    print(f"  総法案数: {len(test_bills)}")
    print(f"  既存ID数: {len(existing_ids)}")
    print(f"  欠損ID数: {len(missing_bills)}")
    print(f"  既存ID: {sorted(existing_ids)}")

    # Generator初期化
    generator = BillIDGenerator()
    generator.set_existing_ids(existing_ids)

    print("\n🔨 Bill ID生成テスト:")
    print("-" * 50)

    generated_ids = []
    for bill in missing_bills:
        try:
            new_id = generator.generate_bill_id(bill)
            generated_ids.append(new_id)

            print(f"✅ {new_id}: {bill.title}")
            print(f"   提出者: {bill.submitter}")
            print(f"   院: {bill.house}")
            print(f"   カテゴリ: {bill.category}")
            print()

        except Exception as e:
            print(f"❌ Error generating ID for {bill.title}: {e}")

    print("📋 生成結果サマリー:")
    print(f"  生成されたID数: {len(generated_ids)}")
    print(f"  生成ID: {sorted(generated_ids)}")

    # 重複チェック
    all_ids = list(existing_ids) + generated_ids
    duplicates = []
    seen = set()

    for id in all_ids:
        if id in seen:
            duplicates.append(id)
        else:
            seen.add(id)

    if duplicates:
        print(f"⚠️  重複ID検出: {duplicates}")
        return False
    else:
        print("✅ 重複なし")

    # フォーマットチェック
    format_violations = []
    for id in generated_ids:
        if not re.match(r'^[HSBG][CMBTAO][0-9]{3}$', id):
            format_violations.append(id)

    if format_violations:
        print(f"⚠️  フォーマット違反: {format_violations}")
        return False
    else:
        print("✅ 全IDが正しいフォーマット")

    return True


def test_specific_cases():
    """特定ケースのテスト"""
    print("\n🎯 特定ケーステスト")
    print("=" * 50)

    generator = BillIDGenerator()

    # テストケース
    test_cases = [
        # (説明, 法案データ, 期待されるパターン)
        ("内閣提出・衆議院", BillRecord("test1", "", "テスト法案", "", "", "", "内閣", "", "", "衆議院"), "HC"),
        ("内閣提出・参議院", BillRecord("test2", "", "テスト法案", "", "", "", "内閣", "", "", "参議院"), "SC"),
        ("内閣提出・院不明", BillRecord("test3", "", "テスト法案", "", "", "", "内閣", "", "", ""), "GC"),
        ("議員提出・衆議院", BillRecord("test4", "", "テスト法案", "", "", "", "田中議員", "", "", "衆議院"), "HM"),
        ("議員提出・参議院", BillRecord("test5", "", "テスト法案", "", "", "", "田中議員", "", "", "参議院"), "SM"),
        ("予算関連", BillRecord("test6", "", "テスト法案", "", "", "", "内閣", "予算", "", "衆議院"), "HB"),
        ("条約", BillRecord("test7", "", "テスト法案", "", "", "", "外務大臣", "条約", "", "両院"), "BT"),
        ("承認案件", BillRecord("test8", "", "テスト法案", "", "", "", "内閣", "承認", "", "衆議院"), "HA"),
        ("その他", BillRecord("test9", "", "テスト法案", "", "", "", "不明", "その他", "", "参議院"), "SO"),
    ]

    success_count = 0
    for description, bill, expected_pattern in test_cases:
        try:
            generated_id = generator.generate_bill_id(bill)
            actual_pattern = generated_id[:2]

            if actual_pattern == expected_pattern:
                print(f"✅ {description}: {generated_id} (期待: {expected_pattern})")
                success_count += 1
            else:
                print(
                    f"❌ {description}: {generated_id} (期待: {expected_pattern}, 実際: {actual_pattern})")

        except Exception as e:
            print(f"❌ {description}: エラー - {e}")

    print(f"\n📊 特定ケーステスト結果: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)


def main():
    """メイン処理"""
    print("🔧 Bill ID生成ロジック総合テスト")
    print("=" * 60)

    try:
        # テスト実行
        test1_passed = test_bill_id_generation()
        test2_passed = test_specific_cases()

        print("\n" + "=" * 60)
        print("📊 テスト結果サマリー:")
        print(f"  基本生成テスト: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"  特定ケーステスト: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

        if test1_passed and test2_passed:
            print("\n🎉 全テストが合格しました！")
            print("Bill ID生成ロジックは正常に動作しています。")
            return 0
        else:
            print("\n⚠️  一部テストが失敗しました。")
            return 1

    except Exception as e:
        print(f"❌ テスト実行中にエラーが発生: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
