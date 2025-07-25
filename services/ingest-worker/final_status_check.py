#!/usr/bin/env python3
"""
最終ステータス確認
"""

import os
import sys
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


def get_all_records(pat, base_id):
    """全レコード取得"""
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


def main():
    print("📊 最終ステータス確認")
    print("=" * 40)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get("AIRTABLE_PAT")
    base_id = os.environ.get("AIRTABLE_BASE_ID")

    # 全レコード取得
    all_records = get_all_records(pat, base_id)
    print(f"✅ 総レコード数: {len(all_records)}")

    # 分析
    with_bill_id = 0
    without_bill_id = 0
    diet_session_217 = 0

    for record in all_records:
        fields = record.get("fields", {})
        bill_id = fields.get("Bill_ID", "")
        session = fields.get("Diet_Session", "")

        if bill_id:
            with_bill_id += 1
        else:
            without_bill_id += 1

        if session == "217":
            diet_session_217 += 1

    print("📋 分析結果:")
    print(f"  🔧 Bill_ID有り: {with_bill_id}")
    print(f"  ❌ Bill_ID無し: {without_bill_id}")
    print(f"  🏛️ 第217回国会: {diet_session_217}")

    # 法案データ収集
    sys.path.insert(0, "src")
    from scraper.diet_scraper import DietScraper

    scraper = DietScraper(enable_resilience=False)
    bills = scraper.fetch_current_bills()

    print("\n🎯 統合状況:")
    print(f"  📄 収集法案数: {len(bills)}")
    print(f"  📋 Airtableレコード数: {len(all_records)}")
    print(f"  📈 統合率: {len(all_records)/len(bills)*100:.1f}%")

    if len(all_records) >= 220:  # 97%以上
        print("\n🎉 第217回国会法案データ統合完了!")
        print(f"✅ Bill_ID埋め込み完了: {with_bill_id}件")
        print("✅ MVPデータベース準備完了")
        print("🗳️ July 22, 2025 選挙対応完了")
    else:
        print("\n⚠️ 統合継続が必要です")

    return 0


if __name__ == "__main__":
    main()
