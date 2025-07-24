"""
History Service - High-level service for managing bill history recording and retrieval.
Provides a unified interface for history-related operations.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, create_engine, desc, func, select
from sqlalchemy.orm import sessionmaker

from ...shared.src.shared.models.bill_process_history import (
    BillProcessHistory,
    HistoryChangeType,
    HistoryEventType,
)
from ..processor.bill_history_recorder import (
    BillHistoryRecorder,
    ChangeDetectionMode,
    HistoryRecordingResult,
)
from ..scheduler.history_recording_scheduler import (
    HistoryRecordingScheduler,
    ScheduleConfig,
)


@dataclass
class HistoryQuery:
    """Query parameters for history retrieval"""
    bill_id: str | None = None
    bill_ids: list[str] | None = None
    event_types: list[HistoryEventType] | None = None
    change_types: list[HistoryChangeType] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    source_system: str | None = None
    min_confidence: float | None = None
    limit: int = 100
    offset: int = 0
    order_by: str = "recorded_at"
    order_direction: str = "desc"


@dataclass
class HistoryAnalytics:
    """Analytics data for bill history"""
    total_records: int
    unique_bills: int
    date_range: dict[str, datetime]
    event_type_distribution: dict[str, int]
    change_type_distribution: dict[str, int]
    confidence_stats: dict[str, float]
    activity_timeline: list[dict[str, Any]]
    top_active_bills: list[dict[str, Any]]


class HistoryService:
    """High-level service for bill history management"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.history_recorder = BillHistoryRecorder(database_url)
        self.scheduler: HistoryRecordingScheduler | None = None

        # Service configuration
        self.config = {
            'default_page_size': 50,
            'max_page_size': 1000,
            'default_analytics_days': 30,
            'cache_ttl_seconds': 300
        }

    def initialize_scheduler(self, config: ScheduleConfig | None = None) -> bool:
        """Initialize the history recording scheduler"""
        try:
            self.scheduler = HistoryRecordingScheduler(self.database_url, config)
            self.scheduler.start()

            self.logger.info("History recording scheduler initialized and started")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize scheduler: {e}")
            return False

    def stop_scheduler(self):
        """Stop the history recording scheduler"""
        if self.scheduler:
            self.scheduler.stop()
            self.scheduler = None
            self.logger.info("History recording scheduler stopped")

    def detect_changes(
        self,
        mode: ChangeDetectionMode = ChangeDetectionMode.INCREMENTAL,
        bill_ids: list[str] | None = None,
        since_timestamp: datetime | None = None
    ) -> HistoryRecordingResult:
        """Detect and record bill changes"""
        try:
            return self.history_recorder.detect_and_record_changes(
                mode=mode,
                bill_ids=bill_ids,
                since_timestamp=since_timestamp
            )
        except Exception as e:
            self.logger.error(f"Error in change detection: {e}")
            raise

    def get_bill_history(
        self,
        bill_id: str,
        limit: int = 100,
        include_metadata: bool = True
    ) -> list[dict[str, Any]]:
        """Get complete history for a specific bill"""
        try:
            with self.SessionLocal() as session:
                query = select(BillProcessHistory).where(
                    BillProcessHistory.bill_id == bill_id
                ).order_by(desc(BillProcessHistory.recorded_at)).limit(limit)

                history_records = session.execute(query).scalars().all()

                result = []
                for record in history_records:
                    history_dict = {
                        'id': record.id,
                        'bill_id': record.bill_id,
                        'event_type': record.event_type.value,
                        'change_type': record.change_type.value,
                        'recorded_at': record.recorded_at.isoformat(),
                        'change_summary': record.change_summary,
                        'confidence_score': record.confidence_score,
                        'source_system': record.source_system,
                        'previous_values': record.previous_values,
                        'new_values': record.new_values
                    }

                    if include_metadata:
                        history_dict['metadata'] = record.metadata

                    result.append(history_dict)

                return result

        except Exception as e:
            self.logger.error(f"Error retrieving bill history: {e}")
            raise

    def query_history(self, query: HistoryQuery) -> dict[str, Any]:
        """Query history records with flexible filtering"""
        try:
            with self.SessionLocal() as session:
                # Build base query
                base_query = select(BillProcessHistory)

                # Apply filters
                conditions = []

                if query.bill_id:
                    conditions.append(BillProcessHistory.bill_id == query.bill_id)

                if query.bill_ids:
                    conditions.append(BillProcessHistory.bill_id.in_(query.bill_ids))

                if query.event_types:
                    conditions.append(
                        BillProcessHistory.event_type.in_(
                            query.event_types))

                if query.change_types:
                    conditions.append(
                        BillProcessHistory.change_type.in_(
                            query.change_types))

                if query.start_date:
                    conditions.append(
                        BillProcessHistory.recorded_at >= query.start_date)

                if query.end_date:
                    conditions.append(BillProcessHistory.recorded_at <= query.end_date)

                if query.source_system:
                    conditions.append(
                        BillProcessHistory.source_system == query.source_system)

                if query.min_confidence is not None:
                    conditions.append(
                        BillProcessHistory.confidence_score >= query.min_confidence)

                if conditions:
                    base_query = base_query.where(and_(*conditions))

                # Count total records
                count_query = select(func.count()).select_from(base_query.subquery())
                total_count = session.execute(count_query).scalar()

                # Apply ordering
                if query.order_by == "recorded_at":
                    order_column = BillProcessHistory.recorded_at
                elif query.order_by == "confidence_score":
                    order_column = BillProcessHistory.confidence_score
                else:
                    order_column = BillProcessHistory.recorded_at

                if query.order_direction == "desc":
                    base_query = base_query.order_by(desc(order_column))
                else:
                    base_query = base_query.order_by(order_column)

                # Apply pagination
                base_query = base_query.offset(query.offset).limit(query.limit)

                # Execute query
                history_records = session.execute(base_query).scalars().all()

                # Format results
                records = []
                for record in history_records:
                    records.append({
                        'id': record.id,
                        'bill_id': record.bill_id,
                        'event_type': record.event_type.value,
                        'change_type': record.change_type.value,
                        'recorded_at': record.recorded_at.isoformat(),
                        'change_summary': record.change_summary,
                        'confidence_score': record.confidence_score,
                        'source_system': record.source_system,
                        'previous_values': record.previous_values,
                        'new_values': record.new_values,
                        'metadata': record.metadata
                    })

                return {
                    'records': records,
                    'total_count': total_count,
                    'page_size': query.limit,
                    'offset': query.offset,
                    'has_more': (query.offset + query.limit) < total_count
                }

        except Exception as e:
            self.logger.error(f"Error querying history: {e}")
            raise

    def get_bill_timeline(self, bill_id: str) -> list[dict[str, Any]]:
        """Get timeline of major events for a bill"""
        try:
            with self.SessionLocal() as session:
                # Get significant events only
                significant_events = [
                    HistoryEventType.BILL_SUBMITTED,
                    HistoryEventType.COMMITTEE_REFERRAL,
                    HistoryEventType.STAGE_CHANGE,
                    HistoryEventType.VOTE_TAKEN,
                    HistoryEventType.STATUS_UPDATE,
                    HistoryEventType.IMPLEMENTATION
                ]

                query = select(BillProcessHistory).where(
                    and_(
                        BillProcessHistory.bill_id == bill_id,
                        BillProcessHistory.event_type.in_(significant_events)
                    )
                ).order_by(BillProcessHistory.recorded_at)

                timeline_records = session.execute(query).scalars().all()

                timeline = []
                for record in timeline_records:
                    timeline.append({
                        'date': record.recorded_at.isoformat(),
                        'event_type': record.event_type.value,
                        'description': record.change_summary,
                        'significance': self._determine_event_significance(record.event_type),
                        'confidence': record.confidence_score,
                        'details': {
                            'previous_values': record.previous_values,
                            'new_values': record.new_values
                        }
                    })

                return timeline

        except Exception as e:
            self.logger.error(f"Error getting bill timeline: {e}")
            raise

    def get_analytics(self, days: int = 30) -> HistoryAnalytics:
        """Get analytics for history data"""
        try:
            with self.SessionLocal() as session:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # Get records in date range
                query = select(BillProcessHistory).where(
                    BillProcessHistory.recorded_at >= start_date
                )

                records = session.execute(query).scalars().all()

                if not records:
                    return HistoryAnalytics(
                        total_records=0,
                        unique_bills=0,
                        date_range={'start': start_date, 'end': end_date},
                        event_type_distribution={},
                        change_type_distribution={},
                        confidence_stats={},
                        activity_timeline=[],
                        top_active_bills=[]
                    )

                # Calculate analytics
                unique_bills = len(set(record.bill_id for record in records))

                # Event type distribution
                event_type_dist = {}
                for record in records:
                    event_type = record.event_type.value
                    event_type_dist[event_type] = event_type_dist.get(event_type, 0) + 1

                # Change type distribution
                change_type_dist = {}
                for record in records:
                    change_type = record.change_type.value
                    change_type_dist[change_type] = change_type_dist.get(
                        change_type, 0) + 1

                # Confidence statistics
                confidence_scores = [
                    record.confidence_score for record in records if record.confidence_score is not None]
                confidence_stats = {}
                if confidence_scores:
                    confidence_stats = {
                        'min': min(confidence_scores),
                        'max': max(confidence_scores),
                        'avg': sum(confidence_scores) / len(confidence_scores),
                        'median': sorted(confidence_scores)[len(confidence_scores) // 2]
                    }

                # Activity timeline (daily activity)
                activity_timeline = self._calculate_activity_timeline(
                    records, start_date, end_date)

                # Top active bills
                bill_activity = {}
                for record in records:
                    bill_activity[record.bill_id] = bill_activity.get(
                        record.bill_id, 0) + 1

                top_active_bills = [
                    {'bill_id': bill_id, 'activity_count': count}
                    for bill_id, count in sorted(bill_activity.items(), key=lambda x: x[1], reverse=True)[:10]
                ]

                return HistoryAnalytics(
                    total_records=len(records),
                    unique_bills=unique_bills,
                    date_range={'start': start_date, 'end': end_date},
                    event_type_distribution=event_type_dist,
                    change_type_distribution=change_type_dist,
                    confidence_stats=confidence_stats,
                    activity_timeline=activity_timeline,
                    top_active_bills=top_active_bills
                )

        except Exception as e:
            self.logger.error(f"Error calculating analytics: {e}")
            raise

    def _calculate_activity_timeline(
        self,
        records: list[BillProcessHistory],
        start_date: datetime,
        end_date: datetime
    ) -> list[dict[str, Any]]:
        """Calculate daily activity timeline"""
        # Group records by date
        daily_activity = {}

        for record in records:
            date_key = record.recorded_at.date()
            if date_key not in daily_activity:
                daily_activity[date_key] = {
                    'date': date_key,
                    'total_changes': 0,
                    'bills_affected': set(),
                    'event_types': set()
                }

            daily_activity[date_key]['total_changes'] += 1
            daily_activity[date_key]['bills_affected'].add(record.bill_id)
            daily_activity[date_key]['event_types'].add(record.event_type.value)

        # Convert to timeline format
        timeline = []
        current_date = start_date.date()

        while current_date <= end_date.date():
            if current_date in daily_activity:
                activity = daily_activity[current_date]
                timeline.append({
                    'date': current_date.isoformat(),
                    'total_changes': activity['total_changes'],
                    'bills_affected': len(activity['bills_affected']),
                    'event_types': list(activity['event_types'])
                })
            else:
                timeline.append({
                    'date': current_date.isoformat(),
                    'total_changes': 0,
                    'bills_affected': 0,
                    'event_types': []
                })

            current_date += timedelta(days=1)

        return timeline

    def _determine_event_significance(self, event_type: HistoryEventType) -> str:
        """Determine significance level of an event"""
        critical_events = [
            HistoryEventType.BILL_SUBMITTED,
            HistoryEventType.VOTE_TAKEN,
            HistoryEventType.STATUS_UPDATE,
            HistoryEventType.IMPLEMENTATION
        ]

        major_events = [
            HistoryEventType.COMMITTEE_REFERRAL,
            HistoryEventType.STAGE_CHANGE,
            HistoryEventType.DOCUMENT_UPDATE
        ]

        if event_type in critical_events:
            return "critical"
        elif event_type in major_events:
            return "major"
        else:
            return "minor"

    def record_manual_change(
        self,
        bill_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        change_reason: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Record a manual change"""
        try:
            history_record = self.history_recorder.record_manual_change(
                bill_id=bill_id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                change_reason=change_reason,
                user_id=user_id
            )

            return {
                'success': True,
                'record_id': history_record.id,
                'recorded_at': history_record.recorded_at.isoformat(),
                'change_summary': history_record.change_summary
            }

        except Exception as e:
            self.logger.error(f"Error recording manual change: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get status of the history recording scheduler"""
        if not self.scheduler:
            return {
                'enabled': False,
                'status': 'not_initialized'
            }

        return {
            'enabled': True,
            'status': self.scheduler.get_status()
        }

    def force_history_recording(self) -> dict[str, Any]:
        """Force immediate history recording"""
        try:
            result = self.history_recorder.detect_and_record_changes(
                mode=ChangeDetectionMode.INCREMENTAL
            )

            return {
                'success': True,
                'changes_detected': result.changes_detected,
                'history_records_created': result.history_records_created,
                'bills_checked': result.total_bills_checked,
                'processing_time_ms': result.processing_time_ms
            }

        except Exception as e:
            self.logger.error(f"Error in forced history recording: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_change_statistics(self, days: int = 7) -> dict[str, Any]:
        """Get change statistics"""
        try:
            stats = self.history_recorder.get_change_statistics(days)

            # Add scheduler statistics if available
            if self.scheduler:
                scheduler_stats = self.scheduler.get_performance_metrics(days)
                stats['scheduler_performance'] = scheduler_stats

            return stats

        except Exception as e:
            self.logger.error(f"Error getting change statistics: {e}")
            return {'error': str(e)}

    def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old history data"""
        try:
            self.history_recorder.cleanup_old_snapshots(retention_days)
            self.logger.info(
                f"Cleaned up history data older than {retention_days} days")

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            raise

    def export_history(
        self,
        query: HistoryQuery,
        format: str = "json"
    ) -> dict[str, Any]:
        """Export history data"""
        try:
            # Remove pagination for export
            export_query = query
            export_query.limit = 10000  # Set reasonable limit for export
            export_query.offset = 0

            result = self.query_history(export_query)

            if format == "json":
                return {
                    'format': 'json',
                    'data': result,
                    'exported_at': datetime.now().isoformat(),
                    'total_records': result['total_count']
                }
            else:
                return {
                    'error': f"Unsupported format: {format}",
                    'supported_formats': ['json']
                }

        except Exception as e:
            self.logger.error(f"Error exporting history: {e}")
            return {'error': str(e)}
