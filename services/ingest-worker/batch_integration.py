#!/usr/bin/env python3
"""
バッチ法案統合 - 10件ずつ効率処理
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
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    return True

def main():
    print("🚀 高速バッチ法案統合")
    print("=" * 40)

    env_file = Path(__file__).parent / ".env.local"
    if not load_env_file(env_file):
        print("❌ .env.local読み込み失敗")
        return 1

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    print("✅ 認証設定確認済み")

    try:
        # 法案データ収集
        sys.path.insert(0, 'src')
        from scraper.diet_scraper import DietScraper

        scraper = DietScraper(enable_resilience=False)
        bills = scraper.fetch_current_bills()
        print(f"✅ {len(bills)}件収集完了")

        # 10件ずつバッチ処理
        url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29"
        headers = {
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json"
        }

        batch_size = 10
        total_success = 0
        total_failed = 0

        for batch_start in range(0, len(bills), batch_size):
            batch_end = min(batch_start + batch_size, len(bills))
            batch_bills = bills[batch_start:batch_end]

            print(f"\n📦 バッチ {batch_start//batch_size + 1}: {batch_start+1}-{batch_end}")

            batch_success = 0
            for i, bill in enumerate(batch_bills):
                try:
                    data = {
                        "fields": {
                            "Name": bill.title,
                            "Bill_ID": bill.bill_id,
                            "Diet_Session": "217",
                            "Bill_Status": bill.status or 'N/A',
                            "Category": bill.category or 'N/A'
                        }
                    }

                    response = requests.post(url, headers=headers, json=data)

                    if response.status_code == 200:
                        batch_success += 1
                        total_success += 1
                        print(f"  ✅ {bill.bill_id}")
                    else:
                        total_failed += 1
                        print(f"  ❌ {bill.bill_id}")

                    time.sleep(0.2)  # レート制限

                except Exception:
                    total_failed += 1
                    print(f"  ❌ {bill.bill_id} (エラー)")

            print(f"  バッチ結果: {batch_success}/{len(batch_bills)} 成功")

            # バッチ間の小休止
            time.sleep(1)

        print("\n📊 最終結果:")
        print(f"  ✅ 成功: {total_success}")
        print(f"  ❌ 失敗: {total_failed}")
        print(f"  📈 成功率: {total_success/(total_success+total_failed)*100:.1f}%")

        if total_success > 200:
            print("\n🎉 第217回国会法案データ統合完了!")
            print("🗳️  MVPデータベース準備完了")
            return 0
        else:
            print("\n⚠️  統合に問題あり")
            return 1

    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
