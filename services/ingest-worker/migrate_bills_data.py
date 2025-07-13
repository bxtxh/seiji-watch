#!/usr/bin/env python3
"""
Migrate existing Bills data from Notes field to structured fields
"""

import asyncio
import aiohttp
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

class BillDataMigrator:
    """Migrate bill data from Notes to structured fields"""
    
    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }
        
        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(3)
        self._last_request_time = 0
    
    async def _rate_limited_request(self, session: aiohttp.ClientSession, method: str, url: str, **kwargs):
        """Rate-limited request to Airtable API"""
        async with self._request_semaphore:
            # Ensure 300ms between requests
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < 0.3:
                await asyncio.sleep(0.3 - time_since_last)
            
            async with session.request(method, url, headers=self.headers, **kwargs) as response:
                self._last_request_time = asyncio.get_event_loop().time()
                
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    await asyncio.sleep(retry_after)
                    return await self._rate_limited_request(session, method, url, **kwargs)
                
                response.raise_for_status()
                return await response.json()
    
    def parse_notes_content(self, notes_text: str) -> dict:
        """Parse Notes field content and extract structured data"""
        
        if not notes_text:
            return {}
        
        parsed_data = {}
        
        # Extract Bill ID
        bill_id_match = re.search(r'法案ID:\s*([^\s🔄]+)', notes_text)
        if bill_id_match:
            bill_id = bill_id_match.group(1).strip()
            parsed_data['Bill_ID'] = bill_id
            
            # Parse Diet Session and Bill Number from Bill_ID (format: 217-1)
            if '-' in bill_id:
                parts = bill_id.split('-')
                parsed_data['Diet_Session'] = parts[0]
                parsed_data['Bill_Number'] = parts[1]
        
        # Extract Status
        status_match = re.search(r'ステータス:\s*([^\s🔄]+)', notes_text)
        if status_match:
            status = status_match.group(1).strip()
            # Map to proper status values
            status_mapping = {
                '議案要旨': '提出',
                '審議中': '審議中',
                '可決': '可決',
                '否決': '否決',
                '成立': '成立',
                '廃案': '廃案'
            }
            parsed_data['Bill_Status'] = status_mapping.get(status, status)
        
        # Extract Stage
        stage_match = re.search(r'段階:\s*([^\s👤]+)', notes_text)
        if stage_match:
            parsed_data['Stage'] = stage_match.group(1).strip()
        
        # Extract Submitter
        submitter_match = re.search(r'提出者:\s*([^\s🏷️]+)', notes_text)
        if submitter_match:
            parsed_data['Submitter'] = submitter_match.group(1).strip()
        
        # Extract Category
        category_match = re.search(r'カテゴリ:\s*([^\s🔗]+)', notes_text)
        if category_match:
            parsed_data['Category'] = category_match.group(1).strip()
        
        # Extract URL
        url_match = re.search(r'URL:\s*(https?://[^\s📅]+)', notes_text)
        if url_match:
            parsed_data['Bill_URL'] = url_match.group(1).strip()
        
        # Extract Collection Date
        collection_date_match = re.search(r'収集日時:\s*([^\s【]+)', notes_text)
        if collection_date_match:
            date_str = collection_date_match.group(1).strip()
            try:
                # Parse ISO format date
                parsed_data['Collection_Date'] = date_str
            except:
                pass
        
        # Extract Data Source
        if 'データソース: 参議院公式サイト' in notes_text:
            parsed_data['Data_Source'] = '参議院公式サイト'
        
        # Extract Process Method
        if '自動スクレイピング + AI処理' in notes_text:
            parsed_data['Process_Method'] = 'AI処理'
        elif '自動スクレイピング' in notes_text:
            parsed_data['Process_Method'] = '自動スクレイピング'
        
        # Set default values
        parsed_data['House'] = '参議院'  # Default based on data source
        parsed_data['Bill_Type'] = '提出法律案'  # Default type
        parsed_data['Priority'] = 'medium'  # Default priority
        parsed_data['Quality_Score'] = 0.8  # Default quality score
        
        # Set timestamps
        now_iso = datetime.now().isoformat()
        parsed_data['Created_At'] = now_iso
        parsed_data['Updated_At'] = now_iso
        
        return parsed_data
    
    async def migrate_bills_data(self) -> dict:
        """Migrate all bills data from Notes to structured fields"""
        
        start_time = datetime.now()
        print("🔄 Bills Data Migration")
        print("=" * 60)
        print(f"📅 開始時刻: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 目標: NotesフィールドからStructured fieldsへの移行")
        print()
        
        result = {
            "success": False,
            "total_time": 0.0,
            "bills_processed": 0,
            "bills_migrated": 0,
            "errors": [],
            "start_time": start_time.isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Get all bills with Notes content
                print("📋 Step 1: 既存議案データ取得...")
                bills_url = f"{self.base_url}/Bills (法案)"
                response = await self._rate_limited_request(session, "GET", bills_url)
                
                bills = response.get("records", [])
                result["bills_processed"] = len(bills)
                print(f"  取得完了: {len(bills)}件の議案")
                
                # Step 2: Parse and migrate each bill
                print(f"\n🔄 Step 2: データ解析・移行...")
                success_count = 0
                
                for i, bill in enumerate(bills, 1):
                    try:
                        record_id = bill["id"]
                        fields = bill.get("fields", {})
                        notes_content = fields.get("Notes", "")
                        bill_name = fields.get("Name", f"Bill {i}")
                        
                        if not notes_content:
                            print(f"  ⚠️  Bill {i}: No Notes content to migrate")
                            continue
                        
                        # Parse Notes content
                        parsed_data = self.parse_notes_content(notes_content)
                        
                        if not parsed_data:
                            print(f"  ⚠️  Bill {i}: Could not parse Notes content")
                            continue
                        
                        # Add title from Name field
                        if bill_name and bill_name != f"Bill {i}":
                            parsed_data['Title'] = bill_name
                        
                        # Update record with structured data
                        update_data = {"fields": parsed_data}
                        update_url = f"{bills_url}/{record_id}"
                        
                        await self._rate_limited_request(session, "PATCH", update_url, json=update_data)
                        success_count += 1
                        
                        if i <= 5 or i % 5 == 0:
                            bill_id = parsed_data.get('Bill_ID', 'N/A')
                            status = parsed_data.get('Bill_Status', 'N/A')
                            print(f"  ✅ Bill {i:02d}: {bill_name[:30]}... (ID:{bill_id}, Status:{status})")
                        
                    except Exception as e:
                        print(f"  ❌ Bill {i} migration failed: {e}")
                        result["errors"].append(f"Bill {i}: {str(e)}")
                
                # Results
                end_time = datetime.now()
                result["total_time"] = (end_time - start_time).total_seconds()
                result["success"] = success_count > 0
                result["bills_migrated"] = success_count
                result["end_time"] = end_time.isoformat()
                
                print(f"\n" + "=" * 60)
                print(f"📊 Migration Results")
                print(f"=" * 60)
                print(f"✅ 成功: {result['success']}")
                print(f"⏱️  実行時間: {result['total_time']:.2f}秒")
                print(f"📋 処理議案数: {result['bills_processed']}件")
                print(f"🔄 移行成功: {success_count}件")
                print(f"📈 成功率: {(success_count/len(bills)*100):.1f}%" if bills else "0%")
                
                if result["success"]:
                    print(f"\n🎉 MIGRATION COMPLETE!")
                    print(f"✅ Bills table now has structured data")
                    print(f"🔄 Ready for efficient API queries and analysis")
                    print(f"💡 次の段階: NotesフィールドのクリーンアップとAPI改善")
                else:
                    print(f"\n❌ Migration failed or no data to migrate")
                
                return result
                
        except Exception as e:
            end_time = datetime.now()
            result["total_time"] = (end_time - start_time).total_seconds()
            result["success"] = False
            result["errors"].append(str(e))
            
            print(f"❌ Migration failed: {e}")
            return result

async def main():
    """Main execution function"""
    try:
        migrator = BillDataMigrator()
        result = await migrator.migrate_bills_data()
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = f"bills_migration_result_{timestamp}.json"
        
        import json
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 結果保存: {result_file}")
        
        return 0 if result["success"] else 1
        
    except Exception as e:
        print(f"💥 Migration error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())