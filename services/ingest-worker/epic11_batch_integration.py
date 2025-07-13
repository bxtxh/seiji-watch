#!/usr/bin/env python3
"""
EPIC 11 Batch Integration - Process data in manageable chunks
"""

import aiohttp
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')

class Epic11BatchIntegrator:
    """Batch integrator to avoid timeouts"""
    
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
            }
        }
        
    async def process_bill_batch(self, bills: list, batch_num: int, total_batches: int):
        """Process a single batch of bills"""
        
        print(f"📦 Processing batch {batch_num}/{total_batches}: {len(bills)} bills")
        
        success_count = 0
        failed_count = 0
        
        async with aiohttp.ClientSession() as session:
            for i, bill in enumerate(bills):
                try:
                    airtable_bill = self.transform_bill_minimal(bill)
                    
                    async with session.post(
                        f"{self.base_url}/Bills (法案)", 
                        headers=self.headers, 
                        json=airtable_bill
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            success_count += 1
                            print(f"  ✅ {success_count}: {bill['title'][:40]}...")
                        else:
                            failed_count += 1
                            error = await response.text()
                            print(f"  ❌ Failed: {bill['title'][:40]}... - {response.status}")
                            if failed_count <= 2:  # Show first few errors
                                print(f"     Error: {error[:100]}")
                    
                    # Rate limiting
                    await asyncio.sleep(0.4)
                    
                except Exception as e:
                    failed_count += 1
                    print(f"  ❌ Exception: {bill['title'][:40]}... - {str(e)[:100]}")
                    
        print(f"📊 Batch {batch_num} results: ✅ {success_count} success, ❌ {failed_count} failed")
        return success_count, failed_count
        
    async def run_full_integration(self, batch_size: int = 20):
        """Run full integration in batches"""
        
        print("=" * 60)
        print("🚀 EPIC 11 T96: BATCH DATA INTEGRATION")
        print(f"Using batch size: {batch_size}")
        print("=" * 60)
        
        # Load production data
        data_file = '/Users/shogen/seiji-watch/services/ingest-worker/production_scraping_june2025_20250709_032237.json'
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        bills = data['production_dataset']['bills']
        print(f"📋 Total bills to process: {len(bills)}")
        
        # Calculate batches
        total_batches = (len(bills) + batch_size - 1) // batch_size
        print(f"📦 Total batches: {total_batches}")
        
        total_success = 0
        total_failed = 0
        start_time = time.time()
        
        # Process in batches
        for i in range(0, len(bills), batch_size):
            batch = bills[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            batch_success, batch_failed = await self.process_bill_batch(
                batch, batch_num, total_batches
            )
            
            total_success += batch_success
            total_failed += batch_failed
            
            # Progress report
            processed = i + len(batch)
            progress = (processed / len(bills)) * 100
            print(f"🔄 Progress: {processed}/{len(bills)} ({progress:.1f}%)")
            
            # Pause between batches
            if batch_num < total_batches:
                print("⏳ Pausing between batches...")
                await asyncio.sleep(3)
                
        end_time = time.time()
        duration = end_time - start_time
        
        # Final results
        print(f"\n" + "=" * 60)
        print(f"🎯 EPIC 11 T96 BATCH INTEGRATION RESULTS")
        print(f"=" * 60)
        print(f"⏱️  Total time: {duration:.1f} seconds")
        print(f"📋 Bills: {total_success}/{len(bills)} ({total_success/len(bills)*100:.1f}%)")
        print(f"✅ Success: {total_success}")
        print(f"❌ Failed: {total_failed}")
        
        # Success criteria
        success_rate = total_success / len(bills)
        if success_rate >= 0.8:
            print(f"🎉 EPIC 11 T96 COMPLETED SUCCESSFULLY!")
            print(f"✅ Ready for T97: API Gateway実データ連携修正")
            return True
        elif total_success >= 150:
            print(f"✅ EPIC 11 T96 PARTIALLY COMPLETED")
            print(f"💡 Sufficient data for MVP ({total_success} bills)")
            return True
        else:
            print(f"❌ EPIC 11 T96 INSUFFICIENT DATA")
            print(f"Need at least 150 bills for MVP")
            return False

async def main():
    """Execute batch integration"""
    
    integrator = Epic11BatchIntegrator()
    
    try:
        success = await integrator.run_full_integration(batch_size=20)
        
        if success:
            print(f"\n🎯 EPIC 11 T96 MISSION ACCOMPLISHED!")
            print(f"✅ Ready to proceed to T97")
        else:
            print(f"\n❌ Integration needs review")
            
    except Exception as e:
        print(f"💥 Integration failed with exception: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())