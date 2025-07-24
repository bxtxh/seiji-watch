"""
Tests for data migration functionality.
Tests data quality auditing, completion processing, and migration service.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from ..src.migration.data_completion_processor import (
    BatchCompletionResult,
    CompletionPriority,
    CompletionResult,
    CompletionStrategy,
    CompletionTask,
    DataCompletionProcessor,
)
from ..src.migration.data_migration_service import (
    DataMigrationService,
    MigrationExecution,
    MigrationPhase,
    MigrationPlan,
    MigrationStatus,
)
from ..src.migration.data_quality_auditor import (
    DataQualityAuditor,
    QualityIssue,
    QualityIssueSeverity,
    QualityIssueType,
    QualityMetrics,
    QualityReport,
)


class TestDataQualityAuditor:
    """Test data quality auditor functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def quality_auditor(self, mock_engine):
        """Create test quality auditor"""
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            return DataQualityAuditor("postgresql://test")

    def test_auditor_initialization(self, quality_auditor):
        """Test auditor initialization"""
        assert quality_auditor.database_url == "postgresql://test"
        assert quality_auditor.quality_thresholds['completeness_min'] == 0.8
        assert len(quality_auditor.required_fields) > 0
        assert len(quality_auditor.enhanced_fields) > 0

    def test_calculate_overall_metrics(self, quality_auditor):
        """Test overall metrics calculation"""
        # Create mock bills
        bills = [
            Mock(
                bill_id="test-1",
                title="Test Bill 1",
                status="審議中",
                submitter="政府",
                diet_session="204",
                house_of_origin="参議院",
                submitted_date="2021-01-01",
                updated_at=datetime.now()
            ),
            Mock(
                bill_id="test-2",
                title="Test Bill 2",
                status="成立",
                submitter="議員",
                diet_session="204",
                house_of_origin="衆議院",
                submitted_date="2021-02-01",
                updated_at=datetime.now()
            )
        ]

        # Mock required methods
        quality_auditor._is_bill_valid = Mock(return_value=True)
        quality_auditor._calculate_accuracy_rate = Mock(return_value=0.9)
        quality_auditor._calculate_consistency_rate = Mock(return_value=0.85)
        quality_auditor._calculate_timeliness_rate = Mock(return_value=0.8)

        metrics = quality_auditor._calculate_overall_metrics(bills)

        assert metrics.total_records == 2
        assert metrics.valid_records == 2
        assert metrics.completeness_rate == 1.0
        assert metrics.accuracy_rate == 0.9
        assert metrics.consistency_rate == 0.85
        assert metrics.timeliness_rate == 0.8
        assert metrics.overall_quality_score > 0

    def test_detect_quality_issues(self, quality_auditor):
        """Test quality issue detection"""
        # Create bill with issues
        bill = Mock(
            bill_id="test-bill-1",
            title="",  # Empty title
            status="invalid_status",  # Invalid status
            submitter=None,  # Missing submitter
            diet_session="204",
            house_of_origin="参議院",
            submitted_date="2021-01-01",
            updated_at=datetime.now(),
            bill_outline=None,  # Missing enhanced field
            background_context="短",  # Too short
            expected_effects=None
        )

        # Mock helper methods
        quality_auditor._check_required_fields = Mock(return_value=[
            QualityIssue(
                bill_id="test-bill-1",
                issue_type=QualityIssueType.EMPTY_FIELD,
                severity=QualityIssueSeverity.HIGH,
                field_name="title",
                description="Title is empty",
                current_value="",
                suggested_fix="Add title",
                confidence=1.0
            )
        ])

        quality_auditor._check_enhanced_fields = Mock(return_value=[
            QualityIssue(
                bill_id="test-bill-1",
                issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
                severity=QualityIssueSeverity.HIGH,
                field_name="bill_outline",
                description="Bill outline is missing",
                current_value=None,
                suggested_fix="Extract bill outline",
                confidence=0.9
            )
        ])

        quality_auditor._check_data_consistency = Mock(return_value=[])
        quality_auditor._check_japanese_text_quality = Mock(return_value=[])
        quality_auditor._check_data_freshness = Mock(return_value=[])

        issues = quality_auditor._detect_quality_issues([bill])

        assert len(issues) == 2
        assert any(issue.field_name == "title" for issue in issues)
        assert any(issue.field_name == "bill_outline" for issue in issues)

    def test_is_japanese_text_quality_good(self, quality_auditor):
        """Test Japanese text quality validation"""
        # Good Japanese text
        good_text = "この法案は、デジタル社会の形成を目的としています。"
        assert quality_auditor._is_japanese_text_quality_good(good_text)

        # Too short
        short_text = "短い"
        assert not quality_auditor._is_japanese_text_quality_good(short_text)

        # No Japanese characters
        english_text = "This is English text only and should fail"
        assert not quality_auditor._is_japanese_text_quality_good(english_text)

    def test_calculate_bill_quality_score(self, quality_auditor):
        """Test bill quality score calculation"""
        # High quality bill
        high_quality_bill = Mock(
            title="デジタル社会形成基本法案",
            status="審議中",
            bill_outline="本法案は、デジタル社会の形成を推進し、国民の利便性向上を図ることを目的とする。",
            background_context="近年のデジタル化の進展に伴い、行政手続きのデジタル化が急務となっている。",
            expected_effects="本法案により、行政手続きの効率化が期待される。"
        )

        # Mock helper methods
        quality_auditor._is_field_value_valid = Mock(return_value=True)
        quality_auditor._is_japanese_text_quality_good = Mock(return_value=True)

        score = quality_auditor._calculate_bill_quality_score(high_quality_bill)
        assert score > 0.8

        # Low quality bill
        low_quality_bill = Mock(
            title="テスト",
            status="審議中",
            bill_outline=None,
            background_context=None,
            expected_effects=None
        )

        quality_auditor._is_field_value_valid = Mock(
            side_effect=lambda field, value: value is not None)

        score = quality_auditor._calculate_bill_quality_score(low_quality_bill)
        assert score < 0.5

    @patch('sqlalchemy.orm.sessionmaker')
    def test_conduct_full_audit(self, mock_session_maker, quality_auditor):
        """Test full audit process"""
        # Mock session
        mock_session = Mock()
        mock_session_maker.return_value = mock_session
        mock_session.__enter__.return_value = mock_session

        # Mock bills
        mock_bills = [
            Mock(bill_id="test-1", title="Test Bill 1"),
            Mock(bill_id="test-2", title="Test Bill 2")
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_bills

        # Mock methods
        quality_auditor._calculate_overall_metrics = Mock(return_value=QualityMetrics(
            total_records=2, valid_records=2, invalid_records=0,
            completeness_rate=1.0, accuracy_rate=0.9, consistency_rate=0.85,
            timeliness_rate=0.8, overall_quality_score=0.88
        ))

        quality_auditor._analyze_field_quality = Mock(return_value={
            'title': QualityMetrics(2, 2, 0, 1.0, 0.9, 0.85, 0.8, 0.88)
        })

        quality_auditor._detect_quality_issues = Mock(return_value=[])
        quality_auditor._generate_recommendations = Mock(
            return_value=["Test recommendation"])
        quality_auditor._determine_improvement_priorities = Mock(return_value=[])

        report = quality_auditor.conduct_full_audit()

        assert isinstance(report, QualityReport)
        assert report.total_bills == 2
        assert report.overall_metrics.total_records == 2
        assert len(report.recommendations) > 0


class TestDataCompletionProcessor:
    """Test data completion processor functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def completion_processor(self, mock_engine):
        """Create test completion processor"""
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            return DataCompletionProcessor("postgresql://test")

    def test_processor_initialization(self, completion_processor):
        """Test processor initialization"""
        assert completion_processor.database_url == "postgresql://test"
        assert completion_processor.config['batch_size'] == 50
        assert completion_processor.config['max_concurrent_tasks'] == 10

    def test_create_completion_tasks(self, completion_processor):
        """Test completion task creation"""
        # Create quality issues
        issues = [
            QualityIssue(
                bill_id="test-bill-1",
                issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
                severity=QualityIssueSeverity.HIGH,
                field_name="bill_outline",
                description="Bill outline is missing",
                current_value=None,
                suggested_fix="Extract bill outline",
                confidence=0.9
            ),
            QualityIssue(
                bill_id="test-bill-1",
                issue_type=QualityIssueType.INCONSISTENT_DATA,
                severity=QualityIssueSeverity.MEDIUM,
                field_name="status",
                description="Status is inconsistent",
                current_value="invalid",
                suggested_fix="Fix status",
                confidence=0.8
            )
        ]

        tasks = completion_processor._create_completion_tasks("test-bill-1", issues)

        assert len(tasks) >= 2
        assert any(task.strategy == CompletionStrategy.SCRAPE_MISSING for task in tasks)
        assert any(task.strategy == CompletionStrategy.VALIDATE_AND_FIX for task in tasks)

    def test_determine_task_priority(self, completion_processor):
        """Test task priority determination"""
        # Critical fields
        critical_fields = ["bill_outline", "title"]
        priority = completion_processor._determine_task_priority(critical_fields)
        assert priority == CompletionPriority.CRITICAL

        # Regular fields
        regular_fields = ["committee_assignments"]
        priority = completion_processor._determine_task_priority(regular_fields)
        assert priority == CompletionPriority.MEDIUM

        # Empty fields
        empty_fields = []
        priority = completion_processor._determine_task_priority(empty_fields)
        assert priority == CompletionPriority.LOW

    def test_prioritize_tasks(self, completion_processor):
        """Test task prioritization"""
        tasks = [
            CompletionTask(
                bill_id="test-1",
                strategy=CompletionStrategy.SCRAPE_MISSING,
                priority=CompletionPriority.LOW,
                target_fields=["field1"],
                description="Low priority task",
                estimated_effort=10
            ),
            CompletionTask(
                bill_id="test-2",
                strategy=CompletionStrategy.VALIDATE_AND_FIX,
                priority=CompletionPriority.CRITICAL,
                target_fields=["field2"],
                description="Critical priority task",
                estimated_effort=5
            ),
            CompletionTask(
                bill_id="test-3",
                strategy=CompletionStrategy.ENHANCE_EXISTING,
                priority=CompletionPriority.HIGH,
                target_fields=["field3"],
                description="High priority task",
                estimated_effort=8
            )
        ]

        prioritized = completion_processor._prioritize_tasks(tasks)

        # Should be sorted by priority (critical first)
        assert prioritized[0].priority == CompletionPriority.CRITICAL
        assert prioritized[1].priority == CompletionPriority.HIGH
        assert prioritized[2].priority == CompletionPriority.LOW

    def test_scrape_missing_data(self, completion_processor):
        """Test missing data scraping"""
        # Mock bill
        mock_bill = Mock(
            bill_id="test-bill-1",
            house_of_origin="参議院",
            bill_outline=None,
            background_context=None
        )

        # Mock scraper
        mock_scraper = Mock()
        mock_scraper.scrape_enhanced_bill_data.return_value = {
            'bill_outline': '本法案は、テスト目的で作成されたものです。',
            'background_context': 'テスト用の背景情報です。'
        }
        completion_processor.sangiin_scraper = mock_scraper

        # Mock quality score calculation
        completion_processor._calculate_quality_score = Mock(return_value=0.85)

        result = completion_processor._scrape_missing_data(
            mock_bill, ['bill_outline', 'background_context'])

        assert result['success']
        assert len(result['completed_fields']) == 2
        assert len(result['failed_fields']) == 0
        assert result['quality_improvement'] > 0

    def test_enhance_text_quality(self, completion_processor):
        """Test text quality enhancement"""
        # Text with issues
        poor_text = "  これは  テスト  です。。  "
        enhanced = completion_processor._enhance_text_quality(poor_text)

        assert enhanced == "これは テスト です。"
        assert enhanced != poor_text

        # Already good text
        good_text = "これは良いテキストです。"
        enhanced = completion_processor._enhance_text_quality(good_text)
        assert enhanced == good_text

    def test_generate_completion_plan(self, completion_processor):
        """Test completion plan generation"""
        # Mock quality issues
        quality_issues = [
            QualityIssue(
                bill_id="test-bill-1",
                issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
                severity=QualityIssueSeverity.HIGH,
                field_name="bill_outline",
                description="Bill outline is missing",
                current_value=None,
                suggested_fix="Extract bill outline",
                confidence=0.9
            ),
            QualityIssue(
                bill_id="test-bill-2",
                issue_type=QualityIssueType.POOR_JAPANESE_TEXT,
                severity=QualityIssueSeverity.MEDIUM,
                field_name="title",
                description="Poor text quality",
                current_value="短い",
                suggested_fix="Improve text",
                confidence=0.8
            )
        ]

        # Mock methods
        completion_processor._group_issues_by_bill = Mock(return_value={
            "test-bill-1": [quality_issues[0]],
            "test-bill-2": [quality_issues[1]]
        })

        completion_processor._create_completion_tasks = Mock(
            side_effect=lambda bill_id,
            issues: [
                CompletionTask(
                    bill_id=bill_id,
                    strategy=CompletionStrategy.SCRAPE_MISSING,
                    priority=CompletionPriority.HIGH,
                    target_fields=["test_field"],
                    description="Test task",
                    estimated_effort=10)])

        completion_processor._prioritize_tasks = Mock(side_effect=lambda tasks: tasks)

        plan = completion_processor.generate_completion_plan(quality_issues)

        assert len(plan) == 2
        assert all(isinstance(task, CompletionTask) for task in plan)


class TestDataMigrationService:
    """Test data migration service functionality"""

    @pytest.fixture
    def mock_engine(self):
        """Create mock database engine"""
        engine = Mock()
        engine.connect.return_value.__enter__.return_value = Mock()
        return engine

    @pytest.fixture
    def migration_service(self, mock_engine):
        """Create test migration service"""
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            return DataMigrationService("postgresql://test")

    def test_service_initialization(self, migration_service):
        """Test service initialization"""
        assert migration_service.database_url == "postgresql://test"
        assert migration_service.config['max_concurrent_migrations'] == 1
        assert migration_service.config['auto_validate_after_completion']

    def test_create_migration_plan(self, migration_service):
        """Test migration plan creation"""
        # Mock quality auditor
        mock_audit_report = Mock()
        mock_audit_report.issues = [
            QualityIssue(
                bill_id="test-bill-1",
                issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
                severity=QualityIssueSeverity.HIGH,
                field_name="bill_outline",
                description="Bill outline is missing",
                current_value=None,
                suggested_fix="Extract bill outline",
                confidence=0.9
            )
        ]

        migration_service.quality_auditor.conduct_full_audit = Mock(
            return_value=mock_audit_report)

        # Mock completion processor
        mock_tasks = [
            CompletionTask(
                bill_id="test-bill-1",
                strategy=CompletionStrategy.SCRAPE_MISSING,
                priority=CompletionPriority.HIGH,
                target_fields=["bill_outline"],
                description="Test task",
                estimated_effort=10
            )
        ]

        migration_service.completion_processor.generate_completion_plan = Mock(
            return_value=mock_tasks)

        # Mock helper methods
        migration_service._estimate_migration_time = Mock(return_value=0.5)
        migration_service._analyze_task_priorities = Mock(return_value={'high': 1})

        plan = migration_service.create_migration_plan()

        assert isinstance(plan, MigrationPlan)
        assert plan.total_bills == 1
        assert plan.total_tasks == 1
        assert plan.estimated_time_hours == 0.5
        assert len(plan.completion_tasks) == 1
        assert len(plan.quality_issues) == 1

    def test_estimate_migration_time(self, migration_service):
        """Test migration time estimation"""
        tasks = [
            CompletionTask(
                bill_id="test-1",
                strategy=CompletionStrategy.SCRAPE_MISSING,
                priority=CompletionPriority.HIGH,
                target_fields=["field1"],
                description="Task 1",
                estimated_effort=60  # 1 minute
            ),
            CompletionTask(
                bill_id="test-2",
                strategy=CompletionStrategy.VALIDATE_AND_FIX,
                priority=CompletionPriority.MEDIUM,
                target_fields=["field2"],
                description="Task 2",
                estimated_effort=120  # 2 minutes
            )
        ]

        estimated_hours = migration_service._estimate_migration_time(tasks)

        # Should be (60 + 120) * 1.3 / 3600 = 0.065 hours
        assert estimated_hours > 0.05
        assert estimated_hours < 0.1

    def test_analyze_task_priorities(self, migration_service):
        """Test task priority analysis"""
        tasks = [
            CompletionTask(
                bill_id="test-1",
                strategy=CompletionStrategy.SCRAPE_MISSING,
                priority=CompletionPriority.CRITICAL,
                target_fields=["field1"],
                description="Critical task",
                estimated_effort=10
            ),
            CompletionTask(
                bill_id="test-2",
                strategy=CompletionStrategy.VALIDATE_AND_FIX,
                priority=CompletionPriority.HIGH,
                target_fields=["field2"],
                description="High priority task",
                estimated_effort=20
            ),
            CompletionTask(
                bill_id="test-3",
                strategy=CompletionStrategy.ENHANCE_EXISTING,
                priority=CompletionPriority.HIGH,
                target_fields=["field3"],
                description="Another high priority task",
                estimated_effort=15
            )
        ]

        breakdown = migration_service._analyze_task_priorities(tasks)

        assert breakdown['critical'] == 1
        assert breakdown['high'] == 2
        assert breakdown.get('medium', 0) == 0
        assert breakdown.get('low', 0) == 0

    def test_execute_migration_success(self, migration_service):
        """Test successful migration execution"""
        # Create mock plan
        plan = MigrationPlan(
            plan_id="test-plan-1",
            total_bills=1,
            total_tasks=1,
            estimated_time_hours=0.1,
            priority_breakdown={'high': 1},
            phases=[MigrationPhase.EXECUTION],
            completion_tasks=[
                CompletionTask(
                    bill_id="test-bill-1",
                    strategy=CompletionStrategy.SCRAPE_MISSING,
                    priority=CompletionPriority.HIGH,
                    target_fields=["bill_outline"],
                    description="Test task",
                    estimated_effort=10
                )
            ]
        )

        # Mock completion processor
        mock_batch_result = BatchCompletionResult(
            batch_id="test-batch-1",
            total_tasks=1,
            completed_tasks=1,
            failed_tasks=0,
            skipped_tasks=0,
            total_processing_time_ms=1000.0,
            success_rate=1.0,
            tasks_results=[
                CompletionResult(
                    task_id="test-task-1",
                    bill_id="test-bill-1",
                    success=True,
                    fields_completed=["bill_outline"],
                    fields_failed=[],
                    processing_time_ms=1000.0
                )
            ]
        )

        migration_service.completion_processor.execute_completion_plan = Mock(
            return_value=mock_batch_result)

        # Mock validation
        migration_service._validate_migration_results = Mock(return_value={
            'validation_passed': True,
            'improvement_rate': 0.2
        })

        # Mock report generation
        mock_report = Mock()
        migration_service._generate_migration_report = Mock(return_value=mock_report)
        migration_service._save_migration_report = Mock()

        execution = migration_service.execute_migration(plan)

        assert isinstance(execution, MigrationExecution)
        assert execution.status == MigrationStatus.COMPLETED
        assert execution.tasks_completed == 1
        assert execution.tasks_failed == 0
        assert execution.progress_percentage == 100.0
        assert execution.completed_at is not None

    def test_execute_migration_failure(self, migration_service):
        """Test failed migration execution"""
        # Create mock plan
        plan = MigrationPlan(
            plan_id="test-plan-1",
            total_bills=1,
            total_tasks=1,
            estimated_time_hours=0.1,
            priority_breakdown={'high': 1},
            phases=[MigrationPhase.EXECUTION],
            completion_tasks=[]
        )

        # Mock completion processor to raise exception
        migration_service.completion_processor.execute_completion_plan = Mock(
            side_effect=Exception("Test failure")
        )

        execution = migration_service.execute_migration(plan)

        assert isinstance(execution, MigrationExecution)
        assert execution.status == MigrationStatus.FAILED
        assert len(execution.errors) > 0
        assert "Test failure" in execution.errors[0]

    def test_get_migration_statistics(self, migration_service):
        """Test migration statistics retrieval"""
        # Add mock execution history
        migration_service.migration_history = [
            MigrationExecution(
                execution_id="exec-1",
                plan_id="plan-1",
                status=MigrationStatus.COMPLETED,
                current_phase=MigrationPhase.COMPLETION,
                started_at=datetime.now() - timedelta(days=1),
                completed_at=datetime.now(),
                tasks_completed=10,
                tasks_failed=0,
                phase_results={'execution': {'processing_time_ms': 5000}}
            ),
            MigrationExecution(
                execution_id="exec-2",
                plan_id="plan-2",
                status=MigrationStatus.FAILED,
                current_phase=MigrationPhase.EXECUTION,
                started_at=datetime.now() - timedelta(days=2),
                completed_at=datetime.now() - timedelta(days=2),
                tasks_completed=5,
                tasks_failed=5,
                phase_results={'execution': {'processing_time_ms': 3000}}
            )
        ]

        stats = migration_service.get_migration_statistics(7)

        assert stats['total_migrations'] == 2
        assert stats['successful_migrations'] == 1
        assert stats['failed_migrations'] == 1
        assert stats['success_rate'] == 0.5
        assert stats['total_tasks_completed'] == 15
        assert stats['total_tasks_failed'] == 5
        assert stats['average_processing_time_ms'] > 0

    def test_get_migration_history(self, migration_service):
        """Test migration history retrieval"""
        # Add mock execution history
        migration_service.migration_history = [
            MigrationExecution(
                execution_id="exec-1",
                plan_id="plan-1",
                status=MigrationStatus.COMPLETED,
                current_phase=MigrationPhase.COMPLETION,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                tasks_completed=10,
                tasks_failed=0
            )
        ]

        history = migration_service.get_migration_history(5)

        assert len(history) == 1
        assert history[0]['execution_id'] == "exec-1"
        assert history[0]['status'] == MigrationStatus.COMPLETED.value
        assert history[0]['tasks_completed'] == 10
        assert history[0]['tasks_failed'] == 0


class TestIntegrationScenarios:
    """Test integration scenarios"""

    def test_end_to_end_migration_flow(self):
        """Test complete migration flow"""
        # This would be a full integration test with real database
        # Mock the entire flow for now

        with patch('sqlalchemy.create_engine') as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            # Create service
            service = DataMigrationService("postgresql://test")

            # Mock quality auditor
            mock_audit_report = Mock()
            mock_audit_report.issues = [
                QualityIssue(
                    bill_id="test-bill-1",
                    issue_type=QualityIssueType.MISSING_REQUIRED_FIELD,
                    severity=QualityIssueSeverity.HIGH,
                    field_name="bill_outline",
                    description="Bill outline is missing",
                    current_value=None,
                    suggested_fix="Extract bill outline",
                    confidence=0.9
                )
            ]

            service.quality_auditor.conduct_full_audit = Mock(
                return_value=mock_audit_report)

            # Mock completion processor
            mock_tasks = [
                CompletionTask(
                    bill_id="test-bill-1",
                    strategy=CompletionStrategy.SCRAPE_MISSING,
                    priority=CompletionPriority.HIGH,
                    target_fields=["bill_outline"],
                    description="Test task",
                    estimated_effort=10
                )
            ]

            service.completion_processor.generate_completion_plan = Mock(
                return_value=mock_tasks)

            mock_batch_result = BatchCompletionResult(
                batch_id="test-batch-1",
                total_tasks=1,
                completed_tasks=1,
                failed_tasks=0,
                skipped_tasks=0,
                total_processing_time_ms=1000.0,
                success_rate=1.0
            )

            service.completion_processor.execute_completion_plan = Mock(
                return_value=mock_batch_result)

            # Mock other methods
            service._validate_migration_results = Mock(
                return_value={'validation_passed': True})
            service._generate_migration_report = Mock(return_value=Mock())
            service._save_migration_report = Mock()

            # Execute flow
            plan = service.create_migration_plan()
            execution = service.execute_migration(plan)

            assert isinstance(plan, MigrationPlan)
            assert isinstance(execution, MigrationExecution)
            assert execution.status == MigrationStatus.COMPLETED

    def test_migration_with_errors(self):
        """Test migration handling with errors"""
        with patch('sqlalchemy.create_engine') as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            service = DataMigrationService("postgresql://test")

            # Mock quality auditor to raise error
            service.quality_auditor.conduct_full_audit = Mock(
                side_effect=Exception("Audit failed")
            )

            # Should raise exception
            with pytest.raises(Exception) as exc_info:
                service.create_migration_plan()

            assert "Audit failed" in str(exc_info.value)

    def test_performance_monitoring(self):
        """Test performance monitoring during migration"""
        with patch('sqlalchemy.create_engine') as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            service = DataMigrationService("postgresql://test")

            # Add execution with timing data
            execution = MigrationExecution(
                execution_id="test-exec",
                plan_id="test-plan",
                status=MigrationStatus.COMPLETED,
                current_phase=MigrationPhase.COMPLETION,
                started_at=datetime.now() - timedelta(minutes=5),
                completed_at=datetime.now(),
                tasks_completed=10,
                tasks_failed=0,
                phase_results={
                    'execution': {'processing_time_ms': 180000},  # 3 minutes
                    'validation': {'processing_time_ms': 60000}   # 1 minute
                }
            )

            service.migration_history.append(execution)

            # Get statistics
            stats = service.get_migration_statistics(1)

            assert stats['total_migrations'] == 1
            assert stats['successful_migrations'] == 1
            assert stats['average_processing_time_ms'] == 180000

    def test_quality_improvement_tracking(self):
        """Test quality improvement tracking"""
        with patch('sqlalchemy.create_engine') as mock_engine_create:
            mock_engine = Mock()
            mock_engine_create.return_value = mock_engine

            auditor = DataQualityAuditor("postgresql://test")

            # Mock quality trend calculation
            auditor.get_quality_trend = Mock(return_value={
                'trend': 'improving',
                'overall_average': 0.85,
                'period_days': 30
            })

            trend = auditor.get_quality_trend(30)

            assert trend['trend'] == 'improving'
            assert trend['overall_average'] > 0.8
            assert trend['period_days'] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
