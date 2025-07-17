#!/usr/bin/env python3
"""
T129 - Data Migration: Bills enum categories → IssueCategories mapping
Creates Bills-PolicyCategory relationships for existing Bills data
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

# Set environment variables
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Category mapping from Bills.category enum to IssueCategories
CATEGORY_MAPPING = {
    # Bills enum category → IssueCategories CAP code mapping
    "予算・決算": "1.1",  # Budget, Fiscal Policy
    "税制": "1.2",        # Tax Policy
    "社会保障": "13.1",   # Social Security, Healthcare
    "外交・国際": "19.1", # International Relations
    "経済・産業": "15.1", # Economic Policy, Industry
    "教育・文化": "2.1",  # Education, Culture
    "環境・エネルギー": "7.1", # Environment, Energy
    "農林水産": "4.1",    # Agriculture, Food
    "司法・法務": "12.1", # Justice, Legal Affairs
    "防衛": "16.1",       # Defense
    "その他": "20.1",     # Others
    "憲法・統治": "11.1"  # Constitution, Governance
}

async def analyze_bills_categories():
    """Analyze existing Bills data to understand category distribution."""
    
    print("🔍 Analyzing Bills Category Distribution")
    print("=" * 60)
    
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables required")
        return False
    
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Get all Bills records
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Bills%20%28%E6%B3%95%E6%A1%88%29"
        all_bills = []
        
        try:
            # Fetch all bills with pagination
            params = {"maxRecords": 100}
            offset = None
            
            while True:
                if offset:
                    params["offset"] = offset
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        print(f"❌ Failed to fetch bills: {response.status}")
                        text = await response.text()
                        print(f"   Error: {text}")
                        return False
                    
                    data = await response.json()
                    records = data.get("records", [])
                    all_bills.extend(records)
                    
                    offset = data.get("offset")
                    if not offset:
                        break
            
            print(f"📋 Total Bills found: {len(all_bills)}")
            
            # Analyze category distribution
            category_counts = defaultdict(int)
            bills_by_category = defaultdict(list)
            
            for bill in all_bills:
                fields = bill.get("fields", {})
                category = fields.get("Category", "その他")
                
                category_counts[category] += 1
                bills_by_category[category].append({
                    "id": bill.get("id"),
                    "name": fields.get("Name", "Unknown"),
                    "bill_number": fields.get("Bill_Number", "Unknown"),
                    "status": fields.get("Bill_Status", "Unknown"),
                    "stage": fields.get("Stage", "Unknown")
                })
            
            print("\n📊 Category Distribution:")
            total_bills = len(all_bills)
            for category, count in sorted(category_counts.items()):
                percentage = (count / total_bills) * 100
                cap_code = CATEGORY_MAPPING.get(category, "Unknown")
                print(f"   {category}: {count} bills ({percentage:.1f}%) → CAP {cap_code}")
            
            # Show unmapped categories
            unmapped_categories = [cat for cat in category_counts.keys() if cat not in CATEGORY_MAPPING]
            if unmapped_categories:
                print(f"\n⚠️  Unmapped categories: {', '.join(unmapped_categories)}")
            
            return {
                "total_bills": total_bills,
                "category_counts": dict(category_counts),
                "bills_by_category": dict(bills_by_category)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing bills: {e}")
            return False

async def fetch_issue_categories():
    """Fetch all IssueCategories to understand the target mapping."""
    
    print("\n🔍 Fetching IssueCategories for Mapping")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Use table ID for reliable access
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/tbl6wK8L9K5ny1dDm"
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"❌ Failed to fetch IssueCategories: {response.status}")
                    text = await response.text()
                    print(f"   Error: {text}")
                    return False
                
                data = await response.json()
                categories = data.get("records", [])
                
                print(f"📋 Total IssueCategories found: {len(categories)}")
                
                if not categories:
                    print("⚠️  No IssueCategories found. Need to populate this table first.")
                    return False
                
                # Organize by CAP code for mapping
                cap_mapping = {}
                for category in categories:
                    fields = category.get("fields", {})
                    cap_code = fields.get("CAP_Code", "")
                    title_ja = fields.get("Title_JA", "")
                    layer = fields.get("Layer", "")
                    
                    if cap_code:
                        cap_mapping[cap_code] = {
                            "id": category.get("id"),
                            "title_ja": title_ja,
                            "layer": layer,
                            "record": category
                        }
                
                print("\n📊 Available PolicyCategories by CAP Code:")
                for cap_code, info in sorted(cap_mapping.items()):
                    print(f"   {cap_code}: {info['title_ja']} ({info['layer']})")
                
                return cap_mapping
                
        except Exception as e:
            print(f"❌ Error fetching IssueCategories: {e}")
            return False

async def create_bills_policy_category_relationships(bills_data: Dict[str, Any], cap_mapping: Dict[str, Any]):
    """Create Bills-PolicyCategory relationships based on mapping."""
    
    print("\n🔄 Creating Bills-PolicyCategory Relationships")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json"
    }
    
    # Check if Bills_PolicyCategories table exists
    bills_policy_categories_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Bills_PolicyCategories"
    
    relationships_to_create = []
    successful_mappings = 0
    failed_mappings = 0
    
    async with aiohttp.ClientSession() as session:
        
        # First, test if the table exists
        try:
            async with session.get(bills_policy_categories_url, headers=headers) as response:
                if response.status == 404:
                    print("❌ Bills_PolicyCategories table not found. Need to create it first.")
                    return False
                elif response.status != 200:
                    print(f"❌ Error accessing Bills_PolicyCategories table: {response.status}")
                    return False
                
                print("✅ Bills_PolicyCategories table found and accessible")
        except Exception as e:
            print(f"❌ Error checking Bills_PolicyCategories table: {e}")
            return False
        
        # Process each category
        for category, bills_list in bills_data["bills_by_category"].items():
            cap_code = CATEGORY_MAPPING.get(category)
            
            if not cap_code:
                print(f"⚠️  Skipping unmapped category: {category}")
                failed_mappings += len(bills_list)
                continue
            
            if cap_code not in cap_mapping:
                print(f"⚠️  CAP code {cap_code} not found in IssueCategories")
                failed_mappings += len(bills_list)
                continue
            
            policy_category = cap_mapping[cap_code]
            print(f"\n📎 Mapping {category} → {policy_category['title_ja']} ({cap_code})")
            
            # Create relationships for all bills in this category
            for bill in bills_list:
                relationship_data = {
                    "Bill_ID": bill["id"],
                    "PolicyCategory_ID": policy_category["id"],
                    "Confidence_Score": 0.9,  # High confidence for enum mapping
                    "Is_Manual": False,
                    "Source": "enum_migration",
                    "Notes": f"Migrated from Bills.Category enum value: {category}",
                    "Created_At": datetime.now().isoformat()
                }
                
                relationships_to_create.append(relationship_data)
                successful_mappings += 1
        
        print(f"\n📊 Migration Summary:")
        print(f"   Successful mappings: {successful_mappings}")
        print(f"   Failed mappings: {failed_mappings}")
        print(f"   Total relationships to create: {len(relationships_to_create)}")
        
        if not relationships_to_create:
            print("⚠️  No relationships to create")
            return True
        
        # Create relationships in batches (Airtable limit: 10 per request)
        created_count = 0
        error_count = 0
        
        for i in range(0, len(relationships_to_create), 10):
            batch = relationships_to_create[i:i+10]
            
            # Prepare batch data
            records_data = []
            for rel in batch:
                record_data = {
                    "fields": {
                        "Bill_ID": rel["Bill_ID"],
                        "PolicyCategory_ID": rel["PolicyCategory_ID"],
                        "Confidence_Score": rel["Confidence_Score"],
                        "Is_Manual": rel["Is_Manual"],
                        "Source": rel["Source"],
                        "Notes": rel["Notes"],
                        "Created_At": rel["Created_At"]
                    }
                }
                records_data.append(record_data)
            
            batch_data = {"records": records_data}
            
            try:
                async with session.post(bills_policy_categories_url, headers=headers, json=batch_data) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        batch_created = len(response_data.get("records", []))
                        created_count += batch_created
                        print(f"✅ Batch {i//10 + 1}: Created {batch_created} relationships")
                    else:
                        error_text = await response.text()
                        print(f"❌ Batch {i//10 + 1} failed: {response.status}")
                        print(f"   Error: {error_text}")
                        error_count += len(batch)
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Batch {i//10 + 1} error: {e}")
                error_count += len(batch)
        
        print(f"\n🎉 Migration Complete!")
        print(f"   Successfully created: {created_count} relationships")
        print(f"   Errors: {error_count}")
        
        return created_count > 0

async def verify_migration():
    """Verify the created relationships."""
    
    print("\n🔍 Verifying Migration Results")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        bills_policy_categories_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Bills_PolicyCategories"
        
        try:
            async with session.get(bills_policy_categories_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    relationships = data.get("records", [])
                    
                    print(f"✅ Total relationships created: {len(relationships)}")
                    
                    # Count by source
                    source_counts = defaultdict(int)
                    confidence_stats = defaultdict(int)
                    
                    for rel in relationships:
                        fields = rel.get("fields", {})
                        source = fields.get("Source", "unknown")
                        confidence = fields.get("Confidence_Score", 0)
                        
                        source_counts[source] += 1
                        
                        if confidence >= 0.9:
                            confidence_stats["high"] += 1
                        elif confidence >= 0.7:
                            confidence_stats["medium"] += 1
                        else:
                            confidence_stats["low"] += 1
                    
                    print("\n📊 Verification Results:")
                    print(f"   Migration sources: {dict(source_counts)}")
                    print(f"   Confidence distribution: {dict(confidence_stats)}")
                    
                    # Show sample relationships
                    print("\n📋 Sample Relationships:")
                    for i, rel in enumerate(relationships[:5]):
                        fields = rel.get("fields", {})
                        bill_id = fields.get("Bill_ID", "Unknown")
                        policy_cat_id = fields.get("PolicyCategory_ID", "Unknown")
                        confidence = fields.get("Confidence_Score", 0)
                        source = fields.get("Source", "Unknown")
                        
                        print(f"   {i+1}. Bill {bill_id} → PolicyCategory {policy_cat_id} (conf: {confidence}, source: {source})")
                    
                    return True
                    
                else:
                    print(f"❌ Verification failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False

async def main():
    """Main migration execution."""
    
    print("🚀 T129 - Bills Category Migration to PolicyCategory")
    print("=" * 70)
    
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("❌ AIRTABLE_PAT and AIRTABLE_BASE_ID environment variables required")
        return 1
    
    # Step 1: Analyze existing Bills data
    bills_data = await analyze_bills_categories()
    if not bills_data:
        return 1
    
    # Step 2: Fetch IssueCategories for mapping
    cap_mapping = await fetch_issue_categories()
    if not cap_mapping:
        return 1
    
    # Step 3: Create Bills-PolicyCategory relationships
    migration_success = await create_bills_policy_category_relationships(bills_data, cap_mapping)
    if not migration_success:
        return 1
    
    # Step 4: Verify migration
    verification_success = await verify_migration()
    if not verification_success:
        return 1
    
    print("\n✅ T129 Migration completed successfully!")
    print("🔧 Next steps: Run T130 to update frontend integration")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)