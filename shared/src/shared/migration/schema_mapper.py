"""Schema mapping and data transformation for Airtable to Supabase migration."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


class SchemaMapper:
    """Maps Airtable schema and data to Supabase format."""

    def __init__(self):
        """Initialize schema mapper with field mappings."""
        self.field_mappings = self._load_field_mappings()
        self.type_converters = self._load_type_converters()

    def _load_field_mappings(self) -> dict[str, dict[str, Any]]:
        """Load field mappings for each table."""
        return {
            "Parties": {
                "Name": "name",
                "Name_EN": "name_en",
                "Abbreviation": "abbreviation",
                "Description": "description",
                "Website_URL": "website_url",
                "Color_Code": "color_code",
                "Is_Active": "is_active",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Members": {
                "Name": "name",
                "Name_Kana": "name_kana",
                "Name_EN": "name_en",
                "Party": "party_id",  # Will need ID resolution
                "House": "house",
                "Constituency": "constituency",
                "Diet_Member_ID": "diet_member_id",
                "Birth_Date": "birth_date",
                "Gender": "gender",
                "First_Elected": "first_elected",
                "Terms_Served": "terms_served",
                "Previous_Occupations": "previous_occupations",
                "Education": "education",
                "Website_URL": "website_url",
                "Twitter_Handle": "twitter_handle",
                "Facebook_URL": "facebook_url",
                "Is_Active": "is_active",
                "Status": "status",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Bills (法案)": {
                "Bill_Number": "bill_number",
                "Title": "title",
                "Title_EN": "title_en",
                "Short_Title": "short_title",
                "Summary": "summary",
                "Purpose": "purpose",
                "Status": "status",
                "Category": "category",
                "Bill_Type": "bill_type",
                "Diet_Session": "diet_session",
                "House_Of_Origin": "house_of_origin",
                "Submitter_Type": "submitter_type",
                "Sponsoring_Ministry": "sponsoring_ministry",
                "Diet_URL": "diet_url",
                "PDF_URL": "pdf_url",
                "Submitted_Date": "submitted_date",
                "Estimated_Cost": "estimated_cost",
                "Is_Controversial": "is_controversial",
                "Priority_Level": "priority_level",
                "Submitting_Members": "submitting_members",
                "Related_Bills": "related_bills",
                "Key_Points": "key_points",
                "Tags": "tags",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "IssueCategories": {
                "CAP_Code": "cap_code",
                "Layer": "layer",
                "Title_JA": "title_ja",
                "Title_EN": "title_en",
                "Summary_150JA": "summary_150ja",
                "Parent_Category": "parent_id",  # Will need ID resolution
                "Is_Seed": "is_seed",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Bills_PolicyCategories": {
                "Bill": "bill_id",  # Will need ID resolution
                "PolicyCategory": "policy_category_id",  # Will need ID resolution
                "Bill_ID": "bill_airtable_id",  # Store original IDs
                "PolicyCategory_ID": "category_airtable_id",
                "Confidence_Score": "confidence_score",
                "Is_Manual": "is_manual",
                "Source": "source",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Meetings": {
                "Meeting_ID": "meeting_id",
                "Title": "title",
                "Meeting_Type": "meeting_type",
                "Committee_Name": "committee_name",
                "Diet_Session": "diet_session",
                "House": "house",
                "Session_Number": "session_number",
                "Meeting_Date": "meeting_date",
                "Start_Time": "start_time",
                "End_Time": "end_time",
                "Summary": "summary",
                "Video_URL": "video_url",
                "Audio_URL": "audio_url",
                "Transcript_URL": "transcript_url",
                "Participant_Count": "participant_count",
                "Is_Public": "is_public",
                "Is_Processed": "is_processed",
                "Transcript_Processed": "transcript_processed",
                "STT_Completed": "stt_completed",
                "Is_Cancelled": "is_cancelled",
                "Agenda": "agenda",
                "Documents_Urls": "documents_urls",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Speeches": {
                "Meeting": "meeting_id",  # Will need ID resolution
                "Speaker": "speaker_id",  # Will need ID resolution
                "Related_Bill": "related_bill_id",  # Will need ID resolution
                "Speech_Order": "speech_order",
                "Speaker_Name": "speaker_name",
                "Speaker_Title": "speaker_title",
                "Speaker_Type": "speaker_type",
                "Original_Text": "original_text",
                "Cleaned_Text": "cleaned_text",
                "Speech_Type": "speech_type",
                "Summary": "summary",
                "Sentiment": "sentiment",
                "Stance": "stance",
                "Word_Count": "word_count",
                "Confidence_Score": "confidence_score",
                "Is_Interruption": "is_interruption",
                "Is_Processed": "is_processed",
                "Needs_Review": "needs_review",
                "Start_Time": "start_time",
                "End_Time": "end_time",
                "Key_Points": "key_points",
                "Topics": "topics",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Votes (投票)": {
                "Bill": "bill_id",  # Will need ID resolution
                "Member": "member_id",  # Will need ID resolution
                "Vote_Result": "vote_result",
                "Vote_Date": "vote_date",
                "House": "house",
                "Vote_Type": "vote_type",
                "Vote_Stage": "vote_stage",
                "Committee_Name": "committee_name",
                "Total_Votes": "total_votes",
                "Yes_Votes": "yes_votes",
                "No_Votes": "no_votes",
                "Abstain_Votes": "abstain_votes",
                "Absent_Votes": "absent_votes",
                "Notes": "notes",
                "Is_Final_Vote": "is_final_vote",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "Issues": {
                "Title": "title",
                "Description": "description",
                "Priority": "priority",
                "Status": "status",
                "Extraction_Confidence": "extraction_confidence",
                "Review_Notes": "review_notes",
                "Is_LLM_Generated": "is_llm_generated",
                "Category": "category_id",  # Will need ID resolution
                "Related_Bills": "related_bill_ids",  # Will need ID resolution
                "Issue_Tags": "tag_ids",  # Will need ID resolution
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
            "IssueTags": {
                "Name": "name",
                "Color_Code": "color_code",
                "Category": "category",
                "Description": "description",
                "Created_At": "created_at",
                "Updated_At": "updated_at",
            },
        }

    def _load_type_converters(self) -> dict[str, callable]:
        """Load type conversion functions."""
        return {
            "boolean": self._convert_boolean,
            "integer": self._convert_integer,
            "decimal": self._convert_decimal,
            "date": self._convert_date,
            "datetime": self._convert_datetime,
            "time": self._convert_time,
            "json": self._convert_json,
            "uuid": self._convert_uuid,
            "array": self._convert_array,
        }

    def airtable_to_supabase(
        self,
        table_name: str,
        airtable_record: dict[str, Any],
        id_mappings: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Convert Airtable record to Supabase format.

        Args:
            table_name: Name of the Airtable table
            airtable_record: Airtable record with 'id' and 'fields'
            id_mappings: Optional ID mappings for foreign key resolution

        Returns:
            Supabase-formatted record
        """
        if table_name not in self.field_mappings:
            raise ValueError(f"Unknown table: {table_name}")

        # Extract Airtable fields
        airtable_id = airtable_record.get("id", "")
        fields = airtable_record.get("fields", {})

        # Start with airtable_id
        supabase_record = {"airtable_id": airtable_id}

        # Map each field
        mapping = self.field_mappings[table_name]
        for airtable_field, supabase_field in mapping.items():
            if airtable_field in fields:
                value = fields[airtable_field]

                # Handle foreign key references
                if supabase_field.endswith("_id") and id_mappings:
                    value = self._resolve_foreign_key(
                        value, supabase_field, id_mappings
                    )
                # Handle JSON fields
                elif airtable_field in [
                    "Submitting_Members",
                    "Related_Bills",
                    "Key_Points",
                    "Tags",
                    "Agenda",
                    "Documents_Urls",
                    "Topics",
                ]:
                    value = self._convert_json(value)
                # Handle date/time fields
                elif "Date" in airtable_field or airtable_field in [
                    "Created_At",
                    "Updated_At",
                ]:
                    value = self._convert_datetime(value)
                elif "Time" in airtable_field:
                    value = self._convert_time(value)
                # Handle boolean fields
                elif airtable_field.startswith("Is_") or airtable_field in [
                    "STT_Completed",
                    "Transcript_Processed",
                ]:
                    value = self._convert_boolean(value)
                # Handle numeric fields
                elif airtable_field in [
                    "Terms_Served",
                    "Session_Number",
                    "Participant_Count",
                    "Speech_Order",
                    "Word_Count",
                    "Total_Votes",
                    "Yes_Votes",
                    "No_Votes",
                    "Abstain_Votes",
                    "Absent_Votes",
                ]:
                    value = self._convert_integer(value)
                elif airtable_field in [
                    "Estimated_Cost",
                    "Confidence_Score",
                    "Extraction_Confidence",
                ]:
                    value = self._convert_decimal(value)

                supabase_record[supabase_field] = value

        # Add sync version
        supabase_record["sync_version"] = 1

        return supabase_record

    def _resolve_foreign_key(
        self,
        value: str | list[str],
        field_name: str,
        id_mappings: dict[str, dict[str, str]],
    ) -> str | list[str] | None:
        """Resolve Airtable record IDs to Supabase UUIDs.

        Args:
            value: Airtable record ID(s)
            field_name: Field name to determine table
            id_mappings: Mapping of table -> airtable_id -> supabase_id

        Returns:
            Supabase UUID(s)
        """
        if not value:
            return None

        # Determine table from field name
        table_map = {
            "party_id": "parties",
            "bill_id": "bills",
            "policy_category_id": "policy_categories",
            "meeting_id": "meetings",
            "speaker_id": "members",
            "member_id": "members",
            "category_id": "policy_categories",
            "parent_id": "policy_categories",
        }

        table = table_map.get(field_name)
        if not table or table not in id_mappings:
            logger.warning(f"Cannot resolve foreign key for {field_name}")
            return None

        # Handle single vs multiple IDs
        if isinstance(value, list):
            resolved = []
            for airtable_id in value:
                supabase_id = id_mappings[table].get(airtable_id)
                if supabase_id:
                    resolved.append(supabase_id)
            return resolved if resolved else None
        else:
            return id_mappings[table].get(value)

    def _convert_boolean(self, value: Any) -> bool:
        """Convert to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on"]
        return bool(value)

    def _convert_integer(self, value: Any) -> int | None:
        """Convert to integer."""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert to integer: {value}")
            return None

    def _convert_decimal(self, value: Any) -> float | None:
        """Convert to decimal."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Cannot convert to decimal: {value}")
            return None

    def _convert_date(self, value: Any) -> str | None:
        """Convert to ISO date string."""
        if not value:
            return None

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, str):
            # Try to parse various date formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y年%m月%d日",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue

            # If no format matches, return as-is and log warning
            logger.warning(f"Cannot parse date: {value}")
            return value

        return str(value)

    def _convert_datetime(self, value: Any) -> str | None:
        """Convert to ISO datetime string."""
        if not value:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, str):
            # Airtable datetime format: 2024-01-15T09:30:00.000Z
            if "T" in value:
                return value

            # Try to parse as date only
            date_str = self._convert_date(value)
            if date_str:
                return f"{date_str}T00:00:00Z"

        return str(value)

    def _convert_time(self, value: Any) -> str | None:
        """Convert to time string."""
        if not value:
            return None

        if isinstance(value, str):
            # Ensure HH:MM:SS format
            if re.match(r"^\d{2}:\d{2}(:\d{2})?$", value):
                if len(value) == 5:  # HH:MM
                    return f"{value}:00"
                return value

        return str(value)

    def _convert_json(self, value: Any) -> str | None:
        """Convert to JSON string."""
        if not value:
            return None

        if isinstance(value, str):
            # Check if already JSON
            try:
                json.loads(value)
                return value
            except json.JSONDecodeError:
                # Treat as single value and wrap in array
                return json.dumps([value])

        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)

        return json.dumps(value)

    def _convert_uuid(self, value: Any) -> str:
        """Convert to UUID string."""
        if not value:
            return str(uuid.uuid4())

        # Check if already UUID
        try:
            uuid.UUID(value)
            return value
        except (ValueError, AttributeError):
            # Generate deterministic UUID from value
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(value)))

    def _convert_array(self, value: Any) -> list[Any]:
        """Convert to array."""
        if not value:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            # Try to parse as JSON array
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

            # Split comma-separated values
            if "," in value:
                return [v.strip() for v in value.split(",")]

        return [value]

    def get_supabase_table_name(self, airtable_table: str) -> str:
        """Get Supabase table name from Airtable table name."""
        table_map = {
            "Parties": "parties",
            "Members": "members",
            "Bills (法案)": "bills",
            "IssueCategories": "policy_categories",
            "Bills_PolicyCategories": "bills_policy_categories",
            "Meetings": "meetings",
            "Speeches": "speeches",
            "Votes (投票)": "votes",
            "Issues": "issues",
            "IssueTags": "issue_tags",
        }

        return table_map.get(airtable_table, airtable_table.lower())

    def validate_record(self, table_name: str, record: dict[str, Any]) -> list[str]:
        """Validate a record for required fields and constraints.

        Args:
            table_name: Supabase table name
            record: Record to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Define required fields per table
        required_fields = {
            "parties": ["airtable_id", "name"],
            "members": ["airtable_id", "name", "house"],
            "bills": ["airtable_id", "bill_number", "title"],
            "policy_categories": ["airtable_id", "cap_code", "layer", "title_ja"],
            "meetings": ["airtable_id", "meeting_id", "title", "meeting_date"],
            "speeches": ["airtable_id", "speech_order", "original_text"],
            "votes": ["airtable_id", "vote_result", "vote_date", "house"],
            "issues": ["airtable_id", "title", "description"],
            "issue_tags": ["airtable_id", "name", "category"],
        }

        # Check required fields
        if table_name in required_fields:
            for field in required_fields[table_name]:
                if field not in record or record[field] is None:
                    errors.append(f"Missing required field: {field}")

        # Validate specific constraints
        if table_name == "members" and "house" in record:
            if record["house"] not in ["衆議院", "参議院"]:
                errors.append(f"Invalid house value: {record['house']}")

        if table_name == "policy_categories" and "layer" in record:
            if record["layer"] not in ["L1", "L2", "L3"]:
                errors.append(f"Invalid layer value: {record['layer']}")

        # Validate color codes
        color_fields = ["color_code"]
        for field in color_fields:
            if field in record and record[field]:
                if not re.match(r"^#[0-9A-Fa-f]{6}$", record[field]):
                    errors.append(f"Invalid color code: {record[field]}")

        return errors
