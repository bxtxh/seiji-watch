#!/usr/bin/env python3
"""
Complete Sangiin (House of Councillors) member data collection
参議院議員データ完全収集スクリプト
"""

import asyncio
import aiohttp
import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

load_dotenv('/Users/shogen/seiji-watch/.env.local')

@dataclass
class SanguinMemberData:
    """Sanguin member data structure"""
    name: str
    name_kana: Optional[str] = None
    house: str = "参議院"
    constituency: Optional[str] = None
    party_name: Optional[str] = None
    first_elected: Optional[str] = None
    terms_served: Optional[int] = None
    is_active: bool = True
    member_id: Optional[str] = None
    profile_url: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    previous_occupations: Optional[str] = None
    education: Optional[str] = None
    website_url: Optional[str] = None
    twitter_handle: Optional[str] = None

class CompleteSanguinMemberCollector:
    """Complete Sanguin member data collector"""
    
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
        
        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(3)
        self._last_request_time = 0
        
        # 参議院公式サイトのURL
        self.sangiin_base_url = "https://www.sangiin.go.jp"
        self.member_list_url = f"{self.sangiin_base_url}/japanese/joho1/kousei/giin/current/giin.htm"
        
        # 政党名正規化マッピング
        self.party_mapping = {
            "自由民主党": "自由民主党",
            "自民党": "自由民主党",
            "立憲民主党": "立憲民主党",
            "立憲": "立憲民主党",
            "日本維新の会": "日本維新の会",
            "維新": "日本維新の会",
            "公明党": "公明党",
            "国民民主党": "国民民主党",
            "国民": "国民民主党",
            "日本共産党": "日本共産党",
            "共産党": "日本共産党",
            "共産": "日本共産党",
            "れいわ新選組": "れいわ新選組",
            "れいわ": "れいわ新選組",
            "社会民主党": "社会民主党",
            "社民党": "社会民主党",
            "社民": "社会民主党",
            "NHK党": "NHK党",
            "NHKから国民を守る党": "NHK党",
            "無所属": "無所属"
        }

    async def rate_limit_delay(self):
        """Rate limiting implementation"""
        async with self._request_semaphore:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < 0.5:  # 500ms minimum interval
                await asyncio.sleep(0.5 - time_since_last)
            self._last_request_time = asyncio.get_event_loop().time()

    async def fetch_html(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch HTML content from URL"""
        await self.rate_limit_delay()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                content = await response.text(encoding='utf-8')
                return content
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""

    def normalize_party_name(self, raw_party: str) -> str:
        """Normalize party name"""
        if not raw_party:
            return "無所属"
        
        # 括弧内の情報を除去
        party = re.sub(r'\(.*?\)', '', raw_party).strip()
        party = re.sub(r'（.*?）', '', party).strip()
        
        # マッピングを使用して正規化
        return self.party_mapping.get(party, party)

    def extract_constituency_info(self, constituency_text: str) -> tuple:
        """Extract constituency and election type"""
        if not constituency_text:
            return None, None
        
        # 比例代表の判定
        if "比例" in constituency_text:
            return "比例代表", "比例代表"
        
        # 選挙区の判定
        if "選挙区" in constituency_text:
            # 都道府県名を抽出
            prefecture = re.search(r'([^選挙区]+)選挙区', constituency_text)
            if prefecture:
                return prefecture.group(1), "選挙区"
        
        return constituency_text, "選挙区"

    async def scrape_sangiin_member_list(self, session: aiohttp.ClientSession) -> List[SanguinMemberData]:
        """Scrape member list from Sangiin official site"""
        members = []
        
        try:
            # メイン議員リストページを取得
            html_content = await self.fetch_html(session, self.member_list_url)
            if not html_content:
                print("Failed to fetch member list page")
                return members
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 議員リストテーブルを探す
            member_tables = soup.find_all('table')
            
            for table in member_tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # ヘッダーをスキップ
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        try:
                            # 議員名を取得
                            name_cell = cells[0]
                            name_link = name_cell.find('a')
                            if name_link:
                                name = name_link.get_text(strip=True)
                                profile_url = name_link.get('href')
                                if profile_url and not profile_url.startswith('http'):
                                    profile_url = f"{self.sangiin_base_url}{profile_url}"
                            else:
                                name = name_cell.get_text(strip=True)
                                profile_url = None
                            
                            if not name:
                                continue
                            
                            # 政党情報を取得
                            party_cell = cells[1] if len(cells) > 1 else None
                            party_name = party_cell.get_text(strip=True) if party_cell else None
                            party_name = self.normalize_party_name(party_name)
                            
                            # 選挙区情報を取得
                            constituency_cell = cells[2] if len(cells) > 2 else None
                            constituency_text = constituency_cell.get_text(strip=True) if constituency_cell else None
                            constituency, election_type = self.extract_constituency_info(constituency_text)
                            
                            member_data = SanguinMemberData(
                                name=name,
                                house="参議院",
                                constituency=constituency,
                                party_name=party_name,
                                profile_url=profile_url,
                                is_active=True
                            )
                            
                            members.append(member_data)
                            
                        except Exception as e:
                            print(f"Error parsing member row: {e}")
                            continue
            
            # 追加の議員リストページも確認
            additional_urls = [
                f"{self.sangiin_base_url}/japanese/joho1/kousei/giin/212/giin2.html",
                f"{self.sangiin_base_url}/japanese/joho1/kousei/giin/212/giin3.html"
            ]
            
            for url in additional_urls:
                try:
                    html_content = await self.fetch_html(session, url)
                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        additional_members = await self.parse_additional_member_page(soup)
                        members.extend(additional_members)
                except Exception as e:
                    print(f"Error fetching additional page {url}: {e}")
                    continue
            
            # 重複を除去
            unique_members = []
            seen_names = set()
            for member in members:
                if member.name not in seen_names:
                    unique_members.append(member)
                    seen_names.add(member.name)
            
            print(f"Successfully scraped {len(unique_members)} unique Sangiin members")
            return unique_members
            
        except Exception as e:
            print(f"Error scraping Sangiin member list: {e}")
            return members

    async def parse_additional_member_page(self, soup: BeautifulSoup) -> List[SanguinMemberData]:
        """Parse additional member pages"""
        members = []
        
        # 様々なテーブル構造に対応
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    try:
                        name_cell = cells[0]
                        name_text = name_cell.get_text(strip=True)
                        
                        # 議員名の妥当性チェック
                        if len(name_text) > 1 and not any(word in name_text.lower() for word in ['氏名', '議員名', 'name', '政党']):
                            member_data = SanguinMemberData(
                                name=name_text,
                                house="参議院",
                                is_active=True
                            )
                            members.append(member_data)
                    except Exception as e:
                        continue
        
        return members

    async def get_existing_parties(self, session: aiohttp.ClientSession) -> Dict[str, str]:
        """Get existing parties from Airtable"""
        try:
            await self.rate_limit_delay()
            async with session.get(
                f"{self.base_url}/Parties (政党)",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {record['fields']['Name']: record['id'] for record in data.get('records', [])}
                else:
                    print(f"Failed to fetch parties: {response.status}")
                    return {}
        except Exception as e:
            print(f"Error fetching parties: {e}")
            return {}

    async def create_party_if_not_exists(self, session: aiohttp.ClientSession, party_name: str, existing_parties: Dict[str, str]) -> Optional[str]:
        """Create party if it doesn't exist"""
        if party_name in existing_parties:
            return existing_parties[party_name]
        
        try:
            await self.rate_limit_delay()
            party_data = {
                "records": [{
                    "fields": {
                        "Name": party_name,
                        "Is_Active": True,
                        "Created_At": datetime.now().isoformat()
                    }
                }]
            }
            
            async with session.post(
                f"{self.base_url}/Parties (政党)",
                headers=self.headers,
                json=party_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    party_id = result['records'][0]['id']
                    existing_parties[party_name] = party_id
                    print(f"Created new party: {party_name}")
                    return party_id
                else:
                    print(f"Failed to create party {party_name}: {response.status}")
                    return None
        except Exception as e:
            print(f"Error creating party {party_name}: {e}")
            return None

    async def insert_members_to_airtable(self, session: aiohttp.ClientSession, members: List[SanguinMemberData]) -> bool:
        """Insert members to Airtable"""
        if not members:
            print("No members to insert")
            return False
        
        try:
            # 既存政党を取得
            existing_parties = await self.get_existing_parties(session)
            
            # バッチサイズを設定
            batch_size = 10
            success_count = 0
            
            for i in range(0, len(members), batch_size):
                batch = members[i:i + batch_size]
                records = []
                
                for member in batch:
                    # 政党IDを取得または作成
                    party_id = None
                    if member.party_name and member.party_name != "無所属":
                        party_id = await self.create_party_if_not_exists(session, member.party_name, existing_parties)
                    
                    # レコードを作成
                    record_fields = {
                        "Name": member.name,
                        "House": member.house,
                        "Is_Active": member.is_active,
                        "Created_At": datetime.now().isoformat(),
                        "Updated_At": datetime.now().isoformat()
                    }
                    
                    # オプションフィールドを追加
                    if member.name_kana:
                        record_fields["Name_Kana"] = member.name_kana
                    if member.constituency:
                        record_fields["Constituency"] = member.constituency
                    if party_id:
                        record_fields["Party"] = [party_id]
                    if member.first_elected:
                        record_fields["First_Elected"] = member.first_elected
                    if member.terms_served:
                        record_fields["Terms_Served"] = member.terms_served
                    if member.profile_url:
                        record_fields["Website_URL"] = member.profile_url
                    if member.birth_date:
                        record_fields["Birth_Date"] = member.birth_date
                    if member.gender:
                        record_fields["Gender"] = member.gender
                    if member.previous_occupations:
                        record_fields["Previous_Occupations"] = member.previous_occupations
                    if member.education:
                        record_fields["Education"] = member.education
                    if member.twitter_handle:
                        record_fields["Twitter_Handle"] = member.twitter_handle
                    
                    records.append({"fields": record_fields})
                
                # バッチ挿入
                await self.rate_limit_delay()
                async with session.post(
                    f"{self.base_url}/Members (議員)",
                    headers=self.headers,
                    json={"records": records}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        success_count += len(result.get('records', []))
                        print(f"Successfully inserted batch {i//batch_size + 1}: {len(result.get('records', []))} members")
                    else:
                        error_text = await response.text()
                        print(f"Failed to insert batch {i//batch_size + 1}: {response.status} - {error_text}")
                
                # バッチ間の待機
                await asyncio.sleep(1)
            
            print(f"Total members inserted: {success_count}")
            return success_count > 0
            
        except Exception as e:
            print(f"Error inserting members: {e}")
            return False

    async def save_results_to_file(self, members: List[SanguinMemberData], filename: str = None):
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sanguin_members_collection_result_{timestamp}.json"
        
        try:
            # Convert to serializable format
            serializable_data = {
                "collection_date": datetime.now().isoformat(),
                "total_members": len(members),
                "members": [asdict(member) for member in members]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
            print(f"Results saved to {filename}")
            return filename
            
        except Exception as e:
            print(f"Error saving results: {e}")
            return None

    async def run(self):
        """Main execution method"""
        print("Starting complete Sanguin member data collection...")
        
        async with aiohttp.ClientSession() as session:
            # 参議院議員データを収集
            members = await self.scrape_sangiin_member_list(session)
            
            if not members:
                print("No members found. Exiting.")
                return
            
            print(f"Found {len(members)} Sanguin members")
            
            # 結果をファイルに保存
            await self.save_results_to_file(members)
            
            # Airtableに挿入
            success = await self.insert_members_to_airtable(session, members)
            
            if success:
                print("✅ Successfully completed Sanguin member data collection")
            else:
                print("❌ Failed to complete Sanguin member data collection")

async def main():
    """Main entry point"""
    collector = CompleteSanguinMemberCollector()
    await collector.run()

if __name__ == "__main__":
    asyncio.run(main())