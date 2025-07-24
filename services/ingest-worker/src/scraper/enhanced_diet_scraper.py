"""
Enhanced Diet website scraper with detailed bill information extraction.
Extends the base diet_scraper.py with comprehensive bill outline and background parsing.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from .diet_scraper import BillData, DietScraper


@dataclass
class EnhancedBillData(BillData):
    """Enhanced bill data structure with detailed information"""

    # Enhanced detailed content
    bill_outline: str | None = None           # 議案要旨相当の長文情報
    background_context: str | None = None     # 提出背景・経緯
    expected_effects: str | None = None       # 期待される効果
    key_provisions: list[str] | None = field(default_factory=list)  # 主要条項リスト
    related_laws: list[str] | None = field(default_factory=list)    # 関連法律リスト
    implementation_date: str | None = None    # 施行予定日

    # Enhanced submission information
    submitting_members: list[str] | None = field(default_factory=list)  # 提出議員一覧
    submitting_party: str | None = None       # 提出会派
    sponsoring_ministry: str | None = None    # 主管省庁

    # Process tracking
    committee_assignments: dict[str, Any] | None = field(
        default_factory=dict)  # 委員会付託情報
    voting_results: dict[str, Any] | None = field(default_factory=dict)         # 採決結果
    amendments: list[dict[str, Any]] | None = field(default_factory=list)       # 修正内容
    inter_house_status: str | None = None     # 両院間の状況

    # Source metadata
    source_house: str = "参議院"                 # データ取得元議院
    source_url: str | None = None             # 元データURL
    data_quality_score: float | None = None   # データ品質スコア


class EnhancedDietScraper(DietScraper):
    """Enhanced Diet scraper with comprehensive bill detail extraction"""

    def __init__(self, delay_seconds: float = 1.5, enable_resilience: bool = True):
        super().__init__(delay_seconds, enable_resilience)
        self.logger = logging.getLogger(__name__)

        # Enhanced parsing patterns
        self.date_patterns = [
            r'令和(\d+)年(\d{1,2})月(\d{1,2})日',     # 令和年号
            r'平成(\d+)年(\d{1,2})月(\d{1,2})日',     # 平成年号
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',       # 西暦
        ]

        # Committee name patterns
        self.committee_patterns = [
            r'(\w+)委員会',
            r'(\w+)特別委員会',
            r'(\w+)調査会',
        ]

        # Bill outline section patterns
        self.outline_patterns = [
            r'議案要旨',
            r'提案理由',
            r'制定の理由',
            r'改正の理由',
            r'目的',
            r'趣旨',
        ]

    def fetch_enhanced_bill_details(self, bill_url: str) -> EnhancedBillData:
        """Fetch comprehensive bill details with enhanced parsing"""
        try:
            response = self._make_request(bill_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Create enhanced bill data
            enhanced_data = EnhancedBillData(
                bill_id="",  # Will be set from URL or content
                title="",
                submission_date=None,
                status="",
                stage="",
                submitter="",
                category="",
                url=bill_url,
                source_url=bill_url
            )

            # Extract basic information
            self._extract_basic_info(soup, enhanced_data)

            # Extract detailed content
            self._extract_bill_outline(soup, enhanced_data)
            self._extract_background_context(soup, enhanced_data)
            self._extract_expected_effects(soup, enhanced_data)
            self._extract_key_provisions(soup, enhanced_data)
            self._extract_related_laws(soup, enhanced_data)
            self._extract_implementation_date(soup, enhanced_data)

            # Extract submission information
            self._extract_submitting_members(soup, enhanced_data)
            self._extract_submitting_party(soup, enhanced_data)
            self._extract_sponsoring_ministry(soup, enhanced_data)

            # Extract process tracking
            self._extract_committee_assignments(soup, enhanced_data)
            self._extract_voting_results(soup, enhanced_data)
            self._extract_amendments(soup, enhanced_data)
            self._extract_inter_house_status(soup, enhanced_data)

            # Calculate data quality score
            enhanced_data.data_quality_score = self._calculate_data_quality_score(
                enhanced_data)

            return enhanced_data

        except Exception as e:
            self.logger.error(
                f"Error fetching enhanced bill details from {bill_url}: {e}")
            return EnhancedBillData(
                bill_id="", title="", submission_date=None, status="", stage="",
                submitter="", category="", url=bill_url, source_url=bill_url
            )

    def _extract_basic_info(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract basic bill information"""
        # Extract title
        title_elem = soup.find('h1') or soup.find('h2') or soup.find('title')
        if title_elem:
            bill_data.title = title_elem.get_text(strip=True)

        # Extract bill ID from URL or content
        bill_id_match = re.search(r'([A-Z]?\d+)', bill_data.url)
        if bill_id_match:
            bill_data.bill_id = bill_id_match.group(1)

        # Extract submission date
        bill_data.submission_date = self._extract_submission_date(soup)

        # Extract status and stage
        status_text = self._find_text_by_patterns(soup, ['状況', '現在の状況', 'ステータス'])
        if status_text:
            bill_data.status = status_text
            bill_data.stage = self._determine_stage(status_text)

    def _extract_bill_outline(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract 議案要旨 (bill outline) from detail page"""
        # Look for various outline section patterns
        outline_text = ""

        for pattern in self.outline_patterns:
            # Find section headers
            outline_header = soup.find(text=re.compile(pattern))
            if outline_header:
                # Get the parent element and extract following content
                parent = outline_header.parent
                if parent:
                    # Look for the next content block
                    next_content = parent.find_next_sibling()
                    if next_content:
                        outline_text = next_content.get_text(strip=True)
                        break

                    # Alternative: look for content within the same parent
                    parent_text = parent.get_text(strip=True)
                    if len(parent_text) > len(pattern) + 10:  # Has substantial content
                        outline_text = parent_text.replace(pattern, '').strip()
                        break

        # If no structured outline found, look for general descriptive content
        if not outline_text:
            # Look for paragraphs with substantial content
            content_paragraphs = soup.find_all('p')
            for p in content_paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 100:  # Substantial content
                    outline_text = text
                    break

        # Clean and validate the outline text
        if outline_text:
            outline_text = self._clean_text(outline_text)
            if len(outline_text) > 50:  # Minimum length for quality
                bill_data.bill_outline = outline_text

    def _extract_background_context(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract background context and reasoning"""
        background_patterns = [
            r'提出の背景',
            r'制定の背景',
            r'改正の背景',
            r'経緯',
            r'背景',
            r'理由',
        ]

        background_text = self._find_text_by_patterns(soup, background_patterns)
        if background_text:
            bill_data.background_context = self._clean_text(background_text)

    def _extract_expected_effects(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract expected effects and impact"""
        effects_patterns = [
            r'期待される効果',
            r'効果',
            r'影響',
            r'期待される結果',
            r'効果的な',
        ]

        effects_text = self._find_text_by_patterns(soup, effects_patterns)
        if effects_text:
            bill_data.expected_effects = self._clean_text(effects_text)

    def _extract_key_provisions(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract key provisions and main points"""
        provisions = []

        # Look for numbered lists or bullet points
        list_items = soup.find_all(['li', 'ol', 'ul'])
        for item in list_items:
            text = item.get_text(strip=True)
            if len(text) > 20:  # Substantial content
                provisions.append(text)

        # Look for structured sections with numbers
        numbered_sections = soup.find_all(text=re.compile(r'^[0-9一二三四五六七八九十]+[．．）\)]'))
        for section in numbered_sections:
            parent = section.parent
            if parent:
                text = parent.get_text(strip=True)
                if len(text) > 20:
                    provisions.append(text)

        if provisions:
            bill_data.key_provisions = provisions[:10]  # Limit to first 10

    def _extract_related_laws(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract related laws and regulations"""
        laws = []

        # Look for law references
        law_patterns = [
            r'(\w+法)',
            r'(\w+令)',
            r'(\w+規則)',
            r'(\w+条例)',
        ]

        text = soup.get_text()
        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            laws.extend(matches)

        # Remove duplicates and filter
        unique_laws = list(set(laws))
        bill_data.related_laws = unique_laws[:20]  # Limit to first 20

    def _extract_implementation_date(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract implementation/effective date"""
        impl_patterns = [
            r'施行日',
            r'施行期日',
            r'効力発生日',
            r'適用開始日',
        ]

        impl_text = self._find_text_by_patterns(soup, impl_patterns)
        if impl_text:
            # Extract date from the text
            for pattern in self.date_patterns:
                match = re.search(pattern, impl_text)
                if match:
                    bill_data.implementation_date = match.group(0)
                    break

    def _extract_submitting_members(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract submitting members list"""
        members = []

        # Look for member lists
        member_patterns = [
            r'提出者',
            r'提出議員',
            r'発議者',
        ]

        member_text = self._find_text_by_patterns(soup, member_patterns)
        if member_text:
            # Extract names (assuming Japanese names)
            name_pattern = r'([一-龯]+\s*[一-龯]+)'
            names = re.findall(name_pattern, member_text)
            members.extend(names)

        if members:
            bill_data.submitting_members = members[:50]  # Limit to first 50

    def _extract_submitting_party(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract submitting party information"""
        party_patterns = [
            r'自由民主党',
            r'立憲民主党',
            r'公明党',
            r'日本維新の会',
            r'国民民主党',
            r'共産党',
            r'れいわ新選組',
            r'社会民主党',
        ]

        text = soup.get_text()
        for pattern in party_patterns:
            if re.search(pattern, text):
                bill_data.submitting_party = pattern
                break

    def _extract_sponsoring_ministry(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract sponsoring ministry"""
        ministry_patterns = [
            r'(\w+省)',
            r'(\w+庁)',
            r'(\w+府)',
            r'内閣官房',
            r'内閣府',
        ]

        text = soup.get_text()
        for pattern in ministry_patterns:
            match = re.search(pattern, text)
            if match:
                bill_data.sponsoring_ministry = match.group(1)
                break

    def _extract_committee_assignments(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract committee assignment information"""
        assignments = {}

        # Look for committee information
        for pattern in self.committee_patterns:
            matches = re.findall(pattern, soup.get_text())
            if matches:
                assignments['committees'] = matches
                break

        # Look for assignment dates
        assignment_text = self._find_text_by_patterns(soup, ['付託', '委員会付託'])
        if assignment_text:
            assignments['assignment_info'] = assignment_text

        if assignments:
            bill_data.committee_assignments = assignments

    def _extract_voting_results(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract voting results"""
        results = {}

        # Look for voting information
        voting_patterns = [
            r'採決',
            r'可決',
            r'否決',
            r'修正可決',
        ]

        voting_text = self._find_text_by_patterns(soup, voting_patterns)
        if voting_text:
            results['voting_info'] = voting_text

        if results:
            bill_data.voting_results = results

    def _extract_amendments(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract amendment information"""
        amendments = []

        # Look for amendment information
        amendment_patterns = [
            r'修正',
            r'改正',
            r'変更',
        ]

        amendment_text = self._find_text_by_patterns(soup, amendment_patterns)
        if amendment_text:
            amendments.append({
                'type': 'amendment',
                'description': amendment_text,
                'date': None
            })

        if amendments:
            bill_data.amendments = amendments

    def _extract_inter_house_status(
            self,
            soup: BeautifulSoup,
            bill_data: EnhancedBillData) -> None:
        """Extract inter-house status"""
        status_patterns = [
            r'衆議院',
            r'参議院',
            r'送付',
            r'回付',
        ]

        status_text = self._find_text_by_patterns(soup, status_patterns)
        if status_text:
            bill_data.inter_house_status = status_text

    def _find_text_by_patterns(
            self,
            soup: BeautifulSoup,
            patterns: list[str]) -> str | None:
        """Find text content by matching patterns"""
        for pattern in patterns:
            element = soup.find(text=re.compile(pattern))
            if element:
                parent = element.parent
                if parent:
                    return parent.get_text(strip=True)
        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')

        # Normalize Japanese punctuation
        text = text.replace('。', '。')
        text = text.replace('、', '、')

        return text.strip()

    def _calculate_data_quality_score(self, bill_data: EnhancedBillData) -> float:
        """Calculate data quality score based on completeness"""
        score = 0.0
        total_fields = 0

        # Core fields (weight: 2)
        core_fields = [
            'bill_id', 'title', 'status', 'stage', 'submitter'
        ]
        for field in core_fields:
            total_fields += 2
            if getattr(bill_data, field):
                score += 2

        # Enhanced fields (weight: 1)
        enhanced_fields = [
            'bill_outline', 'background_context', 'expected_effects',
            'key_provisions', 'related_laws', 'implementation_date',
            'submitting_members', 'submitting_party', 'sponsoring_ministry',
            'committee_assignments', 'voting_results'
        ]
        for field in enhanced_fields:
            total_fields += 1
            value = getattr(bill_data, field)
            if value:
                if isinstance(value, list | dict):
                    if len(value) > 0:
                        score += 1
                else:
                    score += 1

        # Calculate percentage
        if total_fields > 0:
            return round(score / total_fields, 2)
        return 0.0

    async def fetch_enhanced_bills_async(
            self, bill_urls: list[str]) -> list[EnhancedBillData]:
        """Fetch enhanced bill data for multiple URLs asynchronously"""
        results = []

        for url in bill_urls:
            try:
                enhanced_data = self.fetch_enhanced_bill_details(url)
                results.append(enhanced_data)

                # Respect rate limiting
                await asyncio.sleep(self.delay_seconds)

            except Exception as e:
                self.logger.error(f"Error fetching enhanced data for {url}: {e}")
                continue

        return results
