"""Speech-related API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from shared.clients.airtable import AirtableClient

from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speeches", tags=["speeches"])


# Pydantic models for request/response
class SpeechSummaryRequest(BaseModel):
    speech_id: str
    regenerate: bool = False


class SpeechTopicsRequest(BaseModel):
    speech_id: str
    regenerate: bool = False


class BatchProcessRequest(BaseModel):
    speech_ids: list[str]
    generate_summaries: bool = True
    extract_topics: bool = True
    regenerate: bool = False


class SpeechResponse(BaseModel):
    id: str
    speaker_name: str | None
    original_text: str
    summary: str | None
    topics: list[str] | None
    is_processed: bool


# Dependency injection
async def get_airtable_client() -> AirtableClient:
    """Get Airtable client instance."""
    return AirtableClient()


async def get_llm_service() -> LLMService:
    """Get LLM service instance."""
    return LLMService()


@router.get("/health")
async def health_check(
    airtable: AirtableClient = Depends(get_airtable_client),
    llm: LLMService = Depends(get_llm_service),
):
    """Health check for speech services."""
    airtable_healthy = await airtable.health_check()
    llm_healthy = await llm.health_check()

    return {
        "status": "healthy" if (airtable_healthy and llm_healthy) else "unhealthy",
        "airtable": "healthy" if airtable_healthy else "unhealthy",
        "llm": "healthy" if llm_healthy else "unhealthy",
    }


@router.get("/{speech_id}")
async def get_speech(
    speech_id: str, airtable: AirtableClient = Depends(get_airtable_client)
) -> SpeechResponse:
    """Get a speech by ID."""
    try:
        speech_record = await airtable.get_speech(speech_id)
        fields = speech_record.get("fields", {})

        return SpeechResponse(
            id=speech_record["id"],
            speaker_name=fields.get("Speaker_Name"),
            original_text=fields.get("Original_Text", ""),
            summary=fields.get("Summary"),
            topics=(
                fields.get("Topics", "").split(",") if fields.get("Topics") else None
            ),
            is_processed=fields.get("Is_Processed", False),
        )
    except Exception as e:
        logger.error(f"Failed to get speech {speech_id}: {e}")
        raise HTTPException(status_code=404, detail="Speech not found")


@router.get("/")
async def list_speeches(
    limit: int = Query(default=50, le=100),
    processed_only: bool = Query(default=False),
    airtable: AirtableClient = Depends(get_airtable_client),
) -> list[SpeechResponse]:
    """List speeches with optional filtering."""
    try:
        filter_formula = None
        if processed_only:
            filter_formula = "{Is_Processed} = TRUE()"

        speech_records = await airtable.list_speeches(
            filter_formula=filter_formula, max_records=limit
        )

        speeches = []
        for record in speech_records:
            fields = record.get("fields", {})
            speeches.append(
                SpeechResponse(
                    id=record["id"],
                    speaker_name=fields.get("Speaker_Name"),
                    original_text=fields.get("Original_Text", ""),
                    summary=fields.get("Summary"),
                    topics=(
                        fields.get("Topics", "").split(",")
                        if fields.get("Topics")
                        else None
                    ),
                    is_processed=fields.get("Is_Processed", False),
                )
            )

        return speeches
    except Exception as e:
        logger.error(f"Failed to list speeches: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve speeches")


@router.post("/{speech_id}/summary")
async def generate_speech_summary(
    speech_id: str,
    request: SpeechSummaryRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
    llm: LLMService = Depends(get_llm_service),
):
    """Generate summary for a speech."""
    try:
        # Get speech from Airtable
        speech_record = await airtable.get_speech(speech_id)
        fields = speech_record.get("fields", {})

        # Check if summary already exists and regenerate is not requested
        if fields.get("Summary") and not request.regenerate:
            return {
                "speech_id": speech_id,
                "summary": fields["Summary"],
                "regenerated": False,
            }

        # Generate new summary
        original_text = fields.get("Original_Text", "")
        speaker_name = fields.get("Speaker_Name")

        if not original_text:
            raise HTTPException(status_code=400, detail="Speech has no original text")

        summary = await llm.generate_speech_summary(original_text, speaker_name)

        # Update Airtable record
        update_data = {"Summary": summary, "Is_Processed": True}
        await airtable._rate_limited_request(
            "PATCH",
            f"{airtable.base_url}/Speeches/{speech_id}",
            json={"fields": update_data},
        )

        return {"speech_id": speech_id, "summary": summary, "regenerated": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary for speech {speech_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate summary")


@router.post("/{speech_id}/topics")
async def extract_speech_topics(
    speech_id: str,
    request: SpeechTopicsRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
    llm: LLMService = Depends(get_llm_service),
):
    """Extract topics for a speech."""
    try:
        # Get speech from Airtable
        speech_record = await airtable.get_speech(speech_id)
        fields = speech_record.get("fields", {})

        # Check if topics already exist and regenerate is not requested
        if fields.get("Topics") and not request.regenerate:
            topics = fields["Topics"].split(",") if fields["Topics"] else []
            return {"speech_id": speech_id, "topics": topics, "regenerated": False}

        # Extract new topics
        original_text = fields.get("Original_Text", "")
        speaker_name = fields.get("Speaker_Name")

        if not original_text:
            raise HTTPException(status_code=400, detail="Speech has no original text")

        topics = await llm.extract_speech_topics(original_text, speaker_name)

        # Update Airtable record
        update_data = {"Topics": ",".join(topics), "Is_Processed": True}
        await airtable._rate_limited_request(
            "PATCH",
            f"{airtable.base_url}/Speeches/{speech_id}",
            json={"fields": update_data},
        )

        return {"speech_id": speech_id, "topics": topics, "regenerated": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract topics for speech {speech_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract topics")


@router.post("/batch-process")
async def batch_process_speeches(
    request: BatchProcessRequest,
    airtable: AirtableClient = Depends(get_airtable_client),
    llm: LLMService = Depends(get_llm_service),
):
    """Process multiple speeches in batch."""
    try:
        # Get speeches from Airtable
        speeches_data = []
        for speech_id in request.speech_ids:
            try:
                speech_record = await airtable.get_speech(speech_id)
                fields = speech_record.get("fields", {})

                # Skip if already processed and regenerate is not requested
                has_summary = bool(fields.get("Summary"))
                has_topics = bool(fields.get("Topics"))

                skip_summary = (
                    has_summary
                    and not request.regenerate
                    and request.generate_summaries
                )
                skip_topics = (
                    has_topics and not request.regenerate and request.extract_topics
                )

                if skip_summary and skip_topics:
                    continue

                speeches_data.append(
                    {
                        "id": speech_record["id"],
                        "original_text": fields.get("Original_Text", ""),
                        "speaker_name": fields.get("Speaker_Name"),
                        "existing_summary": fields.get("Summary"),
                        "existing_topics": fields.get("Topics"),
                        "needs_summary": request.generate_summaries
                        and (not has_summary or request.regenerate),
                        "needs_topics": request.extract_topics
                        and (not has_topics or request.regenerate),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to get speech {speech_id}: {e}")
                continue

        if not speeches_data:
            return {
                "processed_count": 0,
                "skipped_count": len(request.speech_ids),
                "message": "All speeches already processed or not found",
            }

        # Process speeches with LLM
        processed_speeches = await llm.batch_process_speeches(
            speeches_data,
            generate_summaries=request.generate_summaries,
            extract_topics=request.extract_topics,
        )

        # Update Airtable records
        updated_count = 0
        for speech in processed_speeches:
            try:
                update_data = {"Is_Processed": True}

                if speech.get("summary") and speech["needs_summary"]:
                    update_data["Summary"] = speech["summary"]

                if speech.get("topics") and speech["needs_topics"]:
                    update_data["Topics"] = ",".join(speech["topics"])

                if len(update_data) > 1:  # More than just Is_Processed
                    await airtable._rate_limited_request(
                        "PATCH",
                        f"{airtable.base_url}/Speeches/{speech['id']}",
                        json={"fields": update_data},
                    )
                    updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update speech {speech.get('id')}: {e}")

        return {
            "processed_count": updated_count,
            "skipped_count": len(request.speech_ids) - len(speeches_data),
            "total_requested": len(request.speech_ids),
        }

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail="Batch processing failed")


@router.get("/search/by-topic")
async def search_speeches_by_topic(
    topic: str = Query(..., min_length=1),
    limit: int = Query(default=20, le=100),
    airtable: AirtableClient = Depends(get_airtable_client),
) -> list[SpeechResponse]:
    """Search speeches by topic."""
    try:
        filter_formula = f"FIND('{topic}', {{Topics}}) > 0"

        speech_records = await airtable.list_speeches(
            filter_formula=filter_formula, max_records=limit
        )

        speeches = []
        for record in speech_records:
            fields = record.get("fields", {})
            speeches.append(
                SpeechResponse(
                    id=record["id"],
                    speaker_name=fields.get("Speaker_Name"),
                    original_text=fields.get("Original_Text", ""),
                    summary=fields.get("Summary"),
                    topics=(
                        fields.get("Topics", "").split(",")
                        if fields.get("Topics")
                        else None
                    ),
                    is_processed=fields.get("Is_Processed", False),
                )
            )

        return speeches
    except Exception as e:
        logger.error(f"Topic search failed: {e}")
        raise HTTPException(status_code=500, detail="Topic search failed")
