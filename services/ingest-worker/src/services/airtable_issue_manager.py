"""
Airtable Issue Manager - Enhanced integration for dual-level policy issues.
Manages hierarchical issue structure with human review workflow.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from ....shared.src.shared.clients.airtable import AirtableClient
from .policy_issue_extractor import DualLevelIssue

logger = logging.getLogger(__name__)


@dataclass
class AirtableIssueRecord:
    """Airtable Issues table structure for dual-level issues."""

    # Core fields
    issue_id: str  # UUID (PK)
    label_lv1: str  # High school level (≤60 chars, verb ending)
    label_lv2: str  # General reader level (≤60 chars, verb ending)
    parent_id: str | None = None  # Self-relation (null for lv1)
    confidence: float = 0.0  # LLM confidence score (0-1)

    # Status management
    status: str = "pending"  # pending/approved/rejected/failed_validation
    valid_from: date = field(default_factory=date.today)  # Defaults to created_at
    valid_to: date | None = None  # Nullable, for versioning

    # Metadata
    source_bill_id: str | None = None  # Link to originating bill
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    reviewer_notes: str | None = None  # Optional review comments

    # Quality metrics
    quality_score: float = 0.0  # Calculated quality score
    extraction_version: str = "1.0.0"  # Extractor version

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            "issue_id": self.issue_id,
            "label_lv1": self.label_lv1,
            "label_lv2": self.label_lv2,
            "parent_id": self.parent_id,
            "confidence": self.confidence,
            "status": self.status,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "source_bill_id": self.source_bill_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reviewer_notes": self.reviewer_notes,
            "quality_score": self.quality_score,
            "extraction_version": self.extraction_version,
        }


class AirtableIssueManager:
    """Enhanced Airtable client for dual-level policy issues."""

    def __init__(self, airtable_client: AirtableClient | None = None):
        self.client = airtable_client or AirtableClient()
        self.table_name = "Issues"
        self.logger = logger

        # Rate limiting settings
        self.batch_size = 10  # Airtable limit
        self.batch_delay = 0.3  # Seconds between batches

    async def create_issue_pair(
        self, dual_issue: DualLevelIssue, bill_id: str, quality_score: float = 0.0
    ) -> tuple[str, str]:
        """Create linked lv1 and lv2 issue records."""

        # Generate UUIDs for both records
        lv1_issue_id = str(uuid.uuid4())
        lv2_issue_id = str(uuid.uuid4())

        try:
            # Create lv1 issue (parent)
            lv1_record = await self.client._rate_limited_request(
                "POST",
                f"{self.client.base_url}/{self.table_name}",
                json={
                    "fields": {
                        "Issue_ID": lv1_issue_id,
                        "Label_Lv1": dual_issue.label_lv1,
                        "Label_Lv2": "",  # Empty for lv1 records
                        "Parent_ID": None,
                        "Confidence": dual_issue.confidence,
                        "Status": "pending",
                        "Source_Bill_ID": bill_id,
                        "Valid_From": date.today().isoformat(),
                        "Quality_Score": quality_score,
                        "Extraction_Version": "1.0.0",
                        "Created_At": datetime.now().isoformat(),
                        "Updated_At": datetime.now().isoformat(),
                    }
                },
            )

            # Create lv2 issue (child)
            lv2_record = await self.client._rate_limited_request(
                "POST",
                f"{self.client.base_url}/{self.table_name}",
                json={
                    "fields": {
                        "Issue_ID": lv2_issue_id,
                        "Label_Lv1": "",  # Empty for lv2 records
                        "Label_Lv2": dual_issue.label_lv2,
                        "Parent_ID": lv1_record["id"],  # Link to lv1 record
                        "Confidence": dual_issue.confidence,
                        "Status": "pending",
                        "Source_Bill_ID": bill_id,
                        "Valid_From": date.today().isoformat(),
                        "Quality_Score": quality_score,
                        "Extraction_Version": "1.0.0",
                        "Created_At": datetime.now().isoformat(),
                        "Updated_At": datetime.now().isoformat(),
                    }
                },
            )

            self.logger.info(
                f"Created issue pair: lv1={lv1_record['id']}, lv2={lv2_record['id']}"
            )
            return lv1_record["id"], lv2_record["id"]

        except Exception as e:
            self.logger.error(f"Failed to create issue pair: {e}")
            raise

    async def create_unclassified_issue_pair(self, bill_id: str) -> tuple[str, str]:
        """Create a special "未分類" issue pair for unclassifiable bills."""

        unclassified_issue = DualLevelIssue(
            label_lv1="未分類の課題を扱う",
            label_lv2="分類が困難な政策課題を処理する",
            confidence=0.1,  # Low confidence for unclassified
        )

        return await self.create_issue_pair(
            unclassified_issue, bill_id, quality_score=0.1
        )

    async def get_issue_record(self, record_id: str) -> AirtableIssueRecord | None:
        """Get issue record by Airtable record ID."""
        try:
            response = await self.client._rate_limited_request(
                "GET", f"{self.client.base_url}/{self.table_name}/{record_id}"
            )

            fields = response.get("fields", {})

            return AirtableIssueRecord(
                issue_id=fields.get("Issue_ID", ""),
                label_lv1=fields.get("Label_Lv1", ""),
                label_lv2=fields.get("Label_Lv2", ""),
                parent_id=fields.get("Parent_ID"),
                confidence=fields.get("Confidence", 0.0),
                status=fields.get("Status", "pending"),
                valid_from=(
                    datetime.fromisoformat(fields["Valid_From"]).date()
                    if fields.get("Valid_From")
                    else date.today()
                ),
                valid_to=(
                    datetime.fromisoformat(fields["Valid_To"]).date()
                    if fields.get("Valid_To")
                    else None
                ),
                source_bill_id=fields.get("Source_Bill_ID"),
                created_at=(
                    datetime.fromisoformat(fields["Created_At"])
                    if fields.get("Created_At")
                    else datetime.now()
                ),
                updated_at=(
                    datetime.fromisoformat(fields["Updated_At"])
                    if fields.get("Updated_At")
                    else datetime.now()
                ),
                reviewer_notes=fields.get("Reviewer_Notes"),
                quality_score=fields.get("Quality_Score", 0.0),
                extraction_version=fields.get("Extraction_Version", "1.0.0"),
            )

        except Exception as e:
            self.logger.error(f"Failed to get issue record {record_id}: {e}")
            return None

    async def update_issue_status(
        self, record_id: str, status: str, reviewer_notes: str | None = None
    ) -> bool:
        """Update issue status (for human review workflow)."""
        try:
            update_data = {
                "fields": {"Status": status, "Updated_At": datetime.now().isoformat()}
            }

            if reviewer_notes:
                update_data["fields"]["Reviewer_Notes"] = reviewer_notes

            await self.client._rate_limited_request(
                "PATCH",
                f"{self.client.base_url}/{self.table_name}/{record_id}",
                json=update_data,
            )

            self.logger.info(f"Updated issue {record_id} status to {status}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update issue status: {e}")
            return False

    async def list_issues_by_status(
        self, status: str, max_records: int = 100
    ) -> list[dict[str, Any]]:
        """List issues by status with Airtable record metadata."""
        try:
            filter_formula = f"{{Status}} = '{status}'"

            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"filterByFormula": filter_formula, "maxRecords": max_records},
            )

            return response.get("records", [])

        except Exception as e:
            self.logger.error(f"Failed to list issues by status {status}: {e}")
            return []

    async def count_pending_issues(self, exclude_failed_validation: bool = True) -> int:
        """Count pending issues for Discord notifications."""
        try:
            if exclude_failed_validation:
                filter_formula = "AND({Status} = 'pending')"
            else:
                filter_formula = "{Status} = 'pending'"

            # Get all records to count (Airtable doesn't provide direct count)
            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={
                    "filterByFormula": filter_formula,
                    "maxRecords": 1000,  # Reasonable limit for counting
                },
            )

            return len(response.get("records", []))

        except Exception as e:
            self.logger.error(f"Failed to count pending issues: {e}")
            return 0

    async def get_issues_by_level(
        self, level: int, status: str = "approved", max_records: int = 100
    ) -> list[dict[str, Any]]:
        """Get issues filtered by level (1 or 2)."""
        try:
            if level == 1:
                # Level 1 issues have parent_id = null
                filter_formula = f"AND({{Status}} = '{status}', {{Parent_ID}} = BLANK(), {{Valid_To}} = BLANK())"
            elif level == 2:
                # Level 2 issues have parent_id != null
                filter_formula = f"AND({{Status}} = '{status}', {{Parent_ID}} != BLANK(), {{Valid_To}} = BLANK())"
            else:
                raise ValueError("Level must be 1 or 2")

            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"filterByFormula": filter_formula, "maxRecords": max_records},
            )

            return response.get("records", [])

        except Exception as e:
            self.logger.error(f"Failed to get issues by level {level}: {e}")
            return []

    async def get_issue_tree(self, status: str = "approved") -> dict[str, Any]:
        """Get hierarchical issue tree structure."""
        try:
            # Get all approved issues
            filter_formula = f"AND({{Status}} = '{status}', {{Valid_To}} = BLANK())"

            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"filterByFormula": filter_formula, "maxRecords": 1000},
            )

            all_issues = response.get("records", [])

            # Build tree structure
            tree = {}

            # First pass: create parent entries
            for issue in all_issues:
                fields = issue.get("fields", {})
                if not fields.get("Parent_ID"):  # lv1 issue
                    issue_id = issue["id"]
                    tree[issue_id] = {
                        "issue_id": fields.get("Issue_ID"),
                        "label_lv1": fields.get("Label_Lv1", ""),
                        "confidence": fields.get("Confidence", 0.0),
                        "source_bill_id": fields.get("Source_Bill_ID"),
                        "children": [],
                    }

            # Second pass: add children
            for issue in all_issues:
                fields = issue.get("fields", {})
                parent_id = fields.get("Parent_ID")
                if parent_id and parent_id in tree:  # lv2 issue
                    tree[parent_id]["children"].append(
                        {
                            "issue_id": fields.get("Issue_ID"),
                            "label_lv2": fields.get("Label_Lv2", ""),
                            "confidence": fields.get("Confidence", 0.0),
                            "source_bill_id": fields.get("Source_Bill_ID"),
                        }
                    )

            return tree

        except Exception as e:
            self.logger.error(f"Failed to get issue tree: {e}")
            return {}

    async def get_issues_by_bill(
        self, bill_id: str, status: str = "approved"
    ) -> list[dict[str, Any]]:
        """Get all issues related to a specific bill."""
        try:
            filter_formula = f"AND({{Status}} = '{status}', {{Source_Bill_ID}} = '{bill_id}', {{Valid_To}} = BLANK())"

            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"filterByFormula": filter_formula, "maxRecords": 100},
            )

            return response.get("records", [])

        except Exception as e:
            self.logger.error(f"Failed to get issues for bill {bill_id}: {e}")
            return []

    async def invalidate_issues(
        self, issue_ids: list[str], reason: str = "structural_change"
    ) -> bool:
        """Invalidate existing issues by setting valid_to date (for versioning)."""
        try:
            today = date.today().isoformat()

            for issue_id in issue_ids:
                await self.client._rate_limited_request(
                    "PATCH",
                    f"{self.client.base_url}/{self.table_name}/{issue_id}",
                    json={
                        "fields": {
                            "Valid_To": today,
                            "Updated_At": datetime.now().isoformat(),
                            "Reviewer_Notes": f"Invalidated: {reason}",
                        }
                    },
                )

            self.logger.info(f"Invalidated {len(issue_ids)} issues: {reason}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to invalidate issues: {e}")
            return False

    async def batch_create_issue_pairs(
        self,
        dual_issues: list[tuple[DualLevelIssue, str]],
        quality_scores: list[float] | None = None,
    ) -> list[tuple[str, str]]:
        """Batch create multiple issue pairs for efficiency."""

        if quality_scores is None:
            quality_scores = [0.0] * len(dual_issues)

        results = []

        # Process in batches to respect Airtable limits
        for i in range(
            0, len(dual_issues), self.batch_size // 2
        ):  # Divide by 2 since we create 2 records per issue
            batch = dual_issues[i : i + self.batch_size // 2]
            batch_scores = quality_scores[i : i + self.batch_size // 2]

            batch_results = []

            for j, (dual_issue, bill_id) in enumerate(batch):
                try:
                    quality_score = batch_scores[j]
                    lv1_id, lv2_id = await self.create_issue_pair(
                        dual_issue, bill_id, quality_score
                    )
                    batch_results.append((lv1_id, lv2_id))

                    # Small delay between individual creates within batch
                    if j < len(batch) - 1:
                        await asyncio.sleep(0.1)

                except Exception as e:
                    self.logger.error(f"Failed to create issue pair in batch: {e}")
                    batch_results.append((None, None))

            results.extend(batch_results)

            # Delay between batches
            if i + self.batch_size // 2 < len(dual_issues):
                await asyncio.sleep(self.batch_delay)

        successful_pairs = [pair for pair in results if pair[0] is not None]
        self.logger.info(
            f"Batch created {len(successful_pairs)}/{len(dual_issues)} issue pairs"
        )

        return results

    async def get_issue_statistics(self) -> dict[str, Any]:
        """Get comprehensive issue statistics."""
        try:
            # Get all issues
            all_issues_response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"maxRecords": 1000},
            )

            all_issues = all_issues_response.get("records", [])

            # Calculate statistics
            stats = {
                "total_issues": len(all_issues),
                "by_status": {},
                "by_level": {"lv1": 0, "lv2": 0},
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "failed_validation_count": 0,
                "average_confidence": 0.0,
                "average_quality_score": 0.0,
                "bills_with_issues": set(),
                "issues_by_bill": {},
            }

            confidence_scores = []
            quality_scores = []

            for issue in all_issues:
                fields = issue.get("fields", {})
                status = fields.get("Status", "unknown")

                # Count by status
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                # Count by level
                if fields.get("Parent_ID"):
                    stats["by_level"]["lv2"] += 1
                else:
                    stats["by_level"]["lv1"] += 1

                # Track specific statuses
                if status == "pending":
                    stats["pending_count"] += 1
                elif status == "approved":
                    stats["approved_count"] += 1
                elif status == "rejected":
                    stats["rejected_count"] += 1
                elif status == "failed_validation":
                    stats["failed_validation_count"] += 1

                # Collect confidence and quality scores
                confidence = fields.get("Confidence", 0.0)
                quality = fields.get("Quality_Score", 0.0)
                confidence_scores.append(confidence)
                quality_scores.append(quality)

                # Track bills with issues
                bill_id = fields.get("Source_Bill_ID")
                if bill_id:
                    stats["bills_with_issues"].add(bill_id)
                    stats["issues_by_bill"][bill_id] = (
                        stats["issues_by_bill"].get(bill_id, 0) + 1
                    )

            # Calculate averages
            if confidence_scores:
                stats["average_confidence"] = sum(confidence_scores) / len(
                    confidence_scores
                )
            if quality_scores:
                stats["average_quality_score"] = sum(quality_scores) / len(
                    quality_scores
                )

            stats["unique_bills_count"] = len(stats["bills_with_issues"])
            stats["bills_with_issues"] = list(
                stats["bills_with_issues"]
            )  # Convert set to list for JSON

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get issue statistics: {e}")
            return {}

    async def search_issues(
        self,
        query: str,
        level: int | None = None,
        status: str = "approved",
        max_records: int = 50,
    ) -> list[dict[str, Any]]:
        """Search issues by text query."""
        try:
            # Build search filter
            search_filters = [f"{{Status}} = '{status}'", "{Valid_To} = BLANK()"]

            # Add level filter
            if level == 1:
                search_filters.append("{Parent_ID} = BLANK()")
            elif level == 2:
                search_filters.append("{Parent_ID} != BLANK()")

            # Add text search (search in both label fields)
            text_search = f"OR(FIND('{query}', {{Label_Lv1}}) > 0, FIND('{query}', {{Label_Lv2}}) > 0)"
            search_filters.append(text_search)

            filter_formula = "AND(" + ", ".join(search_filters) + ")"

            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"filterByFormula": filter_formula, "maxRecords": max_records},
            )

            return response.get("records", [])

        except Exception as e:
            self.logger.error(f"Failed to search issues: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if Airtable Issues table is accessible."""
        try:
            # Try to get one record
            response = await self.client._rate_limited_request(
                "GET",
                f"{self.client.base_url}/{self.table_name}",
                params={"maxRecords": 1},
            )

            return "records" in response

        except Exception as e:
            self.logger.error(f"Airtable issue manager health check failed: {e}")
            return False
