"""
Issue Versioning Service - Manages temporal versioning and history tracking.
Handles issue version transitions, audit trails, and conflict resolution.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

from .airtable_issue_manager import AirtableIssueManager, AirtableIssueRecord

logger = logging.getLogger(__name__)


class VersionChangeType(Enum):
    """Types of version changes."""

    CONTENT_UPDATE = "content_update"
    STATUS_CHANGE = "status_change"
    BULK_MIGRATION = "bulk_migration"
    MANUAL_CORRECTION = "manual_correction"
    SYSTEM_CLEANUP = "system_cleanup"


@dataclass
class IssueVersionHistory:
    """Version history entry for an issue."""

    version_id: str  # UUID for this version
    issue_id: str  # Original issue UUID (stays same across versions)
    record_id: str  # Airtable record ID
    version_number: int  # Sequential version number (1, 2, 3, ...)
    change_type: VersionChangeType  # What triggered this version
    change_description: str  # Human-readable description

    # Temporal fields
    valid_from: date
    valid_to: date | None = None  # None means current version
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"  # User or system that made the change

    # Content snapshot
    label_lv1: str = ""
    label_lv2: str = ""
    parent_id: str | None = None
    confidence: float = 0.0
    status: str = "pending"
    source_bill_id: str | None = None
    quality_score: float = 0.0

    # Metadata
    previous_version_id: str | None = None
    next_version_id: str | None = None
    rollback_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "version_id": self.version_id,
            "issue_id": self.issue_id,
            "record_id": self.record_id,
            "version_number": self.version_number,
            "change_type": self.change_type.value,
            "change_description": self.change_description,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "label_lv1": self.label_lv1,
            "label_lv2": self.label_lv2,
            "parent_id": self.parent_id,
            "confidence": self.confidence,
            "status": self.status,
            "source_bill_id": self.source_bill_id,
            "quality_score": self.quality_score,
            "previous_version_id": self.previous_version_id,
            "next_version_id": self.next_version_id,
            "rollback_available": self.rollback_available,
        }


@dataclass
class ConflictResolution:
    """Conflict resolution strategy for concurrent modifications."""

    strategy: str  # merge, overwrite, create_branch, manual_review
    winner_version_id: str  # Which version won the conflict
    loser_version_id: str  # Which version was superseded
    merge_result: dict[str, Any] | None = None  # Merged content if applicable
    resolution_timestamp: datetime = field(default_factory=datetime.now)
    resolved_by: str = "system"
    notes: str = ""


class IssueVersioningService:
    """Service for managing issue versioning and history."""

    def __init__(self, airtable_manager: AirtableIssueManager | None = None):
        self.airtable_manager = airtable_manager or AirtableIssueManager()
        self.logger = logger

        # In-memory version tracking (in production, use database)
        self.version_history: dict[str, list[IssueVersionHistory]] = {}
        self.conflict_log: list[ConflictResolution] = []

        # Configuration
        self.max_versions_per_issue = 50
        self.version_retention_days = 365
        self.auto_cleanup_enabled = True

    async def create_initial_version(
        self, issue_record: AirtableIssueRecord, created_by: str = "system"
    ) -> IssueVersionHistory:
        """Create the initial version entry for a new issue."""

        version_id = str(uuid.uuid4())

        initial_version = IssueVersionHistory(
            version_id=version_id,
            issue_id=issue_record.issue_id,
            record_id="",  # Will be set after Airtable creation
            version_number=1,
            change_type=VersionChangeType.CONTENT_UPDATE,
            change_description="Initial issue creation",
            valid_from=issue_record.valid_from,
            valid_to=None,  # Current version
            created_at=issue_record.created_at,
            created_by=created_by,
            label_lv1=issue_record.label_lv1,
            label_lv2=issue_record.label_lv2,
            parent_id=issue_record.parent_id,
            confidence=issue_record.confidence,
            status=issue_record.status,
            source_bill_id=issue_record.source_bill_id,
            quality_score=issue_record.quality_score,
        )

        # Store in version history
        if issue_record.issue_id not in self.version_history:
            self.version_history[issue_record.issue_id] = []

        self.version_history[issue_record.issue_id].append(initial_version)

        self.logger.info(
            f"Created initial version {version_id} for issue {issue_record.issue_id}"
        )
        return initial_version

    async def create_new_version(
        self,
        issue_id: str,
        updated_record: AirtableIssueRecord,
        change_type: VersionChangeType,
        change_description: str,
        created_by: str = "system",
    ) -> tuple[IssueVersionHistory, bool]:
        """Create a new version of an existing issue."""

        # Get current version
        current_version = await self.get_current_version(issue_id)
        if not current_version:
            raise ValueError(f"No current version found for issue {issue_id}")

        # Check for conflicts (concurrent modifications)
        conflict_detected = await self._detect_version_conflicts(
            issue_id, updated_record
        )

        # Create new version
        new_version_id = str(uuid.uuid4())
        new_version_number = current_version.version_number + 1

        new_version = IssueVersionHistory(
            version_id=new_version_id,
            issue_id=issue_id,
            record_id=updated_record.issue_id,  # Airtable record ID
            version_number=new_version_number,
            change_type=change_type,
            change_description=change_description,
            valid_from=updated_record.valid_from,
            valid_to=None,  # New current version
            created_at=datetime.now(),
            created_by=created_by,
            label_lv1=updated_record.label_lv1,
            label_lv2=updated_record.label_lv2,
            parent_id=updated_record.parent_id,
            confidence=updated_record.confidence,
            status=updated_record.status,
            source_bill_id=updated_record.source_bill_id,
            quality_score=updated_record.quality_score,
            previous_version_id=current_version.version_id,
        )

        # Update current version to close it
        current_version.valid_to = updated_record.valid_from
        current_version.next_version_id = new_version_id

        # Add to version history
        self.version_history[issue_id].append(new_version)

        # Handle conflicts if detected
        if conflict_detected:
            await self._resolve_version_conflict(
                current_version, new_version, created_by
            )

        self.logger.info(
            f"Created version {new_version_number} for issue {issue_id}: {change_description}"
        )
        return new_version, conflict_detected

    async def get_current_version(self, issue_id: str) -> IssueVersionHistory | None:
        """Get the current active version of an issue."""

        if issue_id not in self.version_history:
            return None

        versions = self.version_history[issue_id]
        current_versions = [v for v in versions if v.valid_to is None]

        if not current_versions:
            return None

        if len(current_versions) > 1:
            self.logger.warning(f"Multiple current versions found for issue {issue_id}")
            # Return the most recent one
            return max(current_versions, key=lambda x: x.created_at)

        return current_versions[0]

    async def get_version_history(
        self, issue_id: str, include_closed: bool = True
    ) -> list[IssueVersionHistory]:
        """Get complete version history for an issue."""

        if issue_id not in self.version_history:
            return []

        versions = self.version_history[issue_id]

        if not include_closed:
            versions = [v for v in versions if v.valid_to is None]

        # Sort by version number
        return sorted(versions, key=lambda x: x.version_number)

    async def get_version_at_date(
        self, issue_id: str, target_date: date
    ) -> IssueVersionHistory | None:
        """Get the version that was active on a specific date."""

        if issue_id not in self.version_history:
            return None

        versions = self.version_history[issue_id]

        for version in versions:
            if version.valid_from <= target_date:
                if version.valid_to is None or version.valid_to > target_date:
                    return version

        return None

    async def rollback_to_version(
        self,
        issue_id: str,
        target_version_id: str,
        rollback_reason: str,
        created_by: str = "system",
    ) -> bool:
        """Rollback an issue to a previous version."""

        # Get target version
        target_version = None
        if issue_id in self.version_history:
            for version in self.version_history[issue_id]:
                if version.version_id == target_version_id:
                    target_version = version
                    break

        if not target_version:
            self.logger.error(
                f"Target version {target_version_id} not found for issue {issue_id}"
            )
            return False

        if not target_version.rollback_available:
            self.logger.error(f"Rollback not available for version {target_version_id}")
            return False

        # Create rollback record in Airtable
        rollback_record = AirtableIssueRecord(
            issue_id=issue_id,
            label_lv1=target_version.label_lv1,
            label_lv2=target_version.label_lv2,
            parent_id=target_version.parent_id,
            confidence=target_version.confidence,
            status=target_version.status,
            valid_from=date.today(),
            source_bill_id=target_version.source_bill_id,
            quality_score=target_version.quality_score,
            reviewer_notes=f"Rollback to version {target_version.version_number}: {rollback_reason}",
        )

        # Create new version for the rollback
        rollback_version, _ = await self.create_new_version(
            issue_id=issue_id,
            updated_record=rollback_record,
            change_type=VersionChangeType.MANUAL_CORRECTION,
            change_description=f"Rollback to version {target_version.version_number}: {rollback_reason}",
            created_by=created_by,
        )

        self.logger.info(
            f"Rolled back issue {issue_id} to version {target_version.version_number}"
        )
        return True

    async def _detect_version_conflicts(
        self, issue_id: str, new_record: AirtableIssueRecord
    ) -> bool:
        """Detect if there are concurrent modifications causing conflicts."""

        current_version = await self.get_current_version(issue_id)
        if not current_version:
            return False

        # Check if current version was modified recently by different user
        time_threshold = datetime.now() - timedelta(minutes=5)
        if current_version.created_at > time_threshold:
            # Potential conflict if content differs significantly
            content_diff_score = self._calculate_content_difference(
                current_version, new_record
            )
            return content_diff_score > 0.5  # Significant difference threshold

        return False

    def _calculate_content_difference(
        self, version: IssueVersionHistory, record: AirtableIssueRecord
    ) -> float:
        """Calculate content difference score between version and record."""

        differences = 0
        total_fields = 6

        if version.label_lv1 != record.label_lv1:
            differences += 1
        if version.label_lv2 != record.label_lv2:
            differences += 1
        if version.confidence != record.confidence:
            differences += 1
        if version.status != record.status:
            differences += 1
        if version.source_bill_id != record.source_bill_id:
            differences += 1
        if abs(version.quality_score - record.quality_score) > 0.1:
            differences += 1

        return differences / total_fields

    async def _resolve_version_conflict(
        self,
        old_version: IssueVersionHistory,
        new_version: IssueVersionHistory,
        created_by: str,
    ) -> ConflictResolution:
        """Resolve version conflicts using predefined strategies."""

        # Simple strategy: newer version wins, log the conflict
        resolution = ConflictResolution(
            strategy="overwrite",
            winner_version_id=new_version.version_id,
            loser_version_id=old_version.version_id,
            resolved_by=created_by,
            notes=f"Automatic conflict resolution: newer version {new_version.version_number} overwrote concurrent changes",
        )

        self.conflict_log.append(resolution)

        self.logger.warning(
            f"Version conflict resolved for issue {new_version.issue_id}: "
            f"version {new_version.version_number} overwrote concurrent changes"
        )

        return resolution

    async def cleanup_old_versions(
        self, cutoff_date: date | None = None
    ) -> dict[str, int]:
        """Clean up old versions beyond retention period."""

        if not self.auto_cleanup_enabled:
            return {"cleaned": 0, "retained": 0}

        if cutoff_date is None:
            cutoff_date = date.today() - timedelta(days=self.version_retention_days)

        cleaned_count = 0
        retained_count = 0

        for issue_id, versions in self.version_history.items():
            # Always keep current version and recent versions
            current_version = await self.get_current_version(issue_id)

            for version in versions:
                if (
                    version.valid_to
                    and version.valid_to < cutoff_date
                    and version.version_id != current_version.version_id
                ):
                    # Check if this version has rollback dependencies
                    if not self._has_rollback_dependencies(version):
                        versions.remove(version)
                        cleaned_count += 1
                    else:
                        retained_count += 1
                else:
                    retained_count += 1

        self.logger.info(
            f"Version cleanup: {cleaned_count} versions cleaned, {retained_count} retained"
        )
        return {"cleaned": cleaned_count, "retained": retained_count}

    def _has_rollback_dependencies(self, version: IssueVersionHistory) -> bool:
        """Check if a version has dependencies that prevent cleanup."""

        # Keep versions that are referenced for rollback
        if version.rollback_available:
            return True

        # Keep versions that are part of conflict resolution
        for conflict in self.conflict_log:
            if (
                conflict.winner_version_id == version.version_id
                or conflict.loser_version_id == version.version_id
            ):
                return True

        return False

    async def bulk_migrate_versions(
        self, migration_rules: dict[str, Any], created_by: str = "system"
    ) -> dict[str, int]:
        """Perform bulk version migration with new rules."""

        migrated_count = 0
        failed_count = 0

        for issue_id in self.version_history.keys():
            try:
                current_version = await self.get_current_version(issue_id)
                if not current_version:
                    continue

                # Apply migration rules
                needs_migration = self._check_migration_needed(
                    current_version, migration_rules
                )

                if needs_migration:
                    migrated_record = self._apply_migration_rules(
                        current_version, migration_rules
                    )

                    await self.create_new_version(
                        issue_id=issue_id,
                        updated_record=migrated_record,
                        change_type=VersionChangeType.BULK_MIGRATION,
                        change_description=f"Bulk migration: {migration_rules.get('description', 'Schema update')}",
                        created_by=created_by,
                    )

                    migrated_count += 1

            except Exception as e:
                self.logger.error(f"Failed to migrate issue {issue_id}: {e}")
                failed_count += 1

        self.logger.info(
            f"Bulk migration complete: {migrated_count} migrated, {failed_count} failed"
        )
        return {"migrated": migrated_count, "failed": failed_count}

    def _check_migration_needed(
        self, version: IssueVersionHistory, migration_rules: dict[str, Any]
    ) -> bool:
        """Check if a version needs migration based on rules."""

        # Example migration rules
        if (
            migration_rules.get("update_quality_scores")
            and version.quality_score == 0.0
        ):
            return True

        if migration_rules.get("normalize_confidence") and version.confidence > 1.0:
            return True

        return False

    def _apply_migration_rules(
        self, version: IssueVersionHistory, migration_rules: dict[str, Any]
    ) -> AirtableIssueRecord:
        """Apply migration rules to create updated record."""

        # Create updated record based on current version
        updated_record = AirtableIssueRecord(
            issue_id=version.issue_id,
            label_lv1=version.label_lv1,
            label_lv2=version.label_lv2,
            parent_id=version.parent_id,
            confidence=version.confidence,
            status=version.status,
            valid_from=date.today(),
            source_bill_id=version.source_bill_id,
            quality_score=version.quality_score,
        )

        # Apply migration rules
        if (
            migration_rules.get("update_quality_scores")
            and updated_record.quality_score == 0.0
        ):
            updated_record.quality_score = migration_rules.get(
                "default_quality_score", 0.5
            )

        if (
            migration_rules.get("normalize_confidence")
            and updated_record.confidence > 1.0
        ):
            updated_record.confidence = min(updated_record.confidence, 1.0)

        return updated_record

    async def get_version_statistics(self) -> dict[str, Any]:
        """Get comprehensive version statistics."""

        total_issues = len(self.version_history)
        total_versions = sum(
            len(versions) for versions in self.version_history.values()
        )

        # Calculate average versions per issue
        avg_versions_per_issue = (
            total_versions / total_issues if total_issues > 0 else 0
        )

        # Count by change type
        change_type_counts = {}
        for versions in self.version_history.values():
            for version in versions:
                change_type = version.change_type.value
                change_type_counts[change_type] = (
                    change_type_counts.get(change_type, 0) + 1
                )

        # Recent activity (last 7 days)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_versions = 0
        for versions in self.version_history.values():
            recent_versions += len(
                [v for v in versions if v.created_at > recent_cutoff]
            )

        return {
            "total_issues": total_issues,
            "total_versions": total_versions,
            "average_versions_per_issue": round(avg_versions_per_issue, 2),
            "change_type_distribution": change_type_counts,
            "recent_activity_7_days": recent_versions,
            "total_conflicts_resolved": len(self.conflict_log),
            "version_retention_days": self.version_retention_days,
            "auto_cleanup_enabled": self.auto_cleanup_enabled,
        }

    async def health_check(self) -> bool:
        """Health check for versioning service."""
        try:
            # Check Airtable connectivity
            airtable_healthy = await self.airtable_manager.health_check()

            # Check version history integrity
            integrity_issues = 0
            for issue_id, versions in self.version_history.items():
                current_versions = [v for v in versions if v.valid_to is None]
                if len(current_versions) != 1:
                    integrity_issues += 1

            return airtable_healthy and integrity_issues == 0

        except Exception as e:
            self.logger.error(f"Version service health check failed: {e}")
            return False
