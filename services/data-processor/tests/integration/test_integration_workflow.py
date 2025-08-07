"""
Integration tests for the complete Policy Issue Extraction workflow.
Tests end-to-end scenarios including extraction, validation, storage, and notifications.
"""

import asyncio
import json
import os

# Import all components for integration testing
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from batch.issue_relationship_batch import IssueRelationshipBatchProcessor

from services.airtable_issue_manager import AirtableIssueManager

# TODO: Replace with HTTP client mock for notifications-worker service
# from services.discord_notification_bot import DiscordNotificationBot
from services.issue_versioning_service import IssueVersioningService
from services.policy_issue_extractor import (
    BillData,
    DualLevelIssue,
    PolicyIssueExtractor,
)

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.mark.asyncio
class TestCompleteExtractionWorkflow:
    """Test the complete issue extraction and processing workflow."""

    @pytest.fixture
    def sample_bills(self):
        """Create sample bill data for testing."""
        return [
            BillData(
                id="bill_001",
                title="介護保険制度改正法案",
                outline="高齢者の介護負担を軽減し、制度の持続可能性を確保する",
                background_context="高齢化社会の進展により介護需要が増加",
                expected_effects="介護費用の削減と質の向上",
                key_provisions=["自己負担率見直し", "サービス体制強化"],
                submitter="厚生労働省",
                category="社会保障",
            ),
            BillData(
                id="bill_002",
                title="環境保護促進法案",
                outline="環境保護を促進し、持続可能な社会を実現する",
                background_context="地球温暖化対策の必要性",
                expected_effects="CO2削減と環境改善",
                key_provisions=["排出規制強化", "再エネ推進"],
                submitter="環境省",
                category="環境・エネルギー",
            ),
        ]

    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        # Mock OpenAI client
        mock_openai_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "label_lv1": "政策課題を解決する",
                "label_lv2": "包括的な政策課題の解決を図る",
                "confidence": 0.85,
            }
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        # Mock Airtable client
        mock_airtable_client = AsyncMock()
        mock_airtable_client.base_url = "https://api.airtable.com/v0/test"
        mock_airtable_client._rate_limited_request.return_value = {
            "id": "rec_123",
            "fields": {},
        }
        mock_airtable_client.health_check.return_value = True

        # Mock Discord bot
        mock_discord_bot = AsyncMock()
        mock_discord_bot.send_custom_notification.return_value = True
        mock_discord_bot.health_check.return_value = True

        return {
            "openai_client": mock_openai_client,
            "airtable_client": mock_airtable_client,
            "discord_bot": mock_discord_bot,
        }

    async def test_single_bill_extraction_workflow(self, sample_bills, mock_components):
        """Test complete workflow for a single bill."""
        bill = sample_bills[0]

        # Setup components with mocks
        with patch("openai.AsyncOpenAI", return_value=mock_components["openai_client"]):
            extractor = PolicyIssueExtractor()
            extractor.client = mock_components["openai_client"]

        issue_manager = AirtableIssueManager(mock_components["airtable_client"])

        # Step 1: Extract issues from bill
        issues = await extractor.extract_dual_level_issues(bill)

        assert len(issues) == 1
        assert issues[0].label_lv1 == "政策課題を解決する"
        assert issues[0].confidence == 0.85

        # Step 2: Create issue pairs in Airtable
        mock_components["airtable_client"]._rate_limited_request.side_effect = [
            {"id": "rec_lv1_123", "fields": {}},
            {"id": "rec_lv2_456", "fields": {}},
        ]

        lv1_id, lv2_id = await issue_manager.create_issue_pair(issues[0], bill.id, 0.8)

        assert lv1_id == "rec_lv1_123"
        assert lv2_id == "rec_lv2_456"

        # Verify Airtable calls were made correctly
        calls = mock_components["airtable_client"]._rate_limited_request.call_args_list
        assert len(calls) == 2

        # Check lv1 record
        lv1_data = calls[0][1]["json"]["fields"]
        assert lv1_data["Label_Lv1"] == "政策課題を解決する"
        assert lv1_data["Source_Bill_ID"] == bill.id

        # Check lv2 record
        lv2_data = calls[1][1]["json"]["fields"]
        assert lv2_data["Label_Lv2"] == "包括的な政策課題の解決を図る"
        assert lv2_data["Parent_ID"] == "rec_lv1_123"

    async def test_batch_extraction_workflow(self, sample_bills, mock_components):
        """Test batch extraction workflow for multiple bills."""

        with patch("openai.AsyncOpenAI", return_value=mock_components["openai_client"]):
            extractor = PolicyIssueExtractor()
            extractor.client = mock_components["openai_client"]

        issue_manager = AirtableIssueManager(mock_components["airtable_client"])

        # Mock responses for batch
        mock_components["airtable_client"]._rate_limited_request.side_effect = [
            {"id": f"rec_lv1_{i}", "fields": {}} for i in range(4)
        ] + [{"id": f"rec_lv2_{i}", "fields": {}} for i in range(4)]

        # Extract issues from multiple bills
        results = await extractor.batch_extract_issues(sample_bills)

        assert len(results) == 2
        for result in results:
            assert result["status"] == "success"
            assert len(result["issues"]) == 1

        # Create issue pairs for all extracted issues
        created_pairs = []
        for i, result in enumerate(results):
            if result["status"] == "success":
                for issue_data in result["issues"]:
                    dual_issue = DualLevelIssue(**issue_data)
                    lv1_id, lv2_id = await issue_manager.create_issue_pair(
                        dual_issue, sample_bills[i].id, 0.8
                    )
                    created_pairs.append((lv1_id, lv2_id))

        assert len(created_pairs) == 2
        assert all(pair[0] and pair[1] for pair in created_pairs)

    async def test_human_review_workflow(self, mock_components):
        """Test the human review workflow with status updates."""

        issue_manager = AirtableIssueManager(mock_components["airtable_client"])
        discord_bot = None  # TODO: Mock HTTP client for notifications-worker
        # discord_bot.airtable_manager = issue_manager  # Disabled - service separation

        # Mock Discord webhook
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 204
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = (
                mock_response
            )

            # Step 1: Get pending issues count
            mock_components["airtable_client"]._rate_limited_request.return_value = {
                "records": [
                    {"id": "rec_1", "fields": {"Status": "pending"}},
                    {"id": "rec_2", "fields": {"Status": "pending"}},
                ]
            }

            pending_count = await issue_manager.count_pending_issues()
            assert pending_count == 2

            # Step 2: Send Discord notification
            notification_sent = await discord_bot.send_test_notification()
            assert notification_sent is True

            # Step 3: Update issue status (simulating human review)
            mock_components["airtable_client"]._rate_limited_request.return_value = {
                "id": "rec_1"
            }

            success = await issue_manager.update_issue_status(
                "rec_1", "approved", "High quality issue"
            )
            assert success is True

            # Verify status update call
            calls = mock_components[
                "airtable_client"
            ]._rate_limited_request.call_args_list
            status_update_call = calls[-1]  # Last call should be status update
            update_data = status_update_call[1]["json"]["fields"]
            assert update_data["Status"] == "approved"
            assert update_data["Reviewer_Notes"] == "High quality issue"

    async def test_versioning_workflow(self, mock_components):
        """Test issue versioning and history management."""

        versioning_service = IssueVersioningService()
        issue_manager = AirtableIssueManager(mock_components["airtable_client"])
        versioning_service.airtable_manager = issue_manager

        # Create initial issue record
        from services.airtable_issue_manager import AirtableIssueRecord

        initial_record = AirtableIssueRecord(
            issue_id="issue_001",
            label_lv1="初期の政策課題",
            label_lv2="初期の詳細な政策課題",
            confidence=0.8,
            status="pending",
        )

        # Step 1: Create initial version
        initial_version = await versioning_service.create_initial_version(
            initial_record, "system"
        )

        assert initial_version.version_number == 1
        assert initial_version.label_lv1 == "初期の政策課題"

        # Step 2: Create updated version
        updated_record = AirtableIssueRecord(
            issue_id="issue_001",
            label_lv1="更新された政策課題",
            label_lv2="更新された詳細な政策課題",
            confidence=0.9,
            status="approved",
        )

        from services.issue_versioning_service import VersionChangeType

        new_version, conflict_detected = await versioning_service.create_new_version(
            "issue_001",
            updated_record,
            VersionChangeType.CONTENT_UPDATE,
            "Manual review update",
            "reviewer_001",
        )

        assert new_version.version_number == 2
        assert new_version.label_lv1 == "更新された政策課題"
        assert conflict_detected is False

        # Step 3: Get version history
        history = await versioning_service.get_version_history("issue_001")
        assert len(history) == 2
        assert history[0].version_number == 1
        assert history[1].version_number == 2

    async def test_error_recovery_workflow(self, mock_components):
        """Test error recovery and resilience mechanisms."""

        from monitoring.error_recovery_system import error_recovery_system

        # Test circuit breaker functionality
        circuit_breaker = error_recovery_system.circuit_breakers.get("airtable_api")
        if not circuit_breaker:
            from monitoring.error_recovery_system import (
                CircuitBreaker,
                CircuitBreakerConfig,
            )

            config = CircuitBreakerConfig(
                failure_threshold=2, success_threshold=1, timeout=1.0
            )
            circuit_breaker = CircuitBreaker("airtable_api", config)
            error_recovery_system.circuit_breakers["airtable_api"] = circuit_breaker

        # Simulate failures to open circuit breaker
        assert circuit_breaker.can_execute() is True

        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        # Circuit should now be open
        from monitoring.error_recovery_system import CircuitBreakerState

        assert circuit_breaker.state == CircuitBreakerState.OPEN
        assert circuit_breaker.can_execute() is False

        # Test operation with circuit breaker
        async def failing_operation():
            raise Exception("Simulated failure")

        result = await error_recovery_system.execute_with_recovery(
            failing_operation, "airtable_api"
        )

        assert result.success is False
        assert result.circuit_breaker_triggered is True

    async def test_monitoring_integration(self, mock_components):
        """Test monitoring and health check integration."""

        from monitoring.monitoring_alerting_system import monitoring_system

        # Register custom health checks
        async def test_component_health():
            return True

        monitoring_system.health_checker.register_check(
            "test_component", test_component_health
        )

        # Run health checks
        health_results = await monitoring_system.health_checker.run_all_checks()

        assert "test_component" in health_results
        assert health_results["test_component"].status.value == "healthy"

        # Test metrics collection
        monitoring_system.metrics_collector.increment_counter(
            "test_extraction_count", 1
        )
        monitoring_system.metrics_collector.set_gauge("test_confidence_score", 0.85)

        metrics = monitoring_system.metrics_collector.get_all_metrics(5)
        assert "test_extraction_count" in metrics
        assert "test_confidence_score" in metrics

        # Test alert evaluation
        active_alerts = monitoring_system.alert_manager.get_active_alerts()
        initial_alert_count = len(active_alerts)

        # Trigger a test alert
        from monitoring.monitoring_alerting_system import Alert, AlertSeverity

        test_alert = Alert(
            id="test_alert_001",
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.INFO,
            component="test_component",
        )

        await monitoring_system.alert_manager.trigger_alert(test_alert)

        active_alerts = monitoring_system.alert_manager.get_active_alerts()
        assert len(active_alerts) == initial_alert_count + 1

    async def test_batch_job_integration(self, sample_bills, mock_components):
        """Test integration with batch job processing."""

        # Create batch processor with mocked dependencies
        batch_processor = IssueRelationshipBatchProcessor(
            airtable_client=mock_components["airtable_client"],
            issue_manager=AirtableIssueManager(mock_components["airtable_client"]),
            discord_bot=None,  # TODO: Mock HTTP client
        )

        # Mock bill and issue data
        mock_components["airtable_client"].list_bills.return_value = [
            {"id": "bill_001", "fields": {"Name": "テスト法案", "Notes": "法案の内容"}}
        ]

        mock_issues = [
            {
                "id": "issue_001",
                "fields": {
                    "Label_Lv1": "政策課題",
                    "Source_Bill_ID": None,
                    "Status": "approved",
                },
            }
        ]

        issue_manager = batch_processor.issue_manager
        issue_manager.list_issues_by_status = AsyncMock(return_value=mock_issues)

        # Test relationship update
        result = await batch_processor._update_bill_issue_relationships(
            mock_components["airtable_client"].list_bills.return_value[0], mock_issues
        )

        assert "bill_id" in result
        assert "related_issues" in result

        # Test batch job execution status
        job_statuses = await batch_processor.get_all_job_statuses()

        assert "active_jobs" in job_statuses
        assert "recent_completed_jobs" in job_statuses
        assert "scheduler_status" in job_statuses


@pytest.mark.asyncio
class TestPerformanceAndScalability:
    """Test performance characteristics and scalability."""

    async def test_concurrent_extraction(self, mock_components):
        """Test concurrent issue extraction performance."""

        with patch("openai.AsyncOpenAI", return_value=mock_components["openai_client"]):
            extractor = PolicyIssueExtractor()
            extractor.client = mock_components["openai_client"]

        # Create multiple bills for concurrent processing
        bills = [
            BillData(
                id=f"bill_{i:03d}", title=f"テスト法案{i}", outline=f"法案{i}の概要"
            )
            for i in range(10)
        ]

        # Test concurrent extraction
        start_time = asyncio.get_event_loop().time()

        tasks = [extractor.extract_dual_level_issues(bill) for bill in bills]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Verify all extractions completed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == len(bills)

        # Performance should be reasonable (concurrent should be faster than sequential)
        assert duration < 5.0  # Should complete within 5 seconds

    async def test_batch_processing_efficiency(self, mock_components):
        """Test batch processing efficiency."""

        issue_manager = AirtableIssueManager(mock_components["airtable_client"])

        # Mock responses for batch operations
        mock_responses = [{"id": f"rec_{i}", "fields": {}} for i in range(20)]
        mock_components["airtable_client"]._rate_limited_request.side_effect = (
            mock_responses
        )

        # Create test issues for batch processing
        dual_issues = [
            (
                DualLevelIssue(
                    label_lv1=f"政策課題{i}を解決する",
                    label_lv2=f"詳細な政策課題{i}を包括的に解決する",
                    confidence=0.8,
                ),
                f"bill_{i:03d}",
            )
            for i in range(10)
        ]

        start_time = asyncio.get_event_loop().time()

        results = await issue_manager.batch_create_issue_pairs(dual_issues)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        # Verify batch creation completed successfully
        assert len(results) == 10
        successful_pairs = [pair for pair in results if pair[0] is not None]
        assert len(successful_pairs) == 10

        # Should complete efficiently
        assert duration < 3.0  # Should complete within 3 seconds


@pytest.mark.asyncio
class TestDataConsistency:
    """Test data consistency and integrity across components."""

    async def test_issue_relationship_consistency(self, mock_components):
        """Test consistency of parent-child issue relationships."""

        issue_manager = AirtableIssueManager(mock_components["airtable_client"])

        # Mock hierarchical issue data
        mock_tree_response = {
            "records": [
                {
                    "id": "rec_parent_1",
                    "fields": {
                        "Issue_ID": "issue_parent_1",
                        "Label_Lv1": "親の政策課題",
                        "Parent_ID": None,
                        "Confidence": 0.8,
                        "Status": "approved",
                    },
                },
                {
                    "id": "rec_child_1",
                    "fields": {
                        "Issue_ID": "issue_child_1",
                        "Label_Lv2": "子の政策課題",
                        "Parent_ID": "rec_parent_1",
                        "Confidence": 0.7,
                        "Status": "approved",
                    },
                },
            ]
        }

        mock_components["airtable_client"]._rate_limited_request.return_value = (
            mock_tree_response
        )

        # Get issue tree
        tree = await issue_manager.get_issue_tree("approved")

        # Verify tree structure consistency
        assert len(tree) == 1  # One parent
        assert "rec_parent_1" in tree

        parent_data = tree["rec_parent_1"]
        assert parent_data["label_lv1"] == "親の政策課題"
        assert len(parent_data["children"]) == 1

        child_data = parent_data["children"][0]
        assert child_data["label_lv2"] == "子の政策課題"

    async def test_version_history_integrity(self, mock_components):
        """Test version history integrity and consistency."""

        versioning_service = IssueVersioningService()

        # Create multiple versions
        from services.airtable_issue_manager import AirtableIssueRecord

        records = [
            AirtableIssueRecord(
                issue_id="issue_001",
                label_lv1=f"バージョン{i}の政策課題",
                label_lv2=f"バージョン{i}の詳細課題",
                confidence=0.8 + i * 0.1,
                status="pending",
            )
            for i in range(3)
        ]

        # Create version chain
        initial_version = await versioning_service.create_initial_version(records[0])

        from services.issue_versioning_service import VersionChangeType

        previous_version = initial_version
        for i, record in enumerate(records[1:], 1):
            new_version, _ = await versioning_service.create_new_version(
                "issue_001",
                record,
                VersionChangeType.CONTENT_UPDATE,
                f"Update {i}",
                "system",
            )

            # Verify version linking
            assert new_version.previous_version_id == previous_version.version_id
            assert previous_version.next_version_id == new_version.version_id

            previous_version = new_version

        # Verify complete history
        history = await versioning_service.get_version_history("issue_001")
        assert len(history) == 3

        # Verify version sequence
        for i, version in enumerate(history):
            assert version.version_number == i + 1
            if i > 0:
                assert version.previous_version_id == history[i - 1].version_id


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run integration tests with: python -m pytest test_integration_workflow.py -v
    pytest.main([__file__, "-v"])
