#!/usr/bin/env python3
"""
セキュア全法案データ統合
APIキー非表示、全226件統合実行
"""

import os
import sys
import time
from pathlib import Path

import requests


def load_env_file(env_file_path):
    """Load environment variables from .env file"""
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


def main():
    """セキュアメイン実行"""
    print("🔒 セキュア全法案データ統合")
    print("=" * 50)

    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    if load_env_file(env_file):
        print("✅ 環境変数読み込み完了")
    else:
        print("❌ .env.localが見つかりません")
        return 1

    pat = os.environ.get("AIRTABLE_PAT")
    base_id = os.environ.get("AIRTABLE_BASE_ID")

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    # セキュリティ: APIキー非表示
    print("✅ PAT設定確認済み")
    print(f"✅ Base ID: {base_id}")

    try:
        # 1. 法案データ収集
        print("\n📄 第217回国会法案データ収集")
        sys.path.insert(0, "src")
        from scraper.diet_scraper import DietScraper

        scraper = DietScraper(enable_resilience=False)
        bills = scraper.fetch_current_bills()
        print(f"✅ {len(bills)}件収集完了")

        # 2. 全件統合実行
        print(f"\n💾 全{len(bills)}件Airtable統合開始")
        print("⏱️  推定所要時間: 約45秒 (レート制限対応)")

        url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29"
        headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

        success_count = 0
        failed_count = 0
        start_time = time.time()

        for i, bill in enumerate(bills):
            try:
                # Airtableデータ構築
                airtable_data = {
                    "fields": {
                        "Name": bill.title,
                        "Bill_ID": bill.bill_id,
                        "Diet_Session": "217",
                        "Bill_Status": bill.status or "N/A",
                        "Category": bill.category or "N/A",
                        "Submitter": bill.submitter or "N/A",
                        "Bill_URL": bill.url or "N/A",
                    }
                }

                # API呼び出し
                response = requests.post(url, headers=headers, json=airtable_data)

                if response.status_code == 200:
                    success_count += 1
                    print(f"  {i + 1:3d}/{len(bills)}: ✅ {bill.bill_id}")
                else:
                    failed_count += 1
                    print(
                        f"  {i + 1:3d}/{len(bills)}: ❌ {bill.bill_id} (エラー {response.status_code})"
                    )

                # レート制限対応 (5 req/sec)
                time.sleep(0.2)

                # 進捗表示 (10件ごと)
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    remaining = len(bills) - (i + 1)
                    est_time = (elapsed / (i + 1)) * remaining
                    print(
                        f"    📊 進捗: {i + 1}/{len(bills)} ({success_count}成功, {failed_count}失敗) - 残り約{est_time:.0f}秒"
                    )

            except Exception as e:
                failed_count += 1
                print(
                    f"  {i + 1:3d}/{len(bills)}: ❌ {bill.bill_id} (例外: {str(e)[:50]})"
                )

        elapsed_total = time.time() - start_time

        print("\n📊 統合結果:")
        print(f"  ✅ 成功: {success_count}件")
        print(f"  ❌ 失敗: {failed_count}件")
        print(
            f"  📈 成功率: {success_count / (success_count + failed_count) * 100:.1f}%"
        )
        print(f"  ⏱️  実行時間: {elapsed_total:.1f}秒")

        if success_count > 200:  # 80%以上成功
            print("\n🎉 第217回国会法案データ統合完了!")
            print("✅ MVPに向けたAirtableデータベース準備完了")
            print("🗳️  July 22, 2025 House of Councillors election 対応完了")
            return 0
        else:
            print("\n⚠️  統合結果に問題があります")
            return 1

    except Exception as e:
        print(f"❌ 実行エラー: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
