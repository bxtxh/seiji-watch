#!/usr/bin/env python3
"""
第217回国会法案データ → Airtable直接統合スクリプト
Airtable APIを使用して法案データを直接保存
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


def load_env_file(env_file_path):
    """Load environment variables from .env file"""
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

class SimpleAirtableClient:
    """シンプルなAirtableクライアント"""

    def __init__(self, api_key, base_id, table_name):
        self.api_key = api_key
        self.base_id = base_id
        self.table_name = table_name
        self.base_url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def create_record(self, fields):
        """レコード作成"""
        data = {"fields": fields}

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=data
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Airtableエラー: {response.status_code} - {response.text}")
            return None

    def list_records(self, max_records=100):
        """レコード一覧取得"""
        params = {"maxRecords": max_records}

        response = requests.get(
            self.base_url,
            headers=self.headers,
            params=params
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Airtableエラー: {response.status_code} - {response.text}")
            return None

def bill_to_airtable_fields(bill_data):
    """法案データをAirtableフィールド形式に変換"""

    # カテゴリマッピング
    category_mapping = {
        "税制": "taxation",
        "社会保障": "social_security",
        "外交・国際": "foreign_affairs",
        "予算・決算": "budget",
        "経済・産業": "economy",
        "その他": "other"
    }

    # ステータスマッピング
    status_mapping = {
        "議案要旨": "backlog",
        "審議中": "under_review",
        "採決待ち": "pending_vote",
        "成立": "passed",
        "否決": "rejected",
        "": "backlog"  # 空の場合はbacklog
    }

    fields = {
        "Bill_Number": bill_data["bill_id"],
        "Title": bill_data["title"],
        "Status": status_mapping.get(bill_data["status"], "backlog"),
        "Category": category_mapping.get(bill_data["category"], "other"),
        "Diet_Session": "217",
        "House_Of_Origin": "参議院",
        "Bill_Type": bill_data["submitter"],
        "Diet_URL": bill_data["url"],
        "Created_At": datetime.now().isoformat(),
        "Updated_At": datetime.now().isoformat()
    }

    # オプショナルフィールド
    if bill_data.get("summary"):
        fields["Summary"] = bill_data["summary"]

    if bill_data.get("submission_date"):
        fields["Submitted_Date"] = bill_data["submission_date"]

    return fields

async def integrate_bills_to_airtable():
    """法案データをAirtableに統合"""
    print("🔗 第217回国会法案データ → Airtable統合")
    print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 環境変数確認
    api_key = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not api_key or not base_id:
        print("❌ 環境変数が設定されていません:")
        print("  AIRTABLE_PAT")
        print("  AIRTABLE_BASE_ID")
        return False

    print("✅ Airtable設定確認完了")
    print(f"  Base ID: {base_id[:10]}...")
    print()

    try:
        # 1. スクレイピング実行
        print("📄 Step 1: 参議院サイトから法案データをスクレイピング")
        sys.path.insert(0, 'src')
        from scraper.diet_scraper import DietScraper

        scraper = DietScraper(enable_resilience=False)
        bills = scraper.fetch_current_bills()
        print(f"✅ {len(bills)}件の法案データを収集完了")
        print()

        # 2. Airtableクライアント初期化
        print("🔗 Step 2: Airtable接続初期化")
        airtable = SimpleAirtableClient(api_key, base_id, "Bills%20%28%E6%B3%95%E6%A1%88%29")

        # 既存レコード確認
        existing_records = airtable.list_records(max_records=10)
        if existing_records:
            print(f"📊 既存レコード数: {len(existing_records.get('records', []))}件確認")
        print()

        # 3. データ統合実行
        print("💾 Step 3: Airtableへのデータ統合実行")

        successful_integrations = 0
        failed_integrations = 0

        # 最初の20件でテスト実行
        test_bills = bills[:20]

        for i, bill in enumerate(test_bills):
            try:
                # BillDataオブジェクトを辞書に変換
                bill_dict = {
                    'bill_id': bill.bill_id,
                    'title': bill.title,
                    'status': bill.status,
                    'stage': bill.stage,
                    'submitter': bill.submitter,
                    'category': bill.category,
                    'url': bill.url,
                    'summary': bill.summary,
                    'submission_date': bill.submission_date.isoformat() if bill.submission_date else None
                }

                # Airtableフィールド形式に変換
                airtable_fields = bill_to_airtable_fields(bill_dict)

                # レコード作成
                result = airtable.create_record(airtable_fields)

                if result:
                    successful_integrations += 1
                    record_id = result.get('id', 'Unknown')
                    print(f"  {i+1:2d}/20: ✅ {bill.bill_id} → {record_id}")
                else:
                    failed_integrations += 1
                    print(f"  {i+1:2d}/20: ❌ {bill.bill_id} 統合失敗")

                # レート制限対応（5 requests/second）
                time.sleep(0.2)

            except Exception as e:
                failed_integrations += 1
                print(f"  {i+1:2d}/20: ❌ {bill.bill_id} エラー: {str(e)}")

        print()
        print("📊 統合結果:")
        print(f"  ✅ 成功: {successful_integrations}件")
        print(f"  ❌ 失敗: {failed_integrations}件")
        print(f"  📈 成功率: {successful_integrations/(successful_integrations+failed_integrations)*100:.1f}%")
        print()

        if successful_integrations > 0:
            print("✅ 第217回国会法案データのAirtable統合成功")
            print("🎯 MVP用法案データベース準備完了")
        else:
            print("❌ Airtable統合に失敗しました")
            return False

        return True

    except Exception as e:
        print(f"❌ 統合エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """メイン実行関数"""
    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    if load_env_file(env_file):
        print("✅ 環境変数を読み込み")
    else:
        print("⚠️  .env.localファイルが見つかりません")
        return 1

    success = await integrate_bills_to_airtable()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
