#!/usr/bin/env python3
"""
Bills Improvement Batch 2
第2バッチ - 優先度・ステージ・ステータス改善
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def bills_improvement_batch2():
    """Second batch focusing on Priority, Stage, and Status improvements"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    print("🚀 Starting Bills Improvement Batch 2...")
    print("🎯 Focus: Priority, Stage, Status, Bill_Type completion")

    improvements = {
        "priorities_assigned": 0,
        "stages_filled": 0,
        "statuses_standardized": 0,
        "bill_types_filled": 0,
        "process_methods_filled": 0,
        "errors": 0,
    }

    async with aiohttp.ClientSession() as session:
        # Get next batch of records
        print("📄 Fetching Bills records (offset batch)...")

        async with session.get(
            f"{base_url}/Bills (法案)?maxRecords=50", headers=headers
        ) as response:
            if response.status != 200:
                print(f"❌ Failed to fetch records: {response.status}")
                return

            data = await response.json()
            records = data.get("records", [])
            print(f"📊 Processing {len(records)} Bills records...")

            # Process records 21-40 for comprehensive improvement
            for i, record in enumerate(records):
                if i < 20:  # Skip first 20 (already processed)
                    continue
                if i >= 40:  # Process only next 20
                    break

                record_id = record["id"]
                fields = record.get("fields", {})
                updates = {}

                print(f"\n🔧 Processing record {i+1}/50: {record_id}")

                # 1. Priority assignment (enhanced logic)
                if not fields.get("Priority"):
                    title = fields.get("Title", "").lower()
                    category = fields.get("Category", "")

                    # High priority keywords
                    if any(
                        keyword in title
                        for keyword in ["重要", "基本", "根本", "抜本", "緊急"]
                    ):
                        updates["Priority"] = "high"
                    # Low priority keywords
                    elif any(
                        keyword in title
                        for keyword in ["一部改正", "整備", "技術的", "軽微"]
                    ):
                        updates["Priority"] = "low"
                    # Category-based priority
                    elif category in ["経済・産業", "社会保障", "外交・国際"]:
                        updates["Priority"] = "high"
                    else:
                        updates["Priority"] = "medium"

                    improvements["priorities_assigned"] += 1

                # 2. Stage determination based on status
                if not fields.get("Stage"):
                    status = fields.get("Bill_Status", "")
                    if status == "提出":
                        updates["Stage"] = "Backlog"
                    elif status == "審議中":
                        updates["Stage"] = "審議中"
                    elif status == "採決待ち":
                        updates["Stage"] = "採決待ち"
                    elif status == "成立":
                        updates["Stage"] = "成立"
                    elif status == "廃案":
                        updates["Stage"] = "廃案"
                    else:
                        updates["Stage"] = "Backlog"

                    improvements["stages_filled"] += 1

                # 3. Status standardization
                status = fields.get("Bill_Status", "")
                if status == "議案要旨":
                    updates["Bill_Status"] = "提出"
                    improvements["statuses_standardized"] += 1
                elif not status:
                    updates["Bill_Status"] = "提出"
                    improvements["statuses_standardized"] += 1

                # 4. Bill_Type completion
                if not fields.get("Bill_Type"):
                    updates["Bill_Type"] = "提出法律案"
                    improvements["bill_types_filled"] += 1

                # 5. Process_Method completion
                if not fields.get("Process_Method"):
                    updates["Process_Method"] = "AI処理"
                    improvements["process_methods_filled"] += 1

                # Apply updates if any
                if updates:
                    print(f"   📝 Updating: {list(updates.keys())}")

                    try:
                        update_data = {"fields": updates}
                        async with session.patch(
                            f"{base_url}/Bills (法案)/{record_id}",
                            headers=headers,
                            json=update_data,
                        ) as update_response:
                            if update_response.status == 200:
                                print("   ✅ Update successful")
                            else:
                                print(f"   ❌ Update failed: {update_response.status}")
                                improvements["errors"] += 1
                    except Exception as e:
                        print(f"   ❌ Update error: {e}")
                        improvements["errors"] += 1
                else:
                    print("   ℹ️ No updates needed")

                await asyncio.sleep(0.2)  # Rate limiting

        # Additional improvement - Process all remaining records for essential fields
        print("\n📋 Processing remaining records for essential field completion...")

        # Get all records to fill missing essential fields
        all_records = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(
                f"{base_url}/Bills (法案)", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_records.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    break

        print(
            f"📊 Found {len(all_records)} total records for essential field completion"
        )

        # Quick pass to fill essential missing fields
        for i, record in enumerate(all_records):
            if i >= 50:  # Limit to prevent timeout
                break

            record_id = record["id"]
            fields = record.get("fields", {})
            updates = {}

            # Fill only critical missing fields
            if not fields.get("Bill_Type"):
                updates["Bill_Type"] = "提出法律案"

            if not fields.get("Process_Method"):
                updates["Process_Method"] = "AI処理"

            if not fields.get("Bill_Status"):
                updates["Bill_Status"] = "提出"

            if updates:
                try:
                    update_data = {"fields": updates}
                    async with session.patch(
                        f"{base_url}/Bills (法案)/{record_id}",
                        headers=headers,
                        json=update_data,
                    ) as update_response:
                        if update_response.status == 200:
                            for field in updates.keys():
                                if field == "Bill_Type":
                                    improvements["bill_types_filled"] += 1
                                elif field == "Process_Method":
                                    improvements["process_methods_filled"] += 1
                                elif field == "Bill_Status":
                                    improvements["statuses_standardized"] += 1
                        else:
                            improvements["errors"] += 1
                except Exception:
                    improvements["errors"] += 1

                await asyncio.sleep(0.1)

    # Print summary
    print(f"\n{'='*70}")
    print("📋 BILLS IMPROVEMENT BATCH 2 SUMMARY")
    print(f"{'='*70}")
    print(f"⭐ Priorities assigned: {improvements['priorities_assigned']}")
    print(f"📊 Stages filled: {improvements['stages_filled']}")
    print(f"🔧 Statuses standardized: {improvements['statuses_standardized']}")
    print(f"📋 Bill types filled: {improvements['bill_types_filled']}")
    print(f"⚙️ Process methods filled: {improvements['process_methods_filled']}")
    print(f"❌ Errors: {improvements['errors']}")

    total_improvements = sum(v for k, v in improvements.items() if k != "errors")
    print(f"\n✅ Total improvements in batch 2: {total_improvements}")

    # Save report
    report = {
        "improvement_date": datetime.now().isoformat(),
        "type": "improvement_batch_2",
        "focus": "priority_stage_status_completion",
        "records_processed": "21-40 + essential field completion",
        "improvements": improvements,
        "notes": "Second batch focusing on Priority, Stage, Status standardization and essential field completion",
    }

    filename = (
        f"bills_improvement_batch2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 Report saved: {filename}")

    return improvements


if __name__ == "__main__":
    asyncio.run(bills_improvement_batch2())
