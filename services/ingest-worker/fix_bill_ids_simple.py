#!/usr/bin/env python3
"""
Bill ID 欠損データ修正スクリプト (簡易版)

直接Airtable APIを使用してBill_IDを修正します。
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

import aiohttp


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


class SimpleAirtableClient:
    """簡易Airtableクライアント"""

    def __init__(self):
        self.base_id = os.getenv("AIRTABLE_BASE_ID", "appQMZFZXAiGmjI0N")
        self.api_key = os.getenv("AIRTABLE_API_KEY", "")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_all_bills(self) -> list[dict[str, Any]]:
        """全法案データを取得"""
        bills = []
        offset = None

        while True:
            url = f"{self.base_url}/Bills (法案)"
            params = {}
            if offset:
                params["offset"] = offset

            async with self.session.get(
                url, headers=self.headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])

                    for record in records:
                        fields = record.get("fields", {})
                        bills.append(
                            {
                                "id": record["id"],
                                "bill_id": fields.get("bill_id", ""),
                                "title": fields.get("title", ""),
                                "submission_date": fields.get("submission_date", ""),
                                "status": fields.get("status", ""),
                                "stage": fields.get("stage", ""),
                                "submitter": fields.get("submitter", ""),
                                "category": fields.get("category", ""),
                                "diet_session": fields.get("diet_session", ""),
                                "house": fields.get("house", ""),
                            }
                        )

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"Error fetching bills: {response.status}")
                    break

        return bills

    async def update_bill(self, record_id: str, fields: dict[str, Any]) -> bool:
        """法案レコードを更新"""
        url = f"{self.base_url}/Bills (法案)"

        data = {"records": [{"id": record_id, "fields": fields}]}

        async with self.session.patch(url, headers=self.headers, json=data) as response:
            return response.status == 200


class BillIDGenerator:
    """Bill ID生成器"""

    def __init__(self):
        self.used_ids = set()

        # 法案ID命名規則
        self.HOUSE_CODES = {
            "衆議院": "H",
            "参議院": "S",
            "両院": "B",
            "": "G",  # 政府提出法案
        }

        self.CATEGORY_CODES = {
            "内閣提出": "C",
            "議員提出": "M",
            "予算関連": "B",
            "条約": "T",
            "承認": "A",
            "その他": "O",
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

        if "内閣" in submitter or "政府" in submitter:
            return "C"
        elif "議員" in submitter:
            return "M"
        elif category and "予算" in category:
            return "B"
        elif category and "条約" in category:
            return "T"
        elif category and "承認" in category:
            return "A"
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


async def main():
    """メイン処理"""
    logging.basicConfig(level=logging.INFO)

    print("🔧 Bill ID 欠損データ修正システム (簡易版)")
    print("=" * 50)

    # 環境変数チェック
    if not os.getenv("AIRTABLE_API_KEY"):
        print("❌ AIRTABLE_API_KEY環境変数が設定されていません")
        return 1

    try:
        async with SimpleAirtableClient() as client:
            # 1. 全法案データ取得
            print("\n📊 Step 1: 法案データ取得中...")
            bills_data = await client.get_all_bills()
            print(f"取得完了: {len(bills_data)}件")

            # 2. 分析
            print("\n📊 Step 2: データ分析")
            bills = []
            existing_ids = set()
            missing_count = 0

            for bill_data in bills_data:
                bill = BillRecord(
                    record_id=bill_data["id"],
                    bill_id=bill_data["bill_id"],
                    title=bill_data["title"],
                    submission_date=bill_data["submission_date"],
                    status=bill_data["status"],
                    stage=bill_data["stage"],
                    submitter=bill_data["submitter"],
                    category=bill_data["category"],
                    diet_session=bill_data["diet_session"],
                    house=bill_data["house"],
                )
                bills.append(bill)

                if bill.bill_id and bill.bill_id.strip():
                    existing_ids.add(bill.bill_id.strip())
                else:
                    missing_count += 1

            print(f"  総法案数: {len(bills)}")
            print(f"  Bill_ID有り: {len(existing_ids)}")
            print(f"  Bill_ID無し: {missing_count}")
            print(f"  欠損率: {(missing_count/len(bills))*100:.1f}%")

            # 3. 修正が必要か確認
            if missing_count == 0:
                print("✅ 全ての法案にBill_IDが設定されています。")
                return 0

            # 4. 修正実行
            print(f"\n🔨 Step 3: Bill_ID生成・修正 ({missing_count}件)")

            # 本番環境での確認
            if os.getenv("AIRTABLE_BASE_ID") == "appQMZFZXAiGmjI0N":
                confirm = (
                    input("本番環境のデータを修正します。続行しますか？ (y/N): ")
                    .strip()
                    .lower()
                )
                if confirm != "y":
                    print("修正をキャンセルしました。")
                    return 0

            # Generator初期化
            generator = BillIDGenerator()
            generator.set_existing_ids(existing_ids)

            # 修正実行
            updated = 0
            failed = 0

            for bill in bills:
                if not bill.bill_id or not bill.bill_id.strip():
                    try:
                        # Bill_ID生成
                        new_id = generator.generate_bill_id(bill)

                        # 更新
                        success = await client.update_bill(
                            bill.record_id, {"bill_id": new_id}
                        )

                        if success:
                            updated += 1
                            print(f"✅ {new_id}: {bill.title[:50]}...")
                        else:
                            failed += 1
                            print(f"❌ Failed: {bill.title[:50]}...")

                        # レート制限対応
                        await asyncio.sleep(0.2)

                    except Exception as e:
                        failed += 1
                        print(f"❌ Error: {bill.title[:50]}... - {e}")

            # 5. 結果
            print("\n📊 Step 4: 修正完了")
            print(f"  更新成功: {updated}件")
            print(f"  更新失敗: {failed}件")
            print(f"  成功率: {(updated/(updated+failed))*100:.1f}%")

            # 6. 最終確認
            if updated > 0:
                print("\n✅ Step 5: 最終確認")
                final_data = await client.get_all_bills()
                final_missing = len(
                    [b for b in final_data if not b.get("bill_id", "").strip()]
                )

                print(f"  修正後の欠損数: {final_missing}")
                print(
                    f"  全体完了率: {((len(final_data)-final_missing)/len(final_data))*100:.1f}%"
                )

                if final_missing == 0:
                    print("🎉 全ての法案にBill_IDが設定されました！")
                    return 0

            return 1 if failed > 0 else 0

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
