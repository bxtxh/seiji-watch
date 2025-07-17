"""
Historical Data Batch Processing for NDL API

Ingests all 第217回国会 meetings via NDL API with progress tracking,
resume capability, and comprehensive data validation.

Target Period: 2025-01-24 〜 2025-06-21 (第217回国会)
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pickle

from shared.src.shared.clients.airtable import AirtableClient
from ..collectors.ndl_api_client import NDLAPIClient, NDLMeeting, NDLSpeech
from ..pipeline.ndl_data_mapper import NDLDataMapper, MappingResult


@dataclass
class BatchProgress:
    """Progress tracking for batch ingestion"""
    session_number: int
    start_date: date
    end_date: date
    total_meetings: int = 0
    processed_meetings: int = 0
    total_speeches: int = 0
    processed_speeches: int = 0
    failed_meetings: List[str] = None
    last_processed_date: Optional[date] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.failed_meetings is None:
            self.failed_meetings = []
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_meetings == 0:
            return 0.0
        return (self.processed_meetings / self.total_meetings) * 100
    
    @property
    def is_completed(self) -> bool:
        """Check if batch processing is completed"""
        return self.processed_meetings == self.total_meetings and self.completed_at is not None


@dataclass
class BatchStatistics:
    """Statistics for batch processing results"""
    total_meetings_found: int = 0
    total_meetings_processed: int = 0
    total_speeches_processed: int = 0
    unique_members_found: int = 0
    unique_parties_found: int = 0
    processing_errors: int = 0
    mapping_warnings: int = 0
    average_speeches_per_meeting: float = 0.0
    processing_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HistoricalDataIngester:
    """
    Batch processor for historical Diet meeting data from NDL API
    
    Features:
    - Progress tracking with resume capability
    - Rate limiting and error handling
    - Data validation and quality checks
    - Cost tracking and performance monitoring
    """
    
    # 第217回国会期間
    SESSION_217_START = date(2025, 1, 24)
    SESSION_217_END = date(2025, 6, 21)
    SESSION_NUMBER = 217
    
    def __init__(self, 
                 progress_file: str = "batch_progress.pkl",
                 output_dir: str = "batch_output",
                 batch_size: int = 50):
        self.logger = logging.getLogger(__name__)
        self.progress_file = Path(progress_file)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        
        # Initialize components
        self.ndl_client: Optional[NDLAPIClient] = None
        self.airtable_client: Optional[AirtableClient] = None
        self.data_mapper = NDLDataMapper()
        
        # Progress tracking
        self.progress: Optional[BatchProgress] = None
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Historical ingester initialized - Target: 第{self.SESSION_NUMBER}回国会")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.ndl_client = NDLAPIClient()
        await self.ndl_client.__aenter__()
        
        self.airtable_client = AirtableClient()
        await self.airtable_client.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.ndl_client:
            await self.ndl_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.airtable_client:
            await self.airtable_client.__aexit__(exc_type, exc_val, exc_tb)
    
    def load_progress(self) -> BatchProgress:
        """Load existing progress or create new"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'rb') as f:
                    progress = pickle.load(f)
                self.logger.info(f"Loaded existing progress: {progress.completion_percentage:.1f}% complete")
                return progress
            except Exception as e:
                self.logger.warning(f"Failed to load progress file: {e}")
        
        # Create new progress
        progress = BatchProgress(
            session_number=self.SESSION_NUMBER,
            start_date=self.SESSION_217_START,
            end_date=self.SESSION_217_END,
            started_at=datetime.now()
        )
        self.save_progress(progress)
        return progress
    
    def save_progress(self, progress: BatchProgress):
        """Save current progress"""
        try:
            with open(self.progress_file, 'wb') as f:
                pickle.dump(progress, f)
            self.logger.debug("Progress saved")
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
    
    async def discover_meetings(self) -> List[NDLMeeting]:
        """
        Discover all meetings in the target session
        
        Returns:
            List of NDL meetings to process
        """
        self.logger.info(f"Discovering meetings for 第{self.SESSION_NUMBER}回国会...")
        
        all_meetings = []
        start_record = 1
        batch_size = 100
        
        while True:
            meetings = await self.ndl_client.search_meetings(
                start_date=self.SESSION_217_START,
                end_date=self.SESSION_217_END,
                diet_session=self.SESSION_NUMBER,
                start_record=start_record,
                max_records=batch_size
            )
            
            if not meetings:
                break
            
            all_meetings.extend(meetings)
            self.logger.info(f"Found {len(meetings)} meetings (total: {len(all_meetings)})")
            
            if len(meetings) < batch_size:
                break
            
            start_record += batch_size
        
        # Sort by date for consistent processing order
        all_meetings.sort(key=lambda m: m.meeting_date or date.min)
        
        self.logger.info(f"Discovery complete: {len(all_meetings)} meetings found")
        return all_meetings
    
    async def process_meeting(self, meeting: NDLMeeting) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a single meeting and its speeches
        
        Args:
            meeting: NDL meeting to process
            
        Returns:
            Tuple of (success, processing_stats)
        """
        stats = {
            "meeting_id": meeting.meeting_id,
            "title": meeting.title,
            "date": meeting.meeting_date.isoformat() if meeting.meeting_date else None,
            "speeches_count": 0,
            "members_count": 0,
            "parties_count": 0,
            "warnings": [],
            "errors": []
        }
        
        try:
            # 1. Map meeting to Airtable format
            meeting_result = self.data_mapper.map_ndl_meeting_to_airtable(meeting)
            if not meeting_result.success:
                stats["errors"].extend(meeting_result.errors)
                return False, stats
            
            # 2. Check if meeting already exists
            existing_meeting = await self._find_existing_meeting(meeting.meeting_id)
            if existing_meeting:
                self.logger.info(f"Meeting {meeting.meeting_id} already exists, skipping")
                return True, stats
            
            # 3. Create meeting record
            meeting_record_id = await self.airtable_client.create_meeting(meeting_result.mapped_data)
            self.logger.info(f"Created meeting record: {meeting_record_id}")
            
            # 4. Get all speeches for the meeting
            speeches = await self.ndl_client.get_all_speeches_for_meeting(meeting.meeting_id)
            stats["speeches_count"] = len(speeches)
            
            if not speeches:
                self.logger.warning(f"No speeches found for meeting {meeting.meeting_id}")
                return True, stats
            
            # 5. Map speeches in batches
            batch_result = self.data_mapper.batch_map_speeches(speeches, meeting_record_id)
            stats["members_count"] = batch_result["statistics"]["unique_members"]
            stats["parties_count"] = batch_result["statistics"]["unique_parties"]
            stats["warnings"].extend(batch_result["warnings"])
            stats["errors"].extend(batch_result["errors"])
            
            # 6. Process speeches in smaller batches to avoid rate limits
            mapped_speeches = batch_result["speeches"]
            for i in range(0, len(mapped_speeches), self.batch_size):
                batch = mapped_speeches[i:i + self.batch_size]
                
                for speech in batch:
                    try:
                        await self.airtable_client.create_speech(speech)
                    except Exception as e:
                        error_msg = f"Failed to create speech: {str(e)}"
                        stats["errors"].append(error_msg)
                        self.logger.error(error_msg)
                
                # Rate limiting between batches
                await asyncio.sleep(0.2)
            
            # 7. Process unique members and parties
            await self._process_members_and_parties(
                batch_result["members"],
                batch_result["parties"]
            )
            
            self.logger.info(f"✅ Processed meeting {meeting.meeting_id}: {len(mapped_speeches)} speeches")
            return True, stats
            
        except Exception as e:
            error_msg = f"Failed to process meeting {meeting.meeting_id}: {str(e)}"
            stats["errors"].append(error_msg)
            self.logger.error(error_msg)
            return False, stats
    
    async def _find_existing_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Check if meeting already exists in Airtable"""
        try:
            # Search for existing meeting by meeting_id
            meetings = await self.airtable_client.search_meetings(
                filter_formula=f"{{meeting_id}} = '{meeting_id}'"
            )
            return meetings[0] if meetings else None
        except Exception as e:
            self.logger.warning(f"Failed to check existing meeting: {e}")
            return None
    
    async def _process_members_and_parties(self, members: List[Dict], parties: List[Dict]):
        """Process unique members and parties"""
        # Process parties first (members reference parties)
        for party_data in parties:
            try:
                existing_party = await self._find_existing_party(party_data["name"])
                if not existing_party:
                    await self.airtable_client.create_party(party_data)
                    self.logger.debug(f"Created party: {party_data['name']}")
            except Exception as e:
                self.logger.warning(f"Failed to process party {party_data['name']}: {e}")
        
        # Process members
        for member_data in members:
            try:
                existing_member = await self._find_existing_member(member_data["name"])
                if not existing_member:
                    await self.airtable_client.create_member(member_data)
                    self.logger.debug(f"Created member: {member_data['name']}")
            except Exception as e:
                self.logger.warning(f"Failed to process member {member_data['name']}: {e}")
    
    async def _find_existing_party(self, party_name: str) -> Optional[Dict[str, Any]]:
        """Check if party already exists"""
        try:
            parties = await self.airtable_client.search_parties(
                filter_formula=f"{{name}} = '{party_name}'"
            )
            return parties[0] if parties else None
        except Exception:
            return None
    
    async def _find_existing_member(self, member_name: str) -> Optional[Dict[str, Any]]:
        """Check if member already exists"""
        try:
            members = await self.airtable_client.search_members(
                filter_formula=f"{{name}} = '{member_name}'"
            )
            return members[0] if members else None
        except Exception:
            return None
    
    async def run_batch_ingestion(self, resume: bool = True) -> BatchStatistics:
        """
        Run the complete batch ingestion process
        
        Args:
            resume: Whether to resume from existing progress
            
        Returns:
            BatchStatistics with processing results
        """
        start_time = datetime.now()
        
        # Load or create progress
        if resume:
            self.progress = self.load_progress()
        else:
            self.progress = BatchProgress(
                session_number=self.SESSION_NUMBER,
                start_date=self.SESSION_217_START,
                end_date=self.SESSION_217_END,
                started_at=start_time
            )
        
        # Discover meetings if not already done
        if self.progress.total_meetings == 0:
            meetings = await self.discover_meetings()
            self.progress.total_meetings = len(meetings)
            self.save_progress(self.progress)
        else:
            # Reload meetings for processing
            meetings = await self.discover_meetings()
        
        # Filter meetings to resume from correct position
        if self.progress.last_processed_date:
            meetings = [m for m in meetings 
                       if m.meeting_date and m.meeting_date > self.progress.last_processed_date]
        
        self.logger.info(f"Starting batch processing: {len(meetings)} meetings to process")
        
        # Statistics tracking
        total_speeches = 0
        processing_errors = 0
        mapping_warnings = 0
        
        # Process meetings
        for i, meeting in enumerate(meetings):
            try:
                self.logger.info(f"Processing {i+1}/{len(meetings)}: {meeting.title}")
                
                success, stats = await self.process_meeting(meeting)
                
                # Update progress
                if success:
                    self.progress.processed_meetings += 1
                    self.progress.processed_speeches += stats["speeches_count"]
                    total_speeches += stats["speeches_count"]
                    
                    if meeting.meeting_date:
                        self.progress.last_processed_date = meeting.meeting_date
                else:
                    self.progress.failed_meetings.append(meeting.meeting_id)
                    processing_errors += 1
                
                mapping_warnings += len(stats["warnings"])
                
                # Save progress periodically
                if (i + 1) % 10 == 0:
                    self.save_progress(self.progress)
                    self.logger.info(f"Progress: {self.progress.completion_percentage:.1f}% complete")
                
                # Rate limiting between meetings
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Unexpected error processing meeting {meeting.meeting_id}: {e}")
                processing_errors += 1
                self.progress.failed_meetings.append(meeting.meeting_id)
        
        # Mark completion
        self.progress.completed_at = datetime.now()
        self.save_progress(self.progress)
        
        # Generate final statistics
        processing_time = (datetime.now() - start_time).total_seconds()
        
        statistics = BatchStatistics(
            total_meetings_found=self.progress.total_meetings,
            total_meetings_processed=self.progress.processed_meetings,
            total_speeches_processed=self.progress.processed_speeches,
            processing_errors=processing_errors,
            mapping_warnings=mapping_warnings,
            average_speeches_per_meeting=total_speeches / max(self.progress.processed_meetings, 1),
            processing_time_seconds=processing_time
        )
        
        # Save final report
        await self._generate_final_report(statistics)
        
        self.logger.info(f"✅ Batch ingestion completed in {processing_time:.1f}s")
        self.logger.info(f"📊 Processed {statistics.total_meetings_processed} meetings, "
                        f"{statistics.total_speeches_processed} speeches")
        
        return statistics
    
    async def _generate_final_report(self, statistics: BatchStatistics):
        """Generate final processing report"""
        report = {
            "session": {
                "number": self.SESSION_NUMBER,
                "start_date": self.SESSION_217_START.isoformat(),
                "end_date": self.SESSION_217_END.isoformat()
            },
            "progress": asdict(self.progress),
            "statistics": statistics.to_dict(),
            "generated_at": datetime.now().isoformat()
        }
        
        report_file = self.output_dir / f"batch_report_{self.SESSION_NUMBER}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Final report saved: {report_file}")


# CLI and testing interface
async def main():
    """CLI interface for historical data ingestion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Historical Diet Data Ingestion")
    parser.add_argument("--resume", action="store_true", help="Resume from existing progress")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    parser.add_argument("--progress-file", default="batch_progress.pkl", help="Progress file path")
    parser.add_argument("--output-dir", default="batch_output", help="Output directory")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run batch ingestion
    async with HistoricalDataIngester(
        progress_file=args.progress_file,
        output_dir=args.output_dir,
        batch_size=args.batch_size
    ) as ingester:
        statistics = await ingester.run_batch_ingestion(resume=args.resume)
        
        print("\n📊 Batch Ingestion Results:")
        print(f"  Total Meetings: {statistics.total_meetings_found}")
        print(f"  Processed: {statistics.total_meetings_processed}")
        print(f"  Speeches: {statistics.total_speeches_processed}")
        print(f"  Errors: {statistics.processing_errors}")
        print(f"  Processing Time: {statistics.processing_time_seconds:.1f}s")
        
        if statistics.processing_errors > 0:
            print(f"\n⚠️  {statistics.processing_errors} meetings failed to process")
            return 1
        
        print("\n✅ Batch ingestion completed successfully!")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))