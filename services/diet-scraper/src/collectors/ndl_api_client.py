"""
NDL (National Diet Library) Minutes API Client

Provides rate-limited HTTP client for accessing NDL Meeting Minutes API
with proper error handling and exponential backoff.

Rate Limit: ≤3 requests/second (polite crawling)
API Documentation: https://kokkai.ndl.go.jp/api/
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class NDLMeeting:
    """NDL API Meeting data structure"""

    meeting_id: str
    title: str
    meeting_date: date
    diet_session: int
    house: str  # "参議院" or "衆議院"
    committee_name: str | None = None
    meeting_type: str | None = None
    pdf_url: str | None = None


@dataclass
class NDLSpeech:
    """NDL API Speech data structure"""

    speech_id: str
    meeting_id: str
    speaker_name: str
    speaker_group: str | None  # 政党名
    speech_type: str  # "質問", "答弁", "発言"
    speech_order: int
    speech_content: str
    speech_datetime: datetime | None = None


class NDLRateLimiter:
    """Rate limiter for NDL API (≤3 requests/second)"""

    def __init__(self, max_requests: int = 3, per_seconds: float = 1.0):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request"""
        async with self._lock:
            now = time.time()

            # Remove old requests outside the window
            self.requests = [
                req_time
                for req_time in self.requests
                if now - req_time < self.per_seconds
            ]

            # Wait if we've hit the limit
            if len(self.requests) >= self.max_requests:
                sleep_time = self.per_seconds - (now - self.requests[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    # Retry after sleeping
                    return await self.acquire()

            # Record this request
            self.requests.append(now)


class NDLAPIClient:
    """
    National Diet Library Minutes API Client

    Provides access to meeting minutes and speech data from the NDL API
    with proper rate limiting and error handling.
    """

    BASE_URL = "https://kokkai.ndl.go.jp/api"

    def __init__(self, max_requests_per_second: int = 3, timeout: float = 30.0):
        self.rate_limiter = NDLRateLimiter(max_requests_per_second)
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        # HTTP client with proper headers
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Diet-Issue-Tracker/1.0 (Educational Research; +https://github.com/diet-tracker)"
            },
            timeout=httpx.Timeout(timeout),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=60)
    )
    async def _make_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make rate-limited API request with retry logic"""
        await self.rate_limiter.acquire()

        url = f"{self.BASE_URL}/{endpoint}"
        query_string = urlencode(params)
        full_url = f"{url}?{query_string}"

        self.logger.debug(f"NDL API request: {full_url}")

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            self.logger.debug(
                f"NDL API response: {data.get('numberOfRecords', 0)} records"
            )
            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit exceeded
                self.logger.warning("NDL API rate limit exceeded, waiting 60s")
                await asyncio.sleep(60)
                raise
            elif 500 <= e.response.status_code < 600:  # Server error
                self.logger.error(f"NDL API server error: {e}")
                raise
            else:
                self.logger.error(f"NDL API client error: {e}")
                raise
        except Exception as e:
            self.logger.error(f"NDL API request failed: {e}")
            raise

    async def search_meetings(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        diet_session: int | None = None,
        house: str | None = None,
        committee: str | None = None,
        start_record: int = 1,
        max_records: int = 100,
    ) -> list[NDLMeeting]:
        """
        Search for meetings using NDL API

        Args:
            start_date: Meeting start date (YYYY-MM-DD)
            end_date: Meeting end date (YYYY-MM-DD)
            diet_session: Diet session number (e.g., 217)
            house: "参議院" or "衆議院"
            committee: Committee name
            start_record: Starting record number (1-indexed)
            max_records: Maximum records to return (1-100)

        Returns:
            List of NDLMeeting objects
        """
        params = {
            "startRecord": start_record,
            "maximumRecords": min(max_records, 100),  # API limit
        }

        # Add optional filters
        if start_date:
            params["from"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["until"] = end_date.strftime("%Y-%m-%d")
        if diet_session:
            params["sessionNumber"] = diet_session
        if house:
            params["house"] = house
        if committee:
            params["nameOfMeeting"] = committee

        try:
            data = await self._make_request("meeting", params)
            meetings = []

            meeting_records = data.get("meetingRecord", [])
            self.logger.info(f"Found {len(meeting_records)} meetings")

            for record in meeting_records:
                meeting = self._parse_meeting_record(record)
                if meeting:
                    meetings.append(meeting)

            return meetings

        except Exception as e:
            self.logger.error(f"Failed to search meetings: {e}")
            return []

    async def get_speeches(
        self, meeting_id: str, start_record: int = 1, max_records: int = 100
    ) -> list[NDLSpeech]:
        """
        Get speech records for a specific meeting

        Args:
            meeting_id: NDL meeting ID
            start_record: Starting record number (1-indexed)
            max_records: Maximum records to return (1-100)

        Returns:
            List of NDLSpeech objects
        """
        params = {
            "startRecord": start_record,
            "maximumRecords": min(max_records, 100),
            "meetingId": meeting_id,
        }

        try:
            data = await self._make_request("speech", params)
            speeches = []

            speech_records = data.get("speechRecord", [])
            self.logger.info(
                f"Found {len(speech_records)} speeches for meeting {meeting_id}"
            )

            for record in speech_records:
                speech = self._parse_speech_record(record)
                if speech:
                    speeches.append(speech)

            return speeches

        except Exception as e:
            self.logger.error(f"Failed to get speeches for meeting {meeting_id}: {e}")
            return []

    async def get_all_speeches_for_meeting(self, meeting_id: str) -> list[NDLSpeech]:
        """
        Get all speech records for a meeting (handles pagination)

        Args:
            meeting_id: NDL meeting ID

        Returns:
            List of all NDLSpeech objects for the meeting
        """
        all_speeches = []
        start_record = 1
        batch_size = 100

        while True:
            speeches = await self.get_speeches(
                meeting_id=meeting_id, start_record=start_record, max_records=batch_size
            )

            if not speeches:
                break

            all_speeches.extend(speeches)

            # Check if we've reached the end
            if len(speeches) < batch_size:
                break

            start_record += batch_size

        self.logger.info(
            f"Retrieved {len(all_speeches)} total speeches for meeting {meeting_id}"
        )
        return all_speeches

    def _parse_meeting_record(self, record: dict[str, Any]) -> NDLMeeting | None:
        """Parse NDL meeting record into NDLMeeting object"""
        try:
            meeting_id = record.get("issueID")
            if not meeting_id:
                return None

            # Parse date
            date_str = record.get("date")
            meeting_date = None
            if date_str:
                try:
                    meeting_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    self.logger.warning(f"Invalid date format: {date_str}")

            return NDLMeeting(
                meeting_id=meeting_id,
                title=record.get("nameOfMeeting", ""),
                meeting_date=meeting_date,
                diet_session=int(record.get("session", 0)),
                house=record.get("nameOfHouse", ""),
                committee_name=record.get("nameOfMeeting"),
                meeting_type=record.get("meetingType"),
                pdf_url=record.get("pdfUrl"),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse meeting record: {e}")
            return None

    def _parse_speech_record(self, record: dict[str, Any]) -> NDLSpeech | None:
        """Parse NDL speech record into NDLSpeech object"""
        try:
            speech_id = record.get("speechID")
            if not speech_id:
                return None

            # Parse datetime if available
            datetime_str = record.get("speechDateTime")
            speech_datetime = None
            if datetime_str:
                try:
                    speech_datetime = datetime.fromisoformat(
                        datetime_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    self.logger.warning(f"Invalid datetime format: {datetime_str}")

            return NDLSpeech(
                speech_id=speech_id,
                meeting_id=record.get("meetingId", ""),
                speaker_name=record.get("speakerName", ""),
                speaker_group=record.get("speakerGroup"),
                speech_type=record.get("speechType", "発言"),
                speech_order=int(record.get("speechOrder", 0)),
                speech_content=record.get("speech", ""),
                speech_datetime=speech_datetime,
            )

        except Exception as e:
            self.logger.error(f"Failed to parse speech record: {e}")
            return None

    async def get_statistics(self) -> dict[str, Any]:
        """Get API usage statistics"""
        return {
            "rate_limiter": {
                "max_requests_per_second": self.rate_limiter.max_requests,
                "current_window_requests": len(self.rate_limiter.requests),
            },
            "client_config": {"timeout": self.timeout, "base_url": self.BASE_URL},
        }


# Example usage and testing
async def main():
    """Example usage of NDL API Client"""
    logging.basicConfig(level=logging.INFO)

    async with NDLAPIClient() as client:
        # Search for meetings in June 2025
        meetings = await client.search_meetings(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 21),
            diet_session=217,
            max_records=10,
        )

        print(f"Found {len(meetings)} meetings")

        # Get speeches for first meeting
        if meetings:
            first_meeting = meetings[0]
            print(f"Getting speeches for: {first_meeting.title}")

            speeches = await client.get_all_speeches_for_meeting(
                first_meeting.meeting_id
            )
            print(f"Found {len(speeches)} speeches")

            # Show sample speeches
            for speech in speeches[:3]:
                print(
                    f"- {speech.speaker_name} ({speech.speaker_group}): {speech.speech_content[:100]}..."
                )


if __name__ == "__main__":
    asyncio.run(main())
