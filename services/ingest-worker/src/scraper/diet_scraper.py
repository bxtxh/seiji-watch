"""
Diet website scraper for bill and session data collection.
Enhanced with resilience and optimization features.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
import re
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import asyncio

from .resilience import ResilientScraper, RateLimitConfig, CacheConfig


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
    """Main scraper class for Diet website data collection with resilience features"""
    
    BASE_URL = "https://www.sangiin.go.jp"
    BILLS_URL = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/217/gian.htm"
    
    def __init__(self, delay_seconds: float = 1.5, enable_resilience: bool = True):
        # Traditional session for backward compatibility
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)'
        })
        self.delay_seconds = delay_seconds
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._robots_parser = None
        self._init_robots_parser()
        
        # Enhanced resilience features
        self.enable_resilience = enable_resilience
        self._resilient_scraper: Optional[ResilientScraper] = None
        if enable_resilience:
            self._init_resilient_scraper()
    
    def _init_resilient_scraper(self):
        """Initialize resilient scraper with optimized configuration"""
        try:
            # Configure rate limiting for Diet website
            rate_config = RateLimitConfig(
                requests_per_second=0.5,  # Conservative: 1 request per 2 seconds
                burst_size=3,  # Small burst allowance
                cooldown_seconds=15.0,  # Longer cooldown if rate limited
                respect_retry_after=True
            )
            
            # Configure caching for duplicate detection
            cache_config = CacheConfig(
                enabled=True,
                cache_dir="/tmp/diet_scraper_cache",
                max_age_hours=24,  # Cache for 24 hours
                max_size_mb=50,  # Limit cache size
                hash_algorithm="sha256"
            )
            
            self._resilient_scraper = ResilientScraper(
                rate_limit_config=rate_config,
                cache_config=cache_config,
                max_concurrent_requests=3,  # Conservative concurrency
                request_timeout=30
            )
            
            self.logger.info("Resilient scraper initialized with optimized settings")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize resilient scraper: {e}")
            self._resilient_scraper = None
    
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
    
    # Enhanced resilience and optimization methods
    
    async def fetch_current_bills_async(self, force_refresh: bool = False) -> List[BillData]:
        """
        Async version of fetch_current_bills with resilience features
        
        Args:
            force_refresh: Skip duplicate detection and force fresh fetch
            
        Returns:
            List of BillData objects
        """
        if not self._resilient_scraper:
            # Fall back to synchronous method if resilient scraper not available
            self.logger.warning("Resilient scraper not available, falling back to sync method")
            return self.fetch_current_bills()
        
        try:
            async with self._resilient_scraper as scraper:
                # Create job for tracking
                job = scraper.create_job(
                    job_type="fetch_bills",
                    url=self.BILLS_URL,
                    metadata={"force_refresh": force_refresh}
                )
                
                # Fetch main bills page
                content = await scraper.fetch_with_resilience(
                    self.BILLS_URL,
                    job=job,
                    skip_duplicates=not force_refresh
                )
                
                if content is None:
                    self.logger.info("Bills page content skipped (duplicate)")
                    return []
                
                # Parse bills
                bills = self._parse_bills_from_html(content)
                
                # Fetch bill details in parallel if we have bills
                if bills and not force_refresh:
                    # Only fetch details for bills we haven't seen before
                    detail_urls = []
                    for bill in bills:
                        if hasattr(bill, 'url') and bill.url:
                            # Create detail URL
                            detail_url = urljoin(self.BASE_URL, bill.url)
                            detail_urls.append(detail_url)
                    
                    if detail_urls:
                        self.logger.info(f"Fetching details for {len(detail_urls)} bills")
                        
                        # Fetch details with progress tracking
                        def progress_callback(progress: float):
                            self.logger.info(f"Bill details progress: {progress:.1%}")
                        
                        detail_results = await scraper.fetch_multiple_urls(
                            detail_urls[:10],  # Limit to first 10 for performance
                            job_type="fetch_bill_details",
                            skip_duplicates=not force_refresh,
                            progress_callback=progress_callback
                        )
                        
                        # Process detail results and enhance bill data
                        for i, bill in enumerate(bills[:10]):
                            if i < len(detail_urls):
                                detail_url = detail_urls[i]
                                detail_content = detail_results.get(detail_url)
                                if detail_content:
                                    # Parse and enhance bill with details
                                    try:
                                        soup = BeautifulSoup(detail_content, 'html.parser')
                                        enhanced_summary = self._extract_summary(soup)
                                        if enhanced_summary and len(enhanced_summary) > len(bill.summary or ""):
                                            bill.summary = enhanced_summary
                                    except Exception as e:
                                        self.logger.warning(f"Failed to parse details for {bill.bill_id}: {e}")
                
                self.logger.info(f"Successfully fetched {len(bills)} bills with resilience features")
                return bills
                
        except Exception as e:
            self.logger.error(f"Failed to fetch bills with resilient scraper: {e}")
            # Fall back to synchronous method
            return self.fetch_current_bills()
    
    def _parse_bills_from_html(self, html_content: str) -> List[BillData]:
        """Parse bills from HTML content (extracted from fetch_current_bills)"""
        bills = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for various table structures
            bill_tables = soup.find_all('table')
            
            for table in bill_tables:
                rows = table.find_all('tr')
                if len(rows) <= 1:  # Skip tables with no data rows
                    continue
                
                # Skip header row if exists
                data_rows = rows[1:] if rows[0].find('th') else rows
                
                for row in data_rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:  # Minimum required cells
                        bill = self._parse_bill_row(cells)
                        if bill:
                            bills.append(bill)
        
        except Exception as e:
            self.logger.error(f"Failed to parse bills from HTML: {e}")
        
        return bills
    
    async def fetch_bill_details_async(self, bill_url: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Async version of fetch_bill_details with resilience features
        
        Args:
            bill_url: URL of the bill detail page
            force_refresh: Skip duplicate detection and force fresh fetch
            
        Returns:
            Dictionary containing bill details
        """
        if not self._resilient_scraper:
            # Fall back to synchronous method
            return self.fetch_bill_details(bill_url)
        
        try:
            async with self._resilient_scraper as scraper:
                content = await scraper.fetch_with_resilience(
                    bill_url,
                    skip_duplicates=not force_refresh
                )
                
                if content is None:
                    self.logger.info(f"Bill details skipped (duplicate): {bill_url}")
                    return {}
                
                soup = BeautifulSoup(content, 'html.parser')
                
                details = {
                    'title': soup.title.string if soup.title else '',
                    'summary': self._extract_summary(soup),
                    'submission_date': self._extract_submission_date(soup),
                    'committee': self._extract_committee(soup),
                    'related_documents': self._extract_documents(soup)
                }
                
                return details
                
        except Exception as e:
            self.logger.error(f"Failed to fetch bill details with resilient scraper: {e}")
            return self.fetch_bill_details(bill_url)
    
    def get_scraper_statistics(self) -> Dict[str, Any]:
        """Get scraper performance statistics"""
        stats = {
            "traditional_scraper": {
                "delay_seconds": self.delay_seconds,
                "robots_parser_enabled": self._robots_parser is not None
            }
        }
        
        if self._resilient_scraper:
            stats["resilient_scraper"] = self._resilient_scraper.get_statistics()
        else:
            stats["resilient_scraper"] = {"status": "disabled"}
        
        return stats
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific scraping job"""
        if self._resilient_scraper:
            return self._resilient_scraper.get_job_status(job_id)
        return None
    
    def get_all_jobs(self) -> Dict[str, Any]:
        """Get status of all scraping jobs"""
        if self._resilient_scraper:
            return self._resilient_scraper.get_all_jobs()
        return {"message": "Resilient scraper not enabled"}
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs and cache"""
        if self._resilient_scraper:
            return self._resilient_scraper.cleanup_completed_jobs(max_age_hours)
        return 0


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