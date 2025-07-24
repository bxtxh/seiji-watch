"""
Limited scope scraping pipeline for T52 - Data Pipeline Coordination
Target: First week of June 2025 (June 2-8, 2025)
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from embeddings.vector_client import VectorClient
from monitoring.metrics import ingest_metrics
from scraper.diet_scraper import DietScraper
from scraper.hr_voting_scraper import HouseOfRepresentativesVotingScraper
from scraper.voting_scraper import VotingScraper
from stt.whisper_client import WhisperClient


@dataclass
class ScrapeTarget:
    """Target date range and parameters for limited scraping"""
    start_date: datetime
    end_date: datetime
    max_bills: int = 50
    max_voting_sessions: int = 20
    max_speeches: int = 100
    enable_stt: bool = False  # Disable for pilot to reduce costs
    enable_embeddings: bool = True


@dataclass
class PipelineResult:
    """Results from limited scraping pipeline"""
    success: bool
    total_time: float
    bills_collected: int
    voting_sessions_collected: int
    speeches_processed: int
    embeddings_generated: int
    transcriptions_completed: int
    errors: list[str]
    performance_metrics: dict[str, Any]


class LimitedScrapeCoordinator:
    """Coordinates limited scope scraping for pilot testing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize scrapers
        self.diet_scraper = DietScraper(enable_resilience=True)
        self.voting_scraper = VotingScraper()
        self.hr_voting_scraper = None
        self.whisper_client = None
        self.vector_client = None

        # Try to initialize optional services
        try:
            self.hr_voting_scraper = HouseOfRepresentativesVotingScraper()
            self.logger.info("HR voting scraper initialized")
        except Exception as e:
            self.logger.warning(f"HR voting scraper not available: {e}")

        try:
            self.whisper_client = WhisperClient()
            self.logger.info("Whisper client initialized")
        except Exception as e:
            self.logger.warning(f"Whisper client not available: {e}")

        try:
            self.vector_client = VectorClient()
            self.logger.info("Vector client initialized")
        except Exception as e:
            self.logger.warning(f"Vector client not available: {e}")

    def get_june_first_week_target(self) -> ScrapeTarget:
        """Get target configuration for June first week 2025"""
        start_date = datetime(2025, 6, 2)  # Monday
        end_date = datetime(2025, 6, 8)    # Sunday

        return ScrapeTarget(
            start_date=start_date,
            end_date=end_date,
            max_bills=30,           # Limit to 30 bills for pilot
            max_voting_sessions=10,  # Limit to 10 voting sessions
            max_speeches=50,        # Limit to 50 speeches
            enable_stt=False,       # Disable STT to reduce costs
            enable_embeddings=True  # Enable embeddings for search testing
        )

    def get_june_full_month_target(self) -> ScrapeTarget:
        """Get target configuration for June 2025 full month (production)"""
        start_date = datetime(2025, 6, 1)  # June 1st
        end_date = datetime(2025, 6, 30)   # June 30th

        return ScrapeTarget(
            start_date=start_date,
            end_date=end_date,
            max_bills=200,          # Increased for full month
            max_voting_sessions=50, # Increased for full month
            max_speeches=500,       # Increased for full month
            enable_stt=True,        # Enable STT for production
            enable_embeddings=True  # Enable embeddings for search
        )

    async def execute_limited_scraping(
        self,
        target: ScrapeTarget | None = None,
        dry_run: bool = False
    ) -> PipelineResult:
        """Execute limited scope scraping with monitoring and volume controls"""

        if target is None:
            target = self.get_june_first_week_target()

        start_time = datetime.now()
        self.logger.info("Starting limited scraping pipeline")
        self.logger.info(f"Target period: {target.start_date.date()} to {target.end_date.date()}")
        self.logger.info(f"Limits: {target.max_bills} bills, {target.max_voting_sessions} sessions, {target.max_speeches} speeches")
        self.logger.info(f"Dry run: {dry_run}")

        result = PipelineResult(
            success=False,
            total_time=0.0,
            bills_collected=0,
            voting_sessions_collected=0,
            speeches_processed=0,
            embeddings_generated=0,
            transcriptions_completed=0,
            errors=[],
            performance_metrics={}
        )

        try:
            # Phase 1: Bill data collection
            self.logger.info("Phase 1: Collecting bill data...")
            bills_result = await self._collect_bills_limited(target, dry_run)
            result.bills_collected = bills_result.get('count', 0)
            if bills_result.get('errors'):
                result.errors.extend(bills_result['errors'])

            # Phase 2: Voting data collection
            self.logger.info("Phase 2: Collecting voting data...")
            voting_result = await self._collect_voting_data_limited(target, dry_run)
            result.voting_sessions_collected = voting_result.get('count', 0)
            if voting_result.get('errors'):
                result.errors.extend(voting_result['errors'])

            # Phase 3: Speech processing (if enabled)
            if target.enable_stt and self.whisper_client:
                self.logger.info("Phase 3: Processing speeches...")
                speech_result = await self._process_speeches_limited(target, dry_run)
                result.speeches_processed = speech_result.get('count', 0)
                result.transcriptions_completed = speech_result.get('transcriptions', 0)
                if speech_result.get('errors'):
                    result.errors.extend(speech_result['errors'])
            else:
                self.logger.info("Phase 3: Speech processing disabled")

            # Phase 4: Embedding generation
            if target.enable_embeddings and self.vector_client:
                self.logger.info("Phase 4: Generating embeddings...")
                embedding_result = await self._generate_embeddings_limited(target, dry_run)
                result.embeddings_generated = embedding_result.get('count', 0)
                if embedding_result.get('errors'):
                    result.errors.extend(embedding_result['errors'])
            else:
                self.logger.info("Phase 4: Embedding generation disabled")

            # Calculate final results
            end_time = datetime.now()
            result.total_time = (end_time - start_time).total_seconds()
            result.success = len(result.errors) == 0

            # Collect performance metrics
            result.performance_metrics = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': result.total_time,
                'bills_per_second': result.bills_collected / result.total_time if result.total_time > 0 else 0,
                'voting_sessions_per_second': result.voting_sessions_collected / result.total_time if result.total_time > 0 else 0,
                'embeddings_per_second': result.embeddings_generated / result.total_time if result.total_time > 0 else 0,
                'error_rate': len(result.errors) / max(1, result.bills_collected + result.voting_sessions_collected),
                'target_configuration': {
                    'max_bills': target.max_bills,
                    'max_voting_sessions': target.max_voting_sessions,
                    'max_speeches': target.max_speeches,
                    'enable_stt': target.enable_stt,
                    'enable_embeddings': target.enable_embeddings
                },
                'resource_usage': self._get_resource_usage()
            }

            # Record metrics
            ingest_metrics.record_pipeline_execution(
                pipeline_name="limited_scraping",
                duration_seconds=result.total_time,
                items_processed=result.bills_collected + result.voting_sessions_collected,
                success=result.success
            )

            self.logger.info("Limited scraping pipeline completed:")
            self.logger.info(f"  Success: {result.success}")
            self.logger.info(f"  Duration: {result.total_time:.2f}s")
            self.logger.info(f"  Bills: {result.bills_collected}")
            self.logger.info(f"  Voting sessions: {result.voting_sessions_collected}")
            self.logger.info(f"  Speeches: {result.speeches_processed}")
            self.logger.info(f"  Embeddings: {result.embeddings_generated}")
            self.logger.info(f"  Errors: {len(result.errors)}")

            return result

        except Exception as e:
            end_time = datetime.now()
            result.total_time = (end_time - start_time).total_seconds()
            result.success = False
            result.errors.append(f"Pipeline failure: {str(e)}")

            self.logger.error(f"Limited scraping pipeline failed: {e}")
            return result

    async def _collect_bills_limited(self, target: ScrapeTarget, dry_run: bool) -> dict[str, Any]:
        """Collect limited bill data with volume controls"""
        try:
            self.logger.info(f"Fetching up to {target.max_bills} bills...")

            if dry_run:
                self.logger.info("DRY RUN: Would fetch bills from Diet website")
                return {'count': 5, 'errors': []}  # Simulate 5 bills

            # Use resilient async scraper
            bills_data = await self.diet_scraper.fetch_current_bills_async(force_refresh=True)

            # Apply volume limit
            limited_bills = bills_data[:target.max_bills]

            self.logger.info(f"Collected {len(limited_bills)} bills (limited from {len(bills_data)})")

            # TODO: Store in Airtable
            # For now, just log the data
            for i, bill in enumerate(limited_bills[:3]):  # Log first 3 for verification
                self.logger.debug(f"Bill {i+1}: {bill.bill_id} - {bill.title[:50]}...")

            return {
                'count': len(limited_bills),
                'data': limited_bills,
                'errors': []
            }

        except Exception as e:
            self.logger.error(f"Bill collection failed: {e}")
            return {
                'count': 0,
                'data': [],
                'errors': [f"Bill collection error: {str(e)}"]
            }

    async def _collect_voting_data_limited(self, target: ScrapeTarget, dry_run: bool) -> dict[str, Any]:
        """Collect limited voting data with volume controls"""
        try:
            self.logger.info(f"Fetching up to {target.max_voting_sessions} voting sessions...")

            if dry_run:
                self.logger.info("DRY RUN: Would fetch voting data from Diet website")
                return {'count': 3, 'errors': []}  # Simulate 3 sessions

            # Fetch voting sessions
            voting_sessions = self.voting_scraper.fetch_voting_sessions()

            # Filter by date range if possible (voting scraper may not support date filtering)
            # For now, apply volume limit
            limited_sessions = voting_sessions[:target.max_voting_sessions]

            self.logger.info(f"Collected {len(limited_sessions)} voting sessions (limited from {len(voting_sessions)})")

            # TODO: Store in Airtable
            # For now, just log the data
            for i, session in enumerate(limited_sessions[:2]):  # Log first 2 for verification
                self.logger.debug(f"Session {i+1}: {session.bill_number} - {session.bill_title[:50]}...")
                self.logger.debug(f"  Votes: {len(session.vote_records)} records")

            return {
                'count': len(limited_sessions),
                'data': limited_sessions,
                'errors': []
            }

        except Exception as e:
            self.logger.error(f"Voting data collection failed: {e}")
            return {
                'count': 0,
                'data': [],
                'errors': [f"Voting collection error: {str(e)}"]
            }

    async def _process_speeches_limited(self, target: ScrapeTarget, dry_run: bool) -> dict[str, Any]:
        """Process limited speech data with STT"""
        try:
            if not self.whisper_client:
                return {'count': 0, 'transcriptions': 0, 'errors': ['Whisper client not available']}

            self.logger.info(f"Processing up to {target.max_speeches} speeches...")

            if dry_run:
                self.logger.info("DRY RUN: Would process speeches with STT")
                return {'count': 2, 'transcriptions': 2, 'errors': []}

            # For pilot, we'll skip actual STT processing to reduce costs
            # In full implementation, this would process audio/video content

            self.logger.info("STT processing skipped for cost control in pilot")
            return {
                'count': 0,
                'transcriptions': 0,
                'errors': []
            }

        except Exception as e:
            self.logger.error(f"Speech processing failed: {e}")
            return {
                'count': 0,
                'transcriptions': 0,
                'errors': [f"Speech processing error: {str(e)}"]
            }

    async def _generate_embeddings_limited(self, target: ScrapeTarget, dry_run: bool) -> dict[str, Any]:
        """Generate limited embeddings for collected content"""
        try:
            if not self.vector_client:
                return {'count': 0, 'errors': ['Vector client not available']}

            self.logger.info("Generating embeddings for collected content...")

            if dry_run:
                self.logger.info("DRY RUN: Would generate embeddings")
                return {'count': 8, 'errors': []}  # Simulate 8 embeddings

            # For pilot, generate a few test embeddings
            test_texts = [
                "国会での法案審議について",
                "参議院の投票結果について",
                "政治制度改革に関する議論",
                "予算案の審議状況について",
                "外交政策に関する質疑応答"
            ]

            embeddings_generated = 0
            for i, text in enumerate(test_texts):
                try:
                    # Generate embedding
                    embedding = self.vector_client.generate_embedding(text)

                    # Store test metadata
                    test_metadata = {
                        'bill_number': f'TEST-{i+1}',
                        'title': f'テスト法案{i+1}',
                        'summary': text,
                        'category': 'TEST',
                        'created_at': datetime.now().isoformat()
                    }

                    # Store in Weaviate
                    uuid = self.vector_client.store_bill_embedding(test_metadata, embedding)
                    if uuid:
                        embeddings_generated += 1
                        self.logger.debug(f"Generated embedding {i+1}: {uuid}")

                    # Rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    self.logger.warning(f"Failed to generate embedding {i+1}: {e}")

            self.logger.info(f"Generated {embeddings_generated} test embeddings")

            return {
                'count': embeddings_generated,
                'errors': []
            }

        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            return {
                'count': 0,
                'errors': [f"Embedding generation error: {str(e)}"]
            }

    def _get_resource_usage(self) -> dict[str, Any]:
        """Get current resource usage metrics"""
        try:
            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / (1024 * 1024),
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            }
        except ImportError:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'note': 'psutil not available for resource monitoring'
            }
        except Exception as e:
            return {
                'error': f'Resource monitoring failed: {str(e)}'
            }

    def get_pipeline_status(self) -> dict[str, Any]:
        """Get current pipeline status and configuration"""
        return {
            'status': 'ready',
            'services': {
                'diet_scraper': self.diet_scraper is not None,
                'voting_scraper': self.voting_scraper is not None,
                'hr_voting_scraper': self.hr_voting_scraper is not None,
                'whisper_client': self.whisper_client is not None,
                'vector_client': self.vector_client is not None
            },
            'target_configuration': {
                'start_date': '2025-06-02',
                'end_date': '2025-06-08',
                'max_bills': 30,
                'max_voting_sessions': 10,
                'max_speeches': 50,
                'enable_stt': False,
                'enable_embeddings': True
            },
            'estimated_costs': {
                'openai_embeddings': '$0.50',  # ~50 embeddings
                'openai_stt': '$0.00',         # Disabled
                'airtable_api': '$0.00',       # Within free tier
                'weaviate_cloud': '$0.00',     # Sandbox tier
                'total_estimated': '$0.50'
            }
        }


# Convenience function for execution
async def run_limited_scraping_pipeline(dry_run: bool = True) -> PipelineResult:
    """Run the limited scraping pipeline for T52"""
    coordinator = LimitedScrapeCoordinator()
    return await coordinator.execute_limited_scraping(dry_run=dry_run)


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)

    async def test_pipeline():
        result = await run_limited_scraping_pipeline(dry_run=True)
        print(f"Pipeline result: {result}")

    asyncio.run(test_pipeline())
