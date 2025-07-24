#!/usr/bin/env python3
"""
Airtable統合修正スクリプト
環境変数名の不一致を解決して正しいPAT統合を実行
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

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

async def test_correct_airtable_integration():
    """正しい環境変数名でAirtable統合をテスト"""
    print("🔧 Airtable統合修正スクリプト")
    print("=" * 50)

    # 環境変数の正規化 (AIRTABLE_PATに統一)
    api_key_from_old = os.environ.get('AIRTABLE_API_KEY')
    pat_from_new = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    print("🔍 環境変数確認:")
    print(f"  AIRTABLE_API_KEY: {'存在' if api_key_from_old else '未設定'}")
    print(f"  AIRTABLE_PAT: {'存在' if pat_from_new else '未設定'}")
    print(f"  AIRTABLE_BASE_ID: {'存在' if base_id else '未設定'}")

    # PATとして使用する値を決定 (どちらでも同じ値のはず)
    pat_value = pat_from_new or api_key_from_old

    if not pat_value or not base_id:
        print("❌ 必要な環境変数が不足しています")
        return False

    # AIRTABLE_PATを設定（既存のAirtableClientが使用するため）
    os.environ['AIRTABLE_PAT'] = pat_value

    print("\n✅ PAT設定完了:")
    print(f"  使用PAT: {pat_value[:15]}... (長さ: {len(pat_value)})")
    print(f"  Base ID: {base_id}")

    try:
        # 既存のAirtableClientを使用してテスト
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))
        from shared.clients.airtable import AirtableClient

        print("\n🔗 AirtableClient接続テスト:")

        async with AirtableClient() as client:
            # Bills テーブルへのアクセステスト
            try:
                bills = await client.list_bills(max_records=1)
                print(f"✅ Bills テーブルアクセス成功: {len(bills)}件確認")
                return True

            except Exception as e:
                print(f"❌ Bills テーブルアクセス失敗: {str(e)}")
                return False

    except Exception as e:
        print(f"❌ AirtableClient初期化失敗: {str(e)}")
        return False

async def run_bills_integration_with_correct_client():
    """正しいクライアントで法案データ統合を実行"""
    print("\n📄 第217回国会法案データ統合実行")
    print("=" * 50)

    try:
        # スクレイピング実行
        from scraper.diet_scraper import DietScraper

        scraper = DietScraper(enable_resilience=False)
        bills = scraper.fetch_current_bills()
        print(f"✅ {len(bills)}件の法案データを収集")

        # 正しいAirtableClientで統合
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))
        from shared.clients.airtable import AirtableClient

        async with AirtableClient() as client:
            print("🔄 Airtableへの統合開始...")

            successful_count = 0
            failed_count = 0

            # 最初の10件でテスト
            for i, bill in enumerate(bills[:10]):
                try:
                    # 法案データをAirtable形式に変換
                    bill_data = {
                        "bill_number": bill.bill_id,
                        "title": bill.title,
                        "status": "backlog" if not bill.status else bill.status,
                        "category": bill.category or "other",
                        "diet_session": "217",
                        "house_of_origin": "参議院",
                        "bill_type": bill.submitter or "議員",
                        "diet_url": bill.url or "",
                    }

                    # レコード作成
                    await client.create_bill(bill_data)
                    successful_count += 1

                    print(f"  {i+1:2d}/10: ✅ {bill.bill_id} → 成功")

                    # レート制限対応
                    await asyncio.sleep(0.2)

                except Exception as e:
                    failed_count += 1
                    print(f"  {i+1:2d}/10: ❌ {bill.bill_id} → {str(e)}")

            print("\n📊 統合結果:")
            print(f"  ✅ 成功: {successful_count}件")
            print(f"  ❌ 失敗: {failed_count}件")
            print(f"  📈 成功率: {successful_count/(successful_count+failed_count)*100:.1f}%")

            return successful_count > 0

    except Exception as e:
        print(f"❌ 統合エラー: {str(e)}")
        return False

async def main():
    """メイン実行"""
    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    if load_env_file(env_file):
        print("✅ 環境変数を読み込み")
    else:
        print("⚠️  .env.localファイルが見つかりません")
        return 1

    # 接続テスト
    connection_success = await test_correct_airtable_integration()

    if not connection_success:
        print("\n❌ Airtable接続に失敗しました")
        return 1

    # 法案データ統合実行
    integration_success = await run_bills_integration_with_correct_client()

    if integration_success:
        print("\n✅ 第217回国会法案データのAirtable統合成功!")
        print("🎯 MVPに向けたデータベース準備完了")
        return 0
    else:
        print("\n❌ 法案データ統合に失敗しました")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
