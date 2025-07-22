"""
Bill data merger for combining data from multiple sources.
Handles data integration between Sangiin and Shugiin with conflict resolution.
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

from ..scraper.enhanced_diet_scraper import EnhancedBillData
from ..scraper.shugiin_scraper import ShugiinBillData


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving data conflicts"""

    SANGIIN_PRIORITY = "sangiin_priority"  # 参議院データを優先
    SHUGIIN_PRIORITY = "shugiin_priority"  # 衆議院データを優先
    MOST_COMPLETE = "most_complete"  # より完全なデータを優先
    LATEST_UPDATE = "latest_update"  # 最新更新データを優先
    MERGE_FIELDS = "merge_fields"  # フィールドごとに最適なデータを選択


@dataclass
class MergeConflict:
    """Data conflict information"""

    field_name: str
    sangiin_value: Any
    shugiin_value: Any
    resolution: str
    confidence: float


@dataclass
class MergeResult:
    """Result of data merge operation"""

    merged_bill: EnhancedBillData
    conflicts: list[MergeConflict] = field(default_factory=list)
    merge_quality_score: float = 0.0
    source_info: dict[str, Any] = field(default_factory=dict)


class BillDataMerger:
    """Bill data merger with intelligent conflict resolution"""

    def __init__(
        self,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MOST_COMPLETE,
        similarity_threshold: float = 0.8,
    ):
        self.conflict_strategy = conflict_strategy
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)

        # Field priority mappings for different strategies
        self.field_priorities = {
            ConflictResolutionStrategy.SANGIIN_PRIORITY: {
                "bill_outline": "sangiin",
                "committee_assignments": "sangiin",
                "voting_results": "sangiin",
            },
            ConflictResolutionStrategy.SHUGIIN_PRIORITY: {
                "supporting_members": "shugiin",
                "submitting_members": "shugiin",
            },
            ConflictResolutionStrategy.MOST_COMPLETE: {
                # Will be determined dynamically based on data completeness
            },
        }

    def merge_bills(
        self,
        sangiin_bills: list[EnhancedBillData],
        shugiin_bills: list[ShugiinBillData],
    ) -> list[MergeResult]:
        """Merge bills from both houses with conflict resolution"""

        self.logger.info(
            f"Merging {len(sangiin_bills)} Sangiin bills with {len(shugiin_bills)} Shugiin bills"
        )

        # Step 1: Find matching bills between houses
        bill_matches = self._find_matching_bills(sangiin_bills, shugiin_bills)

        # Step 2: Merge matched bills
        merged_results = []
        processed_shugiin = set()

        for sangiin_bill in sangiin_bills:
            shugiin_match = bill_matches.get(sangiin_bill.bill_id)

            if shugiin_match:
                # Merge the matched bills
                merge_result = self._merge_bill_pair(sangiin_bill, shugiin_match)
                merged_results.append(merge_result)
                processed_shugiin.add(shugiin_match.bill_id)
            else:
                # No match found, keep Sangiin bill as-is
                merge_result = MergeResult(
                    merged_bill=sangiin_bill,
                    conflicts=[],
                    merge_quality_score=sangiin_bill.data_quality_score or 0.0,
                    source_info={"sources": ["sangiin"], "primary_source": "sangiin"},
                )
                merged_results.append(merge_result)

        # Step 3: Add unmatched Shugiin bills
        for shugiin_bill in shugiin_bills:
            if shugiin_bill.bill_id not in processed_shugiin:
                # Convert to EnhancedBillData and add
                enhanced_bill = self._convert_to_enhanced_bill_data(shugiin_bill)
                merge_result = MergeResult(
                    merged_bill=enhanced_bill,
                    conflicts=[],
                    merge_quality_score=enhanced_bill.data_quality_score or 0.0,
                    source_info={"sources": ["shugiin"], "primary_source": "shugiin"},
                )
                merged_results.append(merge_result)

        self.logger.info(
            f"Merged {len(merged_results)} bills with {sum(len(r.conflicts) for r in merged_results)} conflicts"
        )
        return merged_results

    def _find_matching_bills(
        self,
        sangiin_bills: list[EnhancedBillData],
        shugiin_bills: list[ShugiinBillData],
    ) -> dict[str, ShugiinBillData]:
        """Find matching bills between houses using multiple criteria"""

        matches = {}

        for sangiin_bill in sangiin_bills:
            best_match = None
            best_score = 0.0

            for shugiin_bill in shugiin_bills:
                # Calculate similarity score
                score = self._calculate_similarity_score(sangiin_bill, shugiin_bill)

                if score > best_score and score >= self.similarity_threshold:
                    best_score = score
                    best_match = shugiin_bill

            if best_match:
                matches[sangiin_bill.bill_id] = best_match
                self.logger.debug(
                    f"Matched {sangiin_bill.bill_id} with {best_match.bill_id} (score: {best_score:.2f})"
                )

        return matches

    def _calculate_similarity_score(
        self, sangiin_bill: EnhancedBillData, shugiin_bill: ShugiinBillData
    ) -> float:
        """Calculate similarity score between two bills"""

        scores = []

        # Title similarity (high weight)
        if sangiin_bill.title and shugiin_bill.title:
            title_sim = SequenceMatcher(
                None, sangiin_bill.title, shugiin_bill.title
            ).ratio()
            scores.append(("title", title_sim, 0.4))

        # Diet session similarity (medium weight)
        if sangiin_bill.diet_session and shugiin_bill.diet_session:
            session_sim = (
                1.0 if sangiin_bill.diet_session == shugiin_bill.diet_session else 0.0
            )
            scores.append(("session", session_sim, 0.3))

        # Bill number similarity (medium weight)
        if sangiin_bill.bill_id and shugiin_bill.bill_id:
            # Extract numbers from bill IDs
            sangiin_num = re.findall(r"\d+", sangiin_bill.bill_id)
            shugiin_num = re.findall(r"\d+", shugiin_bill.bill_id)

            if sangiin_num and shugiin_num:
                num_sim = 1.0 if sangiin_num[-1] == shugiin_num[-1] else 0.0
                scores.append(("number", num_sim, 0.2))

        # Submitter type similarity (low weight)
        if sangiin_bill.submitter and shugiin_bill.submitter:
            submitter_sim = (
                1.0 if sangiin_bill.submitter == shugiin_bill.submitter else 0.0
            )
            scores.append(("submitter", submitter_sim, 0.1))

        # Calculate weighted average
        if scores:
            total_weight = sum(weight for _, _, weight in scores)
            weighted_sum = sum(score * weight for _, score, weight in scores)
            return weighted_sum / total_weight if total_weight > 0 else 0.0

        return 0.0

    def _merge_bill_pair(
        self, sangiin_bill: EnhancedBillData, shugiin_bill: ShugiinBillData
    ) -> MergeResult:
        """Merge a pair of matching bills"""

        # Convert Shugiin bill to EnhancedBillData for consistency
        shugiin_enhanced = self._convert_to_enhanced_bill_data(shugiin_bill)

        # Create merged bill starting with Sangiin data
        merged_bill = EnhancedBillData(
            bill_id=sangiin_bill.bill_id,
            title=sangiin_bill.title,
            submission_date=sangiin_bill.submission_date,
            status=sangiin_bill.status,
            stage=sangiin_bill.stage,
            submitter=sangiin_bill.submitter,
            category=sangiin_bill.category,
            url=sangiin_bill.url,
            source_url=sangiin_bill.source_url,
        )

        # Track conflicts
        conflicts = []

        # Merge fields based on strategy
        merge_fields = self._get_mergeable_fields()

        for field_name in merge_fields:
            sangiin_value = getattr(sangiin_bill, field_name, None)
            shugiin_value = getattr(shugiin_enhanced, field_name, None)

            merged_value, conflict = self._resolve_field_conflict(
                field_name, sangiin_value, shugiin_value
            )

            setattr(merged_bill, field_name, merged_value)

            if conflict:
                conflicts.append(conflict)

        # Set source information
        merged_bill.source_house = "両院"

        # Calculate merge quality score
        merge_quality = self._calculate_merge_quality_score(merged_bill, conflicts)

        return MergeResult(
            merged_bill=merged_bill,
            conflicts=conflicts,
            merge_quality_score=merge_quality,
            source_info={
                "sources": ["sangiin", "shugiin"],
                "primary_source": "sangiin",
                "sangiin_id": sangiin_bill.bill_id,
                "shugiin_id": shugiin_enhanced.bill_id,
            },
        )

    def _get_mergeable_fields(self) -> list[str]:
        """Get list of fields that can be merged"""
        return [
            "bill_outline",
            "background_context",
            "expected_effects",
            "key_provisions",
            "related_laws",
            "implementation_date",
            "submitting_members",
            "supporting_members",
            "submitting_party",
            "sponsoring_ministry",
            "committee_assignments",
            "voting_results",
            "amendments",
            "inter_house_status",
            "summary",
            "full_text",
            "purpose",
            "submitted_date",
            "first_reading_date",
            "committee_referral_date",
            "committee_report_date",
            "final_vote_date",
            "promulgated_date",
        ]

    def _resolve_field_conflict(
        self, field_name: str, sangiin_value: Any, shugiin_value: Any
    ) -> tuple[Any, MergeConflict | None]:
        """Resolve conflict between field values"""

        # If one value is None, use the other
        if sangiin_value is None and shugiin_value is not None:
            return shugiin_value, None
        if shugiin_value is None and sangiin_value is not None:
            return sangiin_value, None
        if sangiin_value is None and shugiin_value is None:
            return None, None

        # If values are the same, no conflict
        if sangiin_value == shugiin_value:
            return sangiin_value, None

        # Handle different strategies
        if self.conflict_strategy == ConflictResolutionStrategy.SANGIIN_PRIORITY:
            resolution = "sangiin_priority"
            merged_value = sangiin_value
            confidence = 0.8

        elif self.conflict_strategy == ConflictResolutionStrategy.SHUGIIN_PRIORITY:
            resolution = "shugiin_priority"
            merged_value = shugiin_value
            confidence = 0.8

        elif self.conflict_strategy == ConflictResolutionStrategy.MOST_COMPLETE:
            # Choose the more complete value
            sangiin_score = self._calculate_field_completeness(sangiin_value)
            shugiin_score = self._calculate_field_completeness(shugiin_value)

            if sangiin_score > shugiin_score:
                merged_value = sangiin_value
                resolution = "sangiin_more_complete"
                confidence = (
                    sangiin_score / (sangiin_score + shugiin_score)
                    if (sangiin_score + shugiin_score) > 0
                    else 0.5
                )
            else:
                merged_value = shugiin_value
                resolution = "shugiin_more_complete"
                confidence = (
                    shugiin_score / (sangiin_score + shugiin_score)
                    if (sangiin_score + shugiin_score) > 0
                    else 0.5
                )

        elif self.conflict_strategy == ConflictResolutionStrategy.MERGE_FIELDS:
            # Try to merge fields intelligently
            merged_value, resolution, confidence = self._intelligent_field_merge(
                field_name, sangiin_value, shugiin_value
            )

        else:
            # Default to Sangiin priority
            merged_value = sangiin_value
            resolution = "default_sangiin"
            confidence = 0.5

        # Create conflict record
        conflict = MergeConflict(
            field_name=field_name,
            sangiin_value=sangiin_value,
            shugiin_value=shugiin_value,
            resolution=resolution,
            confidence=confidence,
        )

        return merged_value, conflict

    def _calculate_field_completeness(self, value: Any) -> float:
        """Calculate completeness score for a field value"""
        if value is None:
            return 0.0

        if isinstance(value, str):
            return len(value.strip()) / 100.0  # Normalize by length
        elif isinstance(value, list | dict):
            return len(value) / 10.0  # Normalize by item count
        elif isinstance(value, int | float):
            return 1.0 if value != 0 else 0.5
        else:
            return 1.0

    def _intelligent_field_merge(
        self, field_name: str, sangiin_value: Any, shugiin_value: Any
    ) -> tuple[Any, str, float]:
        """Intelligently merge field values"""

        # List fields: merge unique items
        if field_name in [
            "key_provisions",
            "related_laws",
            "submitting_members",
            "supporting_members",
        ]:
            if isinstance(sangiin_value, list) and isinstance(shugiin_value, list):
                merged_list = list(set(sangiin_value + shugiin_value))
                return merged_list, "merged_lists", 0.9

        # Dictionary fields: merge dictionaries
        elif field_name in ["committee_assignments", "voting_results"]:
            if isinstance(sangiin_value, dict) and isinstance(shugiin_value, dict):
                merged_dict = {**sangiin_value, **shugiin_value}
                return merged_dict, "merged_dicts", 0.9

        # Text fields: choose longer text
        elif field_name in [
            "bill_outline",
            "background_context",
            "expected_effects",
            "summary",
        ]:
            if isinstance(sangiin_value, str) and isinstance(shugiin_value, str):
                if len(sangiin_value) > len(shugiin_value):
                    return sangiin_value, "longer_text_sangiin", 0.7
                else:
                    return shugiin_value, "longer_text_shugiin", 0.7

        # Default to Sangiin value
        return sangiin_value, "default_sangiin", 0.5

    def _convert_to_enhanced_bill_data(
        self, shugiin_bill: ShugiinBillData
    ) -> EnhancedBillData:
        """Convert ShugiinBillData to EnhancedBillData"""

        # Create enhanced bill data with Shugiin data
        enhanced_bill = EnhancedBillData(
            bill_id=shugiin_bill.bill_id,
            title=shugiin_bill.title,
            submission_date=shugiin_bill.submission_date,
            status=shugiin_bill.status,
            stage=shugiin_bill.stage,
            submitter=shugiin_bill.submitter,
            category=shugiin_bill.category,
            url=shugiin_bill.url,
            source_url=shugiin_bill.source_url,
            summary=shugiin_bill.summary,
            # Enhanced fields from Shugiin
            bill_outline=shugiin_bill.bill_outline,
            background_context=shugiin_bill.background_context,
            expected_effects=shugiin_bill.expected_effects,
            key_provisions=shugiin_bill.key_provisions,
            related_laws=shugiin_bill.related_laws,
            implementation_date=shugiin_bill.implementation_date,
            # Submission information
            submitting_members=shugiin_bill.submitting_members,
            supporting_members=shugiin_bill.supporting_members,
            submitting_party=shugiin_bill.submitting_party,
            sponsoring_ministry=shugiin_bill.sponsoring_ministry,
            # Process tracking
            committee_assignments=shugiin_bill.committee_assignments,
            voting_results=shugiin_bill.voting_results,
            amendments=shugiin_bill.amendments,
            inter_house_status=shugiin_bill.inter_house_status,
            # Source metadata
            source_house=shugiin_bill.source_house,
            data_quality_score=shugiin_bill.data_quality_score,
            # Other fields
            diet_session=shugiin_bill.diet_session,
            house_of_origin=shugiin_bill.house_of_origin,
            submitter_type=shugiin_bill.submitter_type,
        )

        return enhanced_bill

    def _calculate_merge_quality_score(
        self, merged_bill: EnhancedBillData, conflicts: list[MergeConflict]
    ) -> float:
        """Calculate quality score for merged bill"""

        # Start with base quality score
        base_score = merged_bill.data_quality_score or 0.0

        # Adjust based on conflicts
        if conflicts:
            # Reduce score based on number and confidence of conflicts
            conflict_penalty = 0.0
            for conflict in conflicts:
                conflict_penalty += (1.0 - conflict.confidence) * 0.1

            # Cap penalty at 0.3
            conflict_penalty = min(conflict_penalty, 0.3)
            base_score = max(base_score - conflict_penalty, 0.0)

        # Bonus for having multiple sources
        base_score += 0.1  # Multi-source bonus

        return min(base_score, 1.0)

    def get_merge_statistics(self, merge_results: list[MergeResult]) -> dict[str, Any]:
        """Get statistics about merge results"""

        total_bills = len(merge_results)
        bills_with_conflicts = sum(1 for r in merge_results if r.conflicts)
        total_conflicts = sum(len(r.conflicts) for r in merge_results)

        source_distribution = {
            "sangiin_only": sum(
                1
                for r in merge_results
                if r.source_info.get("primary_source") == "sangiin"
                and len(r.source_info.get("sources", [])) == 1
            ),
            "shugiin_only": sum(
                1
                for r in merge_results
                if r.source_info.get("primary_source") == "shugiin"
                and len(r.source_info.get("sources", [])) == 1
            ),
            "both_houses": sum(
                1 for r in merge_results if len(r.source_info.get("sources", [])) == 2
            ),
        }

        avg_quality_score = (
            sum(r.merge_quality_score for r in merge_results) / total_bills
            if total_bills > 0
            else 0.0
        )

        return {
            "total_bills": total_bills,
            "bills_with_conflicts": bills_with_conflicts,
            "total_conflicts": total_conflicts,
            "conflict_rate": bills_with_conflicts / total_bills
            if total_bills > 0
            else 0.0,
            "avg_conflicts_per_bill": total_conflicts / total_bills
            if total_bills > 0
            else 0.0,
            "source_distribution": source_distribution,
            "avg_quality_score": avg_quality_score,
        }
