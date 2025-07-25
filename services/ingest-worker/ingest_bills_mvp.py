#!/usr/bin/env python3
"""
MVP用 第217回国会法案データ統合スクリプト
参議院サイトからスクレイピングしてAirtableに保存
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add paths
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

# Environment setup


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


async def ingest_bills_to_airtable():
    """第217回国会の法案データをAirtableに統合"""
    print("🏛️ 第217回国会法案データ統合スクリプト")
    print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 1. スクレイピング実行
        print("📄 Step 1: 参議院サイトから法案データをスクレイピング")
        from scraper.diet_scraper import DietScraper

        scraper = DietScraper(enable_resilience=False)
        bills = scraper.fetch_current_bills()
        print(f"✅ {len(bills)}件の法案データを収集完了")
        print()

        # 2. サンプル表示
        print("📋 収集データサンプル:")
        for i, bill in enumerate(bills[:5]):
            print(f"  {i+1}. {bill.bill_id}: {bill.title[:60]}...")
        print()

        # 3. Airtable統合（簡易版）
        print("💾 Step 2: Airtableへのデータ保存")
        print("⚠️  現在は収集のみ実装（Airtable統合は別途実装予定）")
        print()

        # 4. データ保存（JSONとして）
        import json

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"bills_mvp_collection_{timestamp}.json"

        bills_data = []
        for bill in bills:
            bill_dict = {
                "bill_id": bill.bill_id,
                "title": bill.title,
                "status": bill.status,
                "stage": bill.stage,
                "submitter": bill.submitter,
                "category": bill.category,
                "url": bill.url,
                "summary": bill.summary,
                "submission_date": (
                    bill.submission_date.isoformat() if bill.submission_date else None
                ),
                "collected_at": datetime.now().isoformat(),
            }
            bills_data.append(bill_dict)

        output_data = {
            "collection_info": {
                "timestamp": datetime.now().isoformat(),
                "source": "参議院第217回国会議案情報",
                "total_bills": len(bills_data),
                "source_url": "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/217/gian.htm",
            },
            "bills": bills_data,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"💾 データを保存: {output_file}")
        print()

        # 5. 統計表示
        print("📊 収集統計:")
        categories = {}
        statuses = {}

        for bill in bills:
            categories[bill.category] = categories.get(bill.category, 0) + 1
            statuses[bill.status] = statuses.get(bill.status, 0) + 1

        print("  📋 カテゴリ別:")
        for category, count in sorted(
            categories.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    {category}: {count}件")

        print("  📊 ステータス別:")
        for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
            print(f"    {status}: {count}件")

        print()
        print("✅ 第217回国会法案データ収集完了")
        print(f"📁 保存ファイル: {output_file}")

        return True

    except Exception as e:
        print(f"❌ エラー発生: {str(e)}")
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
        print("⚠️  .env.localファイルが見つかりません（システム環境変数を使用）")

    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    success = await ingest_bills_to_airtable()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
