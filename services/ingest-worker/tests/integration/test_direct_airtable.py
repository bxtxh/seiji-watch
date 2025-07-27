#!/usr/bin/env python3
"""
Direct Airtable API test without shared dependencies
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/Users/shogen/seiji-watch/.env.local")


async def test_direct_airtable_access():
    """Test direct Airtable API access for all tables"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not pat or not base_id:
        print("❌ Missing Airtable credentials (PAT or BASE_ID)")
        print(f"  PAT found: {'Yes' if pat else 'No'}")
        print(f"  BASE_ID found: {'Yes' if base_id else 'No'}")
        return False

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    base_url = f"https://api.airtable.com/v0/{base_id}"

    # Test all tables - complete set (9 tables)
    test_tables = [
        ("Bills (法案)", "📋"),
        ("Members (議員)", "👥"),
        ("Speeches (発言)", "🎤"),
        ("Issues (課題)", "🎯"),
        ("Votes (投票)", "🗳️"),
        ("IssueTags (課題タグ)", "🏷️"),
        ("Parties (政党)", "🏛️"),
        ("Meetings (会議)", "📅"),
        ("IssueCategories (課題カテゴリ)", "📂"),
    ]

    async with aiohttp.ClientSession() as session:
        print("🔍 T107: Airtable権限確認・テスト実行")
        print("=" * 60)

        success_count = 0
        total_records = 0

        for table_name, emoji in test_tables:
            try:
                print(f"\n{emoji} Testing {table_name}...")

                # Test basic read access
                async with session.get(
                    f"{base_url}/{table_name}",
                    headers=headers,
                    params={"maxRecords": 3},
                ) as response:
                    print(f"  Status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        records = data.get("records", [])
                        count = len(records)
                        total_records += count
                        success_count += 1

                        print(f"  ✅ SUCCESS: {count} records accessible")

                        if count > 0:
                            sample = records[0]
                            fields = list(sample["fields"].keys())
                            print(
                                f"  Fields: {fields[:3]}{'...' if len(fields) > 3 else ''}"
                            )

                    elif response.status == 403:
                        print("  ❌ PERMISSION DENIED (403)")
                        error_text = await response.text()
                        print(f"  Error: {error_text[:100]}...")

                    elif response.status == 404:
                        print("  ⚠️  TABLE NOT FOUND (404)")

                    else:
                        print(f"  ❌ ERROR: {response.status}")
                        error_text = await response.text()
                        print(f"  Error: {error_text[:100]}...")

            except Exception as e:
                print(f"  ❌ EXCEPTION: {e}")

        # Test write access on Bills table
        print("\n📝 Testing WRITE access on Bills table...")
        try:
            test_data = {
                "fields": {
                    "Name": "TEST: Data Access Verification",
                    "Notes": f"権限テスト - {asyncio.get_event_loop().time()}",
                }
            }

            async with session.post(
                f"{base_url}/Bills (法案)", headers=headers, json=test_data
            ) as response:
                print(f"  Write Status: {response.status}")

                if response.status == 200:
                    result = await response.json()
                    record_id = result.get("id")
                    print(f"  ✅ WRITE SUCCESS: Created record {record_id}")

                    # Clean up test record
                    async with session.delete(
                        f"{base_url}/Bills (法案)/{record_id}", headers=headers
                    ) as delete_response:
                        if delete_response.status == 200:
                            print("  🗑️  Test record cleaned up")

                else:
                    error_text = await response.text()
                    print(f"  ❌ WRITE FAILED: {error_text[:100]}...")

        except Exception as e:
            print(f"  ❌ WRITE TEST EXCEPTION: {e}")

        # Summary
        print("\n" + "=" * 60)
        print("📊 T107 Results Summary")
        print("=" * 60)
        print(f"✅ Accessible Tables: {success_count}/{len(test_tables)}")
        print(f"📈 Total Records Found: {total_records}")
        print(f"🎯 Success Rate: {success_count / len(test_tables) * 100:.1f}%")

        if success_count == len(test_tables):
            print("\n🎉 ALL TABLES ACCESSIBLE!")
            print("✅ T107 COMPLETED - Ready for T108 (議員データ収集)")
            return True
        elif success_count >= 2:
            print("\n⚠️  PARTIAL ACCESS - Some tables accessible")
            print("💡 可以继续进行有限的数据收集")
            return "partial"
        else:
            print("\n❌ MAJOR ACCESS ISSUES")
            print("🔧 需要进一步检查Airtable权限设置")
            return False


async def main():
    """Main function"""
    print("🚀 EPIC 13 T107: Airtable権限確認・テスト実行")
    print("🎯 目標: 全9テーブルへのアクセス確認")
    print()

    result = await test_direct_airtable_access()

    if result:
        print("\n✅ T107 COMPLETE: All permissions working")
        print("🔄 Next: T108 議員データ収集実行")
    elif result == "partial":
        print("\n⚠️  T107 PARTIAL: Limited access available")
        print("🔄 可以进行有限的数据收集")
    else:
        print("\n❌ T107 FAILED: Permission issues remain")
        print("🔧 需要进一步权限配置")

    return result


if __name__ == "__main__":
    result = asyncio.run(main())
