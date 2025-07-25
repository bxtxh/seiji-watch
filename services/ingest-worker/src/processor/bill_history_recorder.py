"""
Bill History Recorder - Automatic bill state change detection and recording system.
Monitors bill data changes and automatically records process history.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ...shared.src.shared.models.bill import Bill
from ...shared.src.shared.models.bill_process_history import (
    BillProcessHistory,
    HistoryChangeType,
    HistoryEventType,
)


class ChangeDetectionMode(Enum):
    """Change detection modes"""

    FULL_SCAN = "full_scan"  # Complete database scan
    INCREMENTAL = "incremental"  # Only check recent changes
    TARGETED = "targeted"  # Check specific bills


class ChangeSignificance(Enum):
    """Significance levels for changes"""

    CRITICAL = "critical"  # Major status changes (成立, 否決, etc.)
    MAJOR = "major"  # Stage changes, committee assignments
    MINOR = "minor"  # Minor updates, corrections
    TRIVIAL = "trivial"  # Formatting, non-essential changes


@dataclass
class BillChange:
    """Represents a detected change in bill data"""

    bill_id: str
    field_name: str
    old_value: Any
    new_value: Any
    change_type: HistoryChangeType
    significance: ChangeSignificance
    confidence: float
    detected_at: datetime

    # Additional metadata
    change_reason: str | None = None
    related_fields: list[str] = field(default_factory=list)
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BillSnapshot:
    """Snapshot of bill data for change detection"""

    bill_id: str
    snapshot_time: datetime
    data_hash: str
    tracked_fields: dict[str, Any]
    quality_score: float

    def calculate_hash(self) -> str:
        """Calculate hash of tracked fields for change detection"""
        # Sort fields for consistent hashing
        sorted_fields = dict(sorted(self.tracked_fields.items()))
        data_str = json.dumps(sorted_fields, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()


@dataclass
class HistoryRecordingResult:
    """Result of history recording operation"""

    total_bills_checked: int
    changes_detected: int
    history_records_created: int
    errors: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

    # Detailed statistics
    changes_by_type: dict[HistoryChangeType, int] = field(default_factory=dict)
    changes_by_significance: dict[ChangeSignificance, int] = field(default_factory=dict)
    bills_with_changes: set[str] = field(default_factory=set)


class BillHistoryRecorder:
    """Automatic bill history recording system"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.config = {
            "snapshot_retention_days": 30,
            "change_detection_threshold": 0.8,
            "max_bills_per_batch": 1000,
            "significant_fields": [
                "status",
                "stage",
                "final_vote_date",
                "implementation_date",
                "committee_assignments",
                "vote_results",
                "promulgated_date",
            ],
            "tracked_fields": [
                "title",
                "status",
                "stage",
                "submitter",
                "diet_session",
                "submitted_date",
                "final_vote_date",
                "implementation_date",
                "bill_outline",
                "background_context",
                "expected_effects",
                "committee_assignments",
                "vote_results",
                "promulgated_date",
                "data_quality_score",
            ],
            "ignore_fields": [
                "created_at",
                "updated_at",
                "last_scraped_at",
                "scraping_metadata",
            ],
        }

        # Field significance mapping
        self.field_significance = {
            "status": ChangeSignificance.CRITICAL,
            "stage": ChangeSignificance.CRITICAL,
            "final_vote_date": ChangeSignificance.CRITICAL,
            "implementation_date": ChangeSignificance.CRITICAL,
            "promulgated_date": ChangeSignificance.CRITICAL,
            "vote_results": ChangeSignificance.MAJOR,
            "committee_assignments": ChangeSignificance.MAJOR,
            "bill_outline": ChangeSignificance.MAJOR,
            "background_context": ChangeSignificance.MINOR,
            "expected_effects": ChangeSignificance.MINOR,
            "title": ChangeSignificance.MINOR,
            "submitter": ChangeSignificance.MINOR,
            "data_quality_score": ChangeSignificance.TRIVIAL,
        }

        # Change type detection patterns
        self.change_patterns = {
            HistoryChangeType.STATUS_CHANGE: ["status"],
            HistoryChangeType.STAGE_TRANSITION: ["stage"],
            HistoryChangeType.COMMITTEE_ASSIGNMENT: ["committee_assignments"],
            HistoryChangeType.VOTE_RECORDED: ["vote_results", "final_vote_date"],
            HistoryChangeType.DOCUMENT_UPDATE: [
                "bill_outline",
                "background_context",
                "expected_effects",
            ],
            HistoryChangeType.METADATA_UPDATE: ["title", "submitter", "diet_session"],
            HistoryChangeType.IMPLEMENTATION: [
                "implementation_date",
                "promulgated_date",
            ],
            HistoryChangeType.DATA_CORRECTION: ["data_quality_score"],
        }

    def detect_and_record_changes(
        self,
        mode: ChangeDetectionMode = ChangeDetectionMode.INCREMENTAL,
        bill_ids: list[str] | None = None,
        since_timestamp: datetime | None = None,
    ) -> HistoryRecordingResult:
        """Main method to detect and record bill changes"""
        start_time = datetime.now()
        result = HistoryRecordingResult()

        try:
            with self.SessionLocal() as session:
                # Get bills to check
                bills_to_check = self._get_bills_to_check(
                    session, mode, bill_ids, since_timestamp
                )
                result.total_bills_checked = len(bills_to_check)

                if not bills_to_check:
                    self.logger.info("No bills to check for changes")
                    return result

                # Process bills in batches
                batch_size = self.config["max_bills_per_batch"]
                for i in range(0, len(bills_to_check), batch_size):
                    batch = bills_to_check[i : i + batch_size]
                    batch_result = self._process_bill_batch(session, batch)

                    # Accumulate results
                    result.changes_detected += batch_result.changes_detected
                    result.history_records_created += (
                        batch_result.history_records_created
                    )
                    result.errors.extend(batch_result.errors)

                    # Merge statistics
                    for change_type, count in batch_result.changes_by_type.items():
                        result.changes_by_type[change_type] = (
                            result.changes_by_type.get(change_type, 0) + count
                        )

                    for (
                        significance,
                        count,
                    ) in batch_result.changes_by_significance.items():
                        result.changes_by_significance[significance] = (
                            result.changes_by_significance.get(significance, 0) + count
                        )

                    result.bills_with_changes.update(batch_result.bills_with_changes)

                # Calculate processing time
                result.processing_time_ms = (
                    datetime.now() - start_time
                ).total_seconds() * 1000

                # Log summary
                self.logger.info(
                    f"History recording completed: {result.changes_detected} changes detected, "
                    f"{result.history_records_created} records created from {result.total_bills_checked} bills"
                )

                return result

        except Exception as e:
            self.logger.error(f"Error in change detection and recording: {e}")
            result.errors.append(f"System error: {str(e)}")
            result.processing_time_ms = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            return result

    def _get_bills_to_check(
        self,
        session: Session,
        mode: ChangeDetectionMode,
        bill_ids: list[str] | None = None,
        since_timestamp: datetime | None = None,
    ) -> list[Bill]:
        """Get list of bills to check for changes"""
        query = select(Bill)

        if mode == ChangeDetectionMode.TARGETED and bill_ids:
            query = query.where(Bill.bill_id.in_(bill_ids))

        elif mode == ChangeDetectionMode.INCREMENTAL:
            # Check bills updated in the last 24 hours by default
            if since_timestamp is None:
                since_timestamp = datetime.now(UTC) - timedelta(hours=24)
            query = query.where(Bill.updated_at >= since_timestamp)

        # For FULL_SCAN mode, check all bills (no additional filters)

        # Order by most recently updated first
        query = query.order_by(desc(Bill.updated_at))

        return session.execute(query).scalars().all()

    def _process_bill_batch(
        self, session: Session, bills: list[Bill]
    ) -> HistoryRecordingResult:
        """Process a batch of bills for change detection"""
        result = HistoryRecordingResult()

        for bill in bills:
            try:
                # Get current snapshot
                current_snapshot = self._create_bill_snapshot(bill)

                # Get last recorded snapshot
                last_snapshot = self._get_last_snapshot(session, bill.bill_id)

                # Detect changes
                changes = self._detect_changes(current_snapshot, last_snapshot)

                if changes:
                    # Record history entries
                    history_records = self._create_history_records(bill, changes)

                    # Save to database
                    for record in history_records:
                        session.add(record)

                    # Update statistics
                    result.changes_detected += len(changes)
                    result.history_records_created += len(history_records)
                    result.bills_with_changes.add(bill.bill_id)

                    # Count by type and significance
                    for change in changes:
                        result.changes_by_type[change.change_type] = (
                            result.changes_by_type.get(change.change_type, 0) + 1
                        )
                        result.changes_by_significance[change.significance] = (
                            result.changes_by_significance.get(change.significance, 0)
                            + 1
                        )

                # Store current snapshot for future comparisons
                self._store_snapshot(session, current_snapshot)

            except Exception as e:
                self.logger.error(f"Error processing bill {bill.bill_id}: {e}")
                result.errors.append(f"Bill {bill.bill_id}: {str(e)}")

        try:
            session.commit()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in batch processing: {e}")
            session.rollback()
            result.errors.append(f"Database error: {str(e)}")

        return result

    def _create_bill_snapshot(self, bill: Bill) -> BillSnapshot:
        """Create a snapshot of bill data for change detection"""
        tracked_fields = {}

        for field_name in self.config["tracked_fields"]:
            if hasattr(bill, field_name):
                value = getattr(bill, field_name)
                # Convert complex types to strings for comparison
                if isinstance(value, dict | list):
                    tracked_fields[field_name] = json.dumps(
                        value, sort_keys=True, default=str
                    )
                else:
                    tracked_fields[field_name] = value

        snapshot = BillSnapshot(
            bill_id=bill.bill_id,
            snapshot_time=datetime.now(UTC),
            data_hash="",
            tracked_fields=tracked_fields,
            quality_score=getattr(bill, "data_quality_score", 0.0),
        )

        snapshot.data_hash = snapshot.calculate_hash()
        return snapshot

    def _get_last_snapshot(self, session: Session, bill_id: str) -> BillSnapshot | None:
        """Get the last recorded snapshot for a bill"""
        # This would typically query a snapshots table
        # For now, we'll simulate by checking the most recent history record
        try:
            latest_history = session.execute(
                select(BillProcessHistory)
                .where(BillProcessHistory.bill_id == bill_id)
                .order_by(desc(BillProcessHistory.recorded_at))
                .limit(1)
            ).scalar_one_or_none()

            if latest_history and latest_history.previous_values:
                # Reconstruct snapshot from history data
                return BillSnapshot(
                    bill_id=bill_id,
                    snapshot_time=latest_history.recorded_at,
                    data_hash="",
                    tracked_fields=latest_history.previous_values,
                    quality_score=latest_history.previous_values.get(
                        "data_quality_score", 0.0
                    ),
                )

            return None

        except Exception as e:
            self.logger.debug(f"Could not retrieve last snapshot for {bill_id}: {e}")
            return None

    def _detect_changes(
        self, current_snapshot: BillSnapshot, last_snapshot: BillSnapshot | None
    ) -> list[BillChange]:
        """Detect changes between snapshots"""
        changes = []

        if last_snapshot is None:
            # First time seeing this bill - record as initial state
            return []

        # Compare tracked fields
        for field_name, current_value in current_snapshot.tracked_fields.items():
            last_value = last_snapshot.tracked_fields.get(field_name)

            if self._is_significant_change(field_name, last_value, current_value):
                change = BillChange(
                    bill_id=current_snapshot.bill_id,
                    field_name=field_name,
                    old_value=last_value,
                    new_value=current_value,
                    change_type=self._determine_change_type(
                        field_name, last_value, current_value
                    ),
                    significance=self.field_significance.get(
                        field_name, ChangeSignificance.MINOR
                    ),
                    confidence=self._calculate_change_confidence(
                        field_name, last_value, current_value
                    ),
                    detected_at=current_snapshot.snapshot_time,
                    change_reason=self._infer_change_reason(
                        field_name, last_value, current_value
                    ),
                )
                changes.append(change)

        return changes

    def _is_significant_change(
        self, field_name: str, old_value: Any, new_value: Any
    ) -> bool:
        """Determine if a change is significant enough to record"""
        # Handle None values
        if old_value is None and new_value is None:
            return False

        if old_value is None or new_value is None:
            return True

        # String comparison
        if isinstance(old_value, str) and isinstance(new_value, str):
            # Use similarity threshold for text fields
            similarity = SequenceMatcher(None, old_value, new_value).ratio()
            return similarity < self.config["change_detection_threshold"]

        # Direct comparison for other types
        return old_value != new_value

    def _determine_change_type(
        self, field_name: str, old_value: Any, new_value: Any
    ) -> HistoryChangeType:
        """Determine the type of change based on field and values"""
        # Check patterns
        for change_type, patterns in self.change_patterns.items():
            if field_name in patterns:
                return change_type

        # Default to generic update
        return HistoryChangeType.DATA_CORRECTION

    def _calculate_change_confidence(
        self, field_name: str, old_value: Any, new_value: Any
    ) -> float:
        """Calculate confidence score for the change detection"""
        # Base confidence
        confidence = 0.8

        # Increase confidence for critical fields
        if field_name in self.config["significant_fields"]:
            confidence += 0.15

        # Increase confidence for complete changes (None to value or vice versa)
        if old_value is None or new_value is None:
            confidence += 0.1

        # Decrease confidence for minor text changes
        if isinstance(old_value, str) and isinstance(new_value, str):
            similarity = SequenceMatcher(None, old_value, new_value).ratio()
            if similarity > 0.9:
                confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _infer_change_reason(
        self, field_name: str, old_value: Any, new_value: Any
    ) -> str | None:
        """Infer the reason for the change"""
        if old_value is None and new_value is not None:
            return "Data added"
        elif old_value is not None and new_value is None:
            return "Data removed"
        elif field_name == "status":
            return f"Status changed from {old_value} to {new_value}"
        elif field_name == "stage":
            return f"Stage transition from {old_value} to {new_value}"
        elif field_name in ["bill_outline", "background_context", "expected_effects"]:
            return "Document content updated"
        else:
            return f"Field {field_name} updated"

    def _create_history_records(
        self, bill: Bill, changes: list[BillChange]
    ) -> list[BillProcessHistory]:
        """Create history records from detected changes"""
        history_records = []

        for change in changes:
            # Determine event type
            event_type = self._map_change_to_event_type(change)

            # Create history record
            history_record = BillProcessHistory(
                bill_id=bill.bill_id,
                event_type=event_type,
                change_type=change.change_type,
                recorded_at=change.detected_at,
                previous_values={change.field_name: change.old_value},
                new_values={change.field_name: change.new_value},
                change_summary=change.change_reason or f"{change.field_name} updated",
                confidence_score=change.confidence,
                source_system="auto_history_recorder",
                metadata={
                    "detection_mode": "automatic",
                    "significance": change.significance.value,
                    "related_fields": change.related_fields,
                    "source_metadata": change.source_metadata,
                },
            )

            history_records.append(history_record)

        return history_records

    def _map_change_to_event_type(self, change: BillChange) -> HistoryEventType:
        """Map change type to history event type"""
        mapping = {
            HistoryChangeType.STATUS_CHANGE: HistoryEventType.STATUS_UPDATE,
            HistoryChangeType.STAGE_TRANSITION: HistoryEventType.STAGE_CHANGE,
            HistoryChangeType.COMMITTEE_ASSIGNMENT: HistoryEventType.COMMITTEE_REFERRAL,
            HistoryChangeType.VOTE_RECORDED: HistoryEventType.VOTE_TAKEN,
            HistoryChangeType.DOCUMENT_UPDATE: HistoryEventType.DOCUMENT_UPDATE,
            HistoryChangeType.METADATA_UPDATE: HistoryEventType.METADATA_CHANGE,
            HistoryChangeType.IMPLEMENTATION: HistoryEventType.IMPLEMENTATION,
            HistoryChangeType.DATA_CORRECTION: HistoryEventType.DATA_CORRECTION,
        }

        return mapping.get(change.change_type, HistoryEventType.GENERAL_UPDATE)

    def _store_snapshot(self, session: Session, snapshot: BillSnapshot):
        """Store snapshot for future comparisons"""
        # In a full implementation, this would store to a dedicated snapshots table
        # For now, we'll log the snapshot creation
        self.logger.debug(
            f"Snapshot created for bill {snapshot.bill_id} at {snapshot.snapshot_time}"
        )

    def cleanup_old_snapshots(self, retention_days: int = 30):
        """Clean up old snapshots to manage storage"""
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        try:
            with self.SessionLocal() as session:
                # Clean up old history records that are no longer needed
                old_records = (
                    session.execute(
                        select(BillProcessHistory)
                        .where(BillProcessHistory.recorded_at < cutoff_date)
                        .where(
                            BillProcessHistory.change_type
                            == HistoryChangeType.DATA_CORRECTION
                        )
                    )
                    .scalars()
                    .all()
                )

                for record in old_records:
                    session.delete(record)

                session.commit()

                self.logger.info(f"Cleaned up {len(old_records)} old history records")

        except Exception as e:
            self.logger.error(f"Error cleaning up old snapshots: {e}")

    def get_change_statistics(self, days: int = 7) -> dict[str, Any]:
        """Get statistics about recent changes"""
        try:
            with self.SessionLocal() as session:
                since_date = datetime.now(UTC) - timedelta(days=days)

                # Get recent history records
                recent_records = (
                    session.execute(
                        select(BillProcessHistory)
                        .where(BillProcessHistory.recorded_at >= since_date)
                        .where(
                            BillProcessHistory.source_system == "auto_history_recorder"
                        )
                    )
                    .scalars()
                    .all()
                )

                # Calculate statistics
                stats = {
                    "total_changes": len(recent_records),
                    "unique_bills": len(set(r.bill_id for r in recent_records)),
                    "changes_by_type": {},
                    "changes_by_event": {},
                    "average_confidence": 0.0,
                    "period_days": days,
                }

                if recent_records:
                    # Count by change type
                    for record in recent_records:
                        change_type = record.change_type.value
                        stats["changes_by_type"][change_type] = (
                            stats["changes_by_type"].get(change_type, 0) + 1
                        )

                        event_type = record.event_type.value
                        stats["changes_by_event"][event_type] = (
                            stats["changes_by_event"].get(event_type, 0) + 1
                        )

                    # Calculate average confidence
                    total_confidence = sum(
                        r.confidence_score or 0.0 for r in recent_records
                    )
                    stats["average_confidence"] = total_confidence / len(recent_records)

                return stats

        except Exception as e:
            self.logger.error(f"Error getting change statistics: {e}")
            return {"error": str(e)}

    def force_full_scan(self) -> HistoryRecordingResult:
        """Force a full scan of all bills for changes"""
        self.logger.info("Starting forced full scan for bill changes")
        return self.detect_and_record_changes(mode=ChangeDetectionMode.FULL_SCAN)

    def record_manual_change(
        self,
        bill_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        change_reason: str,
        user_id: str | None = None,
    ) -> BillProcessHistory:
        """Manually record a change (for manual corrections)"""
        try:
            with self.SessionLocal() as session:
                # Create manual history record
                history_record = BillProcessHistory(
                    bill_id=bill_id,
                    event_type=HistoryEventType.MANUAL_CORRECTION,
                    change_type=HistoryChangeType.DATA_CORRECTION,
                    recorded_at=datetime.now(UTC),
                    previous_values={field_name: old_value},
                    new_values={field_name: new_value},
                    change_summary=change_reason,
                    confidence_score=1.0,  # Manual changes have full confidence
                    source_system="manual_entry",
                    metadata={
                        "user_id": user_id,
                        "manual_entry": True,
                        "field_name": field_name,
                    },
                )

                session.add(history_record)
                session.commit()

                self.logger.info(
                    f"Manual change recorded for bill {bill_id}: {change_reason}"
                )
                return history_record

        except Exception as e:
            self.logger.error(f"Error recording manual change: {e}")
            raise
