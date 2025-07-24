"""
Tests for automatic history recording functionality.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from ...shared.src.shared.models.bill_process_history import (
    HistoryChangeType,
    HistoryEventType,
)
from ..src.processor.bill_history_recorder import (
    BillChange,
    BillHistoryRecorder,
    BillSnapshot,
    ChangeDetectionMode,
    ChangeSignificance,
    HistoryRecordingResult,
)
from ..src.scheduler.history_recording_scheduler import (
    HistoryRecordingScheduler,
    ScheduleConfig,
    ScheduleFrequency,
)
from ..src.services.history_service import (
    HistoryService,
)


class TestBillHistoryRecorder:
    """Test bill history recorder functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def history_recorder(self, mock_engine):
        """Create test history recorder"""
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            return BillHistoryRecorder("postgresql://test")

    def test_create_bill_snapshot(self, history_recorder):
        """Test bill snapshot creation"""
        # Mock bill object
        mock_bill = Mock()
        mock_bill.bill_id = "test-bill-1"
        mock_bill.title = "Test Bill"
        mock_bill.status = "審議中"
        mock_bill.stage = "committee_review"
        mock_bill.data_quality_score = 0.85

        # Create snapshot
        snapshot = history_recorder._create_bill_snapshot(mock_bill)

        assert snapshot.bill_id == "test-bill-1"
        assert "title" in snapshot.tracked_fields
        assert "status" in snapshot.tracked_fields
        assert "stage" in snapshot.tracked_fields
        assert snapshot.quality_score == 0.85
        assert len(snapshot.data_hash) > 0

    def test_detect_changes_no_previous_snapshot(self, history_recorder):
        """Test change detection with no previous snapshot"""
        current_snapshot = BillSnapshot(
            bill_id="test-bill-1",
            snapshot_time=datetime.now(UTC),
            data_hash="test-hash",
            tracked_fields={"title": "Test Bill", "status": "審議中"},
            quality_score=0.8
        )

        changes = history_recorder._detect_changes(current_snapshot, None)

        # Should return empty list for first-time bills
        assert changes == []

    def test_detect_changes_with_modifications(self, history_recorder):
        """Test change detection with modifications"""
        # Previous snapshot
        previous_snapshot = BillSnapshot(
            bill_id="test-bill-1",
            snapshot_time=datetime.now(UTC) - timedelta(hours=1),
            data_hash="old-hash",
            tracked_fields={"title": "Old Title", "status": "提出"},
            quality_score=0.7
        )

        # Current snapshot
        current_snapshot = BillSnapshot(
            bill_id="test-bill-1",
            snapshot_time=datetime.now(UTC),
            data_hash="new-hash",
            tracked_fields={"title": "New Title", "status": "審議中"},
            quality_score=0.8
        )

        changes = history_recorder._detect_changes(current_snapshot, previous_snapshot)

        # Should detect changes in both fields
        assert len(changes) == 2

        # Check title change
        title_change = next(c for c in changes if c.field_name == "title")
        assert title_change.old_value == "Old Title"
        assert title_change.new_value == "New Title"

        # Check status change
        status_change = next(c for c in changes if c.field_name == "status")
        assert status_change.old_value == "提出"
        assert status_change.new_value == "審議中"
        assert status_change.significance == ChangeSignificance.CRITICAL

    def test_is_significant_change(self, history_recorder):
        """Test significance detection"""
        # Significant change
        assert history_recorder._is_significant_change("status", "提出", "審議中")

        # Non-significant change
        assert not history_recorder._is_significant_change("title", "Test Bill", "Test Bill")

        # None to value
        assert history_recorder._is_significant_change("title", None, "Test Bill")

        # Value to None
        assert history_recorder._is_significant_change("title", "Test Bill", None)

        # Similar strings (should be non-significant)
        assert not history_recorder._is_significant_change("title", "Test Bill", "Test Bill Updated")

    def test_determine_change_type(self, history_recorder):
        """Test change type determination"""
        # Status change
        change_type = history_recorder._determine_change_type("status", "提出", "審議中")
        assert change_type == HistoryChangeType.STATUS_CHANGE

        # Stage change
        change_type = history_recorder._determine_change_type("stage", "submitted", "committee_review")
        assert change_type == HistoryChangeType.STAGE_TRANSITION

        # Document update
        change_type = history_recorder._determine_change_type("bill_outline", "Old outline", "New outline")
        assert change_type == HistoryChangeType.DOCUMENT_UPDATE

        # Default change
        change_type = history_recorder._determine_change_type("unknown_field", "old", "new")
        assert change_type == HistoryChangeType.DATA_CORRECTION

    def test_calculate_change_confidence(self, history_recorder):
        """Test confidence calculation"""
        # High confidence for critical field
        confidence = history_recorder._calculate_change_confidence("status", "提出", "審議中")
        assert confidence > 0.9

        # Medium confidence for regular field
        confidence = history_recorder._calculate_change_confidence("title", "Old Title", "New Title")
        assert 0.7 <= confidence <= 0.9

        # Lower confidence for similar strings
        confidence = history_recorder._calculate_change_confidence("title", "Test Bill", "Test Bill v2")
        assert confidence < 0.7

    def test_create_history_records(self, history_recorder):
        """Test history record creation"""
        # Mock bill
        mock_bill = Mock()
        mock_bill.bill_id = "test-bill-1"

        # Mock changes
        changes = [
            BillChange(
                bill_id="test-bill-1",
                field_name="status",
                old_value="提出",
                new_value="審議中",
                change_type=HistoryChangeType.STATUS_CHANGE,
                significance=ChangeSignificance.CRITICAL,
                confidence=0.95,
                detected_at=datetime.now(UTC),
                change_reason="Status updated"
            )
        ]

        records = history_recorder._create_history_records(mock_bill, changes)

        assert len(records) == 1
        record = records[0]
        assert record.bill_id == "test-bill-1"
        assert record.change_type == HistoryChangeType.STATUS_CHANGE
        assert record.confidence_score == 0.95
        assert record.change_summary == "Status updated"
        assert record.previous_values == {"status": "提出"}
        assert record.new_values == {"status": "審議中"}

    @patch('sqlalchemy.orm.sessionmaker')
    def test_detect_and_record_changes_success(self, mock_session_maker, history_recorder):
        """Test successful change detection and recording"""
        # Mock session
        mock_session = Mock()
        mock_session_maker.return_value = mock_session
        mock_session.__enter__.return_value = mock_session

        # Mock bill
        mock_bill = Mock()
        mock_bill.bill_id = "test-bill-1"
        mock_bill.title = "Test Bill"
        mock_bill.status = "審議中"
        mock_bill.updated_at = datetime.now(UTC)

        # Mock database query
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_bill]

        # Mock get_last_snapshot to return a different snapshot
        with patch.object(history_recorder, '_get_last_snapshot') as mock_get_last:
            mock_get_last.return_value = BillSnapshot(
                bill_id="test-bill-1",
                snapshot_time=datetime.now(UTC) - timedelta(hours=1),
                data_hash="old-hash",
                tracked_fields={"title": "Test Bill", "status": "提出"},
                quality_score=0.7
            )

            result = history_recorder.detect_and_record_changes(
                mode=ChangeDetectionMode.INCREMENTAL
            )

            assert isinstance(result, HistoryRecordingResult)
            assert result.total_bills_checked == 1
            assert result.changes_detected > 0

    def test_cleanup_old_snapshots(self, history_recorder):
        """Test cleanup of old snapshots"""
        with patch.object(history_recorder, 'SessionLocal') as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_session.__enter__.return_value = mock_session

            # Mock old records
            old_records = [Mock(), Mock()]
            mock_session.execute.return_value.scalars.return_value.all.return_value = old_records

            # Execute cleanup
            history_recorder.cleanup_old_snapshots(retention_days=30)

            # Verify deletion
            assert mock_session.delete.call_count == 2
            mock_session.commit.assert_called_once()


class TestHistoryRecordingScheduler:
    """Test history recording scheduler"""

    @pytest.fixture
    def scheduler_config(self):
        """Create test scheduler configuration"""
        return ScheduleConfig(
            frequency=ScheduleFrequency.EVERY_5_MINUTES,
            detection_mode=ChangeDetectionMode.INCREMENTAL,
            max_execution_time_minutes=10,
            retry_on_failure=True,
            max_retries=2
        )

    @pytest.fixture
    def scheduler(self, scheduler_config):
        """Create test scheduler"""
        return HistoryRecordingScheduler("postgresql://test", scheduler_config)

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization"""
        assert scheduler.config.frequency == ScheduleFrequency.EVERY_5_MINUTES
        assert scheduler.config.detection_mode == ChangeDetectionMode.INCREMENTAL
        assert not scheduler.status.is_running
        assert scheduler.status.total_executions == 0

    def test_get_status(self, scheduler):
        """Test status retrieval"""
        status = scheduler.get_status()

        assert 'is_running' in status
        assert 'total_executions' in status
        assert 'successful_executions' in status
        assert 'failed_executions' in status
        assert 'configuration' in status
        assert status['configuration']['frequency'] == 'every_5_minutes'

    def test_force_execution(self, scheduler):
        """Test forced execution"""
        with patch.object(scheduler.history_recorder, 'detect_and_record_changes') as mock_detect:
            mock_result = HistoryRecordingResult(
                total_bills_checked=10,
                changes_detected=3,
                history_records_created=3,
                processing_time_ms=1500.0
            )
            mock_detect.return_value = mock_result

            result = scheduler.force_execution()

            assert result['success']
            assert result['changes_detected'] == 3
            assert result['history_records_created'] == 3

    def test_get_performance_metrics(self, scheduler):
        """Test performance metrics"""
        # Add some mock execution history
        scheduler.execution_history = [
            {
                'timestamp': datetime.now(),
                'success': True,
                'execution_time_ms': 1000.0,
                'changes_detected': 2,
                'history_records_created': 2
            },
            {
                'timestamp': datetime.now(),
                'success': False,
                'execution_time_ms': 500.0,
                'error_message': 'Test error'
            }
        ]

        metrics = scheduler.get_performance_metrics(days=7)

        assert metrics['total_executions'] == 2
        assert metrics['successful_executions'] == 1
        assert metrics['failed_executions'] == 1
        assert metrics['success_rate'] == 0.5
        assert metrics['total_changes_detected'] == 2
        assert metrics['most_recent_error'] == 'Test error'


class TestHistoryService:
    """Test history service"""

    @pytest.fixture
    def history_service(self):
        """Create test history service"""
        return HistoryService("postgresql://test")

    def test_service_initialization(self, history_service):
        """Test service initialization"""
        assert history_service.database_url == "postgresql://test"
        assert history_service.history_recorder is not None
        assert history_service.scheduler is None

    def test_initialize_scheduler(self, history_service):
        """Test scheduler initialization"""
        config = ScheduleConfig(frequency=ScheduleFrequency.HOURLY)

        with patch.object(history_service, 'HistoryRecordingScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler

            result = history_service.initialize_scheduler(config)

            assert result
            assert history_service.scheduler is not None
            mock_scheduler.start.assert_called_once()

    def test_detect_changes(self, history_service):
        """Test change detection via service"""
        with patch.object(history_service.history_recorder, 'detect_and_record_changes') as mock_detect:
            mock_result = HistoryRecordingResult(
                total_bills_checked=5,
                changes_detected=2,
                history_records_created=2
            )
            mock_detect.return_value = mock_result

            result = history_service.detect_changes(
                mode=ChangeDetectionMode.INCREMENTAL
            )

            assert result.total_bills_checked == 5
            assert result.changes_detected == 2
            mock_detect.assert_called_once()

    @patch('sqlalchemy.orm.sessionmaker')
    def test_get_bill_history(self, mock_session_maker, history_service):
        """Test bill history retrieval"""
        # Mock session
        mock_session = Mock()
        mock_session_maker.return_value = mock_session
        mock_session.__enter__.return_value = mock_session

        # Mock history record
        mock_record = Mock()
        mock_record.id = 1
        mock_record.bill_id = "test-bill-1"
        mock_record.event_type = HistoryEventType.STATUS_UPDATE
        mock_record.change_type = HistoryChangeType.STATUS_CHANGE
        mock_record.recorded_at = datetime.now(UTC)
        mock_record.change_summary = "Status changed"
        mock_record.confidence_score = 0.9
        mock_record.source_system = "auto_recorder"
        mock_record.previous_values = {"status": "提出"}
        mock_record.new_values = {"status": "審議中"}
        mock_record.metadata = {"test": "value"}

        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_record]

        history = history_service.get_bill_history("test-bill-1")

        assert len(history) == 1
        record = history[0]
        assert record['bill_id'] == "test-bill-1"
        assert record['event_type'] == "STATUS_UPDATE"
        assert record['change_type'] == "STATUS_CHANGE"
        assert record['confidence_score'] == 0.9
        assert record['metadata'] == {"test": "value"}

    def test_record_manual_change(self, history_service):
        """Test manual change recording"""
        with patch.object(history_service.history_recorder, 'record_manual_change') as mock_record:
            mock_history_record = Mock()
            mock_history_record.id = 123
            mock_history_record.recorded_at = datetime.now(UTC)
            mock_history_record.change_summary = "Manual update"
            mock_record.return_value = mock_history_record

            result = history_service.record_manual_change(
                bill_id="test-bill-1",
                field_name="status",
                old_value="提出",
                new_value="審議中",
                change_reason="Manual status update",
                user_id="admin"
            )

            assert result['success']
            assert result['record_id'] == 123
            assert result['change_summary'] == "Manual update"

    def test_get_scheduler_status_not_initialized(self, history_service):
        """Test scheduler status when not initialized"""
        status = history_service.get_scheduler_status()

        assert not status['enabled']
        assert status['status'] == 'not_initialized'

    def test_get_scheduler_status_initialized(self, history_service):
        """Test scheduler status when initialized"""
        mock_scheduler = Mock()
        mock_scheduler.get_status.return_value = {
            'is_running': True,
            'total_executions': 5
        }
        history_service.scheduler = mock_scheduler

        status = history_service.get_scheduler_status()

        assert status['enabled']
        assert status['status']['is_running']
        assert status['status']['total_executions'] == 5

    def test_force_history_recording(self, history_service):
        """Test forced history recording"""
        with patch.object(history_service.history_recorder, 'detect_and_record_changes') as mock_detect:
            mock_result = HistoryRecordingResult(
                total_bills_checked=10,
                changes_detected=3,
                history_records_created=3,
                processing_time_ms=2000.0
            )
            mock_detect.return_value = mock_result

            result = history_service.force_history_recording()

            assert result['success']
            assert result['changes_detected'] == 3
            assert result['history_records_created'] == 3
            assert result['processing_time_ms'] == 2000.0


class TestIntegrationScenarios:
    """Test integration scenarios"""

    def test_end_to_end_history_recording(self):
        """Test complete history recording workflow"""
        # This would be a full integration test with real database
        # Mock the entire flow for now

        with patch('sqlalchemy.create_engine') as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            # Create service
            service = HistoryService("postgresql://test")

            # Initialize scheduler
            config = ScheduleConfig(frequency=ScheduleFrequency.EVERY_30_MINUTES)

            with patch.object(service, 'HistoryRecordingScheduler'):
                result = service.initialize_scheduler(config)
                assert result

    def test_change_detection_workflow(self):
        """Test change detection workflow"""
        with patch('sqlalchemy.create_engine') as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            recorder = BillHistoryRecorder("postgresql://test")

            # Mock the workflow
            with patch.object(recorder, '_get_bills_to_check') as mock_get_bills, \
                 patch.object(recorder, '_process_bill_batch') as mock_process:

                # Mock bills
                mock_bills = [Mock(), Mock()]
                mock_get_bills.return_value = mock_bills

                # Mock batch result
                mock_batch_result = HistoryRecordingResult(
                    total_bills_checked=2,
                    changes_detected=1,
                    history_records_created=1
                )
                mock_process.return_value = mock_batch_result

                # Execute
                result = recorder.detect_and_record_changes(
                    mode=ChangeDetectionMode.INCREMENTAL
                )

                assert result.total_bills_checked == 2
                assert result.changes_detected == 1
                assert result.history_records_created == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
