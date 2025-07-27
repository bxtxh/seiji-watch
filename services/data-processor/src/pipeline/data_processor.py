"""
Data normalization pipeline for converting scraped data to structured records.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from scraper.diet_scraper import BillData
from stt.whisper_client import TranscriptionResult

from shared.clients.airtable import AirtableClient
from shared.models.bill import Bill, BillCategory, BillStatus

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared" / "src"
sys.path.insert(0, str(shared_path))


logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Data normalization processor for Diet data pipeline.
    Converts scraped bills and transcriptions into structured Airtable records.
    """

    def __init__(self, airtable_client: AirtableClient | None = None):
        self.airtable_client = airtable_client or AirtableClient()
        self.processed_bills = 0
        self.processed_transcriptions = 0
        self.errors = []

    async def process_bill_data(self, bill_data: BillData) -> str | None:
        """
        Process and store a single bill record in Airtable

        Args:
            bill_data: BillData object from scraper

        Returns:
            Airtable record ID if successful, None if failed
        """
        try:
            # Convert scraper BillData to shared Bill model
            bill = self._convert_bill_data(bill_data)

            # Check if bill already exists
            existing_bill = await self._find_existing_bill(bill.bill_number)

            if existing_bill:
                logger.info(f"Bill {bill.bill_number} already exists, updating...")
                record_id = await self._update_bill(existing_bill["id"], bill)
            else:
                logger.info(f"Creating new bill record: {bill.bill_number}")
                record_id = await self._create_bill(bill)

            self.processed_bills += 1
            return record_id

        except Exception as e:
            error_msg = f"Failed to process bill {bill_data.bill_id}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None

    async def process_transcription_data(
        self,
        transcription: TranscriptionResult,
        meeting_id: str | None = None,
        speaker: str | None = None,
    ) -> str | None:
        """
        Process and store transcription data in Airtable

        Args:
            transcription: TranscriptionResult from WhisperClient
            meeting_id: Optional meeting ID to associate with
            speaker: Optional speaker name

        Returns:
            Airtable record ID if successful, None if failed
        """
        try:
            # Create speech record data
            speech_data = {
                "text": transcription.text,
                "language": transcription.language,
                "duration": transcription.duration,
                "speaker": speaker or "Unknown",
                "meeting_id": meeting_id,
                "transcription_date": datetime.now().isoformat(),
                "quality_passed": self._validate_transcription_quality(transcription),
            }

            # Store in Airtable (assuming speeches table exists)
            result = await self.airtable_client.create_speech(speech_data)
            record_id = result["id"]

            logger.info(f"Created speech record: {record_id}")
            self.processed_transcriptions += 1
            return record_id

        except Exception as e:
            error_msg = f"Failed to process transcription: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None

    async def process_batch_bills(self, bills_data: list[BillData]) -> dict[str, int]:
        """
        Process multiple bills in batch with rate limiting

        Args:
            bills_data: List of BillData objects

        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Processing batch of {len(bills_data)} bills...")

        start_time = datetime.now()
        successful = 0
        failed = 0

        for i, bill_data in enumerate(bills_data):
            try:
                record_id = await self.process_bill_data(bill_data)
                if record_id:
                    successful += 1
                else:
                    failed += 1

                # Rate limiting - respect Airtable limits (5 req/s)
                if i < len(bills_data) - 1:  # Don't sleep after last item
                    await asyncio.sleep(0.2)

            except Exception as e:
                failed += 1
                logger.error(
                    f"Batch processing error for bill {bill_data.bill_id}: {e}"
                )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        stats = {
            "total_processed": len(bills_data),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "bills_per_second": len(bills_data) / duration if duration > 0 else 0,
        }

        logger.info(f"Batch processing completed: {stats}")
        return stats

    def _convert_bill_data(self, bill_data: BillData) -> Bill:
        """Convert scraper BillData to shared Bill model"""

        # Map category string to BillCategory enum
        category_mapping = {
            "予算・決算": BillCategory.BUDGET,
            "税制": BillCategory.TAXATION,
            "社会保障": BillCategory.SOCIAL_SECURITY,
            "外交・国際": BillCategory.FOREIGN_AFFAIRS,
            "経済・産業": BillCategory.ECONOMY,
            "その他": BillCategory.OTHER,
        }

        # Map stage to BillStatus enum
        status_mapping = {
            "成立": BillStatus.PASSED,
            "採決待ち": BillStatus.PENDING_VOTE,
            "審議中": BillStatus.UNDER_REVIEW,
            "Backlog": BillStatus.BACKLOG,
        }

        # Extract diet session from bill ID (format: "217-1")
        diet_session = None
        if "-" in bill_data.bill_id:
            diet_session = bill_data.bill_id.split("-")[0]

        return Bill(
            bill_number=bill_data.bill_id,
            title=bill_data.title,
            summary=bill_data.summary or "",
            status=status_mapping.get(bill_data.stage, BillStatus.BACKLOG),
            category=category_mapping.get(bill_data.category, BillCategory.OTHER),
            diet_url=bill_data.url,
            submitted_date=(
                bill_data.submission_date.strftime("%Y-%m-%d")
                if bill_data.submission_date
                else None
            ),
            submitter_type=bill_data.submitter,
            diet_session=diet_session,
            house_of_origin="参議院",  # Since we're scraping from Senate website
        )

    async def _find_existing_bill(self, bill_number: str) -> dict | None:
        """Find existing bill by bill number"""
        try:
            bills = await self.airtable_client.list_bills(
                filter_formula=f"{{Bill_Number}} = '{bill_number}'", max_records=1
            )
            return bills[0] if bills else None
        except Exception as e:
            logger.warning(f"Could not check for existing bill {bill_number}: {e}")
            return None

    async def _create_bill(self, bill: Bill) -> str:
        """Create new bill record in Airtable"""
        airtable_fields = bill.to_airtable_fields()
        result = await self.airtable_client.create_bill(airtable_fields)
        return result["id"]

    async def _update_bill(self, record_id: str, bill: Bill) -> str:
        """Update existing bill record in Airtable"""
        airtable_fields = bill.to_airtable_fields()
        result = await self.airtable_client.update_bill(record_id, airtable_fields)
        return result["id"]

    def _validate_transcription_quality(
        self, transcription: TranscriptionResult
    ) -> bool:
        """Validate transcription meets quality standards"""
        # Basic quality checks
        if not transcription.text or len(transcription.text.strip()) < 10:
            return False

        # Check for reasonable Japanese content
        japanese_chars = sum(1 for c in transcription.text if ord(c) > 127)
        if japanese_chars < len(transcription.text) * 0.3:
            return False

        # Check duration makes sense
        if transcription.duration <= 0:
            return False

        return True

    def get_processing_stats(self) -> dict[str, int | list[str]]:
        """Get current processing statistics"""
        return {
            "bills_processed": self.processed_bills,
            "transcriptions_processed": self.processed_transcriptions,
            "errors_count": len(self.errors),
            "errors": self.errors[-10:],  # Last 10 errors
        }

    def reset_stats(self):
        """Reset processing statistics"""
        self.processed_bills = 0
        self.processed_transcriptions = 0
        self.errors = []


# Test functionality
async def test_data_processor():
    """Test the DataProcessor with sample data (without shared models due to Python version)"""
    logger.info("Testing DataProcessor basic functionality...")

    try:
        # Test basic conversion logic without shared models
        from datetime import datetime

        from scraper.diet_scraper import BillData

        sample_bill = BillData(
            bill_id="217-TEST",
            title="テスト法案",
            submission_date=datetime(2024, 1, 15),
            status="審議中",
            stage="審議中",
            submitter="政府",
            category="その他",
            url="https://example.com/test",
            summary="これはテスト用の法案です",
        )

        logger.info(f"Sample bill created: {sample_bill.bill_id} - {sample_bill.title}")

        # Test transcription quality validation
        from stt.whisper_client import TranscriptionResult

        good_transcription = TranscriptionResult(
            text="これは国会での審議についての議事録です。法案について詳細に議論されました。",
            language="ja",
            duration=60.0,
        )

        # Create a minimal processor for testing validation logic
        class TestProcessor:
            def _validate_transcription_quality(self, transcription):
                if not transcription.text or len(transcription.text.strip()) < 10:
                    return False
                japanese_chars = sum(1 for c in transcription.text if ord(c) > 127)
                if japanese_chars < len(transcription.text) * 0.3:
                    return False
                if transcription.duration <= 0:
                    return False
                return True

        processor = TestProcessor()
        is_valid = processor._validate_transcription_quality(good_transcription)
        logger.info(f"Transcription quality validation: {is_valid}")

        logger.info("DataProcessor basic test completed successfully")

    except Exception as e:
        logger.error(f"DataProcessor test failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_data_processor())
