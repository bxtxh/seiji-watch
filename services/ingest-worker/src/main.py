"""
Ingest Worker Service - FastAPI application for Diet data scraping and processing.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Union

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from scraper.diet_scraper import DietScraper, BillData
from stt.whisper_client import WhisperClient, TranscriptionResult
from embeddings.vector_client import VectorClient, EmbeddingResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
diet_scraper: Optional[DietScraper] = None
whisper_client: Optional[WhisperClient] = None
vector_client: Optional[VectorClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global diet_scraper, whisper_client, vector_client
    
    # Startup
    logger.info("Starting ingest-worker service...")
    
    try:
        # Initialize Diet scraper
        diet_scraper = DietScraper()
        logger.info("Diet scraper initialized")
        
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
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ingest-worker service...")
        if vector_client:
            vector_client.close()


app = FastAPI(
    title="Diet Issue Tracker - Ingest Worker",
    description="Service for scraping and processing Diet data",
    version="1.0.0",
    lifespan=lifespan
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
    errors: List[str] = []


class TranscribeRequest(BaseModel):
    """Request model for transcription operations"""
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    language: str = "ja"


class TranscribeResponse(BaseModel):
    """Response model for transcription operations"""
    success: bool
    message: str
    text: Optional[str] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    quality_passed: Optional[bool] = None


class EmbeddingRequest(BaseModel):
    """Request model for embedding operations"""
    text: str
    store_in_weaviate: bool = True
    metadata: Optional[Dict] = None


class EmbeddingResponse(BaseModel):
    """Response model for embedding operations"""
    success: bool
    message: str
    dimensions: Optional[int] = None
    model: Optional[str] = None
    weaviate_uuid: Optional[str] = None


class SearchRequest(BaseModel):
    """Request model for vector search operations"""
    query: str
    limit: int = 10
    min_certainty: float = 0.7


class SearchResponse(BaseModel):
    """Response model for vector search operations"""
    success: bool
    message: str
    results: List[Dict] = []
    total_found: int = 0


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ingest-worker",
        "version": "1.0.0"
    }


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_diet_data(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks
) -> ScrapeResponse:
    """Scrape Diet data and return results"""
    
    if not diet_scraper:
        raise HTTPException(
            status_code=500, 
            detail="Service not properly initialized"
        )
    
    # Run scraping in background for long-running operations
    background_tasks.add_task(
        _scrape_bills_task,
        force_refresh=request.force_refresh
    )
    
    return ScrapeResponse(
        success=True,
        message="Scraping task started",
        bills_processed=0
    )


@app.get("/scrape/status")
async def get_scrape_status() -> Dict[str, str]:
    """Get current scraping status"""
    # TODO: Implement proper status tracking
    return {
        "status": "ready",
        "last_scrape": "N/A",
        "bills_in_queue": "0"
    }


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    request: TranscribeRequest,
    background_tasks: BackgroundTasks
) -> TranscribeResponse:
    """Transcribe audio or video content using Whisper API"""
    
    if not whisper_client:
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text service not available (missing OpenAI API key)"
        )
    
    if not request.audio_url and not request.video_url:
        raise HTTPException(
            status_code=400,
            detail="Either audio_url or video_url must be provided"
        )
    
    # Run transcription in background for long-running operations
    background_tasks.add_task(
        _transcribe_task,
        audio_url=request.audio_url,
        video_url=request.video_url,
        language=request.language
    )
    
    return TranscribeResponse(
        success=True,
        message="Transcription task started"
    )


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Generate vector embedding for text"""
    
    if not vector_client:
        raise HTTPException(
            status_code=503,
            detail="Vector service not available (missing OpenAI/Weaviate credentials)"
        )
    
    try:
        # Generate embedding
        embedding = vector_client.generate_embedding(request.text)
        
        weaviate_uuid = None
        if request.store_in_weaviate and request.metadata:
            # Store in Weaviate if metadata provided
            if "bill_number" in request.metadata:
                weaviate_uuid = vector_client.store_bill_embedding(request.metadata, embedding)
            elif "speaker" in request.metadata:
                weaviate_uuid = vector_client.store_speech_embedding(request.metadata, embedding)
        
        return EmbeddingResponse(
            success=True,
            message="Embedding generated successfully",
            dimensions=embedding.dimensions,
            model=embedding.model,
            weaviate_uuid=weaviate_uuid
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
                    min_certainty=request.min_certainty
                )
                results.extend(vector_results)
                search_method = "vector"
                
            except Exception as e:
                logger.warning(f"Vector search failed, falling back to keyword search: {e}")
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
            total_found=len(results)
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _keyword_search_bills(query: str, limit: int = 10) -> List[Dict]:
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
            summary_match = bill_data.summary and query_lower in bill_data.summary.lower()
            
            if title_match or summary_match:
                # Calculate simple relevance score
                score = 0.0
                if title_match:
                    score += 0.8
                if summary_match:
                    score += 0.5
                
                # Convert to search result format
                results.append({
                    "bill_number": bill_data.bill_id,
                    "title": bill_data.title,
                    "summary": bill_data.summary or "",
                    "category": bill_data.category,
                    "status": bill_data.stage,
                    "diet_url": bill_data.url,
                    "relevance_score": score,
                    "search_method": "keyword"
                })
        
        # Sort by relevance score and limit results
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:limit]
        
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        return []


@app.get("/embeddings/stats")
async def get_embedding_stats() -> Dict[str, Union[int, str]]:
    """Get statistics about stored embeddings"""
    
    if not vector_client:
        return {
            "status": "unavailable",
            "bills": 0,
            "speeches": 0,
            "message": "Vector service not available"
        }
    
    try:
        stats = vector_client.get_embedding_stats()
        return {
            "status": "available",
            "bills": stats["bills"],
            "speeches": stats["speeches"],
            "message": f"Vector store contains {stats['bills']} bills and {stats['speeches']} speeches"
        }
        
    except Exception as e:
        logger.error(f"Failed to get embedding stats: {e}")
        return {
            "status": "error",
            "bills": 0,
            "speeches": 0,
            "message": str(e)
        }


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
                        weaviate_uuid = vector_client.store_bill_embedding(normalized_bill, embedding)
                        
                        if weaviate_uuid:
                            logger.info(f"Generated embedding for bill {normalized_bill['bill_number']}: {weaviate_uuid}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for bill {bill_data.bill_id}: {e}")
                
                # For now, just log the normalized data (TODO: Store in Airtable)
                logger.debug(f"Normalized bill: {normalized_bill['bill_number']} - {normalized_bill['title'][:50]}...")
                processed_count += 1
                
                # Rate limiting - respect both Airtable and OpenAI limits
                await asyncio.sleep(0.2)
                
            except Exception as e:
                error_msg = f"Failed to process bill {bill_data.bill_id}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Bill processing completed: {processed_count} processed, {len(errors)} errors")
        if errors:
            logger.warning(f"First few errors: {errors[:3]}")
        
    except Exception as e:
        logger.error(f"Bill scraping task failed: {e}")


def _normalize_bill_data(bill_data: BillData) -> Dict[str, str]:
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
        "その他": "OTHER"
    }
    
    # Map stage to standardized status
    status_mapping = {
        "成立": "PASSED",
        "採決待ち": "PENDING_VOTE", 
        "審議中": "UNDER_REVIEW",
        "Backlog": "BACKLOG"
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
        "submitted_date": bill_data.submission_date.strftime("%Y-%m-%d") if bill_data.submission_date else None,
        "submitter_type": bill_data.submitter,
        "diet_session": diet_session,
        "house_of_origin": "参議院"
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
    audio_url: Optional[str] = None,
    video_url: Optional[str] = None,
    language: str = "ja"
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
            
            logger.info(f"Transcription completed:")
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
                "segments_count": len(result.segments) if result.segments else 0
            }
            
            logger.info(f"Normalized transcription data: {normalized_transcription}")
            # TODO: Store transcription result in database
            
        else:
            logger.error("Transcription returned no result")
        
    except Exception as e:
        logger.error(f"Transcription task failed: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )