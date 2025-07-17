"""Airtable client for Diet Issue Tracker structured data."""

from __future__ import annotations

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
    
    def __init__(self, pat: Optional[str] = None, base_id: Optional[str] = None):
        self.pat = pat or os.getenv("AIRTABLE_PAT")
        self.base_id = base_id or os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"
        
        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.pat}",
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
    
    async def update_member(self, record_id: str, member_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a member record."""
        url = f"{self.base_url}/Members/{record_id}"
        data = {
            "fields": {
                "Updated_At": datetime.now().isoformat(),
                **{k: v for k, v in member_data.items() if v is not None}
            }
        }
        
        response = await self._rate_limited_request("PATCH", url, json=data)
        return response
    
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
        url = f"{self.base_url}/Bills (法案)"
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
        url = f"{self.base_url}/Bills (法案)/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_bills(self, filter_formula: Optional[str] = None,
                        max_records: int = 100) -> List[Dict[str, Any]]:
        """List bill records with optional filtering."""
        url = f"{self.base_url}/Bills (法案)"
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
    
    # Issue management operations
    async def create_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue record."""
        url = f"{self.base_url}/Issues"
        data = {
            "fields": {
                "Title": issue_data["title"],
                "Description": issue_data["description"],
                "Priority": issue_data.get("priority", "medium"),
                "Status": issue_data.get("status", "active"),
                "Extraction_Confidence": issue_data.get("extraction_confidence"),
                "Review_Notes": issue_data.get("review_notes"),
                "Is_LLM_Generated": issue_data.get("is_llm_generated", False),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle relationships
        if "related_bills" in issue_data and issue_data["related_bills"]:
            data["fields"]["Related_Bills"] = issue_data["related_bills"]
        if "issue_tags" in issue_data and issue_data["issue_tags"]:
            data["fields"]["Issue_Tags"] = issue_data["issue_tags"]
        if "category_id" in issue_data and issue_data["category_id"]:
            data["fields"]["Category"] = [issue_data["category_id"]]
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_issue(self, record_id: str) -> Dict[str, Any]:
        """Get an issue record by ID."""
        url = f"{self.base_url}/Issues/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_issues(self, filter_formula: Optional[str] = None,
                         max_records: int = 100) -> List[Dict[str, Any]]:
        """List issue records with optional filtering."""
        url = f"{self.base_url}/Issues"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    async def update_issue(self, record_id: str, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an issue record."""
        url = f"{self.base_url}/Issues/{record_id}"
        data = {
            "fields": {
                "Updated_At": datetime.now().isoformat(),
                **{k: v for k, v in issue_data.items() if v is not None}
            }
        }
        
        response = await self._rate_limited_request("PATCH", url, json=data)
        return response
    
    # Issue Tag operations
    async def create_issue_tag(self, tag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue tag record."""
        url = f"{self.base_url}/IssueTags"
        data = {
            "fields": {
                "Name": tag_data["name"],
                "Color_Code": tag_data.get("color_code", "#3B82F6"),
                "Category": tag_data["category"],
                "Description": tag_data.get("description"),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_issue_tag(self, record_id: str) -> Dict[str, Any]:
        """Get an issue tag record by ID."""
        url = f"{self.base_url}/IssueTags/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_issue_tags(self, filter_formula: Optional[str] = None,
                             max_records: int = 100) -> List[Dict[str, Any]]:
        """List issue tag records with optional filtering."""
        url = f"{self.base_url}/IssueTags"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    async def get_bills_with_issues(self, bill_id: str) -> Dict[str, Any]:
        """Get bill with its related issues and tags."""
        bill = await self.get_bill(bill_id)
        
        # If bill has related issues, fetch them
        if "fields" in bill and "Related_Issues" in bill["fields"]:
            issue_ids = bill["fields"]["Related_Issues"]
            issues = []
            for issue_id in issue_ids:
                try:
                    issue = await self.get_issue(issue_id)
                    issues.append(issue)
                except Exception as e:
                    logger.warning(f"Failed to fetch issue {issue_id}: {e}")
            bill["related_issues"] = issues
        
        return bill

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
    
    # Votes table operations
    async def create_vote(self, vote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vote record."""
        url = f"{self.base_url}/Votes (投票)"
        data = {
            "fields": {
                "Vote_Result": vote_data["vote_result"],
                "Vote_Date": vote_data["vote_date"],
                "House": vote_data["house"],
                "Vote_Type": vote_data["vote_type"],
                "Vote_Stage": vote_data.get("vote_stage"),
                "Committee_Name": vote_data.get("committee_name"),
                "Total_Votes": vote_data.get("total_votes"),
                "Yes_Votes": vote_data.get("yes_votes"),
                "No_Votes": vote_data.get("no_votes"),
                "Abstain_Votes": vote_data.get("abstain_votes"),
                "Absent_Votes": vote_data.get("absent_votes"),
                "Notes": vote_data.get("notes"),
                "Is_Final_Vote": vote_data.get("is_final_vote", False),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle relationships
        if "bill_id" in vote_data and vote_data["bill_id"]:
            data["fields"]["Bill"] = [vote_data["bill_id"]]
        if "member_id" in vote_data and vote_data["member_id"]:
            data["fields"]["Member"] = [vote_data["member_id"]]
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response
    
    async def get_vote(self, record_id: str) -> Dict[str, Any]:
        """Get a vote record by ID."""
        url = f"{self.base_url}/Votes (投票)/{record_id}"
        return await self._rate_limited_request("GET", url)
    
    async def list_votes(self, filter_formula: Optional[str] = None,
                        max_records: int = 100) -> List[Dict[str, Any]]:
        """List vote records with optional filtering."""
        url = f"{self.base_url}/Votes (投票)"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])
    
    async def find_member_by_name(self, member_name: str, party_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find member by name and optionally party."""
        filter_parts = [f"{{Name}} = '{member_name}'"]
        if party_name:
            # Note: This assumes we have party name stored directly or via lookup
            filter_parts.append(f"{{Party_Name}} = '{party_name}'")
        
        filter_formula = "AND(" + ", ".join(filter_parts) + ")"
        members = await self.list_members(filter_formula=filter_formula, max_records=1)
        
        return members[0] if members else None
    
    async def find_party_by_name(self, party_name: str) -> Optional[Dict[str, Any]]:
        """Find party by name."""
        filter_formula = f"{{Name}} = '{party_name}'"
        parties = await self.list_parties(filter_formula=filter_formula, max_records=1)
        
        return parties[0] if parties else None
    
    async def find_bill_by_number(self, bill_number: str) -> Optional[Dict[str, Any]]:
        """Find bill by bill number."""
        filter_formula = f"{{Bill_Number}} = '{bill_number}'"
        bills = await self.list_bills(filter_formula=filter_formula, max_records=1)
        
        return bills[0] if bills else None

    # Issue Category operations
    async def create_issue_category(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue category record."""
        url = f"{self.base_url}/IssueCategories"
        data = {
            "fields": {
                "CAP_Code": category_data["cap_code"],
                "Layer": category_data["layer"],
                "Title_JA": category_data["title_ja"],
                "Title_EN": category_data.get("title_en"),
                "Summary_150JA": category_data.get("summary_150ja", ""),
                "Is_Seed": category_data.get("is_seed", False),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle parent relationship
        if "parent_category_id" in category_data and category_data["parent_category_id"]:
            data["fields"]["Parent_Category"] = [category_data["parent_category_id"]]
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response

    async def get_issue_category(self, record_id: str) -> Dict[str, Any]:
        """Get an issue category record by ID."""
        url = f"{self.base_url}/IssueCategories/{record_id}"
        return await self._rate_limited_request("GET", url)

    async def list_issue_categories(self, filter_formula: Optional[str] = None,
                                   max_records: int = 100) -> List[Dict[str, Any]]:
        """List issue category records with optional filtering."""
        url = f"{self.base_url}/IssueCategories"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])

    async def update_issue_category(self, record_id: str, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an issue category record."""
        url = f"{self.base_url}/IssueCategories/{record_id}"
        data = {
            "fields": {
                "Updated_At": datetime.now().isoformat(),
                **{k: v for k, v in category_data.items() if v is not None}
            }
        }
        
        response = await self._rate_limited_request("PATCH", url, json=data)
        return response

    async def get_categories_by_layer(self, layer: str) -> List[Dict[str, Any]]:
        """Get all categories for a specific layer (L1/L2/L3)."""
        filter_formula = f"{{Layer}} = '{layer}'"
        return await self.list_issue_categories(filter_formula=filter_formula, max_records=1000)

    async def get_category_children(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get child categories for a specific parent category."""
        filter_formula = f"FIND('{parent_id}', ARRAYJOIN({{Parent_Category}})) > 0"
        return await self.list_issue_categories(filter_formula=filter_formula, max_records=1000)

    async def find_category_by_cap_code(self, cap_code: str) -> Optional[Dict[str, Any]]:
        """Find category by CAP code."""
        filter_formula = f"{{CAP_Code}} = '{cap_code}'"
        categories = await self.list_issue_categories(filter_formula=filter_formula, max_records=1)
        
        return categories[0] if categories else None

    async def get_category_tree(self) -> Dict[str, Any]:
        """Get full category tree structure."""
        # Get all categories
        all_categories = await self.list_issue_categories(max_records=1000)
        
        # Organize by layer
        tree = {"L1": [], "L2": [], "L3": []}
        
        for category in all_categories:
            fields = category.get("fields", {})
            layer = fields.get("Layer")
            if layer in tree:
                tree[layer].append(category)
        
        # Sort by CAP code for consistent ordering
        for layer in tree:
            tree[layer].sort(key=lambda x: x.get("fields", {}).get("CAP_Code", ""))
        
        return tree

    # Bills_PolicyCategories relationship table operations
    async def create_bill_policy_category_relationship(self, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new bill-policy category relationship."""
        url = f"{self.base_url}/Bills_PolicyCategories"
        data = {
            "fields": {
                "Bill_ID": relationship_data["bill_id"],  # Link to Bills table
                "PolicyCategory_ID": relationship_data["policy_category_id"],  # Link to IssueCategories table
                "Confidence_Score": relationship_data.get("confidence_score", 0.8),
                "Is_Manual": relationship_data.get("is_manual", False),
                "Source": relationship_data.get("source", "auto_migration"),
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }
        
        # Handle relationship links
        if "bill_record_id" in relationship_data and relationship_data["bill_record_id"]:
            data["fields"]["Bill"] = [relationship_data["bill_record_id"]]
        if "policy_category_record_id" in relationship_data and relationship_data["policy_category_record_id"]:
            data["fields"]["PolicyCategory"] = [relationship_data["policy_category_record_id"]]
        
        # Remove None values
        data["fields"] = {k: v for k, v in data["fields"].items() if v is not None}
        
        response = await self._rate_limited_request("POST", url, json=data)
        return response

    async def get_bill_policy_category_relationship(self, record_id: str) -> Dict[str, Any]:
        """Get a bill-policy category relationship by ID."""
        url = f"{self.base_url}/Bills_PolicyCategories/{record_id}"
        return await self._rate_limited_request("GET", url)

    async def list_bill_policy_category_relationships(self, filter_formula: Optional[str] = None,
                                                     max_records: int = 100) -> List[Dict[str, Any]]:
        """List bill-policy category relationships with optional filtering."""
        url = f"{self.base_url}/Bills_PolicyCategories"
        params = {"maxRecords": max_records}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        
        response = await self._rate_limited_request("GET", url, params=params)
        return response.get("records", [])

    async def get_bill_policy_categories(self, bill_record_id: str) -> List[Dict[str, Any]]:
        """Get all policy categories linked to a specific bill."""
        filter_formula = f"FIND('{bill_record_id}', ARRAYJOIN({{Bill}})) > 0"
        return await self.list_bill_policy_category_relationships(filter_formula=filter_formula)

    async def get_policy_category_bills(self, policy_category_record_id: str) -> List[Dict[str, Any]]:
        """Get all bills linked to a specific policy category."""
        filter_formula = f"FIND('{policy_category_record_id}', ARRAYJOIN({{PolicyCategory}})) > 0"
        return await self.list_bill_policy_category_relationships(filter_formula=filter_formula)

    async def update_bill_policy_category_relationship(self, record_id: str, 
                                                      relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a bill-policy category relationship."""
        url = f"{self.base_url}/Bills_PolicyCategories/{record_id}"
        data = {
            "fields": {
                "Updated_At": datetime.now().isoformat(),
                **{k: v for k, v in relationship_data.items() if v is not None}
            }
        }
        
        response = await self._rate_limited_request("PATCH", url, json=data)
        return response

    async def delete_bill_policy_category_relationship(self, record_id: str) -> Dict[str, Any]:
        """Delete a bill-policy category relationship."""
        url = f"{self.base_url}/Bills_PolicyCategories/{record_id}"
        return await self._rate_limited_request("DELETE", url)

    async def find_bill_policy_category_relationship(self, bill_record_id: str, 
                                                    policy_category_record_id: str) -> Optional[Dict[str, Any]]:
        """Find existing relationship between a bill and policy category."""
        filter_formula = f"AND(FIND('{bill_record_id}', ARRAYJOIN({{Bill}})) > 0, FIND('{policy_category_record_id}', ARRAYJOIN({{PolicyCategory}})) > 0)"
        relationships = await self.list_bill_policy_category_relationships(filter_formula=filter_formula, max_records=1)
        
        return relationships[0] if relationships else None

    async def bulk_create_bill_policy_category_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk create bill-policy category relationships (max 10 at a time due to Airtable limits)."""
        results = []
        
        # Process in batches of 10 (Airtable limit)
        for i in range(0, len(relationships), 10):
            batch = relationships[i:i+10]
            
            url = f"{self.base_url}/Bills_PolicyCategories"
            records_data = []
            
            for rel in batch:
                record_data = {
                    "fields": {
                        "Bill_ID": rel["bill_id"],
                        "PolicyCategory_ID": rel["policy_category_id"], 
                        "Confidence_Score": rel.get("confidence_score", 0.8),
                        "Is_Manual": rel.get("is_manual", False),
                        "Source": rel.get("source", "bulk_migration"),
                        "Created_At": datetime.now().isoformat(),
                        "Updated_At": datetime.now().isoformat()
                    }
                }
                
                # Handle relationship links
                if "bill_record_id" in rel and rel["bill_record_id"]:
                    record_data["fields"]["Bill"] = [rel["bill_record_id"]]
                if "policy_category_record_id" in rel and rel["policy_category_record_id"]:
                    record_data["fields"]["PolicyCategory"] = [rel["policy_category_record_id"]]
                
                # Remove None values
                record_data["fields"] = {k: v for k, v in record_data["fields"].items() if v is not None}
                records_data.append(record_data)
            
            data = {"records": records_data}
            
            response = await self._rate_limited_request("POST", url, json=data)
            results.extend(response.get("records", []))
            
            # Rate limiting between batches
            if i + 10 < len(relationships):
                await asyncio.sleep(0.3)  # Additional delay for bulk operations
        
        return results

    # Additional methods for Bills API routes
    async def get_bills_by_policy_category(self, policy_category_id: str) -> List[Dict[str, Any]]:
        """Get all bills linked to a specific policy category by PolicyCategory_ID."""
        filter_formula = f"{{PolicyCategory_ID}} = '{policy_category_id}'"
        return await self.list_bill_policy_category_relationships(filter_formula=filter_formula)

    async def get_policy_categories_by_bill(self, bill_id: str) -> List[Dict[str, Any]]:
        """Get all policy categories linked to a specific bill by Bill_ID."""
        filter_formula = f"{{Bill_ID}} = '{bill_id}'"
        return await self.list_bill_policy_category_relationships(filter_formula=filter_formula)

    async def list_bills_policy_categories(self, max_records: int = 1000) -> List[Dict[str, Any]]:
        """List all Bills-PolicyCategory relationships."""
        return await self.list_bill_policy_category_relationships(max_records=max_records)