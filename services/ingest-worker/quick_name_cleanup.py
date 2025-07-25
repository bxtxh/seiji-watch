#!/usr/bin/env python3
"""
Quick Members Name Cleanup - Remove Trailing Numbers (Batch Processing)
"""

import asyncio
import os
import re

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def quick_name_cleanup():
    """Quick cleanup of member names with trailing numbers"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    print("🧹 Quick Members Name Cleanup...")

    cleaned_count = 0
    errors = 0

    async with aiohttp.ClientSession() as session:
        # Get records with pagination
        all_records = []
        offset = None

        while True:
            params = {"pageSize": 100}
            if offset:
                params["offset"] = offset

            async with session.get(
                f"{base_url}/Members (議員)", headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])
                    all_records.extend(records)

                    offset = data.get("offset")
                    if not offset:
                        break
                else:
                    print(f"❌ Error: {response.status}")
                    return

        print(f"📊 Processing {len(all_records)} records...")

        # Process in batches of 50
        batch_size = 50
        for batch_start in range(0, len(all_records), batch_size):
            batch = all_records[batch_start : batch_start + batch_size]
            batch_cleaned = 0

            for record in batch:
                name = record.get("fields", {}).get("Name", "")

                # Check if name ends with digits
                if re.search(r"\d+$", name):
                    clean_name = re.sub(r"\d+$", "", name).strip()

                    if clean_name != name:  # Only update if changed
                        try:
                            update_data = {"fields": {"Name": clean_name}}

                            async with session.patch(
                                f"{base_url}/Members (議員)/{record['id']}",
                                headers=headers,
                                json=update_data,
                            ) as response:
                                if response.status == 200:
                                    cleaned_count += 1
                                    batch_cleaned += 1
                                else:
                                    errors += 1
                        except Exception:
                            errors += 1

                        await asyncio.sleep(0.05)  # Faster rate limiting

            if batch_cleaned > 0:
                print(
                    f"   ✅ Batch {batch_start//batch_size + 1}: Cleaned {batch_cleaned} names"
                )

        # Quick verification
        print("\n🔍 Quick verification...")

        # Sample check - get first 100 records
        async with session.get(
            f"{base_url}/Members (議員)", headers=headers, params={"pageSize": 100}
        ) as response:
            if response.status == 200:
                data = await response.json()
                sample_records = data.get("records", [])

                remaining_issues = 0
                for record in sample_records:
                    name = record.get("fields", {}).get("Name", "")
                    if re.search(r"\d+$", name):
                        remaining_issues += 1

                print(
                    f"📊 Sample check: {remaining_issues}/100 still have trailing numbers"
                )

    print(f"\n{'='*50}")
    print("🧹 QUICK CLEANUP SUMMARY")
    print(f"{'='*50}")
    print(f"✅ Names cleaned: {cleaned_count}")
    print(f"❌ Errors: {errors}")

    if cleaned_count > 200:
        print("🎉 SUCCESS! Most trailing numbers removed!")
    elif cleaned_count > 100:
        print(f"👍 Good progress - {cleaned_count} names cleaned")
    else:
        print(f"⚠️ Partial - {cleaned_count} names cleaned")

    return {"cleaned": cleaned_count, "errors": errors}


if __name__ == "__main__":
    asyncio.run(quick_name_cleanup())
