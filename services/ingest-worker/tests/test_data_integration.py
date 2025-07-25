"""
Comprehensive tests for data integration functionality.
Tests the complete data processing pipeline including merging, validation, and quality management.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from ..src.processor.bill_data_merger import (
    BillDataMerger,
    MergeResult,
    MergeStrategy,
)
from ..src.processor.bill_data_validator import (
    BillDataValidator,
    ValidationCategory,
    ValidationResult,
    ValidationSeverity,
)
from ..src.processor.bill_progress_tracker import (
    AlertType,
    BillProgressTracker,
    ProgressUpdateResult,
    StageTransition,
)
from ..src.processor.data_integration_manager import (
    DataIntegrationManager,
)


class TestBillDataMerger:
    """Test bill data merger functionality"""

    @pytest.fixture
    def merger(self):
        """Create test merger"""
        return BillDataMerger()

    def test_merge_identical_bills(self, merger):
        """Test merging identical bills"""
        # Create identical bills
        bill1 = {
            "bill_id": "TEST-001",
            "title": "Test Bill",
            "status": "審議中",
            "source_house": "参議院",
            "data_quality_score": 0.8,
        }

        bill2 = {
            "bill_id": "TEST-001",
            "title": "Test Bill",
            "status": "審議中",
            "source_house": "参議院",
            "data_quality_score": 0.8,
        }

        result = merger.merge_bills([bill1, bill2])

        assert result.success is True
        assert len(result.merged_bills) == 1
        assert len(result.conflicts) == 0
        assert result.merged_bills[0]["bill_id"] == "TEST-001"

    def test_merge_bills_with_conflicts(self, merger):
        """Test merging bills with conflicts"""
        # Create bills with conflicts
        bill1 = {
            "bill_id": "TEST-001",
            "title": "Test Bill Original",
            "status": "提出",
            "source_house": "参議院",
            "data_quality_score": 0.7,
        }

        bill2 = {
            "bill_id": "TEST-001",
            "title": "Test Bill Updated",
            "status": "審議中",
            "source_house": "参議院",
            "data_quality_score": 0.9,
        }

        result = merger.merge_bills([bill1, bill2])

        assert result.success is True
        assert len(result.merged_bills) == 1
        assert len(result.conflicts) > 0

        # Check that higher quality data is preferred
        merged = result.merged_bills[0]
        assert merged["title"] == "Test Bill Updated"  # Higher quality
        assert merged["status"] == "審議中"  # Higher quality
        assert merged["data_quality_score"] >= 0.9

    def test_merge_bills_different_houses(self, merger):
        """Test merging bills from different houses"""
        # Create bills from different houses
        sangiin_bill = {
            "bill_id": "TEST-001",
            "title": "Test Bill",
            "status": "審議中",
            "source_house": "参議院",
            "committee_assignments": ["内閣委員会"],
            "data_quality_score": 0.8,
        }

        shugiin_bill = {
            "bill_id": "TEST-001",
            "title": "Test Bill",
            "status": "審議中",
            "source_house": "衆議院",
            "supporting_members": ["田中太郎", "佐藤花子"],
            "data_quality_score": 0.7,
        }

        result = merger.merge_bills([sangiin_bill, shugiin_bill])

        assert result.success is True
        assert len(result.merged_bills) == 1

        merged = result.merged_bills[0]
        # Should contain data from both houses
        assert "committee_assignments" in merged
        assert "supporting_members" in merged
        assert merged["source_house"] == "参議院"  # Higher quality source

    def test_merge_resolution_strategies(self, merger):
        """Test different conflict resolution strategies"""
        bill1 = {
            "bill_id": "TEST-001",
            "title": "Original Title",
            "status": "提出",
            "data_quality_score": 0.6,
        }

        bill2 = {
            "bill_id": "TEST-001",
            "title": "Updated Title",
            "status": "審議中",
            "data_quality_score": 0.9,
        }

        # Test MOST_COMPLETE strategy
        result = merger.merge_bills(
            [bill1, bill2], strategy=MergeStrategy.MOST_COMPLETE
        )
        merged = result.merged_bills[0]
        assert merged["title"] == "Updated Title"
        assert merged["status"] == "審議中"

        # Test HOUSE_PRIORITY strategy with参議院 priority
        bill1["source_house"] = "参議院"
        bill2["source_house"] = "衆議院"

        result = merger.merge_bills(
            [bill1, bill2], strategy=MergeStrategy.HOUSE_PRIORITY
        )
        merged = result.merged_bills[0]
        # Should prefer参議院 data even with lower quality
        assert merged["source_house"] == "参議院"

    def test_detect_conflicts(self, merger):
        """Test conflict detection"""
        bill1 = {
            "bill_id": "TEST-001",
            "title": "Original Title",
            "status": "提出",
            "stage": "submitted",
        }

        bill2 = {
            "bill_id": "TEST-001",
            "title": "Different Title",
            "status": "審議中",
            "stage": "committee_review",
        }

        conflicts = merger._detect_conflicts(bill1, bill2)

        assert len(conflicts) == 3  # title, status, stage
        conflict_fields = [c.field for c in conflicts]
        assert "title" in conflict_fields
        assert "status" in conflict_fields
        assert "stage" in conflict_fields

    def test_similarity_calculation(self, merger):
        """Test similarity calculation between bills"""
        bill1 = {
            "bill_id": "TEST-001",
            "title": "デジタル社会形成基本法案",
            "status": "審議中",
            "submitter": "政府",
        }

        bill2 = {
            "bill_id": "TEST-001",
            "title": "デジタル社会形成基本法案",
            "status": "審議中",
            "submitter": "政府",
        }

        similarity = merger._calculate_similarity(bill1, bill2)
        assert similarity == 1.0  # Identical

        # Test with differences
        bill2["title"] = "デジタル改革関連法案"
        similarity = merger._calculate_similarity(bill1, bill2)
        assert 0.5 < similarity < 1.0  # Similar but not identical


class TestBillDataValidator:
    """Test bill data validator functionality"""

    @pytest.fixture
    def validator(self):
        """Create test validator"""
        return BillDataValidator()

    def test_validate_complete_bill(self, validator):
        """Test validation of complete bill"""
        complete_bill = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "審議中",
            "stage": "committee_review",
            "submitter": "政府",
            "diet_session": "204",
            "house_of_origin": "参議院",
            "submitted_date": "2021-01-01",
            "bill_outline": "本法案は、テスト目的で作成されたものです。",
            "data_quality_score": 0.9,
        }

        result = validator.validate_bill(complete_bill)

        assert result.is_valid is True
        assert result.quality_score >= 0.8
        assert (
            len(
                [
                    issue
                    for issue in result.issues
                    if issue.severity == ValidationSeverity.ERROR
                ]
            )
            == 0
        )

    def test_validate_incomplete_bill(self, validator):
        """Test validation of incomplete bill"""
        incomplete_bill = {
            "bill_id": "TEST-002",
            "title": "",  # Empty title
            "status": "invalid_status",  # Invalid status
            "submitter": "政府",
            # Missing required fields
        }

        result = validator.validate_bill(incomplete_bill)

        assert result.is_valid is False
        assert result.quality_score < 0.5

        # Should have errors for missing/invalid fields
        errors = [
            issue
            for issue in result.issues
            if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(errors) > 0

        # Check for specific validation issues
        issue_types = [issue.category for issue in result.issues]
        assert ValidationCategory.REQUIRED_FIELD in issue_types
        assert ValidationCategory.INVALID_FORMAT in issue_types

    def test_validate_japanese_text(self, validator):
        """Test Japanese text validation"""
        # Valid Japanese text
        valid_text = "この法案は、デジタル社会の形成を目的としています。"
        assert validator._validate_japanese_text(valid_text) is True

        # Invalid text (too short)
        invalid_text = "短"
        assert validator._validate_japanese_text(invalid_text) is False

        # Invalid text (no Japanese characters)
        invalid_text = "This is English text only"
        assert validator._validate_japanese_text(invalid_text) is False

    def test_validate_date_formats(self, validator):
        """Test date format validation"""
        # Valid dates
        assert validator._validate_date("2021-01-01") is True
        assert validator._validate_date("2021-12-31") is True

        # Invalid dates
        assert validator._validate_date("2021-13-01") is False
        assert validator._validate_date("invalid-date") is False
        assert validator._validate_date("") is False

    def test_validate_enum_values(self, validator):
        """Test enum value validation"""
        # Valid status values
        assert validator._validate_enum_value("status", "審議中") is True
        assert validator._validate_enum_value("status", "成立") is True

        # Invalid status values
        assert validator._validate_enum_value("status", "invalid_status") is False
        assert validator._validate_enum_value("status", "") is False

        # Valid house values
        assert validator._validate_enum_value("house_of_origin", "参議院") is True
        assert validator._validate_enum_value("house_of_origin", "衆議院") is True

        # Invalid house values
        assert (
            validator._validate_enum_value("house_of_origin", "invalid_house") is False
        )

    def test_calculate_quality_score(self, validator):
        """Test quality score calculation"""
        # High quality bill
        high_quality_bill = {
            "bill_id": "TEST-001",
            "title": "デジタル社会形成基本法案",
            "status": "審議中",
            "stage": "committee_review",
            "submitter": "政府",
            "diet_session": "204",
            "house_of_origin": "参議院",
            "submitted_date": "2021-01-01",
            "bill_outline": "本法案は、デジタル社会の形成を推進し、国民の利便性向上を図ることを目的とする。",
            "background_context": "近年のデジタル化の進展に伴い...",
            "expected_effects": "本法案により、行政手続きの効率化が期待される。",
        }

        validation_result = validator.validate_bill(high_quality_bill)
        score = validator._calculate_quality_score(
            high_quality_bill, validation_result.issues
        )

        assert score >= 0.8

        # Low quality bill
        low_quality_bill = {
            "bill_id": "TEST-002",
            "title": "テスト",  # Very short title
            "status": "invalid",  # Invalid status
            "submitter": "政府",
            # Missing many fields
        }

        validation_result = validator.validate_bill(low_quality_bill)
        score = validator._calculate_quality_score(
            low_quality_bill, validation_result.issues
        )

        assert score < 0.5

    def test_validate_logical_consistency(self, validator):
        """Test logical consistency validation"""
        # Inconsistent dates
        inconsistent_bill = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "成立",
            "submitted_date": "2021-06-01",
            "final_vote_date": "2021-05-01",  # Before submitted date
            "implementation_date": "2021-04-01",  # Before vote date
        }

        result = validator.validate_bill(inconsistent_bill)

        # Should detect logical inconsistencies
        logic_issues = [
            issue
            for issue in result.issues
            if issue.category == ValidationCategory.LOGICAL_CONSISTENCY
        ]
        assert len(logic_issues) > 0

        # Consistent dates
        consistent_bill = {
            "bill_id": "TEST-002",
            "title": "テスト法案",
            "status": "成立",
            "submitted_date": "2021-01-01",
            "final_vote_date": "2021-03-01",
            "implementation_date": "2021-06-01",
        }

        result = validator.validate_bill(consistent_bill)

        logic_issues = [
            issue
            for issue in result.issues
            if issue.category == ValidationCategory.LOGICAL_CONSISTENCY
        ]
        assert len(logic_issues) == 0


class TestBillProgressTracker:
    """Test bill progress tracker functionality"""

    @pytest.fixture
    def tracker(self):
        """Create test tracker"""
        return BillProgressTracker()

    def test_track_stage_progression(self, tracker):
        """Test stage progression tracking"""
        # Normal progression
        bill_data = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "審議中",
            "stage": "committee_review",
            "submitted_date": "2021-01-01",
            "last_updated": "2021-02-01",
        }

        previous_data = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "提出",
            "stage": "submitted",
            "submitted_date": "2021-01-01",
            "last_updated": "2021-01-01",
        }

        result = tracker.track_progress(bill_data, previous_data)

        assert result.progress_detected is True
        assert len(result.stage_transitions) == 1

        transition = result.stage_transitions[0]
        assert transition.from_stage == "submitted"
        assert transition.to_stage == "committee_review"
        assert transition.transition_date is not None

    def test_detect_stalled_bill(self, tracker):
        """Test detection of stalled bills"""
        # Bill with no progress for extended period
        bill_data = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "審議中",
            "stage": "committee_review",
            "submitted_date": "2020-01-01",
            "last_updated": "2020-02-01",  # Very old update
        }

        result = tracker.track_progress(bill_data)

        # Should detect stalled progress
        alerts = [
            alert for alert in result.alerts if alert.type == AlertType.STALLED_PROGRESS
        ]
        assert len(alerts) > 0

    def test_detect_unusual_progression(self, tracker):
        """Test detection of unusual progression patterns"""
        # Backward progression (unusual)
        bill_data = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "提出",
            "stage": "submitted",
            "submitted_date": "2021-01-01",
            "last_updated": "2021-03-01",
        }

        previous_data = {
            "bill_id": "TEST-001",
            "title": "テスト法案",
            "status": "審議中",
            "stage": "plenary_debate",
            "submitted_date": "2021-01-01",
            "last_updated": "2021-02-01",
        }

        result = tracker.track_progress(bill_data, previous_data)

        # Should detect unusual backward progression
        alerts = [
            alert
            for alert in result.alerts
            if alert.type == AlertType.UNUSUAL_PROGRESSION
        ]
        assert len(alerts) > 0

    def test_calculate_progress_confidence(self, tracker):
        """Test progress confidence calculation"""
        # High confidence transition
        high_confidence_transition = StageTransition(
            from_stage="submitted",
            to_stage="committee_review",
            transition_date=datetime.now(),
            confidence=0.0,  # Will be calculated
        )

        confidence = tracker._calculate_progress_confidence(
            high_confidence_transition, {}
        )
        assert confidence >= 0.8

        # Low confidence transition (unusual)
        low_confidence_transition = StageTransition(
            from_stage="plenary_debate",
            to_stage="submitted",  # Backward
            transition_date=datetime.now(),
            confidence=0.0,
        )

        confidence = tracker._calculate_progress_confidence(
            low_confidence_transition, {}
        )
        assert confidence < 0.5


class TestDataIntegrationManager:
    """Test data integration manager functionality"""

    @pytest.fixture
    def integration_manager(self):
        """Create test integration manager"""
        return DataIntegrationManager("postgresql://test")

    def test_process_bills_complete_pipeline(self, integration_manager):
        """Test complete bill processing pipeline"""
        # Mock the components
        with (
            patch.object(integration_manager, "merger") as mock_merger,
            patch.object(integration_manager, "validator") as mock_validator,
            patch.object(integration_manager, "progress_tracker") as mock_tracker,
        ):
            # Mock merge result
            mock_merge_result = MergeResult(
                success=True,
                merged_bills=[
                    {
                        "bill_id": "TEST-001",
                        "title": "テスト法案",
                        "status": "審議中",
                        "data_quality_score": 0.9,
                    }
                ],
                conflicts=[],
                processing_time_ms=100.0,
            )
            mock_merger.merge_bills.return_value = mock_merge_result

            # Mock validation result
            mock_validation_result = ValidationResult(
                bill_id="TEST-001",
                is_valid=True,
                quality_score=0.9,
                issues=[],
                validation_time_ms=50.0,
            )
            mock_validator.validate_bill.return_value = mock_validation_result

            # Mock progress tracking result
            mock_progress_result = ProgressUpdateResult(
                bill_id="TEST-001",
                progress_detected=True,
                stage_transitions=[],
                alerts=[],
                confidence_score=0.85,
            )
            mock_tracker.track_progress.return_value = mock_progress_result

            # Test data
            bills_data = [
                {
                    "bill_id": "TEST-001",
                    "title": "テスト法案",
                    "status": "審議中",
                    "source_house": "参議院",
                }
            ]

            # Process bills
            result = integration_manager.process_bills(bills_data)

            assert result.success is True
            assert len(result.processed_bills) == 1
            assert result.total_processing_time_ms > 0

            # Verify component calls
            mock_merger.merge_bills.assert_called_once()
            mock_validator.validate_bill.assert_called_once()
            mock_tracker.track_progress.assert_called_once()

    def test_process_bills_with_errors(self, integration_manager):
        """Test processing with errors"""
        with patch.object(integration_manager, "merger") as mock_merger:
            # Mock merger to raise exception
            mock_merger.merge_bills.side_effect = Exception("Merge failed")

            bills_data = [{"bill_id": "TEST-001", "title": "テスト法案"}]

            result = integration_manager.process_bills(bills_data)

            assert result.success is False
            assert len(result.errors) > 0
            assert "Merge failed" in result.errors[0]

    def test_quality_filtering(self, integration_manager):
        """Test quality-based filtering"""
        # High quality bill
        high_quality_bill = {
            "bill_id": "TEST-001",
            "title": "デジタル社会形成基本法案",
            "status": "審議中",
            "data_quality_score": 0.9,
        }

        # Low quality bill
        low_quality_bill = {
            "bill_id": "TEST-002",
            "title": "テスト",
            "status": "invalid",
            "data_quality_score": 0.3,
        }

        bills = [high_quality_bill, low_quality_bill]

        # Filter with minimum quality threshold
        filtered = integration_manager._filter_by_quality(bills, min_quality=0.8)

        assert len(filtered) == 1
        assert filtered[0]["bill_id"] == "TEST-001"

    def test_get_processing_statistics(self, integration_manager):
        """Test processing statistics"""
        # Mock some processing history
        integration_manager.processing_history = [
            {
                "timestamp": datetime.now(),
                "success": True,
                "bills_processed": 10,
                "processing_time_ms": 1000.0,
                "quality_score_avg": 0.85,
            },
            {
                "timestamp": datetime.now(),
                "success": False,
                "bills_processed": 0,
                "processing_time_ms": 500.0,
                "error": "Test error",
            },
        ]

        stats = integration_manager.get_processing_statistics()

        assert stats["total_sessions"] == 2
        assert stats["successful_sessions"] == 1
        assert stats["failed_sessions"] == 1
        assert stats["total_bills_processed"] == 10
        assert stats["average_processing_time_ms"] > 0
        assert stats["success_rate"] == 0.5

    def test_export_results(self, integration_manager):
        """Test results export"""
        # Mock results
        mock_results = [
            {
                "bill_id": "TEST-001",
                "title": "テスト法案",
                "status": "審議中",
                "data_quality_score": 0.9,
                "processing_timestamp": datetime.now(),
            }
        ]

        # Test JSON export
        export_result = integration_manager.export_results(mock_results, format="json")

        assert export_result["success"] is True
        assert export_result["format"] == "json"
        assert len(export_result["data"]) == 1
        assert export_result["data"][0]["bill_id"] == "TEST-001"


class TestIntegrationScenarios:
    """Test complete integration scenarios"""

    def test_full_integration_pipeline(self):
        """Test complete integration pipeline"""
        # Mock all components
        with (
            patch(
                "services.ingest-worker.src.processor.data_integration_manager.BillDataMerger"
            ) as mock_merger_class,
            patch(
                "services.ingest-worker.src.processor.data_integration_manager.BillDataValidator"
            ) as mock_validator_class,
            patch(
                "services.ingest-worker.src.processor.data_integration_manager.BillProgressTracker"
            ) as mock_tracker_class,
        ):
            # Setup mocks
            mock_merger = Mock()
            mock_validator = Mock()
            mock_tracker = Mock()

            mock_merger_class.return_value = mock_merger
            mock_validator_class.return_value = mock_validator
            mock_tracker_class.return_value = mock_tracker

            # Mock successful processing
            mock_merger.merge_bills.return_value = MergeResult(
                success=True,
                merged_bills=[{"bill_id": "TEST-001", "title": "テスト法案"}],
                conflicts=[],
                processing_time_ms=100.0,
            )

            mock_validator.validate_bill.return_value = ValidationResult(
                bill_id="TEST-001",
                is_valid=True,
                quality_score=0.9,
                issues=[],
                validation_time_ms=50.0,
            )

            mock_tracker.track_progress.return_value = ProgressUpdateResult(
                bill_id="TEST-001",
                progress_detected=False,
                stage_transitions=[],
                alerts=[],
                confidence_score=0.8,
            )

            # Create manager and process
            manager = DataIntegrationManager("postgresql://test")

            test_bills = [
                {"bill_id": "TEST-001", "title": "テスト法案", "status": "審議中"}
            ]

            result = manager.process_bills(test_bills)

            assert result.success is True
            assert len(result.processed_bills) == 1
            assert result.merge_statistics["total_merged"] == 1
            assert result.validation_statistics["total_validated"] == 1

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        with patch(
            "services.ingest-worker.src.processor.data_integration_manager.BillDataMerger"
        ) as mock_merger_class:
            mock_merger = Mock()
            mock_merger_class.return_value = mock_merger

            # Mock partial failure
            mock_merger.merge_bills.side_effect = [
                # First call fails
                Exception("Network error"),
                # Second call succeeds
                MergeResult(
                    success=True,
                    merged_bills=[{"bill_id": "TEST-001", "title": "テスト法案"}],
                    conflicts=[],
                    processing_time_ms=100.0,
                ),
            ]

            manager = DataIntegrationManager("postgresql://test")

            # First attempt should fail
            result1 = manager.process_bills(
                [{"bill_id": "TEST-001", "title": "テスト法案"}]
            )
            assert result1.success is False

            # Second attempt should succeed
            result2 = manager.process_bills(
                [{"bill_id": "TEST-001", "title": "テスト法案"}]
            )
            assert result2.success is True

    def test_performance_monitoring(self):
        """Test performance monitoring and metrics"""
        with patch(
            "services.ingest-worker.src.processor.data_integration_manager.BillDataMerger"
        ) as mock_merger_class:
            mock_merger = Mock()
            mock_merger_class.return_value = mock_merger

            # Mock timing data
            mock_merger.merge_bills.return_value = MergeResult(
                success=True,
                merged_bills=[{"bill_id": "TEST-001", "title": "テスト法案"}],
                conflicts=[],
                processing_time_ms=250.0,
            )

            manager = DataIntegrationManager("postgresql://test")

            # Process multiple batches
            for i in range(5):
                test_bills = [{"bill_id": f"TEST-{i:03d}", "title": f"テスト法案{i}"}]
                result = manager.process_bills(test_bills)
                assert result.success is True

            # Check statistics
            stats = manager.get_processing_statistics()
            assert stats["total_sessions"] == 5
            assert stats["successful_sessions"] == 5
            assert stats["average_processing_time_ms"] > 0

    def test_data_quality_improvement(self):
        """Test data quality improvement over time"""
        with patch(
            "services.ingest-worker.src.processor.data_integration_manager.BillDataValidator"
        ) as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator

            # Mock improving quality scores
            quality_scores = [0.6, 0.7, 0.8, 0.9, 0.95]
            mock_validator.validate_bill.side_effect = [
                ValidationResult(
                    bill_id=f"TEST-{i:03d}",
                    is_valid=True,
                    quality_score=score,
                    issues=[],
                    validation_time_ms=50.0,
                )
                for i, score in enumerate(quality_scores)
            ]

            manager = DataIntegrationManager("postgresql://test")

            # Process bills with improving quality
            quality_trend = []
            for i, expected_score in enumerate(quality_scores):
                test_bills = [{"bill_id": f"TEST-{i:03d}", "title": f"テスト法案{i}"}]
                result = manager.process_bills(test_bills)

                if result.success:
                    avg_quality = result.validation_statistics.get("average_quality", 0)
                    quality_trend.append(avg_quality)

            # Verify quality improvement trend
            assert len(quality_trend) > 0
            # Quality should generally improve (allowing for minor fluctuations)
            assert quality_trend[-1] >= quality_trend[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
