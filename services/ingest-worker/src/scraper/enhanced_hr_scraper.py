"""
Enhanced House of Representatives PDF Processing System

This module extends the basic HR scraping functionality with:
- Advanced PDF discovery and classification
- Intelligent content extraction with multiple fallback strategies
- Comprehensive error handling and recovery mechanisms
- Detailed metadata extraction and validation
- Performance monitoring and optimization
- Integration with the existing data pipeline
"""

import asyncio
import json
import logging
import re
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

import aiohttp
import requests
from bs4 import BeautifulSoup

from .hr_voting_scraper import HouseOfRepresentativesVotingScraper
from .pdf_processor import PDFProcessor, PDFVotingSession, PDFVoteRecord
from .resilience import ResilientScraper, RateLimitConfig, CacheConfig


logger = logging.getLogger(__name__)


@dataclass
class EnhancedVotingSession:
    """Enhanced voting session with additional metadata"""
    base_session: PDFVotingSession
    pdf_metadata: Dict[str, Any]
    processing_metadata: Dict[str, Any]
    quality_metrics: Dict[str, float]
    
    @property
    def session_id(self) -> str:
        return self.base_session.session_id
    
    @property
    def vote_records(self) -> List[PDFVoteRecord]:
        return self.base_session.vote_records
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'session_id': self.base_session.session_id,
            'bill_number': self.base_session.bill_number,
            'bill_title': self.base_session.bill_title,
            'vote_date': self.base_session.vote_date.isoformat(),
            'vote_type': self.base_session.vote_type,
            'committee_name': self.base_session.committee_name,
            'pdf_url': self.base_session.pdf_url,
            'total_members': self.base_session.total_members,
            'vote_summary': self.base_session.vote_summary,
            'vote_records': [asdict(record) for record in self.base_session.vote_records],
            'pdf_metadata': self.pdf_metadata,
            'processing_metadata': self.processing_metadata,
            'quality_metrics': self.quality_metrics
        }


@dataclass
class PDFProcessingResult:
    """Result of PDF processing operation"""
    success: bool
    session: Optional[EnhancedVotingSession]
    error_message: Optional[str]
    processing_time: float
    extraction_method: str  # 'text', 'ocr', 'hybrid'
    confidence_score: float


class EnhancedHRProcessor:
    """Enhanced House of Representatives PDF processor with advanced features"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_scraper = HouseOfRepresentativesVotingScraper(enable_resilience=True)
        self.pdf_processor = PDFProcessor()
        
        # Processing statistics
        self.stats = {
            'total_pdfs_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'ocr_fallbacks': 0,
            'processing_times': [],
            'quality_scores': []
        }
        
        # PDF classification patterns
        self.pdf_patterns = {
            'roll_call_vote': [
                r'記名投票',
                r'採決結果',
                r'表決結果',
                r'投票結果'
            ],
            'committee_vote': [
                r'委員会.*採決',
                r'委員会.*表決',
                r'小委員会.*投票'
            ],
            'plenary_vote': [
                r'本会議.*採決',
                r'本会議.*表決',
                r'全体会議.*投票'
            ]
        }
        
        # Quality assessment criteria
        self.quality_thresholds = {
            'min_member_count': 50,  # Minimum expected members in a vote
            'min_text_length': 200,  # Minimum text length for valid extraction
            'min_confidence_score': 0.6,  # Minimum OCR confidence
            'max_missing_data_ratio': 0.2  # Maximum ratio of missing member data
        }
    
    async def process_enhanced_hr_data(
        self,
        days_back: int = 30,
        session_numbers: Optional[List[int]] = None,
        max_concurrent: int = 3
    ) -> List[EnhancedVotingSession]:
        """
        Process House of Representatives voting data with enhanced features
        
        Args:
            days_back: Number of days to look back
            session_numbers: Specific Diet session numbers to process
            max_concurrent: Maximum concurrent PDF processing operations
            
        Returns:
            List of enhanced voting sessions
        """
        logger.info(f"Starting enhanced HR processing (days_back={days_back})")
        
        try:
            # Phase 1: Discovery and classification
            pdf_metadata = await self._discover_and_classify_pdfs(days_back, session_numbers)
            
            if not pdf_metadata:
                logger.warning("No HR voting PDFs found for processing")
                return []
            
            logger.info(f"Discovered {len(pdf_metadata)} PDFs for processing")
            
            # Phase 2: Prioritize PDFs based on classification and importance
            prioritized_pdfs = self._prioritize_pdfs(pdf_metadata)
            
            # Phase 3: Process PDFs with enhanced extraction
            enhanced_sessions = await self._process_pdfs_enhanced(
                prioritized_pdfs, 
                max_concurrent
            )
            
            # Phase 4: Quality assessment and filtering
            validated_sessions = self._validate_and_filter_sessions(enhanced_sessions)
            
            # Phase 5: Update statistics
            self._update_processing_statistics(enhanced_sessions)
            
            logger.info(f"Enhanced HR processing completed: {len(validated_sessions)} valid sessions")
            return validated_sessions
            
        except Exception as e:
            logger.error(f"Enhanced HR processing failed: {e}")
            return []
    
    async def _discover_and_classify_pdfs(
        self,
        days_back: int,
        session_numbers: Optional[List[int]]
    ) -> List[Dict[str, Any]]:
        """Discover and classify HR voting PDFs"""
        pdf_metadata = []
        
        try:
            # Use base scraper to discover PDF URLs
            discovered_urls = await self.base_scraper._discover_voting_pdf_urls(
                days_back, 
                session_numbers
            )
            
            # Classify each PDF and extract metadata
            for pdf_url in discovered_urls:
                try:
                    metadata = await self._extract_pdf_metadata(pdf_url)
                    if metadata:
                        pdf_metadata.append(metadata)
                        
                except Exception as e:
                    logger.warning(f"Failed to classify PDF {pdf_url}: {e}")
                    continue
            
            return pdf_metadata
            
        except Exception as e:
            logger.error(f"PDF discovery and classification failed: {e}")
            return []
    
    async def _extract_pdf_metadata(self, pdf_url: str) -> Optional[Dict[str, Any]]:
        """Extract metadata about a PDF without full processing"""
        try:
            # Basic URL analysis
            url_parts = urlparse(pdf_url)
            filename = Path(url_parts.path).name
            
            # Extract date from URL or filename
            date_patterns = [
                r'(\d{4})(\d{2})(\d{2})',
                r'(\d{4})-(\d{2})-(\d{2})',
                r'令和(\d+)年(\d+)月(\d+)日'
            ]
            
            extracted_date = None
            for pattern in date_patterns:
                match = re.search(pattern, pdf_url + filename)
                if match:
                    try:
                        if pattern.startswith('令和'):
                            year = int(match.group(1)) + 2018
                            month = int(match.group(2))
                            day = int(match.group(3))
                        else:
                            year = int(match.group(1))
                            month = int(match.group(2))
                            day = int(match.group(3))
                        
                        extracted_date = datetime(year, month, day)
                        break
                    except ValueError:
                        continue
            
            # Classify PDF type
            pdf_type = self._classify_pdf_type(pdf_url + filename)
            
            # Estimate importance/priority
            priority = self._calculate_pdf_priority(pdf_url, pdf_type, extracted_date)
            
            return {
                'url': pdf_url,
                'filename': filename,
                'estimated_date': extracted_date,
                'pdf_type': pdf_type,
                'priority': priority,
                'size_estimate': None,  # Will be filled during download
                'processing_attempts': 0
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata for {pdf_url}: {e}")
            return None
    
    def _classify_pdf_type(self, text: str) -> str:
        """Classify PDF type based on URL and filename patterns"""
        text_lower = text.lower()
        
        for pdf_type, patterns in self.pdf_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return pdf_type
        
        return 'unknown'
    
    def _calculate_pdf_priority(
        self, 
        pdf_url: str, 
        pdf_type: str, 
        estimated_date: Optional[datetime]
    ) -> int:
        """Calculate processing priority for PDF (higher = more important)"""
        priority = 0
        
        # Recent PDFs get higher priority
        if estimated_date:
            days_old = (datetime.now() - estimated_date).days
            if days_old <= 7:
                priority += 10
            elif days_old <= 30:
                priority += 5
        
        # PDF type priorities
        type_priorities = {
            'roll_call_vote': 10,
            'plenary_vote': 8,
            'committee_vote': 6,
            'unknown': 1
        }
        priority += type_priorities.get(pdf_type, 0)
        
        # URL patterns that suggest importance
        important_keywords = ['重要', '予算', '法案', '決議']
        for keyword in important_keywords:
            if keyword in pdf_url:
                priority += 3
        
        return priority
    
    def _prioritize_pdfs(self, pdf_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort PDFs by priority for processing"""
        return sorted(pdf_metadata, key=lambda x: x['priority'], reverse=True)
    
    async def _process_pdfs_enhanced(
        self,
        pdf_metadata: List[Dict[str, Any]],
        max_concurrent: int
    ) -> List[PDFProcessingResult]:
        """Process PDFs with enhanced extraction and error handling"""
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_pdf(metadata: Dict[str, Any]) -> PDFProcessingResult:
            async with semaphore:
                return await self._process_pdf_with_fallbacks(metadata)
        
        # Process all PDFs concurrently
        processing_results = await asyncio.gather(
            *[process_single_pdf(metadata) for metadata in pdf_metadata],
            return_exceptions=True
        )
        
        # Collect results
        for result in processing_results:
            if isinstance(result, PDFProcessingResult):
                results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"PDF processing exception: {result}")
        
        return results
    
    async def _process_pdf_with_fallbacks(
        self, 
        metadata: Dict[str, Any]
    ) -> PDFProcessingResult:
        """Process single PDF with multiple fallback strategies"""
        
        pdf_url = metadata['url']
        start_time = time.time()
        
        try:
            # Strategy 1: Standard text extraction
            logger.info(f"Processing PDF (text extraction): {pdf_url}")
            
            session = await self.pdf_processor.extract_voting_data_from_pdf(
                pdf_url,
                await self.base_scraper._get_member_names()
            )
            
            if session and self._assess_extraction_quality(session):
                processing_time = time.time() - start_time
                enhanced_session = self._create_enhanced_session(
                    session, metadata, 'text', processing_time
                )
                
                return PDFProcessingResult(
                    success=True,
                    session=enhanced_session,
                    error_message=None,
                    processing_time=processing_time,
                    extraction_method='text',
                    confidence_score=0.9
                )
            
            # Strategy 2: OCR with preprocessing
            logger.info(f"Text extraction failed, trying OCR: {pdf_url}")
            
            session = await self._extract_with_enhanced_ocr(pdf_url)
            
            if session and self._assess_extraction_quality(session):
                processing_time = time.time() - start_time
                enhanced_session = self._create_enhanced_session(
                    session, metadata, 'ocr', processing_time
                )
                
                return PDFProcessingResult(
                    success=True,
                    session=enhanced_session,
                    error_message=None,
                    processing_time=processing_time,
                    extraction_method='ocr',
                    confidence_score=0.7
                )
            
            # Strategy 3: Hybrid approach with manual patterns
            logger.info(f"OCR failed, trying hybrid approach: {pdf_url}")
            
            session = await self._extract_with_hybrid_approach(pdf_url, metadata)
            
            if session:
                processing_time = time.time() - start_time
                enhanced_session = self._create_enhanced_session(
                    session, metadata, 'hybrid', processing_time
                )
                
                return PDFProcessingResult(
                    success=True,
                    session=enhanced_session,
                    error_message=None,
                    processing_time=processing_time,
                    extraction_method='hybrid',
                    confidence_score=0.5
                )
            
            # All strategies failed
            processing_time = time.time() - start_time
            return PDFProcessingResult(
                success=False,
                session=None,
                error_message="All extraction strategies failed",
                processing_time=processing_time,
                extraction_method='none',
                confidence_score=0.0
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"PDF processing failed completely for {pdf_url}: {e}")
            
            return PDFProcessingResult(
                success=False,
                session=None,
                error_message=str(e),
                processing_time=processing_time,
                extraction_method='error',
                confidence_score=0.0
            )
    
    async def _extract_with_enhanced_ocr(self, pdf_url: str) -> Optional[PDFVotingSession]:
        """Enhanced OCR extraction with better preprocessing"""
        # This would implement enhanced OCR with:
        # - Better image preprocessing
        # - Multiple OCR engines (Tesseract + alternatives)
        # - Post-processing text correction
        # - Japanese language model optimization
        
        # For now, use the existing OCR functionality
        return await self.pdf_processor.extract_voting_data_from_pdf(pdf_url)
    
    async def _extract_with_hybrid_approach(
        self, 
        pdf_url: str, 
        metadata: Dict[str, Any]
    ) -> Optional[PDFVotingSession]:
        """Hybrid extraction using pattern matching and heuristics"""
        
        try:
            # This would implement:
            # 1. Pattern-based extraction for known PDF formats
            # 2. Heuristic rules for member name detection
            # 3. Vote result inference from partial data
            # 4. Cross-validation with existing member lists
            
            # Placeholder implementation
            logger.warning(f"Hybrid extraction not fully implemented for {pdf_url}")
            return None
            
        except Exception as e:
            logger.error(f"Hybrid extraction failed: {e}")
            return None
    
    def _assess_extraction_quality(self, session: PDFVotingSession) -> bool:
        """Assess the quality of extracted voting data"""
        
        try:
            # Check minimum member count
            if len(session.vote_records) < self.quality_thresholds['min_member_count']:
                logger.warning(f"Low member count: {len(session.vote_records)}")
                return False
            
            # Check for reasonable vote distribution
            vote_summary = session.vote_summary
            total_votes = sum(vote_summary.values())
            
            if total_votes == 0:
                return False
            
            # Check that we have actual votes, not just absences
            actual_votes = vote_summary.get('賛成', 0) + vote_summary.get('反対', 0)
            if actual_votes < total_votes * 0.5:  # At least 50% should be actual votes
                logger.warning("Too many non-votes (absences/abstentions)")
                return False
            
            # Check for data completeness
            missing_data_count = 0
            for record in session.vote_records:
                if not record.member_name or not record.party_name:
                    missing_data_count += 1
            
            missing_ratio = missing_data_count / len(session.vote_records)
            if missing_ratio > self.quality_thresholds['max_missing_data_ratio']:
                logger.warning(f"Too much missing data: {missing_ratio:.2%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return False
    
    def _create_enhanced_session(
        self,
        base_session: PDFVotingSession,
        pdf_metadata: Dict[str, Any],
        extraction_method: str,
        processing_time: float
    ) -> EnhancedVotingSession:
        """Create enhanced session with additional metadata"""
        
        # Calculate quality metrics
        quality_metrics = {
            'completeness_score': self._calculate_completeness_score(base_session),
            'confidence_score': self._calculate_confidence_score(base_session),
            'consistency_score': self._calculate_consistency_score(base_session)
        }
        
        # Processing metadata
        processing_metadata = {
            'extraction_method': extraction_method,
            'processing_time': processing_time,
            'processed_at': datetime.now().isoformat(),
            'pdf_type': pdf_metadata.get('pdf_type', 'unknown'),
            'priority': pdf_metadata.get('priority', 0)
        }
        
        return EnhancedVotingSession(
            base_session=base_session,
            pdf_metadata=pdf_metadata,
            processing_metadata=processing_metadata,
            quality_metrics=quality_metrics
        )
    
    def _calculate_completeness_score(self, session: PDFVotingSession) -> float:
        """Calculate data completeness score (0.0 - 1.0)"""
        try:
            total_fields = len(session.vote_records) * 4  # name, party, constituency, vote
            complete_fields = 0
            
            for record in session.vote_records:
                if record.member_name and len(record.member_name.strip()) > 0:
                    complete_fields += 1
                if record.party_name and len(record.party_name.strip()) > 0:
                    complete_fields += 1
                if record.constituency and len(record.constituency.strip()) > 0:
                    complete_fields += 1
                if record.vote_result and record.vote_result in ['賛成', '反対', '欠席', '棄権']:
                    complete_fields += 1
            
            return complete_fields / total_fields if total_fields > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_confidence_score(self, session: PDFVotingSession) -> float:
        """Calculate overall confidence score"""
        try:
            if not session.vote_records:
                return 0.0
            
            total_confidence = sum(record.confidence_score for record in session.vote_records)
            return total_confidence / len(session.vote_records)
            
        except Exception:
            return 0.0
    
    def _calculate_consistency_score(self, session: PDFVotingSession) -> float:
        """Calculate data consistency score"""
        try:
            # Check for duplicate members
            member_names = [record.member_name for record in session.vote_records]
            unique_members = set(member_names)
            
            if len(member_names) == 0:
                return 0.0
            
            uniqueness_ratio = len(unique_members) / len(member_names)
            
            # Check for reasonable party distribution
            parties = [record.party_name for record in session.vote_records if record.party_name]
            unique_parties = set(parties)
            
            # Expect at least 2 parties in a normal vote
            party_diversity = min(len(unique_parties) / 5, 1.0)  # Normalize to max 5 parties
            
            return (uniqueness_ratio + party_diversity) / 2
            
        except Exception:
            return 0.0
    
    def _validate_and_filter_sessions(
        self, 
        results: List[PDFProcessingResult]
    ) -> List[EnhancedVotingSession]:
        """Validate and filter processing results"""
        
        valid_sessions = []
        
        for result in results:
            if not result.success or not result.session:
                continue
            
            # Apply quality thresholds
            session = result.session
            
            if (session.quality_metrics['completeness_score'] >= 0.7 and
                session.quality_metrics['confidence_score'] >= 0.5 and
                session.quality_metrics['consistency_score'] >= 0.5):
                
                valid_sessions.append(session)
                logger.info(f"Validated session: {session.session_id}")
            else:
                logger.warning(f"Session failed validation: {session.session_id}")
        
        return valid_sessions
    
    def _update_processing_statistics(self, results: List[PDFProcessingResult]) -> None:
        """Update processing statistics"""
        
        for result in results:
            self.stats['total_pdfs_processed'] += 1
            
            if result.success:
                self.stats['successful_extractions'] += 1
            else:
                self.stats['failed_extractions'] += 1
            
            if result.extraction_method == 'ocr':
                self.stats['ocr_fallbacks'] += 1
            
            self.stats['processing_times'].append(result.processing_time)
            
            if result.session:
                overall_quality = (
                    result.session.quality_metrics['completeness_score'] +
                    result.session.quality_metrics['confidence_score'] +
                    result.session.quality_metrics['consistency_score']
                ) / 3
                self.stats['quality_scores'].append(overall_quality)
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        
        stats = dict(self.stats)
        
        if self.stats['processing_times']:
            stats['avg_processing_time'] = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
            stats['max_processing_time'] = max(self.stats['processing_times'])
            stats['min_processing_time'] = min(self.stats['processing_times'])
        
        if self.stats['quality_scores']:
            stats['avg_quality_score'] = sum(self.stats['quality_scores']) / len(self.stats['quality_scores'])
            stats['max_quality_score'] = max(self.stats['quality_scores'])
            stats['min_quality_score'] = min(self.stats['quality_scores'])
        
        if self.stats['total_pdfs_processed'] > 0:
            stats['success_rate'] = self.stats['successful_extractions'] / self.stats['total_pdfs_processed']
            stats['ocr_fallback_rate'] = self.stats['ocr_fallbacks'] / self.stats['total_pdfs_processed']
        
        return stats
    
    async def save_processing_results(
        self, 
        sessions: List[EnhancedVotingSession],
        output_path: str
    ) -> bool:
        """Save processing results to JSON file"""
        
        try:
            output_data = {
                'metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'total_sessions': len(sessions),
                    'processing_statistics': self.get_processing_statistics()
                },
                'sessions': [session.to_dict() for session in sessions]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(sessions)} sessions to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return False