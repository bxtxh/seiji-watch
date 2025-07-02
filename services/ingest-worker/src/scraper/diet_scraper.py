"""
Diet website scraper for bill and session data collection.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


@dataclass
class BillData:
    """Diet bill metadata structure"""
    bill_id: str
    title: str
    submission_date: Optional[datetime]
    status: str
    stage: str
    submitter: str
    category: str
    url: str
    summary: Optional[str] = None


class DietScraper:
    """Main scraper class for Diet website data collection"""
    
    BASE_URL = "https://www.sangiin.go.jp"
    BILLS_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/217/gian.htm"
    
    def __init__(self, delay_seconds: float = 1.5):
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
            self.logger.info("Robots.txt parser initialized")
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
        # Check robots.txt
        if not self._can_fetch(url):
            raise requests.RequestException(f"Robots.txt disallows fetching: {url}")
        
        # Apply rate limiting
        self._rate_limit()
        
        # Make request
        response = self.session.get(url, **kwargs)
        response.raise_for_status()
        
        return response
    
    def fetch_current_bills(self) -> List[BillData]:
        """
        Fetch current session bills from Diet website
        Returns list of BillData objects
        """
        try:
            response = self._make_request(self.BILLS_URL, timeout=30)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bills = []
            
            # Debug: Print page structure
            self.logger.info(f"Page title: {soup.title.string if soup.title else 'No title'}")
            
            # Look for various table structures
            bill_tables = soup.find_all('table')
            self.logger.info(f"Found {len(bill_tables)} tables on page")
            
            for i, table in enumerate(bill_tables):
                self.logger.info(f"Table {i}: classes={table.get('class')}, rows={len(table.find_all('tr'))}")
                
                rows = table.find_all('tr')
                if len(rows) <= 1:  # Skip tables with no data rows
                    continue
                
                # Debug first few rows of first table (only if needed)
                if i == 1 and self.logger.level <= logging.DEBUG:
                    self.logger.debug(f"Debugging Table {i}:")
                    for j, row in enumerate(rows[:3]):
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [c.get_text(strip=True)[:20] + '...' if len(c.get_text(strip=True)) > 20 else c.get_text(strip=True) for c in cells]
                        self.logger.debug(f"  Row {j}: {cell_texts}")
                    
                # Skip header row if exists
                data_rows = rows[1:] if rows[0].find('th') else rows
                
                for row in data_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:  # Minimum required cells
                        bill = self._parse_bill_row(cells)
                        if bill:
                            bills.append(bill)
            
            return bills
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching bills: {e}")
            return []
    
    def _parse_bill_row(self, cells) -> Optional[BillData]:
        """Parse individual bill row from table"""
        try:
            if len(cells) < 3:
                return None
            
            # Extract bill information from table cells
            # Column structure: [提出回次, 提出番号, 件名, 議案要旨, 提出法律案]
            diet_session = cells[0].get_text(strip=True)
            bill_number = cells[1].get_text(strip=True)
            title_cell = cells[2]
            
            # Check if this is a header row
            if not diet_session or diet_session in ['提出回次', '回次']:
                return None
            
            # Extract title and URL
            title_link = title_cell.find('a')
            if title_link:
                title = title_link.get_text(strip=True)
                url = urljoin(self.BASE_URL, title_link.get('href'))
            else:
                title = title_cell.get_text(strip=True)
                url = ""
            
            # Skip if no title
            if not title:
                return None
            
            # Create bill ID from session and number
            bill_id = f"{diet_session}-{bill_number}"
            
            # Extract status from remaining cells
            status = cells[3].get_text(strip=True) if len(cells) > 3 else "審議中"
            bill_type = cells[4].get_text(strip=True) if len(cells) > 4 else "提出法律案"
            
            # Determine submitter based on bill type and context
            submitter = "政府" if "政府" in bill_type else "議員"
            
            # Parse bill ID and determine stage
            stage = self._determine_stage(status)
            category = self._determine_category(title)
            
            return BillData(
                bill_id=bill_id,
                title=title,
                submission_date=None,  # To be parsed from detail page
                status=status,
                stage=stage,
                submitter=submitter,
                category=category,
                url=url
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing bill row: {e}")
            return None
    
    def _determine_stage(self, status: str) -> str:
        """Determine bill stage from status text"""
        if "成立" in status:
            return "成立"
        elif "可決" in status:
            return "採決待ち"
        elif "審議" in status:
            return "審議中"
        else:
            return "Backlog"
    
    def _determine_category(self, title: str) -> str:
        """Categorize bill based on title keywords"""
        if any(keyword in title for keyword in ["予算", "補正", "決算"]):
            return "予算・決算"
        elif any(keyword in title for keyword in ["税", "課税", "控除"]):
            return "税制"
        elif any(keyword in title for keyword in ["社会保障", "年金", "保険"]):
            return "社会保障"
        elif any(keyword in title for keyword in ["外交", "条約", "協定"]):
            return "外交・国際"
        elif any(keyword in title for keyword in ["経済", "産業", "貿易"]):
            return "経済・産業"
        else:
            return "その他"
    
    def fetch_bill_details(self, bill_url: str) -> Dict:
        """Fetch detailed information for a specific bill"""
        try:
            response = self._make_request(bill_url, timeout=30)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract detailed information
            details = {
                'summary': self._extract_summary(soup),
                'submission_date': self._extract_submission_date(soup),
                'committee': self._extract_committee(soup),
                'related_documents': self._extract_documents(soup)
            }
            
            return details
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching bill details from {bill_url}: {e}")
            return {}
    
    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract bill summary from detail page"""
        summary_section = soup.find('div', class_='summary')
        if summary_section:
            return summary_section.get_text(strip=True)
        return ""
    
    def _extract_submission_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract submission date from detail page"""
        date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        text = soup.get_text()
        match = re.search(date_pattern, text)
        
        if match:
            year, month, day = map(int, match.groups())
            return datetime(year, month, day)
        return None
    
    def _extract_committee(self, soup: BeautifulSoup) -> str:
        """Extract committee information"""
        committee_section = soup.find(text=re.compile(r'委員会'))
        if committee_section:
            return committee_section.strip()
        return ""
    
    def _extract_documents(self, soup: BeautifulSoup) -> List[str]:
        """Extract related document URLs"""
        documents = []
        doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx)$'))
        
        for link in doc_links:
            doc_url = urljoin(self.BASE_URL, link.get('href'))
            documents.append(doc_url)
        
        return documents


if __name__ == "__main__":
    # PoC test
    logging.basicConfig(level=logging.INFO)
    
    scraper = DietScraper()
    scraper.logger.info("Fetching current bills...")
    
    bills = scraper.fetch_current_bills()
    scraper.logger.info(f"Found {len(bills)} bills")
    
    for bill in bills[:3]:  # Show first 3 bills
        print(f"- {bill.bill_id}: {bill.title[:50]}...")
        print(f"  Status: {bill.status}, Stage: {bill.stage}")
        print(f"  Category: {bill.category}")
        print(f"  URL: {bill.url}")
        print()