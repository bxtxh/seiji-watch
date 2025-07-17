#!/usr/bin/env python3
"""
EPIC 11 Pilot Data Insert - Test data insertion to understand Airtable structure
"""

import aiohttp
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def create_test_bill():
    """Create a test bill record to understand the table structure"""
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Load sample bill data
    data_file = '/Users/shogen/seiji-watch/services/ingest-worker/production_scraping_june2025_20250709_032237.json'
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sample_bill = data['production_dataset']['bills'][0]
    print(f"📋 Sample bill: {sample_bill['title']}")
    
    # Test bill record with structured fields
    test_bill_data = {
        "fields": {
            "Name": sample_bill['title'],  # Using Name field as primary
            "Status": sample_bill['stage'],
            "Bill_ID": sample_bill['bill_id'],
            "Category": sample_bill['category'],
            "Stage": sample_bill['stage'],
            "Submitter": sample_bill['submitter'],
            "URL": sample_bill['url'],
            "Collection_Date": sample_bill['collected_at']
        }
    }
    
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    async with aiohttp.ClientSession() as session:
        try:
            print("\n🚀 Creating test bill record...")
            async with session.post(f"{base_url}/Bills (法案)", headers=headers, json=test_bill_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Test bill created successfully!")
                    print(f"Record ID: {result['id']}")
                    print(f"Created fields: {list(result['fields'].keys())}")
                    return result
                else:
                    print(f"❌ Failed to create test bill: {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
                    
                    # If custom fields don't exist, try with just basic fields
                    if "UNKNOWN_FIELD_NAME" in error_text:
                        print("\n🔄 Retrying with basic fields only...")
                        basic_bill_data = {
                            "fields": {
                                "Name": sample_bill['title'],
                                "Bill_ID": sample_bill['bill_id'],
                                "Category": sample_bill['category'],
                                "Stage": sample_bill['stage'],
                                "URL": sample_bill['url'],
                                "Status": sample_bill['stage']
                            }
                        }
                        
                        async with session.post(f"{base_url}/Bills (法案)", headers=headers, json=basic_bill_data) as retry_response:
                            if retry_response.status == 200:
                                result = await retry_response.json()
                                print(f"✅ Test bill created with basic fields!")
                                print(f"Record ID: {result['id']}")
                                print(f"Available fields: {list(result['fields'].keys())}")
                                return result
                            else:
                                retry_error = await retry_response.text()
                                print(f"❌ Retry failed: {retry_response.status}")
                                print(f"Error: {retry_error}")
                                
        except Exception as e:
            print(f"❌ Exception during test bill creation: {e}")
            
        return None

async def create_test_vote():
    """Create a test vote record"""
    
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Load sample vote data
    data_file = '/Users/shogen/seiji-watch/services/ingest-worker/production_scraping_june2025_20250709_032237.json'
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sample_voting_session = data['production_dataset']['voting_sessions'][0]
    sample_vote_record = sample_voting_session['vote_records'][0]
    
    print(f"🗳️ Sample vote: {sample_vote_record['member_name']} - {sample_vote_record['vote_result']}")
    
    # Test vote record
    test_vote_data = {
        "fields": {
            "Name": f"{sample_vote_record['member_name']} - {sample_voting_session['bill_title']}",
            "Member_Name": sample_vote_record['member_name'],
            "Member_Name_Kana": sample_vote_record['member_name_kana'],
            "Party_Name": sample_vote_record['party_name'],
            "Constituency": sample_vote_record['constituency'],
            "House": sample_vote_record['house'],
            "Vote_Result": sample_vote_record['vote_result'],
            "Bill_Title": sample_voting_session['bill_title'],
            "Vote_Date": sample_voting_session['vote_date'],
            "Status": sample_vote_record['vote_result']
        }
    }
    
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    async with aiohttp.ClientSession() as session:
        try:
            print("\n🚀 Creating test vote record...")
            async with session.post(f"{base_url}/Votes (投票)", headers=headers, json=test_vote_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Test vote created successfully!")
                    print(f"Record ID: {result['id']}")
                    print(f"Created fields: {list(result['fields'].keys())}")
                    return result
                else:
                    print(f"❌ Failed to create test vote: {response.status}")
                    error_text = await response.text()
                    print(f"Error details: {error_text}")
                    
        except Exception as e:
            print(f"❌ Exception during test vote creation: {e}")
            
        return None

async def analyze_data_requirements():
    """Analyze our data vs Airtable requirements"""
    
    print("\n📊 EPIC 11 Data Analysis:")
    
    # Load production data
    data_file = '/Users/shogen/seiji-watch/services/ingest-worker/production_scraping_june2025_20250709_032237.json'
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    bills = data['production_dataset']['bills']
    voting_sessions = data['production_dataset']['voting_sessions']
    
    print(f"📋 Bills to integrate: {len(bills)}")
    print(f"🗳️ Voting sessions: {len(voting_sessions)}")
    
    # Calculate total vote records
    total_vote_records = sum(len(session.get('vote_records', [])) for session in voting_sessions)
    print(f"🗳️ Individual vote records: {total_vote_records}")
    
    # Sample bill fields analysis
    print(f"\n📋 Bill data structure:")
    sample_bill = bills[0]
    for key, value in sample_bill.items():
        print(f"  {key}: {type(value).__name__} - {str(value)[:50]}")
    
    # Sample vote record analysis
    print(f"\n🗳️ Vote record structure:")
    sample_vote = voting_sessions[0]['vote_records'][0]
    for key, value in sample_vote.items():
        print(f"  {key}: {type(value).__name__} - {str(value)[:50]}")

async def main():
    """Execute EPIC 11 Pilot Test"""
    
    print("=" * 60)
    print("🧪 EPIC 11 PILOT: Airtable構造確認・テストデータ投入")
    print("=" * 60)
    
    # Analyze data requirements
    await analyze_data_requirements()
    
    # Create test records
    bill_result = await create_test_bill()
    vote_result = await create_test_vote()
    
    if bill_result and vote_result:
        print("\n🎯 PILOT TEST SUCCESSFUL!")
        print("✅ Ready to proceed with full data integration (T96)")
        print("📝 Next: Modify integration script based on working field mappings")
    else:
        print("\n⚠️ PILOT TEST ISSUES")
        print("🔧 Need to adjust field mappings for full integration")

if __name__ == "__main__":
    asyncio.run(main())