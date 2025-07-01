"""
Diet website scraper for bill and session data collection.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


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
    BILLS_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/current/index.htm"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)'
        })
    
    def fetch_current_bills(self) -> List[BillData]:
        """
        Fetch current session bills from Diet website
        Returns list of BillData objects
        """
        try:
            response = self.session.get(self.BILLS_URL, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            bills = []
            
            # Parse bill listing table
            bill_tables = soup.find_all('table', class_='data')
            
            for table in bill_tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        bill = self._parse_bill_row(cells)
                        if bill:
                            bills.append(bill)
            
            return bills
            
        except requests.RequestException as e:
            print(f"Error fetching bills: {e}")
            return []
    
    def _parse_bill_row(self, cells) -> Optional[BillData]:
        """Parse individual bill row from table"""
        try:
            # Extract bill information from table cells
            bill_number = cells[0].get_text(strip=True)
            title_cell = cells[1]
            status = cells[2].get_text(strip=True)
            submitter = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            
            # Extract title and URL
            title_link = title_cell.find('a')
            if title_link:
                title = title_link.get_text(strip=True)
                url = urljoin(self.BASE_URL, title_link.get('href'))
            else:
                title = title_cell.get_text(strip=True)
                url = ""
            
            # Parse bill ID and determine stage
            stage = self._determine_stage(status)
            category = self._determine_category(title)
            
            return BillData(
                bill_id=bill_number,
                title=title,
                submission_date=None,  # To be parsed from detail page
                status=status,
                stage=stage,
                submitter=submitter,
                category=category,
                url=url
            )
            
        except Exception as e:
            print(f"Error parsing bill row: {e}")
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
            response = self.session.get(bill_url, timeout=30)
            response.raise_for_status()
            
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
            print(f"Error fetching bill details from {bill_url}: {e}")
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
    scraper = DietScraper()
    print("Fetching current bills...")
    
    bills = scraper.fetch_current_bills()
    print(f"Found {len(bills)} bills")
    
    for bill in bills[:3]:  # Show first 3 bills
        print(f"- {bill.bill_id}: {bill.title[:50]}...")
        print(f"  Status: {bill.status}, Stage: {bill.stage}")
        print(f"  Category: {bill.category}")
        print(f"  URL: {bill.url}")
        print()