"""
House of Councillors voting data scraper for Diet Issue Tracker.
Collects member voting records, party affiliations, and vote results.
"""
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


@dataclass
class VoteRecord:
    """Individual vote record structure"""
    member_name: str
    member_name_kana: str | None
    party_name: str
    constituency: str
    vote_result: str  # 賛成/反対/欠席/棄権
    house: str = "参議院"


@dataclass
class VotingSession:
    """Voting session metadata"""
    bill_number: str
    bill_title: str
    vote_date: datetime
    vote_type: str  # 本会議/委員会
    vote_stage: str | None  # 第一読会/第二読会/最終
    committee_name: str | None
    total_votes: int
    yes_votes: int
    no_votes: int
    abstain_votes: int
    absent_votes: int
    vote_records: list[VoteRecord]


class VotingScraper:
    """Scraper for House of Councillors voting data"""

    BASE_URL = "https://www.sangiin.go.jp"
    # URLs for different voting data sources
    # Note: These URLs may need to be adjusted based on actual Diet website structure
    PLENARY_VOTES_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/vote/217/vote.htm"
    COMMITTEE_VOTES_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/iinkai/217/iinkai.htm"
    # Alternative: Try main session pages first
    SESSION_217_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/217/gian.htm"

    def __init__(self, delay_seconds: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)'
        })
        self.delay_seconds = delay_seconds
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._robots_parser = None
        self._init_robots_parser()

    def _init_robots_parser(self):
        """Initialize robots.txt parser"""
        try:
            robots_url = urljoin(self.BASE_URL, '/robots.txt')
            self._robots_parser = RobotFileParser()
            self._robots_parser.set_url(robots_url)
            self._robots_parser.read()
            self.logger.info("Robots.txt parser initialized for voting scraper")
        except Exception as e:
            self.logger.warning(f"Could not load robots.txt: {e}")
            self._robots_parser = None

    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self._robots_parser:
            return True

        user_agent = self.session.headers.get('User-Agent', '*')
        return self._robots_parser.can_fetch(user_agent, url)

    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.delay_seconds:
            sleep_time = self.delay_seconds - time_since_last
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with rate limiting and robots.txt checking"""
        if not self._can_fetch(url):
            raise requests.RequestException(f"Robots.txt disallows fetching: {url}")

        self._rate_limit()

        response = self.session.get(url, **kwargs)
        response.raise_for_status()

        return response

    def fetch_voting_sessions(self) -> list[VotingSession]:
        """
        Fetch all voting sessions from current Diet session
        Returns list of VotingSession objects
        """
        voting_sessions = []

        # For MVP development, return mock data first
        # TODO: Implement actual scraping once correct URLs are determined
        try:
            mock_sessions = self._generate_mock_voting_sessions()
            voting_sessions.extend(mock_sessions)
            self.logger.info(
                f"Generated {len(mock_sessions)} mock voting sessions for development")
        except Exception as e:
            self.logger.error(f"Failed to generate mock voting sessions: {e}")

        # Uncomment below when actual scraping URLs are available
        # # Fetch plenary voting sessions
        # try:
        #     plenary_sessions = self._fetch_plenary_voting_sessions()
        #     voting_sessions.extend(plenary_sessions)
        #     self.logger.info(f"Found {len(plenary_sessions)} plenary voting sessions")
        # except Exception as e:
        #     self.logger.error(f"Failed to fetch plenary voting sessions: {e}")

        # # Fetch committee voting sessions
        # try:
        #     committee_sessions = self._fetch_committee_voting_sessions()
        #     voting_sessions.extend(committee_sessions)
        #     self.logger.info(f"Found {len(committee_sessions)} committee voting sessions")
        # except Exception as e:
        #     self.logger.error(f"Failed to fetch committee voting sessions: {e}")

        return voting_sessions

    def _generate_mock_voting_sessions(self) -> list[VotingSession]:
        """Generate mock voting sessions for development and testing"""
        mock_sessions = []

        # Mock parties based on current Diet composition
        parties = [
            "自由民主党", "立憲民主党", "日本維新の会", "公明党", "国民民主党",
            "日本共産党", "れいわ新選組", "社会民主党", "NHK党", "参政党"
        ]

        # Mock constituencies
        constituencies = [
            "東京都", "大阪府", "神奈川県", "愛知県", "埼玉県", "千葉県", "兵庫県",
            "北海道", "福岡県", "静岡県", "比例代表"
        ]

        # Generate 3 mock voting sessions
        for i in range(1, 4):
            # Generate mock vote records
            vote_records = []
            vote_counts = {"yes": 0, "no": 0, "abstain": 0, "absent": 0}

            # Generate 20 mock members per session
            for j in range(1, 21):
                member_name = f"議員{j:02d}"
                party = parties[j % len(parties)]
                constituency = constituencies[j % len(constituencies)]

                # Simulate realistic voting patterns
                if party in ["自由民主党", "公明党"]:
                    vote_result = "賛成" if j % 10 != 0 else "欠席"
                elif party in ["立憲民主党", "日本共産党"]:
                    vote_result = "反対" if j % 8 != 0 else "欠席"
                else:
                    vote_result = ["賛成", "反対", "棄権"][j % 3]

                if vote_result == "賛成":
                    vote_counts["yes"] += 1
                elif vote_result == "反対":
                    vote_counts["no"] += 1
                elif vote_result == "棄権":
                    vote_counts["abstain"] += 1
                elif vote_result == "欠席":
                    vote_counts["absent"] += 1

                vote_record = VoteRecord(
                    member_name=member_name,
                    member_name_kana=f"{member_name}(ヨミ)",
                    party_name=party,
                    constituency=constituency,
                    vote_result=vote_result
                )
                vote_records.append(vote_record)

            # Create mock voting session
            session = VotingSession(
                bill_number=f"217-{i}",
                bill_title=f"令和6年度補正予算案第{i}号",
                vote_date=datetime(2024, 7, 4 + i),
                vote_type="本会議",
                vote_stage="最終" if i == 1 else "第二読会",
                committee_name=None,
                total_votes=len(vote_records),
                yes_votes=vote_counts["yes"],
                no_votes=vote_counts["no"],
                abstain_votes=vote_counts["abstain"],
                absent_votes=vote_counts["absent"],
                vote_records=vote_records
            )

            mock_sessions.append(session)

        return mock_sessions

    def _fetch_plenary_voting_sessions(self) -> list[VotingSession]:
        """Fetch voting sessions from plenary meetings"""
        try:
            response = self._make_request(self.PLENARY_VOTES_URL, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            sessions = []

            # Look for voting record tables
            vote_tables = soup.find_all('table')
            self.logger.info(f"Found {len(vote_tables)} tables on plenary voting page")

            for i, table in enumerate(vote_tables):
                self.logger.debug(f"Processing table {i}")

                # Check if this table contains voting data
                if self._is_voting_table(table):
                    try:
                        session = self._parse_voting_table(table, "本会議")
                        if session:
                            sessions.append(session)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse voting table {i}: {e}")

            return sessions

        except requests.RequestException as e:
            self.logger.error(f"Error fetching plenary voting data: {e}")
            return []

    def _fetch_committee_voting_sessions(self) -> list[VotingSession]:
        """Fetch voting sessions from committee meetings"""
        try:
            response = self._make_request(self.COMMITTEE_VOTES_URL, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            sessions = []

            # Look for committee links
            committee_links = soup.find_all('a', href=re.compile(r'iinkai.*\.htm'))
            self.logger.info(f"Found {len(committee_links)} committee links")

            # Limit to first 5 committees for initial implementation
            for link in committee_links[:5]:
                committee_url = urljoin(self.BASE_URL, link.get('href'))
                committee_name = link.get_text(strip=True)

                try:
                    committee_sessions = self._fetch_committee_voting_data(
                        committee_url, committee_name)
                    sessions.extend(committee_sessions)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch committee voting data for {committee_name}: {e}")

            return sessions

        except requests.RequestException as e:
            self.logger.error(f"Error fetching committee voting data: {e}")
            return []

    def _fetch_committee_voting_data(
            self,
            committee_url: str,
            committee_name: str) -> list[VotingSession]:
        """Fetch voting data from specific committee"""
        try:
            response = self._make_request(committee_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')

            sessions = []
            vote_tables = soup.find_all('table')

            for table in vote_tables:
                if self._is_voting_table(table):
                    try:
                        session = self._parse_voting_table(table, "委員会", committee_name)
                        if session:
                            sessions.append(session)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to parse committee voting table: {e}")

            return sessions

        except requests.RequestException as e:
            self.logger.error(
                f"Error fetching committee voting data from {committee_url}: {e}")
            return []

    def _is_voting_table(self, table) -> bool:
        """Check if table contains voting data"""
        # Look for voting-related headers
        headers = table.find_all(['th', 'td'])
        header_text = ' '.join([h.get_text(strip=True) for h in headers[:10]])

        voting_keywords = ['議員名', '会派', '投票', '賛成', '反対', '欠席', '棄権']
        return any(keyword in header_text for keyword in voting_keywords)

    def _parse_voting_table(
            self,
            table,
            vote_type: str,
            committee_name: str | None = None) -> VotingSession | None:
        """Parse individual voting table"""
        try:
            rows = table.find_all('tr')
            if len(rows) <= 1:
                return None

            # Extract vote metadata from table caption or surrounding text
            bill_info = self._extract_bill_info_from_table(table)

            # Parse vote records
            vote_records = []
            vote_counts = {"yes": 0, "no": 0, "abstain": 0, "absent": 0}

            # Skip header row(s)
            data_rows = self._identify_data_rows(rows)

            for row in data_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # Minimum: name, party, vote
                    vote_record = self._parse_vote_record(cells)
                    if vote_record:
                        vote_records.append(vote_record)

                        # Count votes
                        if vote_record.vote_result == "賛成":
                            vote_counts["yes"] += 1
                        elif vote_record.vote_result == "反対":
                            vote_counts["no"] += 1
                        elif vote_record.vote_result == "棄権":
                            vote_counts["abstain"] += 1
                        elif vote_record.vote_result == "欠席":
                            vote_counts["absent"] += 1

            if not vote_records:
                return None

            return VotingSession(
                bill_number=bill_info.get("bill_number", "Unknown"),
                bill_title=bill_info.get("bill_title", "Unknown"),
                vote_date=bill_info.get("vote_date", datetime.now()),
                vote_type=vote_type,
                vote_stage=bill_info.get("vote_stage"),
                committee_name=committee_name,
                total_votes=len(vote_records),
                yes_votes=vote_counts["yes"],
                no_votes=vote_counts["no"],
                abstain_votes=vote_counts["abstain"],
                absent_votes=vote_counts["absent"],
                vote_records=vote_records
            )

        except Exception as e:
            self.logger.error(f"Error parsing voting table: {e}")
            return None

    def _extract_bill_info_from_table(self, table) -> dict[str, any]:
        """Extract bill information from table context"""
        # Look for bill information in table caption, previous elements, etc.
        bill_info = {
            "bill_number": "Unknown",
            "bill_title": "Unknown",
            "vote_date": datetime.now(),
            "vote_stage": None
        }

        # Check table caption
        caption = table.find('caption')
        if caption:
            caption_text = caption.get_text(strip=True)
            bill_info.update(self._parse_bill_info_text(caption_text))

        # Check preceding headings
        prev_elements = []
        current = table.find_previous_sibling()
        count = 0
        while current and count < 5:  # Check up to 5 previous elements
            if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
                prev_elements.append(current.get_text(strip=True))
            current = current.find_previous_sibling()
            count += 1

        for text in prev_elements:
            info = self._parse_bill_info_text(text)
            bill_info.update({k: v for k, v in info.items() if v != "Unknown"})

        return bill_info

    def _parse_bill_info_text(self, text: str) -> dict[str, any]:
        """Parse bill information from text"""
        info = {}

        # Extract bill number (e.g., "第217-1号")
        bill_pattern = r'第?(\d+[-ー]\d+)号?'
        bill_match = re.search(bill_pattern, text)
        if bill_match:
            info["bill_number"] = bill_match.group(1)

        # Extract date
        date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        date_match = re.search(date_pattern, text)
        if date_match:
            year, month, day = map(int, date_match.groups())
            info["vote_date"] = datetime(year, month, day)

        # Extract vote stage
        if "第一読会" in text:
            info["vote_stage"] = "第一読会"
        elif "第二読会" in text:
            info["vote_stage"] = "第二読会"
        elif "最終" in text or "三読" in text:
            info["vote_stage"] = "最終"

        # Extract bill title (everything before 案)
        title_pattern = r'([^。]+?案)'
        title_match = re.search(title_pattern, text)
        if title_match:
            info["bill_title"] = title_match.group(1)

        return info

    def _identify_data_rows(self, rows) -> list:
        """Identify which rows contain vote data"""
        data_rows = []

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                # Check if this looks like a data row
                first_cell_text = cells[0].get_text(strip=True)

                # Skip header rows
                if first_cell_text in ['議員名', '氏名', '会派', '党派', '投票結果']:
                    continue

                # Skip empty rows
                if not first_cell_text:
                    continue

                data_rows.append(row)

        return data_rows

    def _parse_vote_record(self, cells) -> VoteRecord | None:
        """Parse individual vote record from table cells"""
        try:
            if len(cells) < 3:
                return None

            # Extract member information
            member_name = cells[0].get_text(strip=True)
            if not member_name or len(member_name) < 2:
                return None

            # Extract party/faction
            party_name = cells[1].get_text(strip=True)

            # Extract constituency (might be in same cell as party or separate)
            constituency = ""
            if len(cells) >= 4:
                constituency = cells[2].get_text(strip=True)
                vote_cell_idx = 3
            else:
                # Constituency might be part of party cell
                party_text = party_name
                if "（" in party_text:
                    parts = party_text.split("（")
                    party_name = parts[0].strip()
                    constituency = parts[1].replace("）", "").strip()
                vote_cell_idx = 2

            # Extract vote result
            vote_result = cells[vote_cell_idx].get_text(
                strip=True) if len(cells) > vote_cell_idx else ""

            # Normalize vote result
            vote_result = self._normalize_vote_result(vote_result)

            # Extract kana reading if available
            member_name_kana = None
            if "（" in member_name:
                parts = member_name.split("（")
                member_name = parts[0].strip()
                member_name_kana = parts[1].replace("）", "").strip()

            return VoteRecord(
                member_name=member_name,
                member_name_kana=member_name_kana,
                party_name=party_name,
                constituency=constituency,
                vote_result=vote_result
            )

        except Exception as e:
            self.logger.error(f"Error parsing vote record: {e}")
            return None

    def _normalize_vote_result(self, vote_text: str) -> str:
        """Normalize vote result text"""
        vote_text = vote_text.strip()

        if vote_text in ["○", "賛成", "可"]:
            return "賛成"
        elif vote_text in ["×", "反対", "否"]:
            return "反対"
        elif vote_text in ["棄権", "△"]:
            return "棄権"
        elif vote_text in ["欠席", "－", "欠"]:
            return "欠席"
        elif vote_text in ["出席", "＋"]:
            return "出席"
        else:
            return vote_text

    def fetch_member_details(self, member_name: str) -> dict[str, any]:
        """Fetch additional member details from Diet website"""
        # This would be implemented to fetch more detailed member information
        # For now, return basic structure
        return {
            "name": member_name,
            "name_kana": None,
            "diet_member_id": None,
            "birth_date": None,
            "first_elected": None,
            "education": None,
            "previous_occupations": None
        }


if __name__ == "__main__":
    # Test the voting scraper
    logging.basicConfig(level=logging.INFO)

    scraper = VotingScraper()
    scraper.logger.info("Fetching voting sessions...")

    sessions = scraper.fetch_voting_sessions()
    scraper.logger.info(f"Found {len(sessions)} voting sessions")

    for session in sessions[:2]:  # Show first 2 sessions
        print(f"Bill: {session.bill_number} - {session.bill_title}")
        print(f"Date: {session.vote_date.strftime('%Y-%m-%d')}")
        print(f"Type: {session.vote_type}")
        print(
            f"Results: Yes={session.yes_votes}, No={session.no_votes}, Abstain={session.abstain_votes}, Absent={session.absent_votes}")
        print(f"Total Members: {session.total_votes}")
        print(
            f"Sample votes: {[f'{v.member_name}({v.party_name})={v.vote_result}' for v in session.vote_records[:3]]}")
        print()
