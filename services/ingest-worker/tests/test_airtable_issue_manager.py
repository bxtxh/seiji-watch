"""
Unit tests for Airtable Issue Manager.
Tests hierarchical issue management, status updates, and batch operations.
"""

import asyncio
import os

# Import the components to test
import sys
import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.airtable_issue_manager import AirtableIssueManager, AirtableIssueRecord
from services.policy_issue_extractor import DualLevelIssue


class TestAirtableIssueRecord:
    """Test the AirtableIssueRecord dataclass."""

    def test_valid_issue_record(self):
        """Test creating a valid issue record."""
        record = AirtableIssueRecord(
            issue_id="test_issue_001",
            label_lv1="高校生向けの課題を説明する",
            label_lv2="一般読者向けの課題を詳しく説明する",
            confidence=0.85,
            source_bill_id="bill_001"
        )

        assert record.issue_id == "test_issue_001"
        assert record.label_lv1 == "高校生向けの課題を説明する"
        assert record.confidence == 0.85
        assert record.status == "pending"  # Default value
        assert record.valid_from == date.today()  # Default value

    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        record = AirtableIssueRecord(
            issue_id="test_issue_001",
            label_lv1="テスト課題",
            label_lv2="詳細なテスト課題",
            confidence=0.9,
            source_bill_id="bill_001"
        )

        result_dict = record.to_dict()

        assert result_dict["issue_id"] == "test_issue_001"
        assert result_dict["label_lv1"] == "テスト課題"
        assert result_dict["confidence"] == 0.9
        assert "created_at" in result_dict
        assert "valid_from" in result_dict


class TestAirtableIssueManager:
    """Test the main AirtableIssueManager class."""

    @pytest.fixture
    def mock_airtable_client(self):
        """Create a mock Airtable client."""
        mock_client = AsyncMock()
        mock_client.base_url = "https://api.airtable.com/v0/test_base"
        return mock_client

    @pytest.fixture
    def issue_manager(self, mock_airtable_client):
        """Create an AirtableIssueManager instance with mock client."""
        manager = AirtableIssueManager(mock_airtable_client)
        return manager

    @pytest.fixture
    def sample_dual_issue(self):
        """Create a sample dual-level issue."""
        return DualLevelIssue(
            label_lv1="介護制度を改善する",
            label_lv2="高齢者介護保険制度の包括的な見直しを実施する",
            confidence=0.85
        )

    def test_manager_initialization(self, issue_manager):
        """Test manager initialization."""
        assert issue_manager.table_name == "Issues"
        assert issue_manager.batch_size == 10
        assert issue_manager.batch_delay == 0.3

    async def test_create_issue_pair_success(self, issue_manager, sample_dual_issue, mock_airtable_client):
        """Test successful creation of issue pair."""
        # Mock Airtable responses
        lv1_response = {"id": "rec_lv1_123", "fields": {}}
        lv2_response = {"id": "rec_lv2_456", "fields": {}}

        mock_airtable_client._rate_limited_request.side_effect = [lv1_response, lv2_response]

        lv1_id, lv2_id = await issue_manager.create_issue_pair(
            sample_dual_issue, "bill_001", 0.8
        )

        assert lv1_id == "rec_lv1_123"
        assert lv2_id == "rec_lv2_456"
        assert mock_airtable_client._rate_limited_request.call_count == 2

        # Verify the calls were made with correct data
        calls = mock_airtable_client._rate_limited_request.call_args_list

        # Check lv1 record creation
        lv1_call = calls[0]
        lv1_data = lv1_call[1]["json"]["fields"]
        assert lv1_data["Label_Lv1"] == sample_dual_issue.label_lv1
        assert lv1_data["Label_Lv2"] == ""  # Empty for lv1 record
        assert lv1_data["Parent_ID"] is None

        # Check lv2 record creation
        lv2_call = calls[1]
        lv2_data = lv2_call[1]["json"]["fields"]
        assert lv2_data["Label_Lv1"] == ""  # Empty for lv2 record
        assert lv2_data["Label_Lv2"] == sample_dual_issue.label_lv2
        assert lv2_data["Parent_ID"] == "rec_lv1_123"

    async def test_create_issue_pair_failure(self, issue_manager, sample_dual_issue, mock_airtable_client):
        """Test handling of issue pair creation failure."""
        mock_airtable_client._rate_limited_request.side_effect = Exception("Airtable API Error")

        with pytest.raises(Exception, match="Airtable API Error"):
            await issue_manager.create_issue_pair(sample_dual_issue, "bill_001", 0.8)

    async def test_create_unclassified_issue_pair(self, issue_manager, mock_airtable_client):
        """Test creation of unclassified issue pair."""
        lv1_response = {"id": "rec_unclass_1", "fields": {}}
        lv2_response = {"id": "rec_unclass_2", "fields": {}}

        mock_airtable_client._rate_limited_request.side_effect = [lv1_response, lv2_response]

        lv1_id, lv2_id = await issue_manager.create_unclassified_issue_pair("bill_001")

        assert lv1_id == "rec_unclass_1"
        assert lv2_id == "rec_unclass_2"

        # Verify unclassified labels were used
        calls = mock_airtable_client._rate_limited_request.call_args_list
        lv1_data = calls[0][1]["json"]["fields"]
        assert lv1_data["Label_Lv1"] == "未分類の課題を扱う"

    async def test_get_issue_record_success(self, issue_manager, mock_airtable_client):
        """Test successful retrieval of issue record."""
        mock_response = {
            "id": "rec_123",
            "fields": {
                "Issue_ID": "issue_001",
                "Label_Lv1": "テスト課題",
                "Label_Lv2": "",
                "Confidence": 0.8,
                "Status": "approved",
                "Source_Bill_ID": "bill_001",
                "Created_At": datetime.now().isoformat(),
                "Updated_At": datetime.now().isoformat()
            }
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        record = await issue_manager.get_issue_record("rec_123")

        assert record is not None
        assert record.issue_id == "issue_001"
        assert record.label_lv1 == "テスト課題"
        assert record.confidence == 0.8
        assert record.status == "approved"

    async def test_get_issue_record_not_found(self, issue_manager, mock_airtable_client):
        """Test handling when issue record is not found."""
        mock_airtable_client._rate_limited_request.side_effect = Exception("Record not found")

        record = await issue_manager.get_issue_record("nonexistent")

        assert record is None

    async def test_update_issue_status_success(self, issue_manager, mock_airtable_client):
        """Test successful status update."""
        mock_airtable_client._rate_limited_request.return_value = {"id": "rec_123"}

        success = await issue_manager.update_issue_status(
            "rec_123", "approved", "Good quality issue"
        )

        assert success is True

        # Verify the update call
        call_args = mock_airtable_client._rate_limited_request.call_args
        update_data = call_args[1]["json"]["fields"]
        assert update_data["Status"] == "approved"
        assert update_data["Reviewer_Notes"] == "Good quality issue"
        assert "Updated_At" in update_data

    async def test_update_issue_status_failure(self, issue_manager, mock_airtable_client):
        """Test handling of status update failure."""
        mock_airtable_client._rate_limited_request.side_effect = Exception("Update failed")

        success = await issue_manager.update_issue_status("rec_123", "approved")

        assert success is False

    async def test_list_issues_by_status(self, issue_manager, mock_airtable_client):
        """Test listing issues by status."""
        mock_response = {
            "records": [
                {"id": "rec_1", "fields": {"Status": "pending"}},
                {"id": "rec_2", "fields": {"Status": "pending"}}
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        issues = await issue_manager.list_issues_by_status("pending", 100)

        assert len(issues) == 2
        assert all(issue["fields"]["Status"] == "pending" for issue in issues)

        # Verify the filter formula was used
        call_args = mock_airtable_client._rate_limited_request.call_args
        params = call_args[1]["params"]
        assert "filterByFormula" in params
        assert "pending" in params["filterByFormula"]

    async def test_count_pending_issues(self, issue_manager, mock_airtable_client):
        """Test counting pending issues."""
        mock_response = {
            "records": [
                {"id": "rec_1", "fields": {"Status": "pending"}},
                {"id": "rec_2", "fields": {"Status": "pending"}},
                {"id": "rec_3", "fields": {"Status": "pending"}}
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        count = await issue_manager.count_pending_issues()

        assert count == 3

    async def test_get_issues_by_level(self, issue_manager, mock_airtable_client):
        """Test getting issues filtered by level."""
        mock_response = {
            "records": [
                {"id": "rec_1", "fields": {"Parent_ID": None}},  # Level 1
                {"id": "rec_2", "fields": {"Parent_ID": None}}   # Level 1
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        # Test level 1 filtering
        issues = await issue_manager.get_issues_by_level(1, "approved", 100)

        assert len(issues) == 2

        # Verify the filter formula
        call_args = mock_airtable_client._rate_limited_request.call_args
        params = call_args[1]["params"]
        filter_formula = params["filterByFormula"]
        assert "Parent_ID" in filter_formula
        assert "BLANK()" in filter_formula

    async def test_get_issue_tree(self, issue_manager, mock_airtable_client):
        """Test getting hierarchical issue tree."""
        mock_response = {
            "records": [
                {
                    "id": "rec_parent_1",
                    "fields": {
                        "Issue_ID": "issue_p1",
                        "Label_Lv1": "親課題1",
                        "Parent_ID": None,
                        "Confidence": 0.8,
                        "Source_Bill_ID": "bill_001"
                    }
                },
                {
                    "id": "rec_child_1",
                    "fields": {
                        "Issue_ID": "issue_c1",
                        "Label_Lv2": "子課題1",
                        "Parent_ID": "rec_parent_1",
                        "Confidence": 0.7,
                        "Source_Bill_ID": "bill_001"
                    }
                }
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        tree = await issue_manager.get_issue_tree("approved")

        assert len(tree) == 1  # One parent
        assert "rec_parent_1" in tree

        parent_data = tree["rec_parent_1"]
        assert parent_data["label_lv1"] == "親課題1"
        assert len(parent_data["children"]) == 1

        child_data = parent_data["children"][0]
        assert child_data["label_lv2"] == "子課題1"

    async def test_get_issues_by_bill(self, issue_manager, mock_airtable_client):
        """Test getting issues by bill ID."""
        mock_response = {
            "records": [
                {"id": "rec_1", "fields": {"Source_Bill_ID": "bill_001"}},
                {"id": "rec_2", "fields": {"Source_Bill_ID": "bill_001"}}
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        issues = await issue_manager.get_issues_by_bill("bill_001", "approved")

        assert len(issues) == 2

        # Verify filter formula
        call_args = mock_airtable_client._rate_limited_request.call_args
        params = call_args[1]["params"]
        filter_formula = params["filterByFormula"]
        assert "bill_001" in filter_formula

    async def test_invalidate_issues(self, issue_manager, mock_airtable_client):
        """Test invalidating issues by setting valid_to date."""
        mock_airtable_client._rate_limited_request.return_value = {"id": "rec_123"}

        success = await issue_manager.invalidate_issues(
            ["rec_1", "rec_2"], "structural_change"
        )

        assert success is True
        assert mock_airtable_client._rate_limited_request.call_count == 2

        # Verify the invalidation data
        calls = mock_airtable_client._rate_limited_request.call_args_list
        for call in calls:
            update_data = call[1]["json"]["fields"]
            assert "Valid_To" in update_data
            assert "structural_change" in update_data["Reviewer_Notes"]

    async def test_batch_create_issue_pairs(self, issue_manager, mock_airtable_client, sample_dual_issue):
        """Test batch creation of issue pairs."""
        # Mock responses for batch creation
        responses = [
            {"id": f"rec_lv1_{i}"} for i in range(4)
        ] + [
            {"id": f"rec_lv2_{i}"} for i in range(4)
        ]

        mock_airtable_client._rate_limited_request.side_effect = responses

        dual_issues = [
            (sample_dual_issue, "bill_001"),
            (sample_dual_issue, "bill_002")
        ]
        quality_scores = [0.8, 0.9]

        results = await issue_manager.batch_create_issue_pairs(dual_issues, quality_scores)

        assert len(results) == 2
        assert all(result[0] is not None for result in results)  # All should succeed
        assert all(result[1] is not None for result in results)

    async def test_get_issue_statistics(self, issue_manager, mock_airtable_client):
        """Test getting comprehensive issue statistics."""
        mock_response = {
            "records": [
                {
                    "id": "rec_1",
                    "fields": {
                        "Status": "approved",
                        "Parent_ID": None,
                        "Confidence": 0.8,
                        "Quality_Score": 0.7,
                        "Source_Bill_ID": "bill_001"
                    }
                },
                {
                    "id": "rec_2",
                    "fields": {
                        "Status": "pending",
                        "Parent_ID": "rec_1",
                        "Confidence": 0.9,
                        "Quality_Score": 0.8,
                        "Source_Bill_ID": "bill_001"
                    }
                }
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        stats = await issue_manager.get_issue_statistics()

        assert stats["total_issues"] == 2
        assert stats["approved_count"] == 1
        assert stats["pending_count"] == 1
        assert stats["by_level"]["lv1"] == 1
        assert stats["by_level"]["lv2"] == 1
        assert stats["average_confidence"] == 0.85  # (0.8 + 0.9) / 2
        assert stats["unique_bills_count"] == 1

    async def test_search_issues(self, issue_manager, mock_airtable_client):
        """Test searching issues by text query."""
        mock_response = {
            "records": [
                {
                    "id": "rec_1",
                    "fields": {
                        "Label_Lv1": "介護制度を改善する",
                        "Status": "approved"
                    }
                }
            ]
        }

        mock_airtable_client._rate_limited_request.return_value = mock_response

        results = await issue_manager.search_issues("介護", None, "approved", 50)

        assert len(results) == 1

        # Verify search filter was applied
        call_args = mock_airtable_client._rate_limited_request.call_args
        params = call_args[1]["params"]
        filter_formula = params["filterByFormula"]
        assert "介護" in filter_formula
        assert "FIND" in filter_formula

    async def test_health_check_success(self, issue_manager, mock_airtable_client):
        """Test successful health check."""
        mock_airtable_client._rate_limited_request.return_value = {"records": []}

        is_healthy = await issue_manager.health_check()

        assert is_healthy is True

    async def test_health_check_failure(self, issue_manager, mock_airtable_client):
        """Test health check failure."""
        mock_airtable_client._rate_limited_request.side_effect = Exception("Connection failed")

        is_healthy = await issue_manager.health_check()

        assert is_healthy is False


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Integration test scenarios combining multiple operations."""

    async def test_complete_issue_lifecycle(self):
        """Test complete issue lifecycle from creation to approval."""
        # This would test the full workflow:
        # 1. Create issue pair
        # 2. Update status to approved
        # 3. Search and retrieve
        # 4. Generate statistics
        pass

    async def test_batch_processing_workflow(self):
        """Test batch processing of multiple issues."""
        # This would test:
        # 1. Batch creation of multiple issue pairs
        # 2. Batch status updates
        # 3. Statistics collection
        pass


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Helper functions
def create_mock_airtable_response(records_data: list):
    """Create a mock Airtable API response."""
    return {
        "records": [
            {
                "id": f"rec_{i}",
                "fields": record_data,
                "createdTime": datetime.now().isoformat()
            }
            for i, record_data in enumerate(records_data)
        ]
    }


def create_test_issue_record(**kwargs):
    """Create a test issue record with defaults."""
    defaults = {
        "issue_id": str(uuid.uuid4()),
        "label_lv1": "テスト課題",
        "label_lv2": "詳細なテスト課題",
        "confidence": 0.8,
        "status": "pending",
        "source_bill_id": "test_bill_001"
    }
    defaults.update(kwargs)
    return AirtableIssueRecord(**defaults)


if __name__ == "__main__":
    # Run tests with: python -m pytest test_airtable_issue_manager.py -v
    pytest.main([__file__, "-v"])
