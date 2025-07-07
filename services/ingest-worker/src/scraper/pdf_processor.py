"""
PDF Processing Module for House of Representatives Voting Data

This module handles:
- PDF collection from House of Representatives voting pages
- PDF text extraction and OCR processing
- Member name dictionary matching for verification
- Graceful handling of OCR recognition errors
- Vote result parsing and normalization
"""

import io
import logging
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

# Optional dependencies with fallbacks
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None


logger = logging.getLogger(__name__)


@dataclass
class PDFVoteRecord:
    """Individual vote record extracted from PDF"""
    member_name: str
    member_name_kana: Optional[str]
    party_name: str
    constituency: str
    vote_result: str  # "賛成", "反対", "欠席", etc.
    confidence_score: float = 1.0  # OCR confidence (0.0-1.0)


@dataclass
class PDFVotingSession:
    """Voting session data extracted from PDF"""
    session_id: str
    bill_number: str
    bill_title: str
    vote_date: datetime
    vote_type: str  # "本会議", "委員会", etc.
    committee_name: Optional[str]
    pdf_url: str
    total_members: int
    vote_records: List[PDFVoteRecord]
    
    @property
    def vote_summary(self) -> Dict[str, int]:
        """Calculate vote summary statistics"""
        summary = {"賛成": 0, "反対": 0, "欠席": 0, "棄権": 0, "その他": 0}
        
        for record in self.vote_records:
            if record.vote_result in summary:
                summary[record.vote_result] += 1
            else:
                summary["その他"] += 1
        
        return summary


class MemberNameMatcher:
    """Handles member name matching and normalization"""
    
    def __init__(self):
        # Common name variations and corrections
        self.name_corrections = {
            # Handle common OCR errors
            "鈴木": ["釣木", "釣本", "鈴本"],
            "田中": ["田申", "由中", "由申"],
            "佐藤": ["佐藤", "作藤", "佐薔"],
            "高橋": ["高栢", "高棒", "商橋"],
            "渡辺": ["渡邊", "渡邉", "渡邊"],
            "小林": ["小林", "小柿", "小株"],
        }
        
        # Common suffixes and prefixes
        self.name_patterns = [
            r"(.+)君$",          # Remove 君 suffix
            r"(.+)先生$",        # Remove 先生 suffix
            r"(.+)議員$",        # Remove 議員 suffix
            r"^○(.+)$",          # Remove ○ prefix
            r"^●(.+)$",          # Remove ● prefix
        ]
    
    def normalize_name(self, name: str) -> str:
        """Normalize member name by removing common suffixes/prefixes"""
        normalized = name.strip()
        
        # Apply name patterns
        for pattern in self.name_patterns:
            match = re.match(pattern, normalized)
            if match:
                normalized = match.group(1)
                break
        
        return normalized
    
    def find_best_match(
        self, 
        ocr_name: str, 
        member_list: List[str],
        threshold: float = 0.7
    ) -> Tuple[Optional[str], float]:
        """
        Find best matching member name from OCR result
        
        Args:
            ocr_name: Name extracted from OCR
            member_list: List of known member names
            threshold: Minimum similarity threshold
            
        Returns:
            Tuple of (matched_name, confidence_score)
        """
        normalized_ocr = self.normalize_name(ocr_name)
        best_match = None
        best_score = 0.0
        
        for member_name in member_list:
            normalized_member = self.normalize_name(member_name)
            
            # Exact match
            if normalized_ocr == normalized_member:
                return member_name, 1.0
            
            # Check name corrections
            for correct_name, variants in self.name_corrections.items():
                if correct_name in normalized_member:
                    for variant in variants:
                        if variant in normalized_ocr:
                            score = 0.9  # High confidence for known corrections
                            if score > best_score:
                                best_match = member_name
                                best_score = score
            
            # Fuzzy matching using simple character overlap
            score = self._calculate_similarity(normalized_ocr, normalized_member)
            if score > best_score:
                best_match = member_name
                best_score = score
        
        if best_score >= threshold:
            return best_match, best_score
        
        return None, 0.0
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using character overlap"""
        if not name1 or not name2:
            return 0.0
        
        # Convert to sets of characters
        chars1 = set(name1)
        chars2 = set(name2)
        
        # Calculate Jaccard similarity
        intersection = len(chars1.intersection(chars2))
        union = len(chars1.union(chars2))
        
        if union == 0:
            return 0.0
        
        return intersection / union


class PDFProcessor:
    """Main PDF processing class for voting data extraction"""
    
    def __init__(self):
        self.name_matcher = MemberNameMatcher()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; DietTracker/1.0; +https://github.com/diet-tracker)'
        })
    
    async def extract_voting_data_from_pdf(
        self, 
        pdf_url: str,
        member_names: Optional[List[str]] = None
    ) -> Optional[PDFVotingSession]:
        """
        Extract voting data from a PDF URL
        
        Args:
            pdf_url: URL of the PDF to process
            member_names: Optional list of known member names for matching
            
        Returns:
            PDFVotingSession object or None if extraction fails
        """
        try:
            # Download PDF
            logger.info(f"Downloading PDF: {pdf_url}")
            pdf_content = await self._download_pdf(pdf_url)
            
            if not pdf_content:
                logger.error(f"Failed to download PDF: {pdf_url}")
                return None
            
            # Extract text from PDF
            text_content = self._extract_text_from_pdf(pdf_content)
            
            # If text extraction fails or yields poor results, try OCR
            if not text_content or len(text_content.strip()) < 100:
                logger.info("Text extraction yielded poor results, trying OCR")
                text_content = await self._extract_text_with_ocr(pdf_content)
            
            if not text_content:
                logger.error("Failed to extract text from PDF")
                return None
            
            # Parse voting data from text
            voting_session = self._parse_voting_data(text_content, pdf_url)
            
            if voting_session and member_names:
                # Improve member name matching with known names
                self._improve_member_matching(voting_session, member_names)
            
            return voting_session
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_url}: {e}")
            return None
    
    async def _download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """Download PDF content from URL"""
        try:
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Verify it's actually a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower():
                # Check if content starts with PDF header
                if not response.content.startswith(b'%PDF'):
                    logger.warning(f"Content doesn't appear to be PDF: {pdf_url}")
                    return None
            
            logger.info(f"Downloaded PDF: {len(response.content)} bytes")
            return response.content
            
        except requests.RequestException as e:
            logger.error(f"Failed to download PDF {pdf_url}: {e}")
            return None
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        """Extract text from PDF using PyMuPDF"""
        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF not available, cannot extract PDF text")
            return None
            
        try:
            # Open PDF from bytes
            pdf_document = fitz.open("pdf", pdf_content)
            
            extracted_text = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text = page.get_text()
                
                if text.strip():
                    extracted_text.append(text)
                    logger.debug(f"Extracted {len(text)} characters from page {page_num + 1}")
            
            pdf_document.close()
            
            full_text = "\n".join(extracted_text)
            logger.info(f"Total text extracted: {len(full_text)} characters")
            
            return full_text if full_text.strip() else None
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return None
    
    async def _extract_text_with_ocr(self, pdf_content: bytes) -> Optional[str]:
        """Extract text using OCR as fallback"""
        if not PYMUPDF_AVAILABLE or not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
            logger.error("Required OCR dependencies not available")
            return None
            
        try:
            # Convert PDF to images
            pdf_document = fitz.open("pdf", pdf_content)
            extracted_text = []
            
            for page_num in range(min(10, len(pdf_document))):  # Limit to first 10 pages
                page = pdf_document[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
                img_data = pix.tobytes("png")
                
                # Process with OCR
                try:
                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Pre-process image for better OCR
                    processed_image = self._preprocess_image_for_ocr(image)
                    
                    # Run OCR with Japanese language support
                    text = pytesseract.image_to_string(
                        processed_image,
                        lang='jpn+eng',  # Japanese + English
                        config='--psm 6'  # Uniform block of text
                    )
                    
                    if text.strip():
                        extracted_text.append(text)
                        logger.debug(f"OCR extracted {len(text)} characters from page {page_num + 1}")
                    
                except Exception as ocr_e:
                    logger.warning(f"OCR failed for page {page_num + 1}: {ocr_e}")
                    continue
            
            pdf_document.close()
            
            full_text = "\n".join(extracted_text)
            logger.info(f"Total OCR text extracted: {len(full_text)} characters")
            
            return full_text if full_text.strip() else None
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None
    
    def _preprocess_image_for_ocr(self, image: Any) -> Any:
        """Preprocess image to improve OCR accuracy"""
        if not OPENCV_AVAILABLE or not np:
            logger.warning("OpenCV not available, returning original image")
            return image
            
        try:
            # Convert PIL to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(thresh)
            
            return processed_image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image  # Return original if preprocessing fails
    
    def _parse_voting_data(self, text_content: str, pdf_url: str) -> Optional[PDFVotingSession]:
        """Parse voting data from extracted text"""
        try:
            # Extract basic metadata
            bill_info = self._extract_bill_information(text_content)
            if not bill_info:
                logger.error("Failed to extract bill information from PDF")
                return None
            
            # Extract individual vote records
            vote_records = self._extract_vote_records(text_content)
            if not vote_records:
                logger.error("Failed to extract vote records from PDF")
                return None
            
            # Create session object
            session = PDFVotingSession(
                session_id=f"hr_{bill_info['bill_number']}_{bill_info['vote_date'].strftime('%Y%m%d')}",
                bill_number=bill_info['bill_number'],
                bill_title=bill_info['bill_title'],
                vote_date=bill_info['vote_date'],
                vote_type=bill_info.get('vote_type', '本会議'),
                committee_name=bill_info.get('committee_name'),
                pdf_url=pdf_url,
                total_members=len(vote_records),
                vote_records=vote_records
            )
            
            logger.info(f"Parsed voting session: {session.bill_number} with {len(vote_records)} votes")
            return session
            
        except Exception as e:
            logger.error(f"Failed to parse voting data: {e}")
            return None
    
    def _extract_bill_information(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract bill metadata from text"""
        try:
            info = {}
            
            # Extract bill number (common patterns)
            bill_patterns = [
                r'(?:法律案|決議案|予算案)\s*第(\d+)号',
                r'議案第(\d+)号',
                r'第(\d+)号\s*(?:法律案|決議案)',
            ]
            
            for pattern in bill_patterns:
                match = re.search(pattern, text)
                if match:
                    info['bill_number'] = f"第{match.group(1)}号"
                    break
            
            if 'bill_number' not in info:
                # Fallback: look for any number pattern
                match = re.search(r'第(\d+)号', text)
                if match:
                    info['bill_number'] = f"第{match.group(1)}号"
                else:
                    info['bill_number'] = "不明"
            
            # Extract bill title (first significant line after bill number)
            title_patterns = [
                r'(?:法律案|決議案|予算案).*?第\d+号\s*(.+?)(?:\n|採決|表決)',
                r'(.+?)に関する(?:法律案|決議案)',
                r'(.+?)について',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    title = match.group(1).strip()
                    if len(title) > 5 and len(title) < 100:  # Reasonable title length
                        info['bill_title'] = title
                        break
            
            if 'bill_title' not in info:
                info['bill_title'] = "タイトル不明"
            
            # Extract date
            date_patterns = [
                r'令和(\d+)年(\d+)月(\d+)日',
                r'平成(\d+)年(\d+)月(\d+)日',
                r'(\d{4})年(\d+)月(\d+)日',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    if pattern.startswith('令和'):
                        year = int(match.group(1)) + 2018  # Convert Reiwa to Western year
                    elif pattern.startswith('平成'):
                        year = int(match.group(1)) + 1988  # Convert Heisei to Western year
                    else:
                        year = int(match.group(1))
                    
                    month = int(match.group(2))
                    day = int(match.group(3))
                    
                    info['vote_date'] = datetime(year, month, day)
                    break
            
            if 'vote_date' not in info:
                info['vote_date'] = datetime.now()  # Fallback to current date
            
            # Extract vote type and committee
            if '委員会' in text:
                info['vote_type'] = '委員会'
                committee_match = re.search(r'(.{2,10}委員会)', text)
                if committee_match:
                    info['committee_name'] = committee_match.group(1)
            else:
                info['vote_type'] = '本会議'
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to extract bill information: {e}")
            return None
    
    def _extract_vote_records(self, text: str) -> List[PDFVoteRecord]:
        """Extract individual vote records from text"""
        vote_records = []
        
        try:
            # Common vote patterns
            vote_patterns = [
                # Pattern: Name + Party + Constituency + Vote
                r'([^\n]{2,15})\s+([^\n]{2,20})\s+([^\n]{2,20})\s+(賛成|反対|欠席|棄権)',
                # Pattern: Name (Party/Constituency) Vote
                r'([^\n]{2,15})\s*\(([^)]+)\)\s+(賛成|反対|欠席|棄権)',
                # Pattern: More flexible matching
                r'([^\n]{2,15})\s+([^\n]+?)\s+(賛成|反対|欠席|棄権)',
            ]
            
            for pattern in vote_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                
                for match in matches:
                    try:
                        if len(match) == 4:  # Name, Party, Constituency, Vote
                            name, party, constituency, vote = match
                        elif len(match) == 3:  # Name, Party/Constituency, Vote
                            name, party_constituency, vote = match
                            # Try to split party and constituency
                            if '/' in party_constituency:
                                party, constituency = party_constituency.split('/', 1)
                            else:
                                party = party_constituency
                                constituency = "不明"
                        else:
                            continue
                        
                        # Clean up extracted data
                        name = name.strip()
                        party = party.strip()
                        constituency = constituency.strip() if 'constituency' in locals() else "不明"
                        vote = vote.strip()
                        
                        # Validate extracted data
                        if (len(name) >= 2 and len(name) <= 15 and 
                            vote in ['賛成', '反対', '欠席', '棄権']):
                            
                            record = PDFVoteRecord(
                                member_name=name,
                                member_name_kana=None,  # Not available in PDFs usually
                                party_name=party,
                                constituency=constituency,
                                vote_result=vote,
                                confidence_score=0.8  # Medium confidence for PDF extraction
                            )
                            vote_records.append(record)
                    
                    except Exception as record_e:
                        logger.debug(f"Failed to parse vote record: {match} - {record_e}")
                        continue
                
                # If we found records with this pattern, use them
                if vote_records:
                    break
            
            # Remove duplicates based on member name
            seen_names = set()
            unique_records = []
            for record in vote_records:
                if record.member_name not in seen_names:
                    seen_names.add(record.member_name)
                    unique_records.append(record)
            
            logger.info(f"Extracted {len(unique_records)} unique vote records")
            return unique_records
            
        except Exception as e:
            logger.error(f"Failed to extract vote records: {e}")
            return []
    
    def _improve_member_matching(
        self, 
        session: PDFVotingSession, 
        known_member_names: List[str]
    ) -> None:
        """Improve member name matching using known member list"""
        try:
            improved_records = []
            
            for record in session.vote_records:
                # Try to find better match for member name
                matched_name, confidence = self.name_matcher.find_best_match(
                    record.member_name, 
                    known_member_names
                )
                
                if matched_name and confidence > record.confidence_score:
                    # Update with better match
                    record.member_name = matched_name
                    record.confidence_score = confidence
                    logger.debug(f"Improved name match: {record.member_name} (confidence: {confidence:.2f})")
                
                improved_records.append(record)
            
            session.vote_records = improved_records
            
        except Exception as e:
            logger.error(f"Failed to improve member matching: {e}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get PDF processing statistics"""
        # This would be expanded to track actual statistics
        return {
            "total_pdfs_processed": 0,
            "successful_extractions": 0,
            "ocr_fallbacks": 0,
            "failed_extractions": 0,
            "average_confidence_score": 0.0
        }