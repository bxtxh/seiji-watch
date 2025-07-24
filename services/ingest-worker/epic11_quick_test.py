#!/usr/bin/env python3
"""
EPIC 11 Quick Test - Insert just 5 bills to verify the approach works
"""

import asyncio
import json
import os

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')

class Epic11QuickTest:
    """Quick test with just a few records"""

    def __init__(self):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def transform_bill_minimal(self, bill: dict) -> dict:
        """Transform bill data using only Name and Notes fields"""

        # Create comprehensive Notes field with all details
        notes = f"""【法案詳細】
🏛️ 法案ID: {bill['bill_id']}
📋 ステータス: {bill['status']}
🔄 段階: {bill['stage']}
👤 提出者: {bill['submitter']}
🏷️ カテゴリ: {bill['category']}
🔗 URL: {bill['url']}
📅 収集日時: {bill['collected_at']}

【追加情報】
- データソース: 参議院公式サイト
- 収集期間: 2025年6月1日〜30日
- プロセス: 自動スクレイピング + AI処理"""

        return {
            "fields": {
                "Name": bill['title'][:100],  # Airtable Name field length limit
                "Notes": notes
                # No Status field to avoid permission issues
            }
        }

    async def quick_test_5_bills(self):
        """Test with just 5 bills"""

        print("🧪 Testing with 5 bills...")

        # Load sample data
        data_file = '/Users/shogen/seiji-watch/services/ingest-worker/production_scraping_june2025_20250709_032237.json'
        with open(data_file, encoding='utf-8') as f:
            data = json.load(f)

        bills = data['production_dataset']['bills'][:5]  # Just first 5 bills
        print(f"📋 Processing {len(bills)} bills...")

        success_count = 0
        failed_count = 0

        async with aiohttp.ClientSession() as session:
            for i, bill in enumerate(bills):
                try:
                    test_bill = self.transform_bill_minimal(bill)

                    async with session.post(
                        f"{self.base_url}/Bills (法案)",
                        headers=self.headers,
                        json=test_bill
                    ) as response:

                        if response.status == 200:
                            await response.json()
                            success_count += 1
                            print(f"  ✅ {success_count}: {bill['title'][:40]}...")
                        else:
                            failed_count += 1
                            error = await response.text()
                            print(f"  ❌ Failed: {bill['title'][:40]}... - {response.status}")
                            print(f"     Error: {error[:150]}")

                    # Rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    failed_count += 1
                    print(f"  ❌ Exception: {bill['title'][:40]}... - {str(e)[:100]}")

        print(f"\n📊 Quick test results: ✅ {success_count} success, ❌ {failed_count} failed")

        if success_count >= 3:
            print("🎉 Quick test PASSED! Ready for full integration.")
            return True
        else:
            print("❌ Quick test FAILED. Need to debug issues.")
            return False

async def main():
    """Execute quick test"""

    print("=" * 50)
    print("🧪 EPIC 11 T96: QUICK TEST (5 bills)")
    print("=" * 50)

    tester = Epic11QuickTest()

    try:
        success = await tester.quick_test_5_bills()

        if success:
            print("\n🎯 QUICK TEST SUCCESSFUL!")
            print("✅ Ready to proceed with full integration")
        else:
            print("\n❌ Quick test failed - need to debug")

    except Exception as e:
        print(f"💥 Quick test failed with exception: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
