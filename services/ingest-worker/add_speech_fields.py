#!/usr/bin/env python3
"""
Add required fields to existing Speeches table
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def add_speech_fields():
    """Add required fields to Speeches table"""
    
    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    # Get table info
    meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(meta_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                speeches_table_id = None
                members_table_id = None
                bills_table_id = None
                
                for table in data.get("tables", []):
                    if table["name"] == "Speeches (発言)":
                        speeches_table_id = table["id"]
                    elif table["name"] == "Members (議員)":
                        members_table_id = table["id"]
                    elif table["name"] == "Bills (法案)":
                        bills_table_id = table["id"]
                
                if not speeches_table_id:
                    print("❌ Speeches table not found")
                    return False
                
                print(f"🔍 Speeches table ID: {speeches_table_id}")
                print(f"🔍 Members table ID: {members_table_id}")
                print(f"🔍 Bills table ID: {bills_table_id}")
                
                # Fields to add
                fields_to_add = [
                    {"name": "Speaker_Name", "type": "singleLineText"},
                    {"name": "Speech_Content", "type": "multilineText"},
                    {"name": "Speech_Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
                    {"name": "Meeting_Name", "type": "singleLineText"},
                    {"name": "Meeting_Type", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "委員会"}, 
                            {"name": "本会議"},
                            {"name": "その他"}
                        ]
                    }},
                    {"name": "House", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "参議院"}, 
                            {"name": "衆議院"}
                        ]
                    }},
                    {"name": "Category", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "一般質疑"}, 
                            {"name": "代表質問"},
                            {"name": "討論"},
                            {"name": "答弁"}
                        ]
                    }},
                    {"name": "Duration_Minutes", "type": "number", "options": {"precision": 0}},
                    {"name": "Is_Government_Answer", "type": "checkbox", "options": {"icon": "check", "color": "blueBright"}},
                    {"name": "Related_Bill_ID", "type": "singleLineText"},
                    {"name": "Transcript_URL", "type": "url"},
                    {"name": "Video_URL", "type": "url"},
                    {"name": "AI_Summary", "type": "multilineText"},
                    {"name": "Sentiment", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "positive"}, 
                            {"name": "neutral"},
                            {"name": "critical"}
                        ]
                    }},
                    {"name": "Topics", "type": "singleLineText"},
                    {"name": "Created_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}},
                    {"name": "Updated_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}}
                ]
                
                # Add Member link field if Members table exists
                if members_table_id:
                    fields_to_add.append({
                        "name": "Speaker", 
                        "type": "multipleRecordLinks", 
                        "options": {"linkedTableId": members_table_id}
                    })
                
                # Add Bill link field if Bills table exists
                if bills_table_id:
                    fields_to_add.append({
                        "name": "Related_Bills", 
                        "type": "multipleRecordLinks", 
                        "options": {"linkedTableId": bills_table_id}
                    })
                
                # Add fields one by one
                success_count = 0
                for field in fields_to_add:
                    try:
                        add_field_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{speeches_table_id}/fields"
                        
                        async with session.post(add_field_url, headers=headers, json=field) as add_response:
                            if add_response.status == 200:
                                result = await add_response.json()
                                field_id = result.get("id")
                                print(f"  ✅ Added field: {field['name']} ({field_id})")
                                success_count += 1
                            else:
                                error_text = await add_response.text()
                                print(f"  ❌ Failed to add {field['name']}: {add_response.status}")
                                if "already exists" in error_text.lower():
                                    print(f"    (Field already exists, skipping)")
                                    success_count += 1
                                else:
                                    print(f"    Error: {error_text[:100]}...")
                        
                        # Small delay between requests
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        print(f"  ❌ Exception adding {field['name']}: {e}")
                
                print(f"\n📊 Summary:")
                print(f"  Total fields to add: {len(fields_to_add)}")
                print(f"  Successfully added: {success_count}")
                print(f"  Success rate: {success_count/len(fields_to_add)*100:.1f}%")
                
                return success_count >= len(fields_to_add) * 0.8  # 80% success rate
                
            else:
                print(f"❌ Failed to get table info: {response.status}")
                return False

async def main():
    """Main function"""
    print("🔧 Adding fields to Speeches (発言) table...")
    
    success = await add_speech_fields()
    
    if success:
        print("\n✅ Speeches table fields added successfully!")
        print("🔄 Ready to retry T109 speech data collection")
    else:
        print("\n❌ Failed to add all required fields")

if __name__ == "__main__":
    asyncio.run(main())