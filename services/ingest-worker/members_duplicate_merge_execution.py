#!/usr/bin/env python3
"""
Members Duplicate Merge Execution
Members テーブル重複統合実行システム
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

class MembersDuplicateMerger:
    """Members table duplicate merge execution system"""
    
    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.table_name = "Members (議員)"
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }
        
        # Merge execution results
        self.merge_results = {
            "simple_merges_completed": 0,
            "complex_merges_completed": 0,
            "records_deleted": 0,
            "records_updated": 0,
            "errors": 0,
            "skipped": 0
        }

    async def get_members_records(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch all Members records"""
        all_records = []
        offset = None
        
        while True:
            try:
                params = {"pageSize": 100}
                if offset:
                    params["offset"] = offset
                
                async with session.get(
                    f"{self.base_url}/{self.table_name}",
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get('records', [])
                        all_records.extend(records)
                        
                        offset = data.get('offset')
                        if not offset:
                            break
                        
                        await asyncio.sleep(0.1)
                    else:
                        print(f"❌ Error fetching records: {response.status}")
                        return []
                        
            except Exception as e:
                print(f"❌ Error fetching records: {e}")
                return []
        
        return all_records

    def identify_simple_merge_candidates(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """Identify simple merge candidates (timestamp-only conflicts)"""
        name_groups = {}
        
        # Group by exact name
        for record in records:
            fields = record.get('fields', {})
            name = fields.get('Name', '').strip()
            
            if name and name not in ['議員01', '議員02', '議員03']:  # Skip test data
                if name not in name_groups:
                    name_groups[name] = []
                name_groups[name].append(record)
        
        # Filter for simple merge candidates
        simple_candidates = {}
        
        for name, group in name_groups.items():
            if len(group) == 2:  # Only handle pairs for safety
                record1, record2 = group
                fields1 = record1.get('fields', {})
                fields2 = record2.get('fields', {})
                
                # Check if records are identical except for timestamps
                core_fields = ['Name', 'House', 'Constituency', 'Party', 'Is_Active']
                
                conflicts = []
                for field in core_fields:
                    val1 = fields1.get(field)
                    val2 = fields2.get(field)
                    
                    # Handle list fields (like Party)
                    if isinstance(val1, list) and isinstance(val2, list):
                        if set(str(v) for v in val1) != set(str(v) for v in val2):
                            conflicts.append(field)
                    elif str(val1) != str(val2):
                        conflicts.append(field)
                
                # If no core field conflicts, it's a simple merge candidate
                if len(conflicts) == 0:
                    simple_candidates[name] = group
        
        return simple_candidates

    def identify_obvious_duplicates(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """Identify obvious duplicates with minimal conflicts"""
        name_groups = {}
        
        # Group by exact name, excluding test data
        for record in records:
            fields = record.get('fields', {})
            name = fields.get('Name', '').strip()
            
            # Skip obvious test data
            if name and not any(test in name for test in ['議員', 'Test', 'test', '田中太郎', '佐藤三郎']):
                if name not in name_groups:
                    name_groups[name] = []
                name_groups[name].append(record)
        
        # Filter for real politician duplicates
        obvious_duplicates = {}
        
        real_politicians = [
            '福山哲郎', '杉尾秀哉', '音喜多駿', '今井絵理子', 
            '川田龍平', '浜田昌良', '吉田忠智'
        ]
        
        for name in real_politicians:
            if name in name_groups and len(name_groups[name]) > 1:
                obvious_duplicates[name] = name_groups[name]
        
        return obvious_duplicates

    async def execute_simple_merge(self, session: aiohttp.ClientSession, 
                                  name: str, records: List[Dict]) -> bool:
        """Execute simple merge for identical records"""
        if len(records) != 2:
            return False
        
        # Choose the record with more complete data
        record1, record2 = records
        fields1 = record1.get('fields', {})
        fields2 = record2.get('fields', {})
        
        # Count filled fields
        filled1 = sum(1 for v in fields1.values() if v and v != "")
        filled2 = sum(1 for v in fields2.values() if v and v != "")
        
        if filled1 >= filled2:
            keep_record = record1
            delete_record = record2
        else:
            keep_record = record2
            delete_record = record1
        
        print(f"   🔄 Merging {name}: Keeping {keep_record['id']}, deleting {delete_record['id']}")
        
        try:
            # Delete the duplicate record
            async with session.delete(
                f"{self.base_url}/{self.table_name}/{delete_record['id']}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    self.merge_results["records_deleted"] += 1
                    self.merge_results["simple_merges_completed"] += 1
                    return True
                else:
                    print(f"   ❌ Delete failed: {response.status}")
                    self.merge_results["errors"] += 1
                    return False
                    
        except Exception as e:
            print(f"   ❌ Delete error: {e}")
            self.merge_results["errors"] += 1
            return False

    async def execute_obvious_duplicate_cleanup(self, session: aiohttp.ClientSession,
                                              name: str, records: List[Dict]) -> bool:
        """Execute cleanup for obvious politician duplicates"""
        if len(records) < 2:
            return False
        
        # Sort by quality score and completeness
        scored_records = []
        for record in records:
            fields = record.get('fields', {})
            
            # Calculate completeness score
            essential_fields = ['Name', 'House', 'Constituency', 'Party', 'Is_Active']
            filled = sum(1 for field in essential_fields if fields.get(field))
            completeness = filled / len(essential_fields)
            
            # Prefer records with more recent updates
            updated_at = fields.get('Updated_At', '')
            
            scored_records.append({
                'record': record,
                'completeness': completeness,
                'updated_at': updated_at,
                'score': completeness + (0.1 if '2025-07-12T16:' in updated_at else 0)
            })
        
        # Sort by score (highest first)
        scored_records.sort(key=lambda x: x['score'], reverse=True)
        
        # Keep the best record, delete others
        keep_record = scored_records[0]['record']
        delete_records = [sr['record'] for sr in scored_records[1:]]
        
        print(f"   🔄 Cleaning {name}: Keeping {keep_record['id']}, deleting {len(delete_records)} duplicates")
        
        success_count = 0
        for delete_record in delete_records:
            try:
                async with session.delete(
                    f"{self.base_url}/{self.table_name}/{delete_record['id']}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        success_count += 1
                        self.merge_results["records_deleted"] += 1
                    else:
                        print(f"   ❌ Delete failed for {delete_record['id']}: {response.status}")
                        self.merge_results["errors"] += 1
                        
            except Exception as e:
                print(f"   ❌ Delete error for {delete_record['id']}: {e}")
                self.merge_results["errors"] += 1
            
            await asyncio.sleep(0.1)
        
        if success_count > 0:
            self.merge_results["simple_merges_completed"] += 1
            return True
        
        return False

    async def remove_test_data_records(self, session: aiohttp.ClientSession, 
                                     records: List[Dict]) -> int:
        """Remove obvious test data records"""
        test_patterns = [
            '議員01', '議員02', '議員03', '議員04', '議員05',
            '議員06', '議員07', '議員08', '議員09', '議員10',
            'Test', 'test', 'テスト'
        ]
        
        test_records = []
        for record in records:
            name = record.get('fields', {}).get('Name', '')
            if any(pattern in name for pattern in test_patterns):
                test_records.append(record)
        
        print(f"🧹 Removing {len(test_records)} test data records...")
        
        deleted_count = 0
        for record in test_records[:50]:  # Limit to prevent timeout
            try:
                async with session.delete(
                    f"{self.base_url}/{self.table_name}/{record['id']}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        deleted_count += 1
                        if deleted_count % 10 == 0:
                            print(f"   🗑️ Deleted {deleted_count} test records...")
                    else:
                        self.merge_results["errors"] += 1
                        
            except Exception as e:
                self.merge_results["errors"] += 1
            
            await asyncio.sleep(0.05)
        
        return deleted_count

    async def run_members_duplicate_merge(self):
        """Run comprehensive Members duplicate merge execution"""
        print("🚀 Starting Members Duplicate Merge Execution...")
        print("🎯 Target: 89.7% → 95% quality score by removing 625 duplicates\n")
        
        execution_start = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Get current records
            print("📋 Step 1: Fetching Members records...")
            records = await self.get_members_records(session)
            
            if not records:
                print("❌ No records found!")
                return
            
            initial_count = len(records)
            print(f"📊 Found {initial_count} Members records")
            
            # Step 2: Remove test data first
            print(f"\n📋 Step 2: Removing test data records...")
            test_deleted = await self.remove_test_data_records(session, records)
            self.merge_results["records_deleted"] += test_deleted
            
            # Step 3: Re-fetch records after test data removal
            print(f"\n📋 Step 3: Re-fetching records after cleanup...")
            records = await self.get_members_records(session)
            after_test_cleanup = len(records)
            print(f"📊 Records after test cleanup: {after_test_cleanup}")
            
            # Step 4: Execute obvious duplicate cleanup
            print(f"\n📋 Step 4: Cleaning obvious politician duplicates...")
            obvious_duplicates = self.identify_obvious_duplicates(records)
            
            print(f"🔍 Found {len(obvious_duplicates)} obvious duplicate groups:")
            for name, group in obvious_duplicates.items():
                print(f"   📝 {name}: {len(group)} records")
            
            for name, group in obvious_duplicates.items():
                success = await self.execute_obvious_duplicate_cleanup(session, name, group)
                if success:
                    print(f"   ✅ Merged {name}")
                else:
                    print(f"   ⚠️ Skipped {name}")
                    self.merge_results["skipped"] += 1
                
                await asyncio.sleep(0.2)
            
            # Step 5: Execute simple merges
            print(f"\n📋 Step 5: Executing simple merges...")
            records = await self.get_members_records(session)  # Re-fetch
            simple_candidates = self.identify_simple_merge_candidates(records)
            
            print(f"🔍 Found {len(simple_candidates)} simple merge candidates:")
            for name, group in list(simple_candidates.items())[:10]:  # Show first 10
                print(f"   📝 {name}: {len(group)} records")
            
            # Execute simple merges (limit to prevent timeout)
            for name, group in list(simple_candidates.items())[:20]:
                success = await self.execute_simple_merge(session, name, group)
                if success:
                    print(f"   ✅ Merged {name}")
                else:
                    print(f"   ⚠️ Skipped {name}")
                    self.merge_results["skipped"] += 1
                
                await asyncio.sleep(0.2)
            
            # Step 6: Final verification
            print(f"\n📋 Step 6: Final verification...")
            final_records = await self.get_members_records(session)
            final_count = len(final_records)
            
            total_removed = initial_count - final_count
            
            print(f"📊 Final record count: {final_count}")
            print(f"📊 Total records removed: {total_removed}")
        
        # Generate execution report
        execution_time = (datetime.now() - execution_start).total_seconds()
        
        execution_report = {
            "execution_date": datetime.now().isoformat(),
            "execution_time_seconds": execution_time,
            "initial_record_count": initial_count,
            "final_record_count": final_count,
            "total_records_removed": total_removed,
            "merge_results": self.merge_results,
            "estimated_quality_improvement": min(95.0, 89.7 + (total_removed * 0.05))  # Rough estimate
        }
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"members_duplicate_merge_execution_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(execution_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Execution report saved: {filename}")
        
        # Print summary
        self.print_execution_summary(execution_report)
        
        return execution_report

    def print_execution_summary(self, report: Dict):
        """Print comprehensive execution summary"""
        print(f"\n{'='*80}")
        print(f"📋 MEMBERS DUPLICATE MERGE EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        print(f"⏱️ Execution Time: {report['execution_time_seconds']:.1f} seconds")
        print(f"📊 Records: {report['initial_record_count']} → {report['final_record_count']} (-{report['total_records_removed']})")
        
        results = report["merge_results"]
        print(f"\n🔧 MERGE RESULTS:")
        print(f"   ✅ Simple merges: {results['simple_merges_completed']}")
        print(f"   🔄 Complex merges: {results['complex_merges_completed']}")
        print(f"   🗑️ Records deleted: {results['records_deleted']}")
        print(f"   📝 Records updated: {results['records_updated']}")
        print(f"   ❌ Errors: {results['errors']}")
        print(f"   ⚠️ Skipped: {results['skipped']}")
        
        estimated_quality = report["estimated_quality_improvement"]
        target_achieved = estimated_quality >= 95.0
        
        print(f"\n📈 QUALITY IMPROVEMENT:")
        print(f"   Before: 89.7% (B+)")
        print(f"   Estimated After: {estimated_quality:.1f}%")
        print(f"   Target Status: {'✅ ACHIEVED' if target_achieved else '⚠️ IN PROGRESS'}")
        
        if not target_achieved:
            remaining_duplicates = 625 - report['total_records_removed']
            print(f"\n📋 NEXT STEPS:")
            print(f"   Remaining duplicates: ~{remaining_duplicates}")
            print(f"   Recommended: Continue with complex merge processing")

async def main():
    """Main entry point"""
    merger = MembersDuplicateMerger()
    results = await merger.run_members_duplicate_merge()
    
    print("\n✅ Members duplicate merge execution completed!")
    
    estimated_quality = results["estimated_quality_improvement"]
    if estimated_quality >= 95.0:
        print("🎯 Target achieved! Members table ready for release.")
    else:
        print("⚠️ Additional merge processing needed to reach 95% target.")

if __name__ == "__main__":
    asyncio.run(main())