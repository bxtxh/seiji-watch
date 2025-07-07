"""
House of Representatives Voting Data Scraper

Specialized scraper for collecting roll-call voting data from the House of Representatives.
Handles PDF collection, processing, and data normalization for lower house voting records.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

from .pdf_processor import PDFProcessor, PDFVotingSession
from .resilience import ResilientScraper, RateLimitConfig, CacheConfig


logger = logging.getLogger(__name__)


class HouseOfRepresentativesVotingScraper:
    """
    Scraper for House of Representatives voting data
    
    Focuses on roll-call votes which are typically published as PDFs
    on the House of Representatives website.
    """
    
    BASE_URL = "https://www.shugiin.go.jp"
    VOTING_BASE_URL = "https://www.shugiin.go.jp/internet/itdb_rchome.nsf"
    
    def __init__(self, enable_resilience: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)'
        })
        
        self.logger = logging.getLogger(__name__)
        self.pdf_processor = PDFProcessor()
        
        # Enhanced resilience features
        self.enable_resilience = enable_resilience
        self._resilient_scraper: Optional[ResilientScraper] = None
        if enable_resilience:
            self._init_resilient_scraper()
        
        # Cache for member names to improve PDF processing
        self._member_names_cache: Optional[List[str]] = None
        self._cache_expiry: Optional[datetime] = None
    
    def _init_resilient_scraper(self):
        """Initialize resilient scraper for HR website"""
        try:
            # Configure rate limiting for House of Representatives website
            rate_config = RateLimitConfig(
                requests_per_second=0.3,  # Very conservative: 1 request per 3+ seconds
                burst_size=2,  # Small burst allowance
                cooldown_seconds=20.0,  # Longer cooldown
                respect_retry_after=True
            )
            
            # Configure caching
            cache_config = CacheConfig(
                enabled=True,
                cache_dir="/tmp/hr_scraper_cache",
                max_age_hours=12,  # Shorter cache for HR data
                max_size_mb=100,
                hash_algorithm="sha256"
            )
            
            self._resilient_scraper = ResilientScraper(
                rate_limit_config=rate_config,
                cache_config=cache_config,
                max_concurrent_requests=2,  # Very conservative
                request_timeout=45  # Longer timeout for PDF downloads
            )
            
            self.logger.info("House of Representatives resilient scraper initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize HR resilient scraper: {e}")
            self._resilient_scraper = None
    
    async def fetch_recent_voting_sessions(
        self, 
        days_back: int = 30,
        session_numbers: Optional[List[int]] = None
    ) -> List[PDFVotingSession]:
        """
        Fetch recent voting sessions from House of Representatives
        
        Args:
            days_back: Number of days to look back for voting data
            session_numbers: Optional list of specific Diet session numbers to fetch
            
        Returns:
            List of PDFVotingSession objects
        """
        try:
            self.logger.info(f"Fetching HR voting sessions from last {days_back} days")
            
            # Get list of PDF URLs for voting records
            pdf_urls = await self._discover_voting_pdf_urls(days_back, session_numbers)
            
            if not pdf_urls:
                self.logger.warning("No voting PDF URLs found")
                return []
            
            self.logger.info(f"Found {len(pdf_urls)} voting PDFs to process")
            
            # Get cached member names for better matching
            member_names = await self._get_member_names()
            
            # Process PDFs to extract voting data
            voting_sessions = []
            
            if self._resilient_scraper:
                # Use resilient scraper for concurrent processing
                voting_sessions = await self._process_pdfs_with_resilience(pdf_urls, member_names)
            else:
                # Fallback to sequential processing
                voting_sessions = await self._process_pdfs_sequential(pdf_urls, member_names)
            
            self.logger.info(f"Successfully processed {len(voting_sessions)} voting sessions")
            return voting_sessions
            
        except Exception as e:
            self.logger.error(f"Failed to fetch HR voting sessions: {e}")
            return []
    
    async def _discover_voting_pdf_urls(
        self, 
        days_back: int,
        session_numbers: Optional[List[int]] = None
    ) -> List[str]:
        """Discover PDF URLs containing voting data"""
        pdf_urls = []
        
        try:
            # Define search URLs for different types of voting records
            search_urls = [
                f"{self.VOTING_BASE_URL}/Xhtml/result/vote_list.html",  # Main voting page
                f"{self.VOTING_BASE_URL}/Xhtml/result/record_list.html",  # Record page
            ]
            
            # If specific session numbers provided, use those
            if session_numbers:
                for session_num in session_numbers:
                    search_urls.append(
                        f"{self.VOTING_BASE_URL}/Xhtml/result/vote_list.html?session={session_num}"
                    )
            
            for search_url in search_urls:
                try:
                    self.logger.debug(f"Searching for PDFs at: {search_url}")
                    
                    if self._resilient_scraper:
                        async with self._resilient_scraper as scraper:
                            content = await scraper.fetch_with_resilience(search_url)
                    else:
                        response = self.session.get(search_url, timeout=30)
                        response.raise_for_status()
                        content = response.text
                    
                    if content:
                        page_pdfs = self._extract_pdf_urls_from_page(content, search_url, days_back)
                        pdf_urls.extend(page_pdfs)
                        self.logger.debug(f"Found {len(page_pdfs)} PDFs from {search_url}")
                
                except Exception as e:
                    self.logger.warning(f"Failed to search {search_url}: {e}")
                    continue
            
            # Remove duplicates
            pdf_urls = list(set(pdf_urls))
            
            return pdf_urls
            
        except Exception as e:
            self.logger.error(f"Failed to discover PDF URLs: {e}")
            return []
    
    def _extract_pdf_urls_from_page(
        self, 
        html_content: str, 
        base_url: str,
        days_back: int
    ) -> List[str]:
        """Extract PDF URLs from HTML page"""
        pdf_urls = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for link in pdf_links:
                try:
                    href = link.get('href')
                    if not href:
                        continue
                    
                    # Make absolute URL
                    pdf_url = urljoin(base_url, href)
                    
                    # Check if this looks like a voting PDF
                    link_text = link.get_text(strip=True).lower()
                    href_lower = href.lower()
                    
                    voting_keywords = ['採決', '表決', 'vote', '議決', '投票']
                    if any(keyword in link_text or keyword in href_lower for keyword in voting_keywords):
                        
                        # Try to extract date from link text or URL
                        if self._is_recent_enough(link_text, href, cutoff_date):
                            pdf_urls.append(pdf_url)
                            self.logger.debug(f"Found voting PDF: {pdf_url}")
                
                except Exception as e:
                    self.logger.debug(f"Error processing PDF link: {e}")
                    continue
            
            return pdf_urls
            
        except Exception as e:
            self.logger.error(f"Failed to extract PDF URLs from page: {e}")
            return []
    
    def _is_recent_enough(self, link_text: str, href: str, cutoff_date: datetime) -> bool:
        """Check if PDF is recent enough based on text/URL patterns"""
        try:
            # Look for date patterns in link text and URL
            text_to_check = f"{link_text} {href}"
            
            date_patterns = [
                r'令和(\d+)年(\d+)月(\d+)日',
                r'(\d{4})年(\d+)月(\d+)日',
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{4})(\d{2})(\d{2})',
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_to_check)
                for match in matches:
                    try:
                        if pattern.startswith('令和'):
                            year = int(match[0]) + 2018
                            month = int(match[1])
                            day = int(match[2])
                        else:
                            year = int(match[0])
                            month = int(match[1])
                            day = int(match[2])
                        
                        pdf_date = datetime(year, month, day)
                        if pdf_date >= cutoff_date:
                            return True
                            
                    except (ValueError, IndexError):
                        continue
            
            # If no date found, assume it might be recent
            return True
            
        except Exception:
            return True  # Default to including if we can't determine
    
    async def _get_member_names(self) -> List[str]:
        """Get list of current House of Representatives members"""
        try:
            # Check cache first
            if (self._member_names_cache and self._cache_expiry and 
                datetime.now() < self._cache_expiry):
                return self._member_names_cache
            
            self.logger.info("Fetching current HR member list")
            
            # URL for current members list
            members_url = f"{self.BASE_URL}/internet/itdb_iinkai.nsf/html/members/list.html"
            
            if self._resilient_scraper:
                async with self._resilient_scraper as scraper:
                    content = await scraper.fetch_with_resilience(members_url)
            else:
                response = self.session.get(members_url, timeout=30)
                response.raise_for_status()
                content = response.text
            
            if not content:
                self.logger.warning("Failed to fetch member list")
                return []
            
            # Parse member names from HTML
            member_names = self._parse_member_names_from_html(content)
            
            # Cache the results
            self._member_names_cache = member_names
            self._cache_expiry = datetime.now() + timedelta(hours=24)  # Cache for 24 hours
            
            self.logger.info(f"Found {len(member_names)} HR members")
            return member_names
            
        except Exception as e:
            self.logger.error(f"Failed to get HR member names: {e}")
            return []
    
    def _parse_member_names_from_html(self, html_content: str) -> List[str]:
        """Parse member names from HTML content"""
        member_names = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for various patterns where member names might appear
            name_patterns = [
                soup.find_all('td', class_='member-name'),
                soup.find_all('span', class_='name'),
                soup.find_all('a', href=re.compile(r'member|議員')),
            ]
            
            for pattern_results in name_patterns:
                for element in pattern_results:
                    name_text = element.get_text(strip=True)
                    
                    # Clean up the name
                    name = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3400-\u4DBF]', '', name_text)
                    
                    # Validate name (should be 2-4 Japanese characters typically)
                    if 2 <= len(name) <= 6 and name not in member_names:
                        member_names.append(name)
            
            # If no specific patterns found, look for general Japanese names
            if not member_names:
                # Look for patterns that look like Japanese names
                all_text = soup.get_text()
                potential_names = re.findall(r'[\u4E00-\u9FAF]{2,4}[\u3040-\u309F]*[\u4E00-\u9FAF]*', all_text)
                
                for name in potential_names:
                    if 2 <= len(name) <= 6:
                        member_names.append(name)
            
            # Remove duplicates and return
            return list(set(member_names))
            
        except Exception as e:
            self.logger.error(f"Failed to parse member names: {e}")
            return []
    
    async def _process_pdfs_with_resilience(
        self, 
        pdf_urls: List[str], 
        member_names: List[str]
    ) -> List[PDFVotingSession]:
        """Process PDFs using resilient scraper"""
        voting_sessions = []
        
        try:
            # Process PDFs with limited concurrency
            semaphore = asyncio.Semaphore(2)  # Maximum 2 concurrent PDF downloads
            
            async def process_single_pdf(pdf_url: str) -> Optional[PDFVotingSession]:
                async with semaphore:
                    try:
                        session = await self.pdf_processor.extract_voting_data_from_pdf(
                            pdf_url, member_names
                        )
                        if session:
                            self.logger.info(f"Successfully processed PDF: {pdf_url}")
                        return session
                    except Exception as e:
                        self.logger.error(f"Failed to process PDF {pdf_url}: {e}")
                        return None
            
            # Process all PDFs concurrently
            results = await asyncio.gather(
                *[process_single_pdf(url) for url in pdf_urls],
                return_exceptions=True
            )
            
            # Collect successful results
            for result in results:
                if isinstance(result, PDFVotingSession):
                    voting_sessions.append(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"PDF processing exception: {result}")
            
            return voting_sessions
            
        except Exception as e:
            self.logger.error(f"Error in resilient PDF processing: {e}")
            return []
    
    async def _process_pdfs_sequential(
        self, 
        pdf_urls: List[str], 
        member_names: List[str]
    ) -> List[PDFVotingSession]:
        """Process PDFs sequentially as fallback"""
        voting_sessions = []
        
        for i, pdf_url in enumerate(pdf_urls):
            try:
                self.logger.info(f"Processing PDF {i+1}/{len(pdf_urls)}: {pdf_url}")
                
                session = await self.pdf_processor.extract_voting_data_from_pdf(
                    pdf_url, member_names
                )
                
                if session:
                    voting_sessions.append(session)
                    self.logger.info(f"Successfully processed: {session.bill_number}")
                else:
                    self.logger.warning(f"Failed to extract data from: {pdf_url}")
                
                # Add delay between requests
                await asyncio.sleep(3)  # 3 second delay
                
            except Exception as e:
                self.logger.error(f"Error processing PDF {pdf_url}: {e}")
                continue
        
        return voting_sessions
    
    def get_scraper_statistics(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        stats = {
            "pdf_processor": self.pdf_processor.get_processing_statistics(),
            "member_names_cached": len(self._member_names_cache) if self._member_names_cache else 0,
            "cache_expires": self._cache_expiry.isoformat() if self._cache_expiry else None
        }
        
        if self._resilient_scraper:
            stats["resilient_scraper"] = self._resilient_scraper.get_statistics()
        
        return stats