"""
Ingest Worker Service - FastAPI application for Diet data scraping and processing.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import uvicorn
from batch_queue.batch_processor import (
    BatchConfig,
    BatchProcessor,
    EmbeddingTaskProcessor,
    TaskPriority,
    TaskType,
    TranscriptionTaskProcessor,
)
from embeddings.vector_client import VectorClient
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

# Import monitoring components
from monitoring import (
    get_alerts_dashboard,
    get_dashboard_overview,
    get_health_status,
    get_metrics_export,
    get_performance_dashboard,
    get_pipeline_status,
    get_quality_metrics,
    get_system_status,
    ingest_metrics,
)
from pipeline.hr_data_integration import run_hr_integration_pipeline

# Import limited scraping pipeline for T52
from pipeline.limited_scraping import (
    LimitedScrapeCoordinator,
)
from pydantic import BaseModel
from scheduler.scheduler import IngestionScheduler
from scraper.diet_scraper import BillData, DietScraper
from scraper.enhanced_hr_scraper import EnhancedHRProcessor
from scraper.hr_voting_scraper import HouseOfRepresentativesVotingScraper
from scraper.voting_scraper import VoteRecord, VotingScraper, VotingSession
from stt.whisper_client import TranscriptionResult, WhisperClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
diet_scraper: DietScraper | None = None
voting_scraper: VotingScraper | None = None
hr_voting_scraper: HouseOfRepresentativesVotingScraper | None = None
whisper_client: WhisperClient | None = None
vector_client: VectorClient | None = None
scheduler: IngestionScheduler | None = None
batch_processor: BatchProcessor | None = None
limited_scrape_coordinator: LimitedScrapeCoordinator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global \
        diet_scraper, \
        voting_scraper, \
        hr_voting_scraper, \
        whisper_client, \
        vector_client, \
        scheduler, \
        batch_processor, \
        limited_scrape_coordinator

    # Startup
    logger.info("Starting ingest-worker service...")

    try:
        # Initialize Diet scraper
        diet_scraper = DietScraper()
        logger.info("Diet scraper initialized")

        # Initialize Voting scraper
        voting_scraper = VotingScraper()
        logger.info("Voting scraper initialized")

        # Initialize House of Representatives voting scraper
        try:
            hr_voting_scraper = HouseOfRepresentativesVotingScraper()
            logger.info("House of Representatives voting scraper initialized")
        except Exception as e:
            logger.warning(f"HR voting scraper not initialized: {e}")
            hr_voting_scraper = None

        # Initialize Whisper client (only if API key is available)
        try:
            whisper_client = WhisperClient()
            logger.info("Whisper client initialized")
        except ValueError as e:
            logger.warning(f"Whisper client not initialized: {e}")
            whisper_client = None

        # Initialize Vector client (only if API keys are available)
        try:
            vector_client = VectorClient()
            logger.info("Vector client initialized")
        except ValueError as e:
            logger.warning(f"Vector client not initialized: {e}")
            vector_client = None

        # Initialize Scheduler
        try:
            scheduler = IngestionScheduler()
            logger.info("Ingestion scheduler initialized")
        except Exception as e:
            logger.warning(f"Scheduler not initialized: {e}")
            scheduler = None

        # Initialize Batch Processor
        try:
            batch_config = BatchConfig(
                max_concurrent_tasks=3,
                max_queue_size=500,
                batch_size=5,
                enable_persistence=True,
                persistence_backend="file",
            )
            batch_processor = BatchProcessor(batch_config)

            # Register task processors
            if vector_client:
                batch_processor.register_processor(
                    TaskType.GENERATE_EMBEDDINGS, EmbeddingTaskProcessor(vector_client)
                )

            if whisper_client:
                batch_processor.register_processor(
                    TaskType.TRANSCRIBE_AUDIO,
                    TranscriptionTaskProcessor(whisper_client),
                )

            # Start batch processing
            asyncio.create_task(batch_processor.start_processing())
            logger.info("Batch processor initialized and started")

        except Exception as e:
            logger.warning(f"Batch processor not initialized: {e}")
            batch_processor = None

        # Start system metrics collection
        try:

            async def collect_system_metrics():
                while True:
                    ingest_metrics.record_system_metrics()
                    await asyncio.sleep(60)  # Collect every minute

            asyncio.create_task(collect_system_metrics())
            logger.info("System metrics collection started")

        except Exception as e:
            logger.warning(f"System metrics collection not started: {e}")

        # Initialize Limited Scraping Coordinator for T52
        try:
            limited_scrape_coordinator = LimitedScrapeCoordinator()
            logger.info("Limited scraping coordinator initialized for T52")
        except Exception as e:
            logger.warning(f"Limited scraping coordinator not initialized: {e}")
            limited_scrape_coordinator = None

        yield

    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ingest-worker service...")

        if batch_processor:
            await batch_processor.stop_processing()

        if vector_client:
            vector_client.close()


app = FastAPI(
    title="Diet Issue Tracker - Ingest Worker",
    description="Service for scraping and processing Diet data",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    """Request model for scraping operations"""

    source: str = "diet_bills"
    force_refresh: bool = False


class ScrapeResponse(BaseModel):
    """Response model for scraping operations"""

    success: bool
    message: str
    bills_processed: int
    errors: list[str] = []


class TranscribeRequest(BaseModel):
    """Request model for transcription operations"""

    audio_url: str | None = None
    video_url: str | None = None
    language: str = "ja"


class TranscribeResponse(BaseModel):
    """Response model for transcription operations"""

    success: bool
    message: str
    text: str | None = None
    duration: float | None = None
    language: str | None = None
    quality_passed: bool | None = None


class EmbeddingRequest(BaseModel):
    """Request model for embedding operations"""

    text: str
    store_in_weaviate: bool = True
    metadata: dict | None = None


class EmbeddingResponse(BaseModel):
    """Response model for embedding operations"""

    success: bool
    message: str
    dimensions: int | None = None
    model: str | None = None
    weaviate_uuid: str | None = None


class SearchRequest(BaseModel):
    """Request model for vector search operations"""

    query: str
    limit: int = 10
    min_certainty: float = 0.7


class SearchResponse(BaseModel):
    """Response model for vector search operations"""

    success: bool
    message: str
    results: list[dict] = []
    total_found: int = 0


class VotingRequest(BaseModel):
    """Request model for voting data collection"""

    force_refresh: bool = False
    vote_type: str = "all"  # "plenary", "committee", "all"


class VotingResponse(BaseModel):
    """Response model for voting data collection"""

    success: bool
    message: str
    sessions_processed: int
    votes_processed: int
    members_processed: int
    errors: list[str] = []


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "ingest-worker", "version": "1.0.0"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_diet_data(
    request: ScrapeRequest, background_tasks: BackgroundTasks
) -> ScrapeResponse:
    """Scrape Diet data and return results"""

    if not diet_scraper:
        raise HTTPException(status_code=500, detail="Service not properly initialized")

    # Run scraping in background for long-running operations
    background_tasks.add_task(_scrape_bills_task, force_refresh=request.force_refresh)

    return ScrapeResponse(
        success=True, message="Scraping task started", bills_processed=0
    )


@app.get("/scrape/status")
async def get_scrape_status() -> dict[str, str]:
    """Get current scraping status"""
    # TODO: Implement proper status tracking
    return {"status": "ready", "last_scrape": "N/A", "bills_in_queue": "0"}


@app.post("/voting/collect", response_model=VotingResponse)
async def collect_voting_data(
    request: VotingRequest, background_tasks: BackgroundTasks
) -> VotingResponse:
    """Collect voting data from Diet website and store in Airtable"""

    if not voting_scraper:
        raise HTTPException(
            status_code=500, detail="Voting scraper not properly initialized"
        )

    # Run voting data collection in background
    background_tasks.add_task(
        _collect_voting_data_task,
        vote_type=request.vote_type,
        force_refresh=request.force_refresh,
    )

    return VotingResponse(
        success=True,
        message="Voting data collection task started",
        sessions_processed=0,
        votes_processed=0,
        members_processed=0,
    )


@app.get("/voting/status")
async def get_voting_status() -> dict[str, str]:
    """Get current voting data collection status"""
    # TODO: Implement proper status tracking
    return {"status": "ready", "last_collection": "N/A", "sessions_in_queue": "0"}


@app.get("/voting/stats")
async def get_voting_stats() -> dict[str, int | str]:
    """Get voting data statistics"""
    # TODO: Implement with Airtable queries
    return {
        "total_sessions": 0,
        "total_votes": 0,
        "total_members": 0,
        "latest_session_date": "N/A",
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    request: TranscribeRequest, background_tasks: BackgroundTasks
) -> TranscribeResponse:
    """Transcribe audio or video content using Whisper API"""

    if not whisper_client:
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text service not available (missing OpenAI API key)",
        )

    if not request.audio_url and not request.video_url:
        raise HTTPException(
            status_code=400, detail="Either audio_url or video_url must be provided"
        )

    # Run transcription in background for long-running operations
    background_tasks.add_task(
        _transcribe_task,
        audio_url=request.audio_url,
        video_url=request.video_url,
        language=request.language,
    )

    return TranscribeResponse(success=True, message="Transcription task started")


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Generate vector embedding for text"""

    if not vector_client:
        raise HTTPException(
            status_code=503,
            detail="Vector service not available (missing OpenAI/Weaviate credentials)",
        )

    try:
        # Generate embedding
        embedding = vector_client.generate_embedding(request.text)

        weaviate_uuid = None
        if request.store_in_weaviate and request.metadata:
            # Store in Weaviate if metadata provided
            if "bill_number" in request.metadata:
                weaviate_uuid = vector_client.store_bill_embedding(
                    request.metadata, embedding
                )
            elif "speaker" in request.metadata:
                weaviate_uuid = vector_client.store_speech_embedding(
                    request.metadata, embedding
                )

        return EmbeddingResponse(
            success=True,
            message="Embedding generated successfully",
            dimensions=embedding.dimensions,
            model=embedding.model,
            weaviate_uuid=weaviate_uuid,
        )

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search_similar_bills(request: SearchRequest) -> SearchResponse:
    """
    Hybrid search for bills using vector similarity and keyword matching.
    Falls back to keyword search if vector search is unavailable.
    """

    try:
        results = []

        if vector_client:
            # Perform vector similarity search
            try:
                vector_results = vector_client.search_similar_bills(
                    query_text=request.query,
                    limit=request.limit,
                    min_certainty=request.min_certainty,
                )
                results.extend(vector_results)
                search_method = "vector"

            except Exception as e:
                logger.warning(
                    f"Vector search failed, falling back to keyword search: {e}"
                )
                # Fallback to keyword search if vector search fails
                results = await _keyword_search_bills(request.query, request.limit)
                search_method = "keyword (fallback)"
        else:
            # Use keyword search if vector client not available
            results = await _keyword_search_bills(request.query, request.limit)
            search_method = "keyword"

        return SearchResponse(
            success=True,
            message=f"Found {len(results)} bills using {search_method} search",
            results=results,
            total_found=len(results),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _keyword_search_bills(query: str, limit: int = 10) -> list[dict]:
    """
    Fallback keyword search using scraped bill data.
    In production, this would query Airtable directly.
    """
    try:
        # For now, search through scraped bills in memory
        # TODO: Replace with Airtable query when integrated

        bills_data = diet_scraper.fetch_current_bills()
        results = []

        query_lower = query.lower()

        for bill_data in bills_data:
            # Simple keyword matching
            title_match = query_lower in bill_data.title.lower()
            summary_match = (
                bill_data.summary and query_lower in bill_data.summary.lower()
            )

            if title_match or summary_match:
                # Calculate simple relevance score
                score = 0.0
                if title_match:
                    score += 0.8
                if summary_match:
                    score += 0.5

                # Convert to search result format
                results.append(
                    {
                        "bill_number": bill_data.bill_id,
                        "title": bill_data.title,
                        "summary": bill_data.summary or "",
                        "category": bill_data.category,
                        "status": bill_data.stage,
                        "diet_url": bill_data.url,
                        "relevance_score": score,
                        "search_method": "keyword",
                    }
                )

        # Sort by relevance score and limit results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]

    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []


@app.get("/embeddings/stats")
async def get_embedding_stats() -> dict[str, int | str]:
    """Get statistics about stored embeddings"""

    if not vector_client:
        return {
            "status": "unavailable",
            "bills": 0,
            "speeches": 0,
            "message": "Vector service not available",
        }

    try:
        stats = vector_client.get_embedding_stats()
        return {
            "status": "available",
            "bills": stats["bills"],
            "speeches": stats["speeches"],
            "message": f"Vector store contains {stats['bills']} bills and {stats['speeches']} speeches",
        }

    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        return {"status": "error", "bills": 0, "speeches": 0, "message": str(e)}


async def _scrape_bills_task(force_refresh: bool = False) -> None:
    """Background task to scrape bills and process them"""
    logger.info("Starting bill scraping and processing task...")

    try:
        # Fetch bills from Diet website
        bills_data = diet_scraper.fetch_current_bills()
        logger.info(f"Scraped {len(bills_data)} bills from Diet website")

        # Process and normalize the data
        processed_count = 0
        errors = []

        for bill_data in bills_data:
            try:
                # Convert and normalize bill data
                normalized_bill = _normalize_bill_data(bill_data)

                # Generate embedding if vector client is available
                if vector_client and bill_data.title:
                    try:
                        # Create text for embedding (title + summary)
                        embedding_text = f"{bill_data.title}\n{bill_data.summary or ''}"

                        # Generate embedding
                        embedding = vector_client.generate_embedding(embedding_text)

                        # Store in Weaviate
                        weaviate_uuid = vector_client.store_bill_embedding(
                            normalized_bill, embedding
                        )

                        if weaviate_uuid:
                            logger.info(
                                f"Generated embedding for bill {normalized_bill['bill_number']}: {weaviate_uuid}"
                            )

                    except Exception as e:
                        logger.warning(
                            f"Failed to generate embedding for bill {bill_data.bill_id}: {e}"
                        )

                # For now, just log the normalized data (TODO: Store in Airtable)
                logger.debug(
                    f"Normalized bill: {normalized_bill['bill_number']} - {normalized_bill['title'][:50]}..."
                )
                processed_count += 1

                # Rate limiting - respect both Airtable and OpenAI limits
                await asyncio.sleep(0.2)

            except Exception as e:
                error_msg = f"Failed to process bill {bill_data.bill_id}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)

        logger.info(
            f"Bill processing completed: {processed_count} processed, {len(errors)} errors"
        )
        if errors:
            logger.warning(f"First few errors: {errors[:3]}")

    except Exception as e:
        logger.error(f"Bill scraping task failed: {e}")


def _normalize_bill_data(bill_data: BillData) -> dict[str, str]:
    """
    Normalize bill data from scraper format to structured format

    Args:
        bill_data: BillData object from scraper

    Returns:
        Normalized bill data dictionary
    """
    # Map category string to standardized category
    category_mapping = {
        "予算・決算": "BUDGET",
        "税制": "TAXATION",
        "社会保障": "SOCIAL_SECURITY",
        "外交・国際": "FOREIGN_AFFAIRS",
        "経済・産業": "ECONOMY",
        "その他": "OTHER",
    }

    # Map stage to standardized status
    status_mapping = {
        "成立": "PASSED",
        "採決待ち": "PENDING_VOTE",
        "審議中": "UNDER_REVIEW",
        "Backlog": "BACKLOG",
    }

    # Extract diet session from bill ID (format: "217-1")
    diet_session = None
    if "-" in bill_data.bill_id:
        diet_session = bill_data.bill_id.split("-")[0]

    return {
        "bill_number": bill_data.bill_id,
        "title": bill_data.title,
        "summary": bill_data.summary or "",
        "status": status_mapping.get(bill_data.stage, "BACKLOG"),
        "category": category_mapping.get(bill_data.category, "OTHER"),
        "diet_url": bill_data.url,
        "submitted_date": bill_data.submission_date.strftime("%Y-%m-%d")
        if bill_data.submission_date
        else None,
        "submitter_type": bill_data.submitter,
        "diet_session": diet_session,
        "house_of_origin": "参議院",
    }


def _validate_transcription_quality(transcription: TranscriptionResult) -> bool:
    """Validate transcription meets quality standards (WER <= 15%)"""
    # Basic quality checks since we don't have reference text
    if not transcription.text or len(transcription.text.strip()) < 10:
        return False

    # Check for reasonable Japanese content
    japanese_chars = sum(1 for c in transcription.text if ord(c) > 127)
    if japanese_chars < len(transcription.text) * 0.3:
        return False

    # Check duration makes sense
    if transcription.duration <= 0:
        return False

    # Check for excessive repetition (poor transcription indicator)
    words = transcription.text.split()
    if len(words) > 10:
        unique_words = set(words)
        repetition_rate = 1.0 - (len(unique_words) / len(words))
        if repetition_rate > 0.5:  # More than 50% repetition
            return False

    return True


async def _transcribe_task(
    audio_url: str | None = None, video_url: str | None = None, language: str = "ja"
) -> None:
    """Background task to transcribe audio/video"""
    logger.info("Starting transcription task...")

    try:
        result = None

        if video_url:
            logger.info(f"Transcribing video: {video_url}")
            result, audio_file = whisper_client.download_and_transcribe_video(video_url)
        elif audio_url:
            # For audio URLs, we would need to download first
            # This is a simplified implementation
            logger.info(f"Audio URL transcription not yet implemented: {audio_url}")
            return

        if result:
            # Validate transcription quality using local function
            quality_passed = _validate_transcription_quality(result)

            logger.info("Transcription completed:")
            logger.info(f"  Text length: {len(result.text)} characters")
            logger.info(f"  Duration: {result.duration:.2f} seconds")
            logger.info(f"  Language: {result.language}")
            logger.info(f"  Quality passed: {quality_passed}")
            logger.info(f"  Preview: {result.text[:100]}...")

            # Normalize transcription data
            normalized_transcription = {
                "text": result.text,
                "language": result.language,
                "duration": result.duration,
                "quality_passed": quality_passed,
                "processing_date": datetime.now().isoformat(),
                "segments_count": len(result.segments) if result.segments else 0,
            }

            logger.info(f"Normalized transcription data: {normalized_transcription}")
            # TODO: Store transcription result in database

        else:
            logger.error("Transcription returned no result")

    except Exception as e:
        logger.error(f"Transcription task failed: {e}")


async def _collect_voting_data_task(
    vote_type: str = "all", force_refresh: bool = False
) -> None:
    """Background task to collect voting data and store in Airtable"""
    logger.info(f"Starting voting data collection task (type: {vote_type})...")

    try:
        # Fetch voting sessions from Diet website
        voting_sessions = voting_scraper.fetch_voting_sessions()
        logger.info(f"Scraped {len(voting_sessions)} voting sessions from Diet website")

        # Process and store the data
        sessions_processed = 0
        votes_processed = 0
        members_processed = 0
        errors = []
        unique_members = set()
        unique_parties = set()

        for session in voting_sessions:
            try:
                # Process voting session
                session_data = _normalize_voting_session(session)
                logger.debug(
                    f"Processing session: {session_data['bill_number']} - {session_data['bill_title'][:50]}..."
                )

                # Process individual vote records
                for vote_record in session.vote_records:
                    try:
                        # Normalize vote data
                        _normalize_vote_record(vote_record, session)

                        # Track unique members and parties for later processing
                        unique_members.add(
                            (
                                vote_record.member_name,
                                vote_record.party_name,
                                vote_record.constituency,
                            )
                        )
                        unique_parties.add(vote_record.party_name)

                        votes_processed += 1

                        # Rate limiting - respect Airtable API limits
                        await asyncio.sleep(0.2)

                    except Exception as e:
                        error_msg = f"Failed to process vote record for {vote_record.member_name}: {str(e)}"
                        logger.warning(error_msg)
                        errors.append(error_msg)

                sessions_processed += 1

                # TODO: Store session data in Airtable
                # TODO: Store vote records in Airtable

            except Exception as e:
                error_msg = (
                    f"Failed to process voting session {session.bill_number}: {str(e)}"
                )
                logger.warning(error_msg)
                errors.append(error_msg)

        # Process unique members and parties
        members_processed = len(unique_members)
        logger.info(
            f"Found {len(unique_parties)} unique parties and {members_processed} unique members"
        )

        # TODO: Store parties and members in Airtable if they don't exist

        logger.info("Voting data collection completed:")
        logger.info(f"  Sessions processed: {sessions_processed}")
        logger.info(f"  Votes processed: {votes_processed}")
        logger.info(f"  Members identified: {members_processed}")
        logger.info(f"  Parties identified: {len(unique_parties)}")
        logger.info(f"  Errors: {len(errors)}")

        if errors:
            logger.warning(f"First few errors: {errors[:3]}")

    except Exception as e:
        logger.error(f"Voting data collection task failed: {e}")


def _normalize_voting_session(session: VotingSession) -> dict[str, any]:
    """
    Normalize voting session data for Airtable storage

    Args:
        session: VotingSession object from scraper

    Returns:
        Normalized voting session data dictionary
    """
    return {
        "bill_number": session.bill_number,
        "bill_title": session.bill_title,
        "vote_date": session.vote_date.strftime("%Y-%m-%d"),
        "vote_type": session.vote_type,
        "vote_stage": session.vote_stage,
        "committee_name": session.committee_name,
        "house": "参議院",
        "total_votes": session.total_votes,
        "yes_votes": session.yes_votes,
        "no_votes": session.no_votes,
        "abstain_votes": session.abstain_votes,
        "absent_votes": session.absent_votes,
        "is_final_vote": session.vote_stage == "最終" if session.vote_stage else False,
    }


def _normalize_vote_record(
    vote_record: VoteRecord, session: VotingSession
) -> dict[str, any]:
    """
    Normalize individual vote record for Airtable storage

    Args:
        vote_record: VoteRecord object from scraper
        session: Parent VotingSession object

    Returns:
        Normalized vote record data dictionary
    """
    # Map Japanese vote results to standardized format
    vote_result_mapping = {
        "賛成": "yes",
        "反対": "no",
        "棄権": "abstain",
        "欠席": "absent",
        "出席": "present",
    }

    return {
        "member_name": vote_record.member_name,
        "member_name_kana": vote_record.member_name_kana,
        "party_name": vote_record.party_name,
        "constituency": vote_record.constituency,
        "house": vote_record.house,
        "vote_result": vote_result_mapping.get(
            vote_record.vote_result, vote_record.vote_result
        ),
        "vote_date": session.vote_date.strftime("%Y-%m-%d"),
        "vote_type": session.vote_type,
        "vote_stage": session.vote_stage,
        "committee_name": session.committee_name,
        "bill_number": session.bill_number,
        "bill_title": session.bill_title,
        "is_final_vote": session.vote_stage == "最終" if session.vote_stage else False,
    }


# Scheduler endpoints
@app.get("/scheduler/status")
async def get_scheduler_status() -> dict[str, Any]:
    """Get current scheduler status and task information"""
    if not scheduler:
        return {"status": "unavailable", "message": "Scheduler service not initialized"}

    return {
        "status": "available",
        "config": {
            "project_id": scheduler.config.project_id,
            "location": scheduler.config.location,
            "pubsub_topic": scheduler.config.pubsub_topic,
        },
        "tasks": scheduler.get_task_status(),
    }


@app.get("/scheduler/tasks")
async def get_all_scheduled_tasks() -> dict[str, Any]:
    """Get all scheduled tasks configuration"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler service not available")

    return scheduler.get_task_status()


@app.get("/scheduler/tasks/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get status of a specific scheduled task"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler service not available")

    task_status = scheduler.get_task_status(task_id)
    if "error" in task_status:
        raise HTTPException(status_code=404, detail=task_status["error"])

    return task_status


@app.post("/scheduler/setup")
async def setup_cloud_scheduler() -> dict[str, Any]:
    """Set up Google Cloud Scheduler jobs (admin only)"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler service not available")

    try:
        success = await scheduler.setup_cloud_scheduler()
        if success:
            return {
                "success": True,
                "message": "Cloud Scheduler jobs set up successfully",
            }
        else:
            return {
                "success": False,
                "message": "Failed to set up Cloud Scheduler jobs",
            }
    except Exception as e:
        logger.error(f"Failed to set up Cloud Scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scheduler/execute")
async def execute_scheduled_task(task_data: dict[str, Any]) -> dict[str, Any]:
    """Execute a scheduled task manually (for Pub/Sub integration)"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler service not available")

    try:
        success = await scheduler.handle_pubsub_message(task_data)
        return {
            "success": success,
            "message": "Task execution completed"
            if success
            else "Task execution failed",
        }
    except Exception as e:
        logger.error(f"Failed to execute scheduled task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scheduler/cleanup")
async def cleanup_scheduler_history(days_to_keep: int = 30) -> dict[str, Any]:
    """Clean up old scheduler execution history"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler service not available")

    try:
        cleaned_count = scheduler.cleanup_old_executions(days_to_keep)
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} old execution records",
            "cleaned_count": cleaned_count,
        }
    except Exception as e:
        logger.error(f"Failed to cleanup scheduler history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced scraper endpoints with resilience features
@app.get("/scraper/statistics")
async def get_scraper_statistics() -> dict[str, Any]:
    """Get scraper performance statistics and resilience metrics"""
    if not diet_scraper:
        raise HTTPException(status_code=503, detail="Diet scraper not available")

    return diet_scraper.get_scraper_statistics()


@app.get("/scraper/jobs")
async def get_scraper_jobs() -> dict[str, Any]:
    """Get all scraping jobs status"""
    if not diet_scraper:
        raise HTTPException(status_code=503, detail="Diet scraper not available")

    return diet_scraper.get_all_jobs()


@app.get("/scraper/jobs/{job_id}")
async def get_scraper_job_status(job_id: str) -> dict[str, Any]:
    """Get status of a specific scraping job"""
    if not diet_scraper:
        raise HTTPException(status_code=503, detail="Diet scraper not available")

    job_status = diet_scraper.get_job_status(job_id)
    if job_status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status


@app.post("/scraper/cleanup")
async def cleanup_scraper_cache(max_age_hours: int = 24) -> dict[str, Any]:
    """Clean up old scraper jobs and cache"""
    if not diet_scraper:
        raise HTTPException(status_code=503, detail="Diet scraper not available")

    try:
        cleaned_count = diet_scraper.cleanup_old_jobs(max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} old scraper jobs",
            "cleaned_count": cleaned_count,
        }
    except Exception as e:
        logger.error(f"Failed to cleanup scraper cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape/async", response_model=ScrapeResponse)
async def scrape_diet_data_async(request: ScrapeRequest) -> ScrapeResponse:
    """Scrape Diet data using enhanced async resilient scraper"""

    if not diet_scraper:
        raise HTTPException(status_code=500, detail="Service not properly initialized")

    try:
        # Use the async resilient scraper
        bills_data = await diet_scraper.fetch_current_bills_async(
            force_refresh=request.force_refresh
        )

        return ScrapeResponse(
            success=True,
            message=f"Successfully scraped {len(bills_data)} bills with resilience features",
            bills_processed=len(bills_data),
        )

    except Exception as e:
        logger.error(f"Async scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch processing endpoints
@app.get("/batch/status")
async def get_batch_status() -> dict[str, Any]:
    """Get batch processing queue status"""
    if not batch_processor:
        return {"status": "unavailable", "message": "Batch processor not initialized"}

    return batch_processor.get_queue_status()


@app.post("/batch/tasks")
async def add_batch_task(
    task_type: TaskType,
    payload: dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    timeout_seconds: int = 300,
    tags: list[str] | None = None,
    depends_on: list[str] | None = None,
) -> dict[str, str]:
    """Add a new task to the batch processing queue"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    try:
        task_id = await batch_processor.add_task(
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            tags=tags,
            depends_on=depends_on,
        )

        return {
            "task_id": task_id,
            "message": f"Task added to queue with priority {priority.value}",
        }

    except Exception as e:
        logger.error(f"Failed to add batch task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/tasks/{task_id}")
async def get_batch_task_status(task_id: str) -> dict[str, Any]:
    """Get status of a specific batch task"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    task_status = batch_processor.get_task_status(task_id)
    if task_status is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_status


@app.post("/batch/tasks/{task_id}/cancel")
async def cancel_batch_task(task_id: str) -> dict[str, Any]:
    """Cancel a queued or active batch task"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    try:
        cancelled = await batch_processor.cancel_task(task_id)
        if cancelled:
            return {"success": True, "message": f"Task {task_id} cancelled"}
        else:
            return {
                "success": False,
                "message": f"Task {task_id} not found or cannot be cancelled",
            }
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/cleanup")
async def cleanup_batch_tasks(max_age_hours: int = 24) -> dict[str, Any]:
    """Clean up old completed batch tasks"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    try:
        cleaned_count = batch_processor.cleanup_completed_tasks(max_age_hours)
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} old batch tasks",
            "cleaned_count": cleaned_count,
        }
    except Exception as e:
        logger.error(f"Failed to cleanup batch tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Convenience endpoints for specific batch operations
@app.post("/batch/embeddings")
async def queue_embedding_generation(
    texts: list[str],
    metadata_list: list[dict[str, Any]] | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> dict[str, str]:
    """Queue embedding generation for multiple texts"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    payload = {"texts": texts, "metadata_list": metadata_list or [{}] * len(texts)}

    try:
        task_id = await batch_processor.add_task(
            task_type=TaskType.GENERATE_EMBEDDINGS,
            payload=payload,
            priority=priority,
            tags=["embeddings", "batch"],
        )

        return {
            "task_id": task_id,
            "message": f"Queued embedding generation for {len(texts)} texts",
        }

    except Exception as e:
        logger.error(f"Failed to queue embedding generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/transcriptions")
async def queue_transcription_batch(
    audio_urls: list[str] | None = None,
    video_urls: list[str] | None = None,
    language: str = "ja",
    priority: TaskPriority = TaskPriority.NORMAL,
) -> dict[str, str]:
    """Queue transcription for multiple audio/video files"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    if not audio_urls and not video_urls:
        raise HTTPException(
            status_code=400,
            detail="At least one of audio_urls or video_urls must be provided",
        )

    payload = {
        "audio_urls": audio_urls or [],
        "video_urls": video_urls or [],
        "language": language,
    }

    try:
        task_id = await batch_processor.add_task(
            task_type=TaskType.TRANSCRIBE_AUDIO,
            payload=payload,
            priority=priority,
            timeout_seconds=1800,  # 30 minutes for transcription
            tags=["transcription", "batch"],
        )

        total_files = len(audio_urls or []) + len(video_urls or [])
        return {
            "task_id": task_id,
            "message": f"Queued transcription for {total_files} files",
        }

    except Exception as e:
        logger.error(f"Failed to queue transcription batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# House of Representatives voting endpoints
@app.post("/voting/hr/collect")
async def collect_hr_voting_data(
    days_back: int = 30, session_numbers: list[int] | None = None
) -> dict[str, Any]:
    """Collect voting data from House of Representatives PDFs"""
    if not hr_voting_scraper:
        raise HTTPException(
            status_code=503,
            detail="House of Representatives voting scraper not available",
        )

    try:
        logger.info(f"Starting HR voting data collection (days_back: {days_back})")

        voting_sessions = await hr_voting_scraper.fetch_recent_voting_sessions(
            days_back=days_back, session_numbers=session_numbers
        )

        # Process results
        total_sessions = len(voting_sessions)
        total_votes = sum(len(session.vote_records) for session in voting_sessions)

        # Extract unique members and parties
        unique_members = set()
        unique_parties = set()

        for session in voting_sessions:
            for vote_record in session.vote_records:
                unique_members.add(vote_record.member_name)
                unique_parties.add(vote_record.party_name)

        return {
            "success": True,
            "message": "Successfully collected HR voting data",
            "sessions_processed": total_sessions,
            "votes_processed": total_votes,
            "unique_members": len(unique_members),
            "unique_parties": len(unique_parties),
            "sessions": [
                {
                    "session_id": session.session_id,
                    "bill_number": session.bill_number,
                    "bill_title": session.bill_title,
                    "vote_date": session.vote_date.isoformat(),
                    "vote_summary": session.vote_summary,
                    "total_members": session.total_members,
                    "pdf_url": session.pdf_url,
                }
                for session in voting_sessions
            ],
        }

    except Exception as e:
        logger.error(f"Failed to collect HR voting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voting/hr/statistics")
async def get_hr_voting_statistics() -> dict[str, Any]:
    """Get House of Representatives voting scraper statistics"""
    if not hr_voting_scraper:
        raise HTTPException(
            status_code=503,
            detail="House of Representatives voting scraper not available",
        )

    return hr_voting_scraper.get_scraper_statistics()


@app.post("/batch/hr-voting")
async def queue_hr_voting_collection(
    days_back: int = 30,
    session_numbers: list[int] | None = None,
    priority: TaskPriority = TaskPriority.HIGH,
) -> dict[str, str]:
    """Queue House of Representatives voting data collection as batch task"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not available")

    payload = {
        "days_back": days_back,
        "session_numbers": session_numbers or [],
        "task_type": "hr_voting_collection",
    }

    try:
        task_id = await batch_processor.add_task(
            task_type=TaskType.PROCESS_VOTING_DATA,
            payload=payload,
            priority=priority,
            timeout_seconds=3600,  # 1 hour for PDF processing
            tags=["hr-voting", "pdf-processing", "batch"],
        )

        return {
            "task_id": task_id,
            "message": f"Queued HR voting data collection for {days_back} days",
        }

    except Exception as e:
        logger.error(f"Failed to queue HR voting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class HRProcessingRequest(BaseModel):
    """Request model for HR PDF processing"""

    days_back: int = 7
    session_numbers: list[int] | None = None
    max_concurrent: int = 2
    dry_run: bool = False


class HRProcessingResponse(BaseModel):
    """Response model for HR PDF processing"""

    success: bool
    message: str
    sessions_processed: int
    processing_time: float
    bills_created: int
    bills_updated: int
    members_created: int
    members_updated: int
    votes_created: int
    vote_records_created: int
    conflicts_detected: int
    errors: list[str] = []


@app.post("/hr/process", response_model=HRProcessingResponse)
async def process_hr_pdfs(
    request: HRProcessingRequest, background_tasks: BackgroundTasks
) -> HRProcessingResponse:
    """Process House of Representatives PDF voting data with enhanced extraction"""

    logger.info(
        f"Starting HR PDF processing: days_back={request.days_back}, dry_run={request.dry_run}"
    )

    try:
        # Run the complete HR integration pipeline
        pipeline_result = await run_hr_integration_pipeline(
            days_back=request.days_back,
            dry_run=request.dry_run,
            max_concurrent=request.max_concurrent,
        )

        # Extract results
        integration_result = pipeline_result.get("integration_results")

        if integration_result:
            return HRProcessingResponse(
                success=pipeline_result["success"],
                message="HR PDF processing completed successfully"
                if pipeline_result["success"]
                else "HR PDF processing completed with errors",
                sessions_processed=integration_result.sessions_processed,
                processing_time=pipeline_result["total_time"],
                bills_created=integration_result.bills_created,
                bills_updated=integration_result.bills_updated,
                members_created=integration_result.members_created,
                members_updated=integration_result.members_updated,
                votes_created=integration_result.votes_created,
                vote_records_created=integration_result.vote_records_created,
                conflicts_detected=integration_result.conflicts_detected,
                errors=pipeline_result.get("errors", []),
            )
        else:
            return HRProcessingResponse(
                success=False,
                message="HR PDF processing failed - no results generated",
                sessions_processed=0,
                processing_time=pipeline_result["total_time"],
                bills_created=0,
                bills_updated=0,
                members_created=0,
                members_updated=0,
                votes_created=0,
                vote_records_created=0,
                conflicts_detected=0,
                errors=pipeline_result.get(
                    "errors", ["No integration results generated"]
                ),
            )

    except Exception as e:
        logger.error(f"HR PDF processing failed: {e}")
        return HRProcessingResponse(
            success=False,
            message=f"HR PDF processing failed: {str(e)}",
            sessions_processed=0,
            processing_time=0.0,
            bills_created=0,
            bills_updated=0,
            members_created=0,
            members_updated=0,
            votes_created=0,
            vote_records_created=0,
            conflicts_detected=0,
            errors=[str(e)],
        )


@app.get("/hr/status")
async def get_hr_processing_status() -> dict[str, Any]:
    """Get House of Representatives processing status and statistics"""

    try:
        # Initialize processor to get current statistics
        processor = EnhancedHRProcessor()
        processing_stats = processor.get_processing_statistics()

        # Get base scraper statistics
        base_stats = {}
        if hr_voting_scraper:
            base_stats = hr_voting_scraper.get_scraper_statistics()

        return {
            "status": "ready",
            "service": "enhanced_hr_processor",
            "version": "1.0.0",
            "capabilities": [
                "pdf_text_extraction",
                "ocr_fallback",
                "member_name_matching",
                "quality_assessment",
                "data_validation",
                "conflict_resolution",
            ],
            "processing_statistics": processing_stats,
            "base_scraper_statistics": base_stats,
            "last_check": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get HR status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get HR processing status: {str(e)}"
        )


# Monitoring and Observability Endpoints
@app.get("/monitoring/overview")
async def monitoring_overview() -> dict[str, Any]:
    """Get comprehensive monitoring overview"""
    return get_dashboard_overview()


@app.get("/monitoring/pipeline")
async def monitoring_pipeline() -> dict[str, Any]:
    """Get processing pipeline status"""
    return get_pipeline_status()


@app.get("/monitoring/quality")
async def monitoring_quality() -> dict[str, Any]:
    """Get data quality metrics"""
    return get_quality_metrics()


@app.get("/monitoring/system")
async def monitoring_system() -> dict[str, Any]:
    """Get system resource metrics"""
    return get_system_status()


@app.get("/monitoring/alerts")
async def monitoring_alerts() -> dict[str, Any]:
    """Get alerts dashboard"""
    return get_alerts_dashboard()


@app.get("/monitoring/performance")
async def monitoring_performance(hours: int = 24) -> dict[str, Any]:
    """Get performance trends"""
    return get_performance_dashboard(hours)


@app.get("/monitoring/health")
async def monitoring_health() -> dict[str, Any]:
    """Get comprehensive health status"""
    return get_health_status()


@app.get("/metrics")
async def get_metrics(format: str = "json") -> dict[str, Any] | str:
    """Get metrics in specified format (json or prometheus)"""
    if format == "prometheus":
        return PlainTextResponse(
            content=get_metrics_export("prometheus"),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    else:
        return get_metrics_export("json")


# T52 Limited Scraping Endpoints
class T52ScrapeRequest(BaseModel):
    """Request model for T52 limited scraping"""

    dry_run: bool = True
    force_refresh: bool = False
    enable_stt: bool = False  # Disabled for cost control
    enable_embeddings: bool = True
    max_bills: int = 30
    max_voting_sessions: int = 10


class T52ScrapeResponse(BaseModel):
    """Response model for T52 limited scraping"""

    success: bool
    message: str
    total_time: float
    bills_collected: int
    voting_sessions_collected: int
    speeches_processed: int
    embeddings_generated: int
    transcriptions_completed: int
    errors: list[str]
    performance_metrics: dict[str, Any]


@app.post("/t52/scrape", response_model=T52ScrapeResponse)
async def execute_t52_limited_scraping(request: T52ScrapeRequest) -> T52ScrapeResponse:
    """Execute T52 limited scope scraping for June 2025 first week"""

    if not limited_scrape_coordinator:
        raise HTTPException(
            status_code=503, detail="Limited scraping coordinator not available"
        )

    logger.info(f"Starting T52 limited scraping (dry_run: {request.dry_run})")

    try:
        # Get target configuration
        target = limited_scrape_coordinator.get_june_first_week_target()

        # Apply request parameters
        target.enable_stt = request.enable_stt
        target.enable_embeddings = request.enable_embeddings
        target.max_bills = request.max_bills
        target.max_voting_sessions = request.max_voting_sessions

        # Execute pipeline
        result = await limited_scrape_coordinator.execute_limited_scraping(
            target=target, dry_run=request.dry_run
        )

        return T52ScrapeResponse(
            success=result.success,
            message="T52 limited scraping completed successfully"
            if result.success
            else "T52 limited scraping completed with errors",
            total_time=result.total_time,
            bills_collected=result.bills_collected,
            voting_sessions_collected=result.voting_sessions_collected,
            speeches_processed=result.speeches_processed,
            embeddings_generated=result.embeddings_generated,
            transcriptions_completed=result.transcriptions_completed,
            errors=result.errors,
            performance_metrics=result.performance_metrics,
        )

    except Exception as e:
        logger.error(f"T52 limited scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/t52/status")
async def get_t52_status() -> dict[str, Any]:
    """Get T52 limited scraping pipeline status"""

    if not limited_scrape_coordinator:
        return {
            "status": "unavailable",
            "message": "Limited scraping coordinator not initialized",
        }

    return limited_scrape_coordinator.get_pipeline_status()


@app.get("/t52/target")
async def get_t52_target() -> dict[str, Any]:
    """Get T52 target configuration"""

    if not limited_scrape_coordinator:
        raise HTTPException(
            status_code=503, detail="Limited scraping coordinator not available"
        )

    target = limited_scrape_coordinator.get_june_first_week_target()

    return {
        "start_date": target.start_date.isoformat(),
        "end_date": target.end_date.isoformat(),
        "max_bills": target.max_bills,
        "max_voting_sessions": target.max_voting_sessions,
        "max_speeches": target.max_speeches,
        "enable_stt": target.enable_stt,
        "enable_embeddings": target.enable_embeddings,
        "description": "Limited scraping for June 2025 first week (2025-06-02 to 2025-06-08)",
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
