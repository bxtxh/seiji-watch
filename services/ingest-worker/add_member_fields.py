#!/usr/bin/env python3
"""
Add required fields to existing Members table
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def add_member_fields():
    """Add required fields to Members table"""
    
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
                members_table_id = None
                parties_table_id = None
                
                for table in data.get("tables", []):
                    if table["name"] == "Members (議員)":
                        members_table_id = table["id"]
                    elif table["name"] == "Parties (政党)":
                        parties_table_id = table["id"]
                
                if not members_table_id:
                    print("❌ Members table not found")
                    return False
                
                print(f"🔍 Members table ID: {members_table_id}")
                print(f"🔍 Parties table ID: {parties_table_id}")
                
                # Fields to add
                fields_to_add = [
                    {"name": "Name_Kana", "type": "singleLineText"},
                    {"name": "Name_EN", "type": "singleLineText"},
                    {"name": "House", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "衆議院"}, 
                            {"name": "参議院"}
                        ]
                    }},
                    {"name": "Constituency", "type": "singleLineText"},
                    {"name": "Diet_Member_ID", "type": "singleLineText"},
                    {"name": "Birth_Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
                    {"name": "Gender", "type": "singleSelect", "options": {
                        "choices": [
                            {"name": "男性"}, 
                            {"name": "女性"},
                            {"name": "その他"}
                        ]
                    }},
                    {"name": "First_Elected", "type": "singleLineText"},
                    {"name": "Terms_Served", "type": "number", "options": {"precision": 0}},
                    {"name": "Previous_Occupations", "type": "multilineText"},
                    {"name": "Education", "type": "multilineText"},
                    {"name": "Website_URL", "type": "url"},
                    {"name": "Twitter_Handle", "type": "singleLineText"},
                    {"name": "Facebook_URL", "type": "url"},
                    {"name": "Is_Active", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
                    {"name": "Created_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}},
                    {"name": "Updated_At", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Tokyo"}}
                ]
                
                # Add Party link field if Parties table exists
                if parties_table_id:
                    fields_to_add.append({
                        "name": "Party", 
                        "type": "multipleRecordLinks", 
                        "options": {"linkedTableId": parties_table_id}
                    })
                
                # Add fields one by one
                success_count = 0
                for field in fields_to_add:
                    try:
                        add_field_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{members_table_id}/fields"
                        
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
    print("🔧 Adding fields to Members (議員) table...")
    
    success = await add_member_fields()
    
    if success:
        print("\n✅ Members table fields added successfully!")
        print("🔄 Ready to retry T108 member data collection")
    else:
        print("\n❌ Failed to add all required fields")

if __name__ == "__main__":
    asyncio.run(main())