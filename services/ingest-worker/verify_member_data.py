#!/usr/bin/env python3
"""
Verify member data in Airtable
議員データの検証スクリプト
"""

import asyncio
import os
from collections import defaultdict
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')


class MemberDataVerifier:
    """Member data verification tool"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }

    async def get_all_members(self, session: aiohttp.ClientSession) -> list:
        """Get all members from Airtable"""
        all_members = []
        offset = None

        while True:
            try:
                url = f"{self.base_url}/Members (議員)"
                params = {}
                if offset:
                    params['offset'] = offset

                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        all_members.extend(data.get('records', []))

                        # Check for pagination
                        offset = data.get('offset')
                        if not offset:
                            break
                    else:
                        print(f"Error fetching members: {response.status}")
                        break

            except Exception as e:
                print(f"Error in get_all_members: {e}")
                break

        return all_members

    async def get_all_parties(self, session: aiohttp.ClientSession) -> dict:
        """Get all parties from Airtable"""
        try:
            async with session.get(
                f"{self.base_url}/Parties (政党)",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {record['id']: record['fields']['Name']
                            for record in data.get('records', [])}
                else:
                    print(f"Error fetching parties: {response.status}")
                    return {}
        except Exception as e:
            print(f"Error in get_all_parties: {e}")
            return {}

    def analyze_member_data(self, members: list, parties: dict) -> dict:
        """Analyze member data and generate statistics"""
        stats = {
            'total_members': len(members),
            'house_distribution': defaultdict(int),
            'party_distribution': defaultdict(int),
            'constituency_distribution': defaultdict(int),
            'data_completeness': defaultdict(int),
            'missing_data': defaultdict(list),
            'duplicates': []
        }

        seen_names = defaultdict(list)

        for member in members:
            fields = member.get('fields', {})
            name = fields.get('Name', 'Unknown')

            # Track duplicates
            seen_names[name].append(member['id'])

            # House distribution
            house = fields.get('House', 'Unknown')
            stats['house_distribution'][house] += 1

            # Party distribution
            party_links = fields.get('Party', [])
            if party_links:
                party_id = party_links[0] if isinstance(
                    party_links, list) else party_links
                party_name = parties.get(party_id, 'Unknown Party')
                stats['party_distribution'][party_name] += 1
            else:
                stats['party_distribution']['無所属'] += 1

            # Constituency distribution
            constituency = fields.get('Constituency', 'Unknown')
            stats['constituency_distribution'][constituency] += 1

            # Data completeness analysis
            required_fields = ['Name', 'House', 'Is_Active']
            optional_fields = [
                'Name_Kana',
                'Constituency',
                'Party',
                'First_Elected',
                'Terms_Served',
                'Birth_Date',
                'Gender',
                'Previous_Occupations',
                'Education',
                'Website_URL',
                'Twitter_Handle']

            for field in required_fields:
                if field in fields and fields[field]:
                    stats['data_completeness'][field] += 1
                else:
                    stats['missing_data'][field].append(name)

            for field in optional_fields:
                if field in fields and fields[field]:
                    stats['data_completeness'][field] += 1

        # Find duplicates
        for name, member_ids in seen_names.items():
            if len(member_ids) > 1:
                stats['duplicates'].append({'name': name, 'ids': member_ids})

        return stats

    def print_verification_report(self, stats: dict):
        """Print verification report"""
        print("\n" + "=" * 60)
        print("🔍 議員データベース検証レポート")
        print("=" * 60)
        print(f"📊 総議員数: {stats['total_members']:,}名")
        print(f"📅 検証日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # House distribution
        print("\n📋 院別分布:")
        for house, count in sorted(stats['house_distribution'].items()):
            percentage = (count / stats['total_members']) * 100
            print(f"  {house}: {count:,}名 ({percentage:.1f}%)")

        # Party distribution
        print("\n🏛️ 政党別分布:")
        sorted_parties = sorted(
            stats['party_distribution'].items(),
            key=lambda x: x[1],
            reverse=True)
        for party, count in sorted_parties:
            percentage = (count / stats['total_members']) * 100
            print(f"  {party}: {count:,}名 ({percentage:.1f}%)")

        # Constituency distribution (top 10)
        print("\n🗺️ 選挙区別分布（上位10）:")
        sorted_constituencies = sorted(stats['constituency_distribution'].items(),
                                       key=lambda x: x[1], reverse=True)[:10]
        for constituency, count in sorted_constituencies:
            percentage = (count / stats['total_members']) * 100
            print(f"  {constituency}: {count:,}名 ({percentage:.1f}%)")

        # Data completeness
        print("\n📈 データ完全性:")
        required_fields = ['Name', 'House', 'Is_Active']
        optional_fields = [
            'Name_Kana',
            'Constituency',
            'Party',
            'First_Elected',
            'Terms_Served',
            'Birth_Date',
            'Gender',
            'Previous_Occupations',
            'Education',
            'Website_URL',
            'Twitter_Handle']

        print("  必須フィールド:")
        for field in required_fields:
            count = stats['data_completeness'][field]
            percentage = (count / stats['total_members']) * 100
            status = "✅" if percentage >= 95 else "⚠️" if percentage >= 80 else "❌"
            print(
                f"    {status} {field}: {count:,}/{stats['total_members']:,} ({percentage:.1f}%)")

        print("  オプションフィールド:")
        for field in optional_fields:
            count = stats['data_completeness'][field]
            percentage = (count / stats['total_members']) * 100
            status = "✅" if percentage >= 70 else "⚠️" if percentage >= 30 else "❌"
            print(
                f"    {status} {field}: {count:,}/{stats['total_members']:,} ({percentage:.1f}%)")

        # Missing data alerts
        print("\n⚠️ 欠損データアラート:")
        for field, missing_names in stats['missing_data'].items():
            if missing_names:
                print(f"  {field}: {len(missing_names)}名の議員で欠損")
                if len(missing_names) <= 5:
                    print(f"    対象: {', '.join(missing_names)}")
                else:
                    print(
                        f"    対象: {', '.join(missing_names[:5])}...他{len(missing_names)-5}名")

        # Duplicates
        if stats['duplicates']:
            print("\n🔍 重複データ検出:")
            for duplicate in stats['duplicates']:
                print(
                    f"  ⚠️ {duplicate['name']}: {len(duplicate['ids'])}件 (ID: {', '.join(duplicate['ids'])})")
        else:
            print("\n✅ 重複データなし")

        # Overall health score
        total_fields = len(required_fields) + len(optional_fields)
        completeness_score = sum(stats['data_completeness'].values(
        )) / (stats['total_members'] * total_fields) * 100

        print(f"\n🎯 データ品質スコア: {completeness_score:.1f}%")

        if completeness_score >= 80:
            print("✅ 優秀: データ品質は非常に良好です")
        elif completeness_score >= 60:
            print("⚠️ 良好: データ品質は良好ですが、改善の余地があります")
        else:
            print("❌ 要改善: データ品質の向上が必要です")

        print("=" * 60)

    async def run(self):
        """Main execution method"""
        print("🔍 議員データベース検証を開始します...")

        async with aiohttp.ClientSession() as session:
            # Get all members and parties
            members = await self.get_all_members(session)
            parties = await self.get_all_parties(session)

            if not members:
                print("❌ 議員データを取得できませんでした")
                return

            # Analyze data
            stats = self.analyze_member_data(members, parties)

            # Print report
            self.print_verification_report(stats)

            print("\n✅ 検証完了")


async def main():
    """Main entry point"""
    verifier = MemberDataVerifier()
    await verifier.run()

if __name__ == "__main__":
    asyncio.run(main())
