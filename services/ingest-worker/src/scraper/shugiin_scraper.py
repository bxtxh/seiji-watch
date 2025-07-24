"""
House of Representatives (衆議院) bill scraper.
Specialized scraper for Shugiin website with unique format handling.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .enhanced_diet_scraper import EnhancedBillData


@dataclass
class ShugiinBillData(EnhancedBillData):
    """Shugiin-specific bill data structure"""

    # Shugiin-specific fields
    supporting_members: list[str] | None = field(default_factory=list)  # 賛成議員一覧（衆議院のみ）
    diet_session_type: str | None = None      # 国会種別（通常/臨時/特別）
    bill_subcategory: str | None = None       # 法案小分類

    def __post_init__(self):
        """Post-initialization setup"""
        self.source_house = "衆議院"


class ShugiinScraper:
    """House of Representatives bill scraper"""

    BASE_URL = "https://www.shugiin.go.jp"

    # Shugiin bill listing URLs for different sessions
    BILL_URLS = {
        "current": "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/keika.htm",
        "217": "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/217keika.htm",
        "216": "https://www.shugiin.go.jp/internet/itdb_gian.nsf/html/gian/216keika.htm",
    }

    def __init__(self, delay_seconds: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.delay_seconds = delay_seconds
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0

        # Shugiin-specific parsing patterns
        self.date_patterns = [
            r'令和(\d+)年(\d{1,2})月(\d{1,2})日',     # 令和年号
            r'平成(\d+)年(\d{1,2})月(\d{1,2})日',     # 平成年号
            r'(\d{4})/(\d{1,2})/(\d{1,2})',         # 西暦スラッシュ形式
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',       # 西暦ドット形式
            r'(\d{4})-(\d{1,2})-(\d{1,2})',         # 西暦ハイフン形式
        ]

        # Bill type mappings
        self.bill_type_mappings = {
            "政府提出": "政府",
            "議員提出": "議員",
            "内閣提出": "政府",
            "議員発議": "議員",
            "政府": "政府",
            "議員": "議員",
        }

        # Status mappings
        self.status_mappings = {
            "成立": "成立",
            "可決": "可決",
            "否決": "否決",
            "審議中": "審議中",
            "委員会審議": "委員会審議",
            "継続審議": "継続審議",
            "撤回": "撤回",
            "廃案": "廃案",
        }

    def _make_request(self, url: str, timeout: int = 30) -> requests.Response:
        """Make HTTP request with rate limiting"""
        # Rate limiting
        current_time = time.time()
        if current_time - self._last_request_time < self.delay_seconds:
            sleep_time = self.delay_seconds - (current_time - self._last_request_time)
            time.sleep(sleep_time)

        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            self._last_request_time = time.time()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            raise

    def fetch_bill_list(self, session_number: str = "current") -> list[ShugiinBillData]:
        """Fetch bill list from Shugiin website"""
        try:
            url = self.BILL_URLS.get(session_number, self.BILL_URLS["current"])
            response = self._make_request(url)

            soup = BeautifulSoup(response.content, 'html.parser')
            bills = self._parse_bill_list(soup, session_number)

            self.logger.info(f"Fetched {len(bills)} bills from Shugiin session {session_number}")
            return bills

        except Exception as e:
            self.logger.error(f"Error fetching Shugiin bill list: {e}")
            return []

    def _parse_bill_list(self, soup: BeautifulSoup, session_number: str) -> list[ShugiinBillData]:
        """Parse bill list from HTML"""
        bills = []

        # Find bill tables - Shugiin uses multiple table formats
        tables = soup.find_all('table')

        for table in tables:
            # Check if this is a bills table
            if self._is_bills_table(table):
                rows = table.find_all('tr')

                for row in rows[1:]:  # Skip header row
                    bill_data = self._parse_bill_row(row, session_number)
                    if bill_data:
                        bills.append(bill_data)

        return bills

    def _is_bills_table(self, table) -> bool:
        """Check if table contains bill information"""
        # Look for table headers that indicate bill information
        headers = table.find_all(['th', 'td'])
        header_text = ' '.join([h.get_text(strip=True) for h in headers[:5]])

        # Check for characteristic Shugiin bill table patterns
        bill_indicators = [
            '議案番号', '議案件名', '議案種類', '議案提出者', '議案提出年月日',
            '提出番号', '件名', '種類', '提出者', '提出年月日',
            '番号', '件名', '提出者', '状況', '結果'
        ]

        return any(indicator in header_text for indicator in bill_indicators)

    def _parse_bill_row(self, row, session_number: str) -> ShugiinBillData | None:
        """Parse individual bill row"""
        try:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                return None

            # Extract bill information based on Shugiin format
            # Common format: [番号] [件名] [提出者] [状況] [その他]

            # Bill number (first column)
            bill_number = cells[0].get_text(strip=True)
            if not bill_number or bill_number in ['番号', '提出番号']:
                return None

            # Bill title (second column)
            title_cell = cells[1]
            title_link = title_cell.find('a')
            if title_link:
                title = title_link.get_text(strip=True)
                detail_url = urljoin(self.BASE_URL, title_link.get('href'))
            else:
                title = title_cell.get_text(strip=True)
                detail_url = ""

            if not title or title in ['件名', '議案件名']:
                return None

            # Bill type/submitter (third column)
            submitter_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            submitter_type = self._map_submitter_type(submitter_text)

            # Status (fourth column)
            status_text = cells[3].get_text(strip=True) if len(cells) > 3 else "審議中"
            status = self._map_status(status_text)

            # Additional information (fifth column and beyond)
            additional_info = []
            for i in range(4, len(cells)):
                additional_info.append(cells[i].get_text(strip=True))

            # Create bill data
            bill_data = ShugiinBillData(
                bill_id=f"{session_number}-{bill_number}",
                title=title,
                submission_date=None,  # Will be extracted from detail page
                status=status,
                stage=self._determine_stage(status),
                submitter=submitter_type,
                category=self._determine_category(title),
                url=detail_url,
                source_url=detail_url,
                diet_session=session_number,
                house_of_origin="衆議院",
                submitter_type=submitter_type,
            )

            # Extract additional information
            if additional_info:
                bill_data.notes = ' | '.join(additional_info)

            return bill_data

        except Exception as e:
            self.logger.error(f"Error parsing Shugiin bill row: {e}")
            return None

    def _map_submitter_type(self, submitter_text: str) -> str:
        """Map submitter text to standardized type"""
        for key, value in self.bill_type_mappings.items():
            if key in submitter_text:
                return value

        # Default classification
        if "政府" in submitter_text or "内閣" in submitter_text:
            return "政府"
        elif "議員" in submitter_text:
            return "議員"
        else:
            return "議員"  # Default to member-sponsored

    def _map_status(self, status_text: str) -> str:
        """Map status text to standardized status"""
        for key, value in self.status_mappings.items():
            if key in status_text:
                return value
        return status_text  # Return original if no mapping found

    def _determine_stage(self, status: str) -> str:
        """Determine bill stage from status"""
        if "成立" in status:
            return "成立"
        elif "可決" in status:
            return "採決待ち"
        elif "審議" in status:
            return "審議中"
        elif "委員会" in status:
            return "委員会審議"
        elif "継続" in status:
            return "継続審議"
        elif "否決" in status:
            return "否決"
        elif "撤回" in status:
            return "撤回"
        elif "廃案" in status:
            return "廃案"
        else:
            return "審議中"

    def _determine_category(self, title: str) -> str:
        """Categorize bill based on title"""
        # Category classification based on title keywords
        categories = {
            "予算・決算": ["予算", "補正", "決算", "財政"],
            "税制": ["税", "課税", "控除", "租税"],
            "社会保障": ["社会保障", "年金", "保険", "福祉", "医療"],
            "外交・国際": ["外交", "条約", "協定", "通商"],
            "経済・産業": ["経済", "産業", "商工", "貿易", "金融"],
            "教育・文化": ["教育", "文化", "学校", "大学", "研究"],
            "環境・エネルギー": ["環境", "エネルギー", "原子力", "温暖化"],
            "インフラ・交通": ["道路", "交通", "鉄道", "航空", "港湾"],
            "防衛・安全保障": ["防衛", "安全保障", "自衛隊", "軍事"],
            "司法・法務": ["司法", "法務", "刑法", "民法", "裁判"],
            "行政・公務員": ["行政", "公務員", "国家公務員", "地方公務員"],
        }

        for category, keywords in categories.items():
            if any(keyword in title for keyword in keywords):
                return category

        return "その他"

    def fetch_bill_details(self, bill_url: str) -> dict[str, Any]:
        """Fetch detailed bill information from Shugiin detail page"""
        try:
            response = self._make_request(bill_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            details = {
                'submission_date': self._extract_submission_date(soup),
                'submitting_members': self._extract_submitting_members(soup),
                'supporting_members': self._extract_supporting_members(soup),
                'committee_info': self._extract_committee_info(soup),
                'bill_outline': self._extract_bill_outline(soup),
                'background_context': self._extract_background_context(soup),
                'expected_effects': self._extract_expected_effects(soup),
                'key_provisions': self._extract_key_provisions(soup),
                'related_documents': self._extract_related_documents(soup),
                'voting_history': self._extract_voting_history(soup),
                'amendments': self._extract_amendments(soup),
                'implementation_schedule': self._extract_implementation_schedule(soup),
                'sponsoring_ministry': self._extract_sponsoring_ministry(soup),
                'related_laws': self._extract_related_laws(soup),
            }

            return details

        except Exception as e:
            self.logger.error(f"Error fetching Shugiin bill details: {e}")
            return {}

    def _extract_submission_date(self, soup: BeautifulSoup) -> datetime | None:
        """Extract submission date from detail page"""
        text = soup.get_text()

        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if '令和' in pattern:
                        # Convert Reiwa year to Western year
                        reiwa_year = int(match.group(1))
                        year = 2018 + reiwa_year  # Reiwa started in 2019
                        month = int(match.group(2))
                        day = int(match.group(3))
                    elif '平成' in pattern:
                        # Convert Heisei year to Western year
                        heisei_year = int(match.group(1))
                        year = 1988 + heisei_year  # Heisei started in 1989
                        month = int(match.group(2))
                        day = int(match.group(3))
                    else:
                        # Western year
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))

                    return datetime(year, month, day)
                except ValueError:
                    continue

        return None

    def _extract_submitting_members(self, soup: BeautifulSoup) -> list[str]:
        """Extract submitting members list"""
        members = []

        # Look for member sections
        member_sections = soup.find_all(text=re.compile(r'提出者|発議者'))

        for section in member_sections:
            parent = section.parent
            if parent:
                # Extract member names
                member_text = parent.get_text(strip=True)
                # Japanese name pattern
                names = re.findall(r'([一-龯]{2,4}\s*[一-龯]{2,4})', member_text)
                members.extend(names)

        return list(set(members))  # Remove duplicates

    def _extract_supporting_members(self, soup: BeautifulSoup) -> list[str]:
        """Extract supporting members list (Shugiin-specific)"""
        members = []

        # Look for supporting member sections
        support_sections = soup.find_all(text=re.compile(r'賛成者|賛成議員'))

        for section in support_sections:
            parent = section.parent
            if parent:
                # Extract member names
                member_text = parent.get_text(strip=True)
                names = re.findall(r'([一-龯]{2,4}\s*[一-龯]{2,4})', member_text)
                members.extend(names)

        return list(set(members))  # Remove duplicates

    def _extract_committee_info(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract committee information"""
        committee_info = {}

        # Look for committee references
        committee_patterns = [
            r'(\w+)委員会',
            r'(\w+)特別委員会',
            r'(\w+)調査会',
        ]

        text = soup.get_text()
        for pattern in committee_patterns:
            matches = re.findall(pattern, text)
            if matches:
                committee_info['committees'] = matches
                break

        return committee_info

    def _extract_bill_outline(self, soup: BeautifulSoup) -> str:
        """Extract bill outline/summary"""
        # Look for outline sections
        outline_sections = soup.find_all(text=re.compile(r'要旨|概要|目的|趣旨'))

        for section in outline_sections:
            parent = section.parent
            if parent:
                # Get surrounding content
                outline_text = parent.get_text(strip=True)
                if len(outline_text) > 50:  # Minimum length for meaningful content
                    return outline_text

        return ""

    def _extract_related_documents(self, soup: BeautifulSoup) -> list[str]:
        """Extract related document URLs"""
        documents = []

        # Find PDF and document links
        doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx|xls|xlsx)$', re.I))

        for link in doc_links:
            doc_url = urljoin(self.BASE_URL, link.get('href'))
            documents.append(doc_url)

        return documents

    def _extract_voting_history(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract voting history"""
        voting_history = []

        # Look for voting information
        voting_sections = soup.find_all(text=re.compile(r'採決|議決|可決|否決'))

        for section in voting_sections:
            parent = section.parent
            if parent:
                voting_text = parent.get_text(strip=True)
                if voting_text:
                    voting_history.append({
                        'type': 'voting',
                        'description': voting_text,
                        'date': None  # Could be extracted if date patterns are found
                    })

        return voting_history

    def _extract_background_context(self, soup: BeautifulSoup) -> str:
        """Extract background context from detail page"""
        # Look for background/rationale sections
        background_patterns = [
            r'提案理由',
            r'提出の背景',
            r'制定の背景',
            r'改正の背景',
            r'経緯',
            r'背景',
            r'理由',
            r'趣旨',
        ]

        for pattern in background_patterns:
            # Find section headers
            background_header = soup.find(text=re.compile(pattern))
            if background_header:
                parent = background_header.parent
                if parent:
                    # Look for content in the same section
                    content_text = parent.get_text(strip=True)
                    if len(content_text) > len(pattern) + 20:  # Has substantial content
                        return content_text.replace(pattern, '').strip()

                    # Look for next sibling content
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        content_text = next_sibling.get_text(strip=True)
                        if len(content_text) > 20:
                            return content_text

        return ""

    def _extract_expected_effects(self, soup: BeautifulSoup) -> str:
        """Extract expected effects from detail page"""
        effects_patterns = [
            r'期待される効果',
            r'効果',
            r'影響',
            r'期待される結果',
            r'改善効果',
            r'予想される効果',
        ]

        for pattern in effects_patterns:
            effects_header = soup.find(text=re.compile(pattern))
            if effects_header:
                parent = effects_header.parent
                if parent:
                    # Look for content in the same section
                    content_text = parent.get_text(strip=True)
                    if len(content_text) > len(pattern) + 20:
                        return content_text.replace(pattern, '').strip()

                    # Look for next sibling content
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        content_text = next_sibling.get_text(strip=True)
                        if len(content_text) > 20:
                            return content_text

        return ""

    def _extract_key_provisions(self, soup: BeautifulSoup) -> list[str]:
        """Extract key provisions from detail page"""
        provisions = []

        # Look for structured content with numbers or bullets
        list_items = soup.find_all(['li', 'ol', 'ul'])
        for item in list_items:
            text = item.get_text(strip=True)
            if len(text) > 20:  # Substantial content
                provisions.append(text)

        # Look for numbered sections
        numbered_sections = soup.find_all(text=re.compile(r'^[0-9一二三四五六七八九十]+[．．）\)]'))
        for section in numbered_sections:
            parent = section.parent
            if parent:
                text = parent.get_text(strip=True)
                if len(text) > 20:
                    provisions.append(text)

        # Look for article sections (第○条)
        article_sections = soup.find_all(text=re.compile(r'第[0-9一二三四五六七八九十]+条'))
        for section in article_sections:
            parent = section.parent
            if parent:
                text = parent.get_text(strip=True)
                if len(text) > 20:
                    provisions.append(text)

        return provisions[:15]  # Limit to first 15 provisions

    def _extract_amendments(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract amendment information"""
        amendments = []

        # Look for amendment sections
        amendment_patterns = [
            r'修正',
            r'改正',
            r'変更',
            r'附則',
            r'追加',
        ]

        for pattern in amendment_patterns:
            amendment_sections = soup.find_all(text=re.compile(pattern))
            for section in amendment_sections:
                parent = section.parent
                if parent:
                    amendment_text = parent.get_text(strip=True)
                    if amendment_text and len(amendment_text) > 10:
                        amendments.append({
                            'type': 'amendment',
                            'description': amendment_text,
                            'date': None,  # Could be extracted if date patterns are found
                            'status': 'proposed'
                        })

        return amendments[:10]  # Limit to first 10 amendments

    def _extract_implementation_schedule(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract implementation schedule"""
        schedule = {}

        # Look for implementation date patterns
        impl_patterns = [
            r'施行日',
            r'施行期日',
            r'効力発生日',
            r'適用開始日',
            r'施行',
        ]

        for pattern in impl_patterns:
            impl_section = soup.find(text=re.compile(pattern))
            if impl_section:
                parent = impl_section.parent
                if parent:
                    impl_text = parent.get_text(strip=True)
                    # Extract date from the text
                    for date_pattern in self.date_patterns:
                        match = re.search(date_pattern, impl_text)
                        if match:
                            schedule['implementation_date'] = match.group(0)
                            break

                    schedule['implementation_info'] = impl_text
                    break

        return schedule

    def _extract_sponsoring_ministry(self, soup: BeautifulSoup) -> str:
        """Extract sponsoring ministry"""
        # Look for ministry patterns
        ministry_patterns = [
            r'(\w+省)',
            r'(\w+庁)',
            r'(\w+府)',
            r'内閣官房',
            r'内閣府',
            r'総務省',
            r'法務省',
            r'外務省',
            r'財務省',
            r'文部科学省',
            r'厚生労働省',
            r'農林水産省',
            r'経済産業省',
            r'国土交通省',
            r'環境省',
            r'防衛省',
        ]

        text = soup.get_text()
        for pattern in ministry_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return ""

    def _extract_related_laws(self, soup: BeautifulSoup) -> list[str]:
        """Extract related laws"""
        laws = []

        # Look for law references
        law_patterns = [
            r'([^\s]+法)',
            r'([^\s]+令)',
            r'([^\s]+規則)',
            r'([^\s]+条例)',
            r'([^\s]+規程)',
        ]

        text = soup.get_text()
        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Filter out common false positives
                if len(match) > 2 and match not in ['方法', '手法', '処理法', '調査法']:
                    laws.append(match)

        # Remove duplicates and filter
        unique_laws = list(set(laws))
        return unique_laws[:20]  # Limit to first 20

    def fetch_enhanced_bill_data(self, bill_url: str) -> ShugiinBillData:
        """Fetch enhanced bill data by combining list and detail information"""
        try:
            # First, determine bill info from URL or make a basic request
            response = self._make_request(bill_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract basic information
            title = self._extract_title_from_detail_page(soup)
            bill_id = self._extract_bill_id_from_url(bill_url)

            # Create base bill data
            bill_data = ShugiinBillData(
                bill_id=bill_id,
                title=title,
                submission_date=None,
                status="取得中",
                stage="取得中",
                submitter="取得中",
                category="その他",
                url=bill_url,
                source_url=bill_url,
            )

            # Fetch detailed information
            details = self.fetch_bill_details(bill_url)

            # Populate enhanced fields
            if details:
                bill_data.submission_date = details.get('submission_date')
                bill_data.bill_outline = details.get('bill_outline', '')
                bill_data.background_context = details.get('background_context', '')
                bill_data.expected_effects = details.get('expected_effects', '')
                bill_data.key_provisions = details.get('key_provisions', [])
                bill_data.related_laws = details.get('related_laws', [])
                bill_data.submitting_members = details.get('submitting_members', [])
                bill_data.supporting_members = details.get('supporting_members', [])
                bill_data.sponsoring_ministry = details.get('sponsoring_ministry', '')
                bill_data.committee_assignments = details.get('committee_info', {})
                bill_data.voting_results = self._convert_voting_history_to_results(details.get('voting_history', []))
                bill_data.amendments = details.get('amendments', [])

                # Extract implementation date from schedule
                impl_schedule = details.get('implementation_schedule', {})
                if impl_schedule and 'implementation_date' in impl_schedule:
                    bill_data.implementation_date = impl_schedule['implementation_date']

                # Set submitter based on sponsoring ministry
                if bill_data.sponsoring_ministry:
                    bill_data.submitter = "政府"
                    bill_data.submitter_type = "政府"
                elif bill_data.submitting_members:
                    bill_data.submitter = "議員"
                    bill_data.submitter_type = "議員"

                # Determine category based on title and ministry
                bill_data.category = self._determine_category(bill_data.title)

                # Set status based on voting results
                if bill_data.voting_results:
                    if any('可決' in str(v) for v in bill_data.voting_results.values()):
                        bill_data.status = "可決"
                        bill_data.stage = "可決"
                    elif any('否決' in str(v) for v in bill_data.voting_results.values()):
                        bill_data.status = "否決"
                        bill_data.stage = "否決"
                    else:
                        bill_data.status = "審議中"
                        bill_data.stage = "審議中"
                else:
                    bill_data.status = "審議中"
                    bill_data.stage = "審議中"

            # Calculate data quality score
            bill_data.data_quality_score = self._calculate_data_quality_score(bill_data)

            return bill_data

        except Exception as e:
            self.logger.error(f"Error fetching enhanced bill data from {bill_url}: {e}")
            # Return minimal bill data on error
            return ShugiinBillData(
                bill_id=self._extract_bill_id_from_url(bill_url),
                title="取得エラー",
                submission_date=None,
                status="エラー",
                stage="エラー",
                submitter="不明",
                category="その他",
                url=bill_url,
                source_url=bill_url,
            )

    def _extract_title_from_detail_page(self, soup: BeautifulSoup) -> str:
        """Extract title from detail page"""
        # Look for title in various locations
        title_candidates = [
            soup.find('h1'),
            soup.find('h2'),
            soup.find('title'),
            soup.find('div', class_='title'),
            soup.find('div', class_='bill-title'),
        ]

        for candidate in title_candidates:
            if candidate:
                title = candidate.get_text(strip=True)
                if title and len(title) > 5:
                    return title

        return "不明な法案"

    def _extract_bill_id_from_url(self, url: str) -> str:
        """Extract bill ID from URL"""
        # Try to extract ID from URL patterns
        patterns = [
            r'/([A-Z]?\d+)',
            r'id=([A-Z]?\d+)',
            r'bill[_-]?(\d+)',
            r'gian[_-]?(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Fallback to hash of URL
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:8]

    def _convert_voting_history_to_results(self, voting_history: list[dict[str, Any]]) -> dict[str, Any]:
        """Convert voting history to results format"""
        results = {}

        for vote in voting_history:
            if vote.get('type') == 'voting':
                description = vote.get('description', '')
                if '可決' in description:
                    results['latest_result'] = '可決'
                elif '否決' in description:
                    results['latest_result'] = '否決'
                elif '採決' in description:
                    results['latest_action'] = '採決'

        return results

    def _calculate_data_quality_score(self, bill_data: ShugiinBillData) -> float:
        """Calculate data quality score for Shugiin bill"""
        score = 0.0
        total_fields = 0

        # Core fields (weight: 2)
        core_fields = [
            'bill_id', 'title', 'status', 'stage', 'submitter'
        ]
        for field in core_fields:
            total_fields += 2
            value = getattr(bill_data, field, None)
            if value and value not in ['取得中', 'エラー', '不明']:
                score += 2

        # Enhanced fields (weight: 1)
        enhanced_fields = [
            'bill_outline', 'background_context', 'expected_effects',
            'key_provisions', 'related_laws', 'implementation_date',
            'submitting_members', 'supporting_members', 'sponsoring_ministry',
            'committee_assignments', 'voting_results', 'amendments'
        ]
        for field in enhanced_fields:
            total_fields += 1
            value = getattr(bill_data, field, None)
            if value:
                if isinstance(value, list | dict):
                    if len(value) > 0:
                        score += 1
                elif isinstance(value, str):
                    if value.strip() and value not in ['取得中', 'エラー', '不明']:
                        score += 1
                else:
                    score += 1

        # Calculate percentage
        if total_fields > 0:
            return round(score / total_fields, 2)
        return 0.0

    async def fetch_bills_async(self, session_numbers: list[str]) -> list[ShugiinBillData]:
        """Fetch bills from multiple sessions asynchronously"""
        all_bills = []

        for session in session_numbers:
            try:
                bills = self.fetch_bill_list(session)
                all_bills.extend(bills)

                # Respect rate limiting
                await asyncio.sleep(self.delay_seconds)

            except Exception as e:
                self.logger.error(f"Error fetching bills for session {session}: {e}")
                continue

        return all_bills

    async def fetch_enhanced_bills_async(self, bill_urls: list[str]) -> list[ShugiinBillData]:
        """Fetch enhanced bill data for multiple URLs asynchronously"""
        enhanced_bills = []

        for url in bill_urls:
            try:
                enhanced_bill = self.fetch_enhanced_bill_data(url)
                enhanced_bills.append(enhanced_bill)

                # Respect rate limiting
                await asyncio.sleep(self.delay_seconds)

            except Exception as e:
                self.logger.error(f"Error fetching enhanced data for {url}: {e}")
                continue

        return enhanced_bills
