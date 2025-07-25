#!/usr/bin/env python3
"""
Verify Members Name State - Check for remaining trailing numbers
"""

import asyncio
import os
import re

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def verify_member_names():
    """Verify the current state of member names"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    base_url = f"https://api.airtable.com/v0/{base_id}"

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    print("🔍 Verifying Members Name State...")

    async with aiohttp.ClientSession() as session:
        # Get all records
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

        print(f"📊 Total records: {len(all_records)}")

        # Analyze names
        names_with_numbers = []
        clean_names = []

        for record in all_records:
            name = record.get("fields", {}).get("Name", "")
            if name:
                if re.search(r"\d+$", name):
                    names_with_numbers.append(
                        {
                            "id": record["id"],
                            "name": name,
                            "constituency": record.get("fields", {}).get(
                                "Constituency", ""
                            ),
                            "house": record.get("fields", {}).get("House", ""),
                        }
                    )
                else:
                    clean_names.append(name)

        print(f"✅ Clean names: {len(clean_names)}")
        print(f"⚠️ Names with trailing numbers: {len(names_with_numbers)}")

        if names_with_numbers:
            print("\n📋 Names still with trailing numbers:")
            for i, item in enumerate(names_with_numbers[:20]):  # Show first 20
                print(
                    f"   {i+1:2d}. {item['name']} ({item['house']}, {item['constituency']})"
                )

            if len(names_with_numbers) > 20:
                print(f"   ... and {len(names_with_numbers) - 20} more")
        else:
            print("\n🎉 All names are clean! No trailing numbers found.")

        # Quality assessment
        clean_percentage = (len(clean_names) / len(all_records)) * 100
        print(f"\n📈 Name Quality: {clean_percentage:.1f}% clean")

        if clean_percentage == 100:
            print("🏆 PERFECT! All member names are properly formatted.")
        elif clean_percentage >= 98:
            print("🎯 EXCELLENT! Almost all names are clean.")
        elif clean_percentage >= 95:
            print("👍 GOOD! Most names are clean.")
        else:
            print(
                f"⚠️ Needs attention - {len(names_with_numbers)} names still need cleanup."
            )

        return {
            "total_records": len(all_records),
            "clean_names": len(clean_names),
            "names_with_numbers": len(names_with_numbers),
            "clean_percentage": clean_percentage,
        }


if __name__ == "__main__":
    asyncio.run(verify_member_names())
