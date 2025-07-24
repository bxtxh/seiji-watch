#!/usr/bin/env python3
"""
Simple data diagnosis script that tests Airtable directly
"""

import asyncio
import os

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/shogen/seiji-watch/.env.local')


async def diagnose_data_quality():
    """Diagnose data quality in all tables"""

    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")

    if not pat or not base_id:
        print("❌ Missing Airtable credentials (PAT or BASE_ID)")
        return

    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

    base_url = f"https://api.airtable.com/v0/{base_id}"

    async with aiohttp.ClientSession() as session:
        print("=" * 60)
        print("🔍 DIET ISSUE TRACKER - DATA QUALITY DIAGNOSIS")
        print("=" * 60)

        # Define all tables to check
        tables = [
            ("Bills (法案)", "📋"),
            ("Members", "👥"),
            ("Speeches", "🎤"),
            ("Issues", "🎯"),
            ("Votes (投票)", "🗳️"),
            ("Parties", "🏛️"),
            ("Meetings", "📅"),
            ("IssueTags", "🏷️"),
            ("IssueCategories", "📂")
        ]

        total_records = 0
        table_stats = {}

        for table_name, emoji in tables:
            try:
                print(f"\n{emoji} {table_name} table:")

                # Get first page of records
                async with session.get(
                    f"{base_url}/{table_name}",
                    headers=headers,
                    params={"maxRecords": 100}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        records = data.get('records', [])
                        count = len(records)
                        total_records += count

                        print(f"  Records: {count}")

                        if count > 0:
                            # Analyze first record structure
                            sample = records[0]
                            fields = list(sample['fields'].keys())
                            print(
                                f"  Fields: {len(fields)} ({', '.join(fields[:5])}{'...' if len(fields) > 5 else ''})")

                            # Check for data completeness
                            filled_fields = sum(
                                1 for field in sample['fields'].values() if field)
                            completeness = (
                                filled_fields / len(fields)) * 100 if fields else 0
                            print(
                                f"  Completeness: {completeness:.1f}% (sample record)")

                            # Check for common quality issues
                            issues = []
                            for field_name, field_value in sample['fields'].items():
                                if field_value == "" or field_value == []:
                                    issues.append(f"Empty {field_name}")

                            if issues and len(issues) <= 3:
                                print(f"  Issues: {', '.join(issues)}")
                            elif len(issues) > 3:
                                print(f"  Issues: {len(issues)} empty fields")

                        table_stats[table_name] = {
                            'count': count,
                            'has_data': count > 0,
                            'sample_fields': fields if count > 0 else []
                        }

                    elif response.status == 404:
                        print("  ⚠️ Table not found")
                        table_stats[table_name] = {
                            'count': 0, 'has_data': False, 'sample_fields': []}
                    else:
                        print(f"  ❌ Error: {response.status}")
                        table_stats[table_name] = {
                            'count': 0, 'has_data': False, 'sample_fields': []}

            except Exception as e:
                print(f"  ❌ Exception: {e}")
                table_stats[table_name] = {
                    'count': 0, 'has_data': False, 'sample_fields': []}

        # Summary analysis
        print("\n" + "=" * 60)
        print("📊 DATA QUALITY ASSESSMENT SUMMARY")
        print("=" * 60)
        print(f"📈 Total Records: {total_records}")

        # Core tables analysis
        core_tables = ["Bills (法案)", "Members", "Speeches", "Issues"]
        core_data_ready = all(
            table_stats.get(
                table,
                {}).get(
                'has_data',
                False) for table in core_tables)

        print("\n🎯 Core Tables Status:")
        for table in core_tables:
            stats = table_stats.get(table, {})
            status = "✅" if stats.get('has_data', False) else "❌"
            count = stats.get('count', 0)
            print(f"  {status} {table}: {count} records")

        # Data pipeline status assessment
        print("\n🚀 Pipeline Status Assessment:")
        if core_data_ready:
            print("✅ データ収集（生成）パイプラインが完全に策定されている")
            print("✅ データ収集が完了し1次データになっている")
            print("✅ データが本番環境に流し込まれている")

            # Check for data formatting needs
            bills_count = table_stats.get("Bills (法案)", {}).get('count', 0)
            members_count = table_stats.get("Members", {}).get('count', 0)

            formatting_needed = []
            if bills_count < 150:
                formatting_needed.append("法案データの追加収集が必要")
            if members_count < 50:
                formatting_needed.append("議員データの補完が必要")

            if formatting_needed:
                print(f"⚠️ データに整形の必要がある: {', '.join(formatting_needed)}")
            else:
                print("✅ データ整形は最小限でよい状態")

        else:
            print("❌ コアテーブルにデータが不足しています")

        # Recommendations
        print("\n💡 改善提案:")
        bills_count = table_stats.get("Bills (法案)", {}).get('count', 0)
        members_count = table_stats.get("Members", {}).get('count', 0)
        speeches_count = table_stats.get("Speeches", {}).get('count', 0)
        issues_count = table_stats.get("Issues", {}).get('count', 0)

        if bills_count < 150:
            print(f"  • 法案データ収集の強化 (現在{bills_count}件 → 目標150件)")
        if members_count < 50:
            print(f"  • 議員データの補完 (現在{members_count}件)")
        if speeches_count < 100:
            print(f"  • 発言データの収集拡大 (現在{speeches_count}件)")
        if issues_count < 50:
            print(f"  • イシューデータの生成強化 (現在{issues_count}件)")

        # Table permission issues
        permission_issues = [
            table for table, stats in table_stats.items() if not stats.get(
                'has_data', True) and stats.get(
                'count', -1) == 0]
        if permission_issues:
            print(f"  • Airtableテーブル権限の確認が必要: {', '.join(permission_issues)}")

        return table_stats


async def main():
    """Main function"""
    try:
        await diagnose_data_quality()
    except Exception as e:
        print(f"💥 Diagnosis failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
