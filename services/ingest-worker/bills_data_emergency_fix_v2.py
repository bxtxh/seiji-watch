#!/usr/bin/env python3
"""
Bills Data Emergency Fix V2
Airtable computed field constraintsに対応した重複削除
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

class BillsDataEmergencyFixV2:
    """Bills table emergency repair with computed field handling"""
    
    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.table_name = "Bills (法案)"
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }
        
        # Define writable field types (exclude computed fields)
        self.writable_field_types = {
            'singleLineText', 'richText', 'number', 'currency', 'percent',
            'date', 'checkbox', 'singleSelect', 'multipleSelects', 'attachment',
            'phone', 'email', 'url', 'rating', 'duration', 'multilineText'
        }
        
        # Fields to exclude based on our schema analysis
        self.computed_fields = {
            "Attachment Summary"  # Known computed field with emptyDependency error
        }
        
        # Essential writable fields for Bills table
        self.essential_fields = {
            "Title", "Bill_ID", "Bill_Number", "Diet_Session", "House",
            "Bill_Status", "Stage", "Category", "Submitter", "Priority",
            "Bill_Type", "Bill_URL", "Data_Source", "Collection_Date",
            "Process_Method", "Notes", "Quality_Score"
        }

    def filter_writable_fields(self, record_fields: Dict) -> Dict:
        """Filter out computed fields from record data"""
        writable_fields = {}
        
        for field_name, value in record_fields.items():
            # Exclude known computed fields
            if field_name in self.computed_fields:
                continue
                
            # Include only essential fields we know are writable
            if field_name in self.essential_fields:
                writable_fields[field_name] = value
        
        return writable_fields

    async def get_all_bills_records(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Fetch all Bills records for duplicate analysis"""
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
                        
                        print(f"📄 Fetched {len(all_records)} records so far...")
                        await asyncio.sleep(0.2)  # Rate limiting
                    else:
                        print(f"❌ Error fetching records: {response.status}")
                        return []
                        
            except Exception as e:
                print(f"❌ Error in pagination: {e}")
                return []
        
        print(f"✅ Total records fetched: {len(all_records)}")
        return all_records

    def identify_duplicates(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """Identify duplicate records by Bill_ID"""
        bill_id_groups = {}
        
        for record in records:
            fields = record.get('fields', {})
            bill_id = fields.get('Bill_ID')
            
            if bill_id:
                if bill_id not in bill_id_groups:
                    bill_id_groups[bill_id] = []
                bill_id_groups[bill_id].append(record)
        
        # Keep only groups with duplicates
        duplicates = {bill_id: group for bill_id, group in bill_id_groups.items() 
                     if len(group) > 1}
        
        print(f"🔍 Found {len(duplicates)} Bill_IDs with duplicates")
        
        total_duplicate_records = sum(len(group) - 1 for group in duplicates.values())
        print(f"📊 Total duplicate records to remove: {total_duplicate_records}")
        
        return duplicates

    def select_records_to_keep_and_remove(self, duplicate_groups: Dict[str, List[Dict]]) -> tuple[List[Dict], List[str]]:
        """Select which records to keep and which to remove"""
        records_to_keep = []
        records_to_remove = []
        
        for bill_id, group in duplicate_groups.items():
            # Sort by Quality_Score (desc), then by creation date (newest first)
            sorted_group = sorted(group, key=lambda r: (
                r.get('fields', {}).get('Quality_Score', 0),
                r.get('fields', {}).get('Created_At', '')
            ), reverse=True)
            
            # Keep the first (highest quality, newest) record
            keep_record = sorted_group[0]
            records_to_keep.append(keep_record)
            
            # Mark others for removal
            for record in sorted_group[1:]:
                records_to_remove.append(record['id'])
            
            print(f"🔄 {bill_id}: Keeping 1, removing {len(sorted_group) - 1} duplicates")
        
        return records_to_keep, records_to_remove

    async def safe_update_record(self, session: aiohttp.ClientSession, 
                                record_id: str, updated_fields: Dict) -> bool:
        """Safely update a record with only writable fields"""
        try:
            # Filter to only writable fields
            safe_fields = self.filter_writable_fields(updated_fields)
            
            if not safe_fields:
                print(f"⚠️ No writable fields to update for record {record_id}")
                return True  # Nothing to update is not an error
            
            update_data = {"fields": safe_fields}
            
            async with session.patch(
                f"{self.base_url}/{self.table_name}/{record_id}",
                headers=self.headers,
                json=update_data
            ) as response:
                if response.status == 200:
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Update failed for {record_id}: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Exception updating {record_id}: {e}")
            return False

    async def safe_delete_record(self, session: aiohttp.ClientSession, record_id: str) -> bool:
        """Safely delete a record"""
        try:
            async with session.delete(
                f"{self.base_url}/{self.table_name}/{record_id}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Delete failed for {record_id}: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Exception deleting {record_id}: {e}")
            return False

    async def process_duplicate_removal(self, session: aiohttp.ClientSession):
        """Process duplicate removal with improved field handling"""
        print("🚀 Starting Bills table duplicate removal V2...")
        
        # Step 1: Fetch all records
        all_records = await self.get_all_bills_records(session)
        if not all_records:
            print("❌ No records found or fetch failed")
            return
        
        # Step 2: Identify duplicates
        duplicate_groups = self.identify_duplicates(all_records)
        if not duplicate_groups:
            print("✅ No duplicates found!")
            return
        
        # Step 3: Select records to keep and remove
        records_to_keep, record_ids_to_remove = self.select_records_to_keep_and_remove(duplicate_groups)
        
        print(f"\n📋 DUPLICATE REMOVAL PLAN:")
        print(f"   📌 Records to keep: {len(records_to_keep)}")
        print(f"   🗑️ Records to remove: {len(record_ids_to_remove)}")
        
        # Step 4: Update kept records with consolidated data (if needed)
        print(f"\n🔄 Updating kept records...")
        update_success_count = 0
        
        for record in records_to_keep:
            record_id = record['id']
            fields = record.get('fields', {})
            
            # Ensure Quality_Score is updated to reflect repair
            fields['Quality_Score'] = 1.0  # Perfect score after deduplication
            fields['Updated_At'] = datetime.now().isoformat() + 'Z'
            
            success = await self.safe_update_record(session, record_id, fields)
            if success:
                update_success_count += 1
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        print(f"✅ Successfully updated {update_success_count}/{len(records_to_keep)} kept records")
        
        # Step 5: Remove duplicate records
        print(f"\n🗑️ Removing duplicate records...")
        delete_success_count = 0
        
        for record_id in record_ids_to_remove:
            success = await self.safe_delete_record(session, record_id)
            if success:
                delete_success_count += 1
            
            await asyncio.sleep(0.1)  # Rate limiting
        
        print(f"✅ Successfully removed {delete_success_count}/{len(record_ids_to_remove)} duplicate records")
        
        # Step 6: Final report
        print(f"\n🎯 BILLS TABLE REPAIR COMPLETED:")
        print(f"   ✅ Records updated: {update_success_count}")
        print(f"   🗑️ Duplicates removed: {delete_success_count}")
        print(f"   📊 Final unique records: {len(records_to_keep)}")
        
        # Save repair report
        repair_report = {
            "repair_date": datetime.now().isoformat(),
            "original_total_records": len(all_records),
            "duplicate_groups_found": len(duplicate_groups),
            "records_kept": len(records_to_keep),
            "records_removed": delete_success_count,
            "update_success_rate": update_success_count / len(records_to_keep) if records_to_keep else 0,
            "delete_success_rate": delete_success_count / len(record_ids_to_remove) if record_ids_to_remove else 0,
            "writable_fields_used": list(self.essential_fields),
            "computed_fields_excluded": list(self.computed_fields)
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"bills_repair_report_v2_{timestamp}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(repair_report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Repair report saved: {report_filename}")

    async def run_emergency_repair(self):
        """Run the emergency repair process"""
        print("🚨 Bills Table Emergency Repair V2 - Starting...")
        print("📋 Features: Computed field exclusion, safe updates, comprehensive reporting")
        
        async with aiohttp.ClientSession() as session:
            await self.process_duplicate_removal(session)
        
        print("\n✅ Emergency repair completed!")

async def main():
    """Main entry point"""
    repair_tool = BillsDataEmergencyFixV2()
    await repair_tool.run_emergency_repair()

if __name__ == "__main__":
    asyncio.run(main())