#!/usr/bin/env python3
"""
完全統合 - Bill_ID埋め込み + 残り法案統合
"""

import os
import sys
import time
from pathlib import Path

import requests


def load_env_file(env_file_path):
    if not os.path.exists(env_file_path):
        return False

    with open(env_file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip("\"'")
                os.environ[key] = value
    return True


def get_existing_records(pat, base_id):
    """既存レコード取得"""
    url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29"
    headers = {"Authorization": f"Bearer {pat}"}

    all_records = []
    params = {"maxRecords": 100}

    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break

        data = response.json()
        records = data.get("records", [])
        all_records.extend(records)

        offset = data.get("offset")
        if not offset:
            break
        params["offset"] = offset

    return all_records


def update_record(pat, base_id, record_id, fields):
    """レコード更新"""
    url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29/{record_id}"
    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    data = {"fields": fields}
    response = requests.patch(url, headers=headers, json=data)
    return response.status_code == 200


def create_record(pat, base_id, fields):
    """レコード作成"""
    url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29"
    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    data = {"fields": fields}
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200


def main():
    print("🔧 完全統合: Bill_ID埋め込み + 残り法案統合")
    print("=" * 60)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get("AIRTABLE_PAT")
    base_id = os.environ.get("AIRTABLE_BASE_ID")

    # 法案データ収集
    sys.path.insert(0, "src")
    from scraper.diet_scraper import DietScraper

    scraper = DietScraper(enable_resilience=False)
    bills = scraper.fetch_current_bills()
    print(f"✅ {len(bills)}件の法案データ収集完了")

    # 法案データをID別に整理
    bills_by_id = {bill.bill_id: bill for bill in bills}

    # 既存レコード確認
    print("\n📋 既存Airtableレコード確認")
    existing_records = get_existing_records(pat, base_id)
    print(f"✅ {len(existing_records)}件の既存レコード確認")

    # 既存レコードのBill_ID更新
    print("\n🔧 既存レコードのBill_ID更新")
    updated_count = 0

    for record in existing_records:
        record_id = record["id"]
        fields = record.get("fields", {})
        name = fields.get("Name", "")
        current_bill_id = fields.get("Bill_ID", "")

        if current_bill_id:
            continue  # 既にBill_IDが設定済み

        # 法案名から対応するBill_IDを検索
        matching_bill = None
        for bill_id, bill in bills_by_id.items():
            if bill.title == name:
                matching_bill = bill
                break

        if matching_bill:
            update_fields = {"Bill_ID": matching_bill.bill_id}
            if update_record(pat, base_id, record_id, update_fields):
                updated_count += 1
                print(f"  ✅ {record_id}: Bill_ID = {matching_bill.bill_id}")
            else:
                print(f"  ❌ {record_id}: 更新失敗")
        else:
            print(f"  ⚠️ {record_id}: 対応する法案が見つからない")

        time.sleep(0.1)  # レート制限対応

    print(f"\n📊 Bill_ID更新結果: {updated_count}件更新")

    # 未統合の法案を新規作成
    print("\n➕ 未統合法案の新規作成")
    existing_names = {
        record.get("fields", {}).get("Name", "") for record in existing_records
    }

    new_bills = []
    for bill in bills:
        if bill.title not in existing_names:
            new_bills.append(bill)

    print(f"✅ {len(new_bills)}件の新規法案を発見")

    created_count = 0
    for i, bill in enumerate(new_bills):
        try:
            fields = {
                "Name": bill.title,
                "Bill_ID": bill.bill_id,
                "Diet_Session": "217",
                "Bill_Status": bill.status or "N/A",
                "Category": bill.category or "N/A",
                "Submitter": bill.submitter or "N/A",
            }

            if create_record(pat, base_id, fields):
                created_count += 1
                print(
                    f"  ✅ {i + 1}/{len(new_bills)}: {bill.bill_id} - {bill.title[:40]}..."
                )
            else:
                print(f"  ❌ {i + 1}/{len(new_bills)}: {bill.bill_id} - 作成失敗")

            time.sleep(0.2)  # レート制限対応

        except Exception as e:
            print(f"  ❌ {i + 1}/{len(new_bills)}: {bill.bill_id} - エラー: {str(e)}")

    print(f"\n📊 新規作成結果: {created_count}件作成")

    # 最終確認
    final_records = get_existing_records(pat, base_id)
    bill_id_filled = sum(1 for r in final_records if r.get("fields", {}).get("Bill_ID"))

    print("\n🎯 最終結果:")
    print(f"  📋 総レコード数: {len(final_records)}")
    print(f"  🔧 Bill_ID埋め込み済み: {bill_id_filled}")
    print(f"  ➕ 新規作成: {created_count}")
    print(f"  🔄 Bill_ID更新: {updated_count}")

    if len(final_records) >= 200 and bill_id_filled >= 200:
        print("\n🎉 第217回国会法案データ完全統合成功!")
        print("✅ MVPデータベース準備完了")
        print("🗳️ July 22, 2025 House of Councillors election 対応完了")
        return 0
    else:
        print("\n⚠️ 統合結果を確認してください")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
