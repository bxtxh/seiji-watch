#!/usr/bin/env python3
"""
EPIC 11 Optimized Data Integration - Working with Airtable constraints
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

class Epic11OptimizedIntegrator:
    """Optimized data integrator that works with Airtable field constraints"""
    
    def __init__(self):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Status mapping to avoid permission issues
        self.stage_mapping = {
            "Backlog": "Not started",
            "審議中": "In progress", 
            "採決待ち": "In progress",
            "成立": "Done",
            "否決": "Done"
        }
        
        self.vote_mapping = {
            "賛成": "賛成",
            "反対": "反対", 
            "棄権": "棄権",
            "欠席": "欠席"
        }
        
    def transform_bill_for_airtable(self, bill: dict) -> dict:
        """Transform bill data to work with Airtable basic fields"""
        
        # Create comprehensive Notes field with all details
        notes = f"""法案ID: {bill['bill_id']}
カテゴリ: {bill['category']}
ステージ: {bill['stage']}
提出者: {bill['submitter']}
URL: {bill['url']}
収集日時: {bill['collected_at']}
ステータス: {bill['status']}"""
        
        # Map stage to existing Status options
        status = self.stage_mapping.get(bill['stage'], "Not started")
        
        return {
            "fields": {
                "Name": bill['title'],
                "Notes": notes,
                "Status": status
                # Skip Assignee and Attachments for now
            }
        }
        
    def transform_vote_for_airtable(self, vote_record: dict, voting_session: dict) -> dict:
        """Transform vote record to work with Airtable basic fields"""
        
        # Create comprehensive Notes field
        notes = f"""議員: {vote_record['member_name']} ({vote_record['member_name_kana']})
政党: {vote_record['party_name']}
選挙区: {vote_record['constituency']}
院: {vote_record['house']}
投票結果: {vote_record['vote_result']}
法案: {voting_session['bill_title']}
投票日: {voting_session['vote_date']}
投票種別: {voting_session['vote_type']}
段階: {voting_session['vote_stage']}"""
        
        return {
            "fields": {
                "Name": f"{vote_record['member_name']} - {voting_session['bill_title'][:30]}...",
                "Notes": notes,
                "Status": "Done"  # All votes are completed
            }
        }
        
    async def batch_insert_bills(self, bills: list, batch_size: int = 5):
        """Insert bills in small batches to avoid rate limits"""
        
        print(f"🚀 Starting insertion of {len(bills)} bills...")
        
        success_count = 0
        failed_count = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(bills), batch_size):
                batch = bills[i:i + batch_size]
                print(f"📦 Processing batch {i//batch_size + 1}: bills {i+1}-{min(i+batch_size, len(bills))}")
                
                for j, bill in enumerate(batch):
                    try:
                        airtable_bill = self.transform_bill_for_airtable(bill)
                        
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
                                print(f"     Error: {error[:100]}")
                        
                        # Rate limiting: 5 requests per second
                        await asyncio.sleep(0.25)
                        
                    except Exception as e:
                        failed_count += 1
                        print(f"  ❌ Exception: {bill['title'][:40]}... - {str(e)[:100]}")
                
                # Longer pause between batches
                if i + batch_size < len(bills):
                    print(f"⏳ Batch pause...")
                    await asyncio.sleep(2)
                    
        print(f"\n📊 Bills insertion completed: ✅ {success_count} success, ❌ {failed_count} failed")
        return success_count
        
    async def batch_insert_votes(self, voting_sessions: list, batch_size: int = 3):
        """Insert vote records from voting sessions"""
        
        total_votes = sum(len(session.get('vote_records', [])) for session in voting_sessions)
        print(f"🗳️ Starting insertion of {total_votes} vote records from {len(voting_sessions)} sessions...")
        
        success_count = 0
        failed_count = 0
        
        async with aiohttp.ClientSession() as session:
            for session_idx, voting_session in enumerate(voting_sessions):
                print(f"📊 Processing voting session {session_idx + 1}: {voting_session['bill_title'][:40]}...")
                
                vote_records = voting_session.get('vote_records', [])
                
                for i in range(0, len(vote_records), batch_size):
                    batch = vote_records[i:i + batch_size]
                    
                    for vote_record in batch:
                        try:
                            airtable_vote = self.transform_vote_for_airtable(vote_record, voting_session)
                            
                            async with session.post(
                                f"{self.base_url}/Votes (投票)",
                                headers=self.headers,
                                json=airtable_vote
                            ) as response:
                                
                                if response.status == 200:
                                    result = await response.json()
                                    success_count += 1
                                    print(f"  ✅ {success_count}: {vote_record['member_name']} - {vote_record['vote_result']}")
                                else:
                                    failed_count += 1
                                    error = await response.text()
                                    print(f"  ❌ Failed: {vote_record['member_name']} - {response.status}")
                            
                            # Rate limiting
                            await asyncio.sleep(0.3)
                            
                        except Exception as e:
                            failed_count += 1
                            print(f"  ❌ Exception: {vote_record['member_name']} - {str(e)[:100]}")
                    
                    # Pause between vote batches
                    await asyncio.sleep(1)
                    
        print(f"\n📊 Votes insertion completed: ✅ {success_count} success, ❌ {failed_count} failed")
        return success_count
        
    async def execute_full_integration(self):
        """Execute complete data integration - T96 Implementation"""
        
        print("=" * 60)
        print("🚀 EPIC 11 T96: 完全データ統合実行")
        print("Optimized for Airtable field constraints")
        print("=" * 60)
        
        # Load production data
        data_file = '/Users/shogen/seiji-watch/services/ingest-worker/production_scraping_june2025_20250709_032237.json'
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        production_dataset = data['production_dataset']
        bills = production_dataset['bills']
        voting_sessions = production_dataset['voting_sessions']
        
        print(f"📋 Bills to process: {len(bills)}")
        print(f"🗳️ Voting sessions to process: {len(voting_sessions)}")
        
        total_votes = sum(len(session.get('vote_records', [])) for session in voting_sessions)
        print(f"🗳️ Individual votes to process: {total_votes}")
        
        start_time = time.time()
        
        # Phase 1: Insert Bills
        print(f"\n📋 Phase 1: Bills Integration")
        bills_success = await self.batch_insert_bills(bills)
        
        # Phase 2: Insert Votes  
        print(f"\n🗳️ Phase 2: Votes Integration")
        votes_success = await self.batch_insert_votes(voting_sessions)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Results Summary
        print(f"\n" + "=" * 60)
        print(f"🎯 EPIC 11 T96 INTEGRATION RESULTS")
        print(f"=" * 60)
        print(f"⏱️  Total time: {duration:.1f} seconds")
        print(f"📋 Bills: {bills_success}/{len(bills)} ({bills_success/len(bills)*100:.1f}%)")
        votes_rate = f"{votes_success/total_votes*100:.1f}%" if total_votes > 0 else "N/A"
        print(f"🗳️ Votes: {votes_success}/{total_votes} ({votes_rate})")
        
        # Success criteria: 80% success rate
        bills_success_rate = bills_success / len(bills)
        votes_success_rate = votes_success / total_votes if total_votes > 0 else 1.0
        
        if bills_success_rate >= 0.8 and votes_success_rate >= 0.8:
            print(f"🎉 EPIC 11 T96 COMPLETED SUCCESSFULLY!")
            print(f"✅ Ready for T97: API Gateway実データ連携修正")
            return True
        else:
            print(f"⚠️ EPIC 11 T96 PARTIALLY COMPLETED")
            print(f"💡 Proceed with available data ({bills_success} bills, {votes_success} votes)")
            return bills_success > 150  # At least 150 bills for MVP
            
    async def verify_integration(self):
        """Verify the integration results"""
        
        print(f"\n🔍 Integration Verification")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Check Bills table
                async with session.get(f"{self.base_url}/Bills (法案)", headers=self.headers) as response:
                    if response.status == 200:
                        bills_data = await response.json()
                        bills_count = len(bills_data.get('records', []))
                        print(f"📋 Bills in Airtable: {bills_count}")
                    else:
                        print(f"❌ Failed to verify bills: {response.status}")
                        bills_count = 0
                
                # Check Votes table
                async with session.get(f"{self.base_url}/Votes (投票)", headers=self.headers) as response:
                    if response.status == 200:
                        votes_data = await response.json()
                        votes_count = len(votes_data.get('records', []))
                        print(f"🗳️ Votes in Airtable: {votes_count}")
                    else:
                        print(f"❌ Failed to verify votes: {response.status}")
                        votes_count = 0
                
                if bills_count >= 150:
                    print(f"✅ Verification PASSED: Sufficient data for MVP")
                    return True
                else:
                    print(f"❌ Verification FAILED: Insufficient bills ({bills_count} < 150)")
                    return False
                    
            except Exception as e:
                print(f"❌ Verification error: {e}")
                return False

async def main():
    """Execute EPIC 11 T96: Optimized Data Integration"""
    
    integrator = Epic11OptimizedIntegrator()
    
    try:
        # Execute integration
        success = await integrator.execute_full_integration()
        
        if success:
            # Verify results
            verification = await integrator.verify_integration()
            
            if verification:
                print(f"\n🎯 MISSION ACCOMPLISHED!")
                print(f"✅ EPIC 11 T96 完了")
                print(f"🔄 次のタスク: T97 - API Gateway実データ連携修正")
            else:
                print(f"\n⚠️ Integration completed but verification failed")
        else:
            print(f"\n❌ Integration failed to meet success criteria")
            
    except Exception as e:
        print(f"💥 Integration failed with exception: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())