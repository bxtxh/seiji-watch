#!/usr/bin/env python3
"""
新PAT即座テストスクリプト
PAT再生成後の即座動作確認用
"""

import os
import sys
from pathlib import Path


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


async def test_new_pat_integration():
    """新PAT統合テスト"""
    print("🆕 新PAT統合テスト")
    print("=" * 50)

    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    if load_env_file(env_file):
        print("✅ 環境変数読み込み完了")
    else:
        print("❌ .env.localが見つかりません")
        return False

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return False

    print(f"✅ PAT確認: {pat[:15]}... (長さ: {len(pat)})")
    print(f"✅ Base ID: {base_id}")

    try:
        # 1. 法案データ収集
        print("\n📄 法案データ収集")
        sys.path.insert(0, 'src')
        from scraper.diet_scraper import DietScraper

        scraper = DietScraper(enable_resilience=False)
        bills = scraper.fetch_current_bills()
        print(f"✅ {len(bills)}件収集完了")

        # 2. AirtableClient直接テスト
        print("\n🔗 AirtableClient直接テスト")
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared" / "src"))
        from shared.clients.airtable import AirtableClient

        async with AirtableClient() as client:
            # 接続テスト
            bills_test = await client.list_bills(max_records=1)
            print(f"✅ Airtable接続成功: {len(bills_test)}件確認")

            # 実際の統合テスト（最初の3件）
            print("\n💾 実統合テスト (3件)")
            success_count = 0

            for i, bill in enumerate(bills[:3]):
                try:
                    bill_data = {
                        "bill_number": bill.bill_id,
                        "title": bill.title,
                        "status": "backlog",
                        "category": bill.category or "other",
                        "diet_session": "217",
                        "house_of_origin": "参議院",
                        "bill_type": bill.submitter or "議員",
                        "diet_url": bill.url or "",
                    }

                    result = await client.create_bill(bill_data)
                    success_count += 1
                    record_id = result.get('id', 'Unknown')
                    print(f"  {i+1}/3: ✅ {bill.bill_id} → {record_id}")

                except Exception as e:
                    print(f"  {i+1}/3: ❌ {bill.bill_id} → {str(e)}")

            print(f"\n📊 統合結果: {success_count}/3 成功")

            if success_count > 0:
                print("✅ 新PAT統合成功!")
                print("🎯 日次自動更新可能")
                return True

    except Exception as e:
        print(f"❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()

    return False


async def main():
    """メイン実行"""
    success = await test_new_pat_integration()
    return 0 if success else 1

if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
