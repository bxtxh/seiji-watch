"""
Hybrid Ingestion Pipeline Router

Implements date-based routing between NDL API and Whisper STT
with automatic pipeline selection logic and fallback mechanisms.

Routing Logic:
- Meetings ≤ 2025-06-21: NDL Minutes API (Historical)
- Meetings ≥ 2025-06-22: Whisper STT Pipeline (Real-time)
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from ..collectors.ndl_api_client import NDLAPIClient, NDLMeeting, NDLSpeech
from ..pipeline.ndl_data_mapper import NDLDataMapper
from ..batch.historical_ingestion import HistoricalDataIngester
from shared.src.shared.clients.airtable import AirtableClient


class DataSource(Enum):
    """Data source types for ingestion"""
    NDL_API = "ndl_api"
    WHISPER_STT = "whisper_stt"
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    """Result of routing decision"""
    data_source: DataSource
    meeting_date: Optional[date]
    rationale: str
    confidence: float  # 0.0 to 1.0
    fallback_available: bool = False
    manual_override: bool = False


@dataclass
class IngestionRequest:
    """Request for data ingestion"""
    meeting_date: Optional[date] = None
    meeting_id: Optional[str] = None
    diet_session: Optional[int] = None
    force_source: Optional[DataSource] = None
    priority: str = "normal"  # "low", "normal", "high"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class IngestionResult:
    """Result of ingestion operation"""
    success: bool
    data_source: DataSource
    meeting_count: int = 0
    speech_count: int = 0
    processing_time_seconds: float = 0.0
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class HybridIngestionRouter:
    """
    Hybrid Ingestion Pipeline Router
    
    Provides intelligent routing between NDL API and Whisper STT
    based on meeting dates, with fallback mechanisms and manual overrides.
    """
    
    # Cutoff date for routing decision
    CUTOFF_DATE = date(2025, 6, 21)
    
    # Diet session boundaries
    SESSION_217_START = date(2025, 1, 24)
    SESSION_217_END = date(2025, 6, 21)
    SESSION_218_START = date(2025, 6, 22)
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Pipeline components
        self.ndl_client: Optional[NDLAPIClient] = None
        self.airtable_client: Optional[AirtableClient] = None
        self.data_mapper = NDLDataMapper()
        self.historical_ingester: Optional[HistoricalDataIngester] = None
        
        # Statistics tracking
        self.routing_stats = {
            "ndl_api_requests": 0,
            "whisper_stt_requests": 0,
            "fallback_used": 0,
            "manual_overrides": 0,
            "total_meetings_processed": 0,
            "total_speeches_processed": 0
        }
        
        self.logger.info(f"Hybrid router initialized - Cutoff: {self.CUTOFF_DATE}")
    
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
    
    def make_routing_decision(self, request: IngestionRequest) -> RoutingDecision:
        """
        Make routing decision based on request parameters
        
        Args:
            request: Ingestion request with meeting information
            
        Returns:
            RoutingDecision with selected data source and rationale
        """
        # Handle manual override
        if request.force_source:
            self.routing_stats["manual_overrides"] += 1
            return RoutingDecision(
                data_source=request.force_source,
                meeting_date=request.meeting_date,
                rationale=f"Manual override to {request.force_source.value}",
                confidence=1.0,
                manual_override=True,
                fallback_available=True
            )
        
        # Date-based routing
        if request.meeting_date:
            if request.meeting_date <= self.CUTOFF_DATE:
                # Historical data - use NDL API
                rationale = f"Historical meeting ({request.meeting_date}) ≤ cutoff ({self.CUTOFF_DATE})"
                confidence = 1.0 if request.meeting_date >= self.SESSION_217_START else 0.8
                
                return RoutingDecision(
                    data_source=DataSource.NDL_API,
                    meeting_date=request.meeting_date,
                    rationale=rationale,
                    confidence=confidence,
                    fallback_available=False  # Whisper not available for historical data
                )
            else:
                # Recent data - use Whisper STT
                rationale = f"Recent meeting ({request.meeting_date}) > cutoff ({self.CUTOFF_DATE})"
                confidence = 1.0 if request.meeting_date >= self.SESSION_218_START else 0.9
                
                return RoutingDecision(
                    data_source=DataSource.WHISPER_STT,
                    meeting_date=request.meeting_date,
                    rationale=rationale,
                    confidence=confidence,
                    fallback_available=True  # NDL API may have recent data
                )
        
        # Diet session-based routing
        if request.diet_session:
            if request.diet_session <= 217:
                return RoutingDecision(
                    data_source=DataSource.NDL_API,
                    meeting_date=None,
                    rationale=f"Historical session ({request.diet_session}) ≤ 217",
                    confidence=0.9,
                    fallback_available=False
                )
            else:
                return RoutingDecision(
                    data_source=DataSource.WHISPER_STT,
                    meeting_date=None,
                    rationale=f"Recent session ({request.diet_session}) > 217",
                    confidence=0.9,
                    fallback_available=True
                )
        
        # Default to current pipeline (Whisper STT) for unknown dates
        return RoutingDecision(
            data_source=DataSource.WHISPER_STT,
            meeting_date=None,
            rationale="Unknown date/session - defaulting to Whisper STT",
            confidence=0.5,
            fallback_available=True
        )
    
    async def ingest_data(self, request: IngestionRequest) -> IngestionResult:
        """
        Main ingestion method with automatic routing
        
        Args:
            request: Ingestion request
            
        Returns:
            IngestionResult with processing outcome
        """
        start_time = datetime.now()
        
        # Make routing decision
        decision = self.make_routing_decision(request)
        self.logger.info(f"Routing decision: {decision.data_source.value} "
                        f"(confidence: {decision.confidence:.2f}) - {decision.rationale}")
        
        try:
            # Route to appropriate pipeline
            if decision.data_source == DataSource.NDL_API:
                result = await self._ingest_via_ndl_api(request)
                self.routing_stats["ndl_api_requests"] += 1
            elif decision.data_source == DataSource.WHISPER_STT:
                result = await self._ingest_via_whisper_stt(request)
                self.routing_stats["whisper_stt_requests"] += 1
            else:
                raise ValueError(f"Unknown data source: {decision.data_source}")
            
            # Update statistics
            self.routing_stats["total_meetings_processed"] += result.meeting_count
            self.routing_stats["total_speeches_processed"] += result.speech_count
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time_seconds = processing_time
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ingestion failed with {decision.data_source.value}: {e}")
            
            # Try fallback if available and not manual override
            if decision.fallback_available and not decision.manual_override:
                self.logger.info("Attempting fallback to alternative pipeline...")
                return await self._attempt_fallback(request, decision, start_time)
            
            # Return failure result
            processing_time = (datetime.now() - start_time).total_seconds()
            return IngestionResult(
                success=False,
                data_source=decision.data_source,
                processing_time_seconds=processing_time,
                errors=[f"Ingestion failed: {str(e)}"]
            )
    
    async def _ingest_via_ndl_api(self, request: IngestionRequest) -> IngestionResult:
        """Ingest data using NDL API"""
        meetings_processed = 0
        speeches_processed = 0
        warnings = []
        errors = []
        
        try:
            if request.meeting_id:
                # Process specific meeting
                meeting_result = await self._process_single_meeting_ndl(request.meeting_id)
                if meeting_result["success"]:
                    meetings_processed = 1
                    speeches_processed = meeting_result["speeches_count"]
                else:
                    errors.extend(meeting_result["errors"])
            
            elif request.meeting_date:
                # Process meetings for specific date
                meetings = await self.ndl_client.search_meetings(
                    start_date=request.meeting_date,
                    end_date=request.meeting_date,
                    diet_session=request.diet_session
                )
                
                for meeting in meetings:
                    meeting_result = await self._process_single_meeting_ndl(meeting.meeting_id)
                    if meeting_result["success"]:
                        meetings_processed += 1
                        speeches_processed += meeting_result["speeches_count"]
                    else:
                        errors.extend(meeting_result["errors"])
                        
            elif request.diet_session:
                # Use historical batch ingester for full session
                if not self.historical_ingester:
                    self.historical_ingester = HistoricalDataIngester()
                    await self.historical_ingester.__aenter__()
                
                stats = await self.historical_ingester.run_batch_ingestion(resume=True)
                meetings_processed = stats.total_meetings_processed
                speeches_processed = stats.total_speeches_processed
                
                if stats.processing_errors > 0:
                    errors.append(f"{stats.processing_errors} meetings failed to process")
            
            return IngestionResult(
                success=len(errors) == 0,
                data_source=DataSource.NDL_API,
                meeting_count=meetings_processed,
                speech_count=speeches_processed,
                warnings=warnings,
                errors=errors
            )
            
        except Exception as e:
            return IngestionResult(
                success=False,
                data_source=DataSource.NDL_API,
                errors=[f"NDL API ingestion failed: {str(e)}"]
            )
    
    async def _ingest_via_whisper_stt(self, request: IngestionRequest) -> IngestionResult:
        """Ingest data using Whisper STT pipeline"""
        # TODO: Integration with existing Whisper STT pipeline
        # This would connect to the existing scraper/whisper infrastructure
        
        self.logger.warning("Whisper STT integration not yet implemented")
        
        # Placeholder implementation
        return IngestionResult(
            success=False,
            data_source=DataSource.WHISPER_STT,
            errors=["Whisper STT pipeline integration pending"]
        )
    
    async def _process_single_meeting_ndl(self, meeting_id: str) -> Dict[str, Any]:
        """Process a single meeting via NDL API"""
        try:
            # Get meeting details
            meetings = await self.ndl_client.search_meetings()
            meeting = next((m for m in meetings if m.meeting_id == meeting_id), None)
            
            if not meeting:
                return {"success": False, "errors": [f"Meeting {meeting_id} not found"]}
            
            # Map meeting to Airtable format
            meeting_result = self.data_mapper.map_ndl_meeting_to_airtable(meeting)
            if not meeting_result.success:
                return {"success": False, "errors": meeting_result.errors}
            
            # Create meeting record
            meeting_record_id = await self.airtable_client.create_meeting(meeting_result.mapped_data)
            
            # Get and process speeches
            speeches = await self.ndl_client.get_all_speeches_for_meeting(meeting_id)
            
            if speeches:
                batch_result = self.data_mapper.batch_map_speeches(speeches, meeting_record_id)
                
                # Create speech records
                for speech in batch_result["speeches"]:
                    await self.airtable_client.create_speech(speech)
            
            return {
                "success": True,
                "speeches_count": len(speeches),
                "warnings": batch_result.get("warnings", []) if speeches else []
            }
            
        except Exception as e:
            return {"success": False, "errors": [str(e)]}
    
    async def _attempt_fallback(self, 
                              request: IngestionRequest, 
                              failed_decision: RoutingDecision,
                              start_time: datetime) -> IngestionResult:
        """Attempt fallback to alternative pipeline"""
        self.routing_stats["fallback_used"] += 1
        
        # Determine fallback source
        fallback_source = (DataSource.WHISPER_STT if failed_decision.data_source == DataSource.NDL_API 
                          else DataSource.NDL_API)
        
        self.logger.info(f"Fallback: trying {fallback_source.value}")
        
        # Create fallback request
        fallback_request = IngestionRequest(
            meeting_date=request.meeting_date,
            meeting_id=request.meeting_id,
            diet_session=request.diet_session,
            force_source=fallback_source,
            priority=request.priority,
            metadata=request.metadata
        )
        
        try:
            result = await self.ingest_data(fallback_request)
            result.warnings.append(f"Fallback used: {failed_decision.data_source.value} → {fallback_source.value}")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return IngestionResult(
                success=False,
                data_source=fallback_source,
                processing_time_seconds=processing_time,
                errors=[
                    f"Primary pipeline failed: {failed_decision.data_source.value}",
                    f"Fallback also failed: {str(e)}"
                ]
            )
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing and processing statistics"""
        total_requests = (self.routing_stats["ndl_api_requests"] + 
                         self.routing_stats["whisper_stt_requests"])
        
        return {
            "routing_distribution": {
                "ndl_api_requests": self.routing_stats["ndl_api_requests"],
                "whisper_stt_requests": self.routing_stats["whisper_stt_requests"],
                "ndl_api_percentage": (self.routing_stats["ndl_api_requests"] / max(total_requests, 1)) * 100,
                "whisper_stt_percentage": (self.routing_stats["whisper_stt_requests"] / max(total_requests, 1)) * 100
            },
            "reliability": {
                "fallback_used": self.routing_stats["fallback_used"],
                "manual_overrides": self.routing_stats["manual_overrides"],
                "fallback_rate": (self.routing_stats["fallback_used"] / max(total_requests, 1)) * 100
            },
            "throughput": {
                "total_meetings_processed": self.routing_stats["total_meetings_processed"],
                "total_speeches_processed": self.routing_stats["total_speeches_processed"],
                "meetings_per_request": (self.routing_stats["total_meetings_processed"] / max(total_requests, 1))
            },
            "configuration": {
                "cutoff_date": self.CUTOFF_DATE.isoformat(),
                "session_217_period": f"{self.SESSION_217_START} to {self.SESSION_217_END}",
                "session_218_start": self.SESSION_218_START.isoformat()
            }
        }
    
    async def test_routing_decision(self, test_date: date) -> Dict[str, Any]:
        """Test routing decision for a given date"""
        request = IngestionRequest(meeting_date=test_date)
        decision = self.make_routing_decision(request)
        
        return {
            "test_date": test_date.isoformat(),
            "selected_source": decision.data_source.value,
            "rationale": decision.rationale,
            "confidence": decision.confidence,
            "fallback_available": decision.fallback_available
        }


# CLI and testing interface
async def main():
    """CLI interface for testing hybrid ingestion router"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid Ingestion Router")
    parser.add_argument("--test-date", type=str, help="Test routing for date (YYYY-MM-DD)")
    parser.add_argument("--ingest-date", type=str, help="Ingest data for date (YYYY-MM-DD)")
    parser.add_argument("--meeting-id", type=str, help="Ingest specific meeting ID")
    parser.add_argument("--diet-session", type=int, help="Ingest entire diet session")
    parser.add_argument("--force-source", choices=["ndl_api", "whisper_stt"], help="Force specific source")
    parser.add_argument("--stats", action="store_true", help="Show routing statistics")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    async with HybridIngestionRouter() as router:
        
        if args.test_date:
            # Test routing decision
            test_date = datetime.strptime(args.test_date, "%Y-%m-%d").date()
            result = await router.test_routing_decision(test_date)
            print("\n📋 Routing Decision Test:")
            print(f"  Date: {result['test_date']}")
            print(f"  Selected Source: {result['selected_source']}")
            print(f"  Rationale: {result['rationale']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Fallback Available: {result['fallback_available']}")
            
        elif args.ingest_date or args.meeting_id or args.diet_session:
            # Perform ingestion
            request = IngestionRequest()
            
            if args.ingest_date:
                request.meeting_date = datetime.strptime(args.ingest_date, "%Y-%m-%d").date()
            if args.meeting_id:
                request.meeting_id = args.meeting_id
            if args.diet_session:
                request.diet_session = args.diet_session
            if args.force_source:
                request.force_source = DataSource(args.force_source)
            
            print(f"\n🔄 Starting ingestion...")
            result = await router.ingest_data(request)
            
            print(f"\n📊 Ingestion Result:")
            print(f"  Success: {'✅' if result.success else '❌'}")
            print(f"  Data Source: {result.data_source.value}")
            print(f"  Meetings: {result.meeting_count}")
            print(f"  Speeches: {result.speech_count}")
            print(f"  Processing Time: {result.processing_time_seconds:.1f}s")
            
            if result.warnings:
                print(f"  ⚠️  Warnings: {len(result.warnings)}")
                for warning in result.warnings:
                    print(f"    - {warning}")
            
            if result.errors:
                print(f"  ❌ Errors: {len(result.errors)}")
                for error in result.errors:
                    print(f"    - {error}")
        
        if args.stats:
            # Show statistics
            stats = router.get_routing_statistics()
            print(f"\n📈 Routing Statistics:")
            print(f"  NDL API: {stats['routing_distribution']['ndl_api_requests']} requests "
                  f"({stats['routing_distribution']['ndl_api_percentage']:.1f}%)")
            print(f"  Whisper STT: {stats['routing_distribution']['whisper_stt_requests']} requests "
                  f"({stats['routing_distribution']['whisper_stt_percentage']:.1f}%)")
            print(f"  Fallback Rate: {stats['reliability']['fallback_rate']:.1f}%")
            print(f"  Total Processed: {stats['throughput']['total_meetings_processed']} meetings, "
                  f"{stats['throughput']['total_speeches_processed']} speeches")


if __name__ == "__main__":
    asyncio.run(main())