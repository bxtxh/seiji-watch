"""Airtable client for Diet Issue Tracker structured data."""

import os
import asyncio
from typing import List, Dict, Any, Optional, Union
import aiohttp
import json
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class AirtableClient:
    """Async Airtable client for Diet Issue Tracker data management."""
    
    def __init__(self, api_key: Optional[str] = None, base_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("AIRTABLE_API_KEY")
        self.base_id = base_id or os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        if not self.api_key or not self.base_id:
            raise ValueError("Airtable API key and base ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Rate limiting: Airtable allows 5 requests per second
        self._request_semaphore = asyncio.Semaphore(5)
        self._last_request_time = 0
        
    async def _rate_limited_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make rate-limited request to Airtable API."""
        async with self._request_semaphore:
            # Ensure we don't exceed 5 requests per second
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < 0.2:  # 200ms between requests
                await asyncio.sleep(0.2 - time_since_last)
            
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=self.headers, **kwargs) as response:
                    self._last_request_time = asyncio.get_event_loop().time()
                    
                    if response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get("Retry-After", 30))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        return await self._rate_limited_request(method, url, **kwargs)
                    
                    response.raise_for_status()
                    return await response.json()
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize Python values for Airtable API."""
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        return value
    
    # Parties table operations
    async def create_party(self, party_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new party record."""
        url = f"{self.base_url}/Parties"
        data = {
            "fields": {
                "Name": party_data["name"],
                "Name_EN": party_data.get("name_en"),
                "Abbreviation": party_data.get("abbreviation"),
                "Description": party_data.get("description"),
                "Website_URL": party_data.get("website_url"),
                "Color_Code": party_data.get("color_code"),
                "Is_Active": party_data.get("is_active", True),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_party(self, record_id: str) -> Dict[str, Any]:
        """Get a party record by ID."""
        url = f"{self.base_url}/Parties/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def update_party(self, record_id: str, party_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a party record."""
        url = f"{self.base_url}/Parties/{record_id}"
        data = {
            "fields": {
                "Updated_At": datetime.now().isoformat(),
                **{k: v for k, v in party_data.items() if v is not None}
            }
        }
        
        response = await self._rate_limited_request("PATCH", url, json=data)
        return response
    
    async def list_parties(self, filter_formula: Optional[str] = None, 
                          max_records: int = 100) -> List[Dict[str, Any]]:
        """List party records with optional filtering."""
        url = f"{self.base_url}/Parties"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    # Members table operations
    async def create_member(self, member_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new member record."""
        url = f"{self.base_url}/Members"
        data = {
            "fields": {
                "Name": member_data["name"],
                "Name_Kana": member_data.get("name_kana"),
                "Name_EN": member_data.get("name_en"),
                "House": member_data["house"],
                "Constituency": member_data.get("constituency"),
                "Diet_Member_ID": member_data.get("diet_member_id"),
                "Birth_Date": member_data.get("birth_date"),
                "Gender": member_data.get("gender"),
                "First_Elected": member_data.get("first_elected"),
                "Terms_Served": member_data.get("terms_served"),
                "Previous_Occupations": member_data.get("previous_occupations"),
                "Education": member_data.get("education"),
                "Website_URL": member_data.get("website_url"),
                "Twitter_Handle": member_data.get("twitter_handle"),
                "Facebook_URL": member_data.get("facebook_url"),
                "Is_Active": member_data.get("is_active", True),
                "Status": member_data.get("status", "active"),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle party relationship
        if "party_id" in member_data and member_data["party_id"]:
            data["fields"]["Party"] = [member_data["party_id"]]
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_member(self, record_id: str) -> Dict[str, Any]:
        """Get a member record by ID."""
        url = f"{self.base_url}/Members/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_members(self, filter_formula: Optional[str] = None,
                          max_records: int = 100) -> List[Dict[str, Any]]:
        """List member records with optional filtering."""
        url = f"{self.base_url}/Members"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    # Bills table operations
    async def create_bill(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bill record."""
        url = f"{self.base_url}/Bills"
        data = {
            "fields": {
                "Bill_Number": bill_data["bill_number"],
                "Title": bill_data["title"],
                "Title_EN": bill_data.get("title_en"),
                "Short_Title": bill_data.get("short_title"),
                "Summary": bill_data.get("summary"),
                "Purpose": bill_data.get("purpose"),
                "Status": bill_data.get("status", "backlog"),
                "Category": bill_data.get("category"),
                "Bill_Type": bill_data.get("bill_type"),
                "Diet_Session": bill_data.get("diet_session"),
                "House_Of_Origin": bill_data.get("house_of_origin"),
                "Submitter_Type": bill_data.get("submitter_type"),
                "Sponsoring_Ministry": bill_data.get("sponsoring_ministry"),
                "Diet_URL": bill_data.get("diet_url"),
                "PDF_URL": bill_data.get("pdf_url"),
                "Estimated_Cost": bill_data.get("estimated_cost"),
                "Is_Controversial": bill_data.get("is_controversial", False),
                "Priority_Level": bill_data.get("priority_level", "normal"),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle date fields
        if "submitted_date" in bill_data and bill_data["submitted_date"]:
            data["fields"]["Submitted_Date"] = self._serialize_value(bill_data["submitted_date"])
        
        # Handle JSON fields
        for json_field in ["submitting_members", "related_bills", "key_points", "tags"]:
            if json_field in bill_data and bill_data[json_field]:
                data["fields"][json_field.replace("_", " ").title().replace(" ", "_")] = json.dumps(bill_data[json_field])
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_bill(self, record_id: str) -> Dict[str, Any]:
        """Get a bill record by ID."""
        url = f"{self.base_url}/Bills/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_bills(self, filter_formula: Optional[str] = None,
                        max_records: int = 100) -> List[Dict[str, Any]]:
        """List bill records with optional filtering."""
        url = f"{self.base_url}/Bills"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    # Meetings table operations
    async def create_meeting(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new meeting record."""
        url = f"{self.base_url}/Meetings"
        data = {
            "fields": {
                "Meeting_ID": meeting_data["meeting_id"],
                "Title": meeting_data["title"],
                "Meeting_Type": meeting_data["meeting_type"],
                "Committee_Name": meeting_data.get("committee_name"),
                "Diet_Session": meeting_data["diet_session"],
                "House": meeting_data["house"],
                "Session_Number": meeting_data.get("session_number"),
                "Meeting_Date": self._serialize_value(meeting_data["meeting_date"]),
                "Summary": meeting_data.get("summary"),
                "Video_URL": meeting_data.get("video_url"),
                "Audio_URL": meeting_data.get("audio_url"),
                "Transcript_URL": meeting_data.get("transcript_url"),
                "Participant_Count": meeting_data.get("participant_count"),
                "Is_Public": meeting_data.get("is_public", True),
                "Is_Processed": meeting_data.get("is_processed", False),
                "Transcript_Processed": meeting_data.get("transcript_processed", False),
                "STT_Completed": meeting_data.get("stt_completed", False),
                "Is_Cancelled": meeting_data.get("is_cancelled", False),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle time fields
        for time_field in ["start_time", "end_time"]:
            if time_field in meeting_data and meeting_data[time_field]:
                data["fields"][time_field.replace("_", " ").title().replace(" ", "_")] = self._serialize_value(meeting_data[time_field])
        
        # Handle JSON fields
        for json_field in ["agenda", "documents_urls"]:
            if json_field in meeting_data and meeting_data[json_field]:
                data["fields"][json_field.replace("_", " ").title().replace(" ", "_")] = json.dumps(meeting_data[json_field])
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    # Speeches table operations
    async def create_speech(self, speech_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new speech record."""
        url = f"{self.base_url}/Speeches"
        data = {
            "fields": {
                "Speech_Order": speech_data["speech_order"],
                "Speaker_Name": speech_data.get("speaker_name"),
                "Speaker_Title": speech_data.get("speaker_title"),
                "Speaker_Type": speech_data.get("speaker_type", "member"),
                "Original_Text": speech_data["original_text"],
                "Cleaned_Text": speech_data.get("cleaned_text"),
                "Speech_Type": speech_data.get("speech_type"),
                "Summary": speech_data.get("summary"),
                "Sentiment": speech_data.get("sentiment"),
                "Stance": speech_data.get("stance"),
                "Word_Count": speech_data.get("word_count"),
                "Confidence_Score": speech_data.get("confidence_score"),
                "Is_Interruption": speech_data.get("is_interruption", False),
                "Is_Processed": speech_data.get("is_processed", False),
                "Needs_Review": speech_data.get("needs_review", False),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle relationships
        if "meeting_id" in speech_data and speech_data["meeting_id"]:
            data["fields"]["Meeting"] = [speech_data["meeting_id"]]
        if "speaker_id" in speech_data and speech_data["speaker_id"]:
            data["fields"]["Speaker"] = [speech_data["speaker_id"]]
        if "related_bill_id" in speech_data and speech_data["related_bill_id"]:
            data["fields"]["Related_Bill"] = [speech_data["related_bill_id"]]
        
        # Handle time fields
        for time_field in ["start_time", "end_time"]:
            if time_field in speech_data and speech_data[time_field]:
                data["fields"][time_field.replace("_", " ").title().replace(" ", "_")] = self._serialize_value(speech_data[time_field])
        
        # Handle JSON fields
        for json_field in ["key_points", "topics"]:
            if json_field in speech_data and speech_data[json_field]:
                data["fields"][json_field.replace("_", " ").title().replace(" ", "_")] = json.dumps(speech_data[json_field])
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_speech(self, record_id: str) -> Dict[str, Any]:
        """Get a speech record by ID."""
        url = f"{self.base_url}/Speeches/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_speeches(self, filter_formula: Optional[str] = None,
                           max_records: int = 100) -> List[Dict[str, Any]]:
        """List speech records with optional filtering."""
        url = f"{self.base_url}/Speeches"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    # Utility methods
    async def health_check(self) -> bool:
        """Check if Airtable connection is healthy."""
        try:
            # Try to list a small number of records from any table
            await self.list_parties(max_records=1)
            return True
        except Exception as e:
            logger.error(f"Airtable health check failed: {e}")
            return False
    
    async def get_record_count(self, table_name: str) -> int:
        """Get total record count for a table."""
        url = f"{self.base_url}/{table_name}"
        params = {"maxRecords": 1}
        
        response = await self._rate_limited_request("GET", url, params=params)
        # Airtable doesn't return total count directly, so we need to paginate
        # For now, return the number of records in first page
        return len(response.get("records", []))