"""
NDL API Data Mapping & Schema Unification

Maps NDL API data format to existing Airtable schema and provides
unified data interface for both NDL + Whisper sources.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from shared.src.shared.models.meeting import Meeting, Speech

from ..collectors.ndl_api_client import NDLMeeting, NDLSpeech


@dataclass
class MappingResult:
    """Result of data mapping operation"""
    success: bool
    mapped_data: Any | None = None
    warnings: list[str] = None
    errors: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


class SpeakerNormalizer:
    """Normalizes speaker names and identifies political parties"""

    # 敬語表現の除去パターン
    HONORIFIC_PATTERNS = [
        r'君$', r'さん$', r'議員$', r'大臣$', r'長官$', r'副大臣$', r'政務官$'
    ]

    # 政党名正規化マッピング
    PARTY_MAPPING = {
        # 自民党系
        "自由民主党": "自民党",
        "自民": "自民党",
        "自由民主・国民の声": "自民党",

        # 立憲民主党系
        "立憲民主党": "立憲民主党",
        "立憲": "立憲民主党",
        "民主党": "立憲民主党",

        # 維新系
        "日本維新の会": "維新",
        "維新の会": "維新",
        "維新": "維新",

        # 公明党系
        "公明党": "公明党",
        "公明": "公明党",

        # 共産党系
        "日本共産党": "共産党",
        "共産党": "共産党",
        "共産": "共産党",

        # 国民民主党系
        "国民民主党": "国民民主党",
        "国民": "国民民主党",

        # れいわ新選組
        "れいわ新選組": "れいわ新選組",
        "れいわ": "れいわ新選組",

        # 社民党
        "社会民主党": "社民党",
        "社民": "社民党",

        # 無所属・その他
        "無所属": "無所属",
        "無": "無所属",
        "政府": "政府",
        "内閣": "政府"
    }

    @classmethod
    def normalize_speaker_name(cls, name: str) -> str:
        """議員名の表記揺れを統一"""
        if not name:
            return ""

        # 敬語表現の除去
        normalized = name
        for pattern in cls.HONORIFIC_PATTERNS:
            normalized = re.sub(pattern, '', normalized)

        # 全角スペースを半角に統一
        normalized = re.sub(r'　', ' ', normalized)

        # 先頭・末尾の空白を除去
        normalized = normalized.strip()

        return normalized

    @classmethod
    def normalize_party_name(cls, party: str | None) -> str | None:
        """政党名の表記揺れを統一"""
        if not party:
            return None

        # 正規化マッピングを適用
        normalized = cls.PARTY_MAPPING.get(party, party)

        return normalized

    @classmethod
    def extract_speaker_info(cls, speaker_name: str,
                             speaker_group: str | None) -> dict[str, str | None]:
        """発言者情報を抽出・正規化"""
        return {
            "normalized_name": cls.normalize_speaker_name(speaker_name),
            "original_name": speaker_name,
            "normalized_party": cls.normalize_party_name(speaker_group),
            "original_party": speaker_group
        }


class NDLDataMapper:
    """
    Maps NDL API data to Airtable schema format

    Provides unified interface for processing both NDL API and Whisper STT data
    into consistent Airtable records.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.speaker_normalizer = SpeakerNormalizer()

        # Speech type mapping
        self.SPEECH_TYPE_MAPPING = {
            "質問": "質問",
            "答弁": "答弁",
            "発言": "発言",
            "討論": "討論",
            "議事": "議事",
            "その他": "発言"  # Default fallback
        }

    def map_ndl_meeting_to_airtable(self, ndl_meeting: NDLMeeting) -> MappingResult:
        """
        Map NDL Meeting to Airtable Meeting schema

        Args:
            ndl_meeting: NDL Meeting object

        Returns:
            MappingResult with mapped Meeting data
        """
        try:
            # Map meeting data
            meeting_data = {
                "meeting_id": ndl_meeting.meeting_id,
                "title": ndl_meeting.title or "",
                "meeting_type": self._determine_meeting_type(ndl_meeting),
                "committee_name": ndl_meeting.committee_name,
                "diet_session": str(ndl_meeting.diet_session),
                "house": ndl_meeting.house,
                "meeting_date": ndl_meeting.meeting_date.isoformat() if ndl_meeting.meeting_date else None,
                "transcript_url": ndl_meeting.pdf_url,
                "is_processed": False,
                "transcript_processed": True,  # NDL provides processed transcripts
                "stt_completed": False,  # Not from STT
                "is_public": True
            }

            # Create Meeting object for validation
            meeting = Meeting(**meeting_data)

            return MappingResult(
                success=True,
                mapped_data=meeting,
                warnings=[]
            )

        except Exception as e:
            self.logger.error(
                f"Failed to map NDL meeting {ndl_meeting.meeting_id}: {e}")
            return MappingResult(
                success=False,
                errors=[f"Mapping failed: {str(e)}"]
            )

    def map_ndl_speech_to_airtable(
            self,
            ndl_speech: NDLSpeech,
            meeting_id: str) -> MappingResult:
        """
        Map NDL Speech to Airtable Speech schema

        Args:
            ndl_speech: NDL Speech object
            meeting_id: Airtable Meeting record ID

        Returns:
            MappingResult with mapped Speech data
        """
        try:
            # Extract and normalize speaker information
            speaker_info = self.speaker_normalizer.extract_speaker_info(
                ndl_speech.speaker_name,
                ndl_speech.speaker_group
            )

            # Map speech data
            speech_data = {
                "meeting_id": meeting_id,
                "speech_order": ndl_speech.speech_order,
                "speaker_name": speaker_info["normalized_name"],
                "speaker_type": self._determine_speaker_type(speaker_info),
                "original_text": ndl_speech.speech_content,
                "cleaned_text": self._clean_speech_text(
                    ndl_speech.speech_content),
                "speech_type": self.SPEECH_TYPE_MAPPING.get(
                    ndl_speech.speech_type,
                    "発言"),
                "start_time": ndl_speech.speech_datetime.isoformat() if ndl_speech.speech_datetime else None,
                "word_count": len(
                    ndl_speech.speech_content.split()) if ndl_speech.speech_content else 0,
                "is_processed": False,
                "needs_review": False}

            # Create Speech object for validation
            speech = Speech(**speech_data)

            warnings = []
            if not speaker_info["normalized_name"]:
                warnings.append("Speaker name could not be normalized")
            if not speaker_info["normalized_party"]:
                warnings.append("Political party could not be identified")

            return MappingResult(
                success=True,
                mapped_data=speech,
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"Failed to map NDL speech {ndl_speech.speech_id}: {e}")
            return MappingResult(
                success=False,
                errors=[f"Mapping failed: {str(e)}"]
            )

    def extract_members_from_speeches(
            self, speeches: list[NDLSpeech]) -> list[dict[str, Any]]:
        """
        Extract unique member information from speech data

        Args:
            speeches: List of NDL Speech objects

        Returns:
            List of member data dictionaries
        """
        members_dict = {}

        for speech in speeches:
            speaker_info = self.speaker_normalizer.extract_speaker_info(
                speech.speaker_name,
                speech.speaker_group
            )

            normalized_name = speaker_info["normalized_name"]
            if not normalized_name or normalized_name in ["政府", "議長", "委員長"]:
                continue

            if normalized_name not in members_dict:
                members_dict[normalized_name] = {
                    "name": normalized_name,
                    "party": speaker_info["normalized_party"],
                    "house": None,  # Will be determined from meeting context
                    "is_active": True,
                    "speech_count": 0
                }

            members_dict[normalized_name]["speech_count"] += 1

        return list(members_dict.values())

    def extract_parties_from_speeches(
            self, speeches: list[NDLSpeech]) -> list[dict[str, Any]]:
        """
        Extract unique party information from speech data

        Args:
            speeches: List of NDL Speech objects

        Returns:
            List of party data dictionaries
        """
        parties_dict = {}

        for speech in speeches:
            speaker_info = self.speaker_normalizer.extract_speaker_info(
                speech.speaker_name,
                speech.speaker_group
            )

            party_name = speaker_info["normalized_party"]
            if not party_name or party_name in ["政府"]:
                continue

            if party_name not in parties_dict:
                parties_dict[party_name] = {
                    "name": party_name,
                    "is_active": True,
                    "member_count": 0
                }

            parties_dict[party_name]["member_count"] += 1

        return list(parties_dict.values())

    def _determine_meeting_type(self, ndl_meeting: NDLMeeting) -> str:
        """Determine meeting type from NDL meeting data"""
        title = ndl_meeting.title.lower() if ndl_meeting.title else ""

        if "本会議" in title:
            return "本会議"
        elif "委員会" in title:
            return "委員会"
        elif "分科会" in title:
            return "分科会"
        elif "小委員会" in title:
            return "小委員会"
        else:
            return "その他"

    def _determine_speaker_type(self, speaker_info: dict[str, str | None]) -> str:
        """Determine speaker type from normalized speaker information"""
        name = speaker_info["normalized_name"] or ""
        party = speaker_info["normalized_party"] or ""

        if party == "政府" or "大臣" in name or "長官" in name:
            return "minister"
        elif "議長" in name or "委員長" in name:
            return "official"
        elif party and party != "無所属":
            return "member"
        else:
            return "other"

    def _clean_speech_text(self, text: str) -> str:
        """Clean and normalize speech text"""
        if not text:
            return ""

        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text)

        # Remove common artifacts
        cleaned = re.sub(r'○[^○]*', '', cleaned)  # Remove procedural markers
        cleaned = re.sub(r'【[^】]*】', '', cleaned)  # Remove bracketed annotations

        # Trim
        cleaned = cleaned.strip()

        return cleaned

    def batch_map_speeches(
            self, speeches: list[NDLSpeech], meeting_id: str) -> dict[str, Any]:
        """
        Map multiple speeches in batch with statistics

        Args:
            speeches: List of NDL Speech objects
            meeting_id: Airtable Meeting record ID

        Returns:
            Dictionary with mapping results and statistics
        """
        mapped_speeches = []
        warnings = []
        errors = []

        for i, speech in enumerate(speeches):
            result = self.map_ndl_speech_to_airtable(speech, meeting_id)

            if result.success:
                mapped_speeches.append(result.mapped_data)
                warnings.extend(result.warnings)
            else:
                errors.extend(result.errors)
                self.logger.error(f"Failed to map speech {i}: {result.errors}")

        # Extract member and party information
        members = self.extract_members_from_speeches(speeches)
        parties = self.extract_parties_from_speeches(speeches)

        return {
            "speeches": mapped_speeches,
            "members": members,
            "parties": parties,
            "statistics": {
                "total_speeches": len(speeches),
                "mapped_speeches": len(mapped_speeches),
                "unique_members": len(members),
                "unique_parties": len(parties),
                "warnings_count": len(warnings),
                "errors_count": len(errors)
            },
            "warnings": warnings,
            "errors": errors
        }


# Example usage and testing
async def main():
    """Example usage of NDL Data Mapper"""
    from ..collectors.ndl_api_client import NDLAPIClient

    logging.basicConfig(level=logging.INFO)
    mapper = NDLDataMapper()

    # Test with sample data
    async with NDLAPIClient() as client:
        # Get sample meeting
        meetings = await client.search_meetings(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 21),
            max_records=1
        )

        if meetings:
            meeting = meetings[0]
            print(f"Testing with meeting: {meeting.title}")

            # Map meeting
            meeting_result = mapper.map_ndl_meeting_to_airtable(meeting)
            if meeting_result.success:
                print("✅ Meeting mapped successfully")
                print(f"Warnings: {meeting_result.warnings}")
            else:
                print(f"❌ Meeting mapping failed: {meeting_result.errors}")

            # Get and map speeches
            speeches = await client.get_speeches(meeting.meeting_id, max_records=10)
            if speeches:
                batch_result = mapper.batch_map_speeches(speeches, "MEETING_ID_123")
                print(
                    f"✅ Mapped {batch_result['statistics']['mapped_speeches']} speeches")
                print(
                    f"Found {batch_result['statistics']['unique_members']} unique members")
                print(
                    f"Found {batch_result['statistics']['unique_parties']} unique parties")

                if batch_result['warnings']:
                    print(f"⚠️  Warnings: {len(batch_result['warnings'])}")
                if batch_result['errors']:
                    print(f"❌ Errors: {len(batch_result['errors'])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
