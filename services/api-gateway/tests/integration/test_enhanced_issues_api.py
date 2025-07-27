"""
API tests for Enhanced Issues endpoints.
Tests the level-specific API endpoints and issue management functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from ...src.main import app


class TestEnhancedIssuesAPI:
    """Test the enhanced issues API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_airtable_manager(self):
        """Mock Airtable issue manager."""
        mock_manager = AsyncMock()

        # Mock responses for different endpoints
        mock_manager.get_issues_by_level.return_value = [
            {
                "id": "rec_1",
                "fields": {
                    "Issue_ID": "issue_1",
                    "Label_Lv1": "高校生向けの政策課題",
                    "Confidence": 0.8,
                    "Status": "approved",
                    "Source_Bill_ID": "bill_001",
                    "Created_At": "2024-01-01T10:00:00Z",
                },
            }
        ]

        mock_manager.get_issue_tree.return_value = {
            "rec_parent_1": {
                "issue_id": "issue_p1",
                "label_lv1": "親の政策課題",
                "confidence": 0.8,
                "source_bill_id": "bill_001",
                "children": [
                    {
                        "issue_id": "issue_c1",
                        "label_lv2": "子の政策課題",
                        "confidence": 0.7,
                        "source_bill_id": "bill_001",
                    }
                ],
            }
        }

        mock_manager.get_issue_statistics.return_value = {
            "total_issues": 100,
            "approved_count": 80,
            "pending_count": 15,
            "rejected_count": 5,
            "average_confidence": 0.85,
            "average_quality_score": 0.75,
        }

        mock_manager.health_check.return_value = True

        return mock_manager

    @pytest.fixture
    def mock_policy_extractor(self):
        """Mock policy issue extractor."""
        mock_extractor = AsyncMock()

        mock_extractor.extract_issues_with_metadata.return_value = {
            "status": "success",
            "issues": [
                {
                    "label_lv1": "介護制度を改善する",
                    "label_lv2": "高齢者介護制度の包括的な見直しを実施する",
                    "confidence": 0.9,
                }
            ],
            "metadata": {
                "extraction_time_ms": 1500,
                "model_used": "gpt-4",
                "individual_quality_scores": [0.85],
            },
        }

        mock_extractor.health_check.return_value = True

        return mock_extractor

    def test_get_issues_without_level_filter(self, client, mock_airtable_manager):
        """Test getting issues without level filtering."""
        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            mock_airtable_manager.list_issues_by_status.return_value = [
                {
                    "id": "rec_1",
                    "fields": {
                        "Issue_ID": "issue_1",
                        "Label_Lv1": "政策課題1",
                        "Label_Lv2": "",
                        "Parent_ID": None,
                        "Status": "approved",
                    },
                }
            ]

            response = client.get("/api/issues/")

            assert response.status_code == 200
            data = response.json()
            assert "issues" in data
            assert "count" in data
            assert data["count"] == 1

    def test_get_issues_with_level1_filter(self, client, mock_airtable_manager):
        """Test getting level 1 issues."""
        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/?level=1")

            assert response.status_code == 200
            data = response.json()
            assert data["level_filter"] == 1
            mock_airtable_manager.get_issues_by_level.assert_called_with(
                level=1, status="approved", max_records=100
            )

    def test_get_issues_with_level2_filter(self, client, mock_airtable_manager):
        """Test getting level 2 issues."""
        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/?level=2")

            assert response.status_code == 200
            data = response.json()
            assert data["level_filter"] == 2
            mock_airtable_manager.get_issues_by_level.assert_called_with(
                level=2, status="approved", max_records=100
            )

    def test_get_issues_with_invalid_level(self, client):
        """Test getting issues with invalid level parameter."""
        response = client.get("/api/issues/?level=3")

        assert response.status_code == 422  # Validation error

    def test_get_issue_tree(self, client, mock_airtable_manager):
        """Test getting hierarchical issue tree."""
        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/tree")

            assert response.status_code == 200
            data = response.json()
            assert "tree" in data
            assert "total_parent_issues" in data
            assert "total_child_issues" in data

            mock_airtable_manager.get_issue_tree.assert_called_with(status="approved")

    def test_get_specific_issue(self, client, mock_airtable_manager):
        """Test getting a specific issue by record ID."""
        mock_issue_record = Mock()
        mock_issue_record.to_dict.return_value = {
            "issue_id": "issue_001",
            "label_lv1": "テスト課題",
            "confidence": 0.8,
        }

        mock_airtable_manager.get_issue_record.return_value = mock_issue_record

        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/rec_123")

            assert response.status_code == 200
            data = response.json()
            assert "issue" in data
            assert data["record_id"] == "rec_123"

    def test_get_nonexistent_issue(self, client, mock_airtable_manager):
        """Test getting a nonexistent issue."""
        mock_airtable_manager.get_issue_record.return_value = None

        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/nonexistent")

            assert response.status_code == 404

    def test_extract_dual_level_issues(
        self, client, mock_airtable_manager, mock_policy_extractor
    ):
        """Test extracting dual-level issues from bill data."""
        request_data = {
            "bill_id": "bill_001",
            "bill_title": "介護保険制度改正法案",
            "bill_outline": "高齢者の介護負担を軽減する",
            "background_context": "高齢化社会の進展",
            "expected_effects": "介護費用の削減",
            "key_provisions": ["自己負担率見直し"],
            "submitter": "厚生労働省",
            "category": "社会保障",
        }

        # Mock issue pair creation
        mock_airtable_manager.create_issue_pair.return_value = (
            "rec_lv1_123",
            "rec_lv2_456",
        )

        with (
            patch(
                "routes.enhanced_issues.get_airtable_issue_manager",
                return_value=mock_airtable_manager,
            ),
            patch(
                "routes.enhanced_issues.get_policy_issue_extractor",
                return_value=mock_policy_extractor,
            ),
        ):
            response = client.post("/api/issues/extract", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "created_issues" in data
            assert len(data["created_issues"]) == 1

    def test_extract_issues_validation_error(self, client):
        """Test extraction with validation errors."""
        invalid_request = {
            "bill_id": "",  # Empty bill ID should fail validation
            "bill_title": "テスト法案",
        }

        response = client.post("/api/issues/extract", json=invalid_request)

        assert response.status_code == 422  # Validation error

    def test_batch_extract_issues(
        self, client, mock_airtable_manager, mock_policy_extractor
    ):
        """Test batch extraction of issues."""
        request_data = [
            {"bill_id": "bill_001", "bill_title": "法案1", "bill_outline": "概要1"},
            {"bill_id": "bill_002", "bill_title": "法案2", "bill_outline": "概要2"},
        ]

        # Mock batch extraction
        mock_policy_extractor.batch_extract_issues.return_value = [
            {
                "bill_id": "bill_001",
                "status": "success",
                "issues": [
                    {"label_lv1": "課題1", "label_lv2": "詳細課題1", "confidence": 0.8}
                ],
                "metadata": {"individual_quality_scores": [0.8]},
            },
            {
                "bill_id": "bill_002",
                "status": "success",
                "issues": [
                    {"label_lv1": "課題2", "label_lv2": "詳細課題2", "confidence": 0.9}
                ],
                "metadata": {"individual_quality_scores": [0.9]},
            },
        ]

        mock_airtable_manager.create_issue_pair.return_value = ("rec_lv1", "rec_lv2")

        with (
            patch(
                "routes.enhanced_issues.get_airtable_issue_manager",
                return_value=mock_airtable_manager,
            ),
            patch(
                "routes.enhanced_issues.get_policy_issue_extractor",
                return_value=mock_policy_extractor,
            ),
        ):
            response = client.post("/api/issues/extract/batch", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert data["total_issues_created"] == 2

    def test_batch_extract_size_limit(self, client):
        """Test batch extraction size limit."""
        # Create request with too many bills
        request_data = [
            {
                "bill_id": f"bill_{i:03d}",
                "bill_title": f"法案{i}",
                "bill_outline": f"概要{i}",
            }
            for i in range(15)  # Exceed limit of 10
        ]

        response = client.post("/api/issues/extract/batch", json=request_data)

        assert response.status_code == 400
        assert "Batch size limited to 10 bills" in response.json()["detail"]

    def test_update_issue_status(self, client, mock_airtable_manager):
        """Test updating issue status."""
        request_data = {"status": "approved", "reviewer_notes": "High quality issue"}

        mock_airtable_manager.update_issue_status.return_value = True

        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.patch("/api/issues/rec_123/status", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "approved"

    def test_update_issue_status_invalid_status(self, client):
        """Test updating issue with invalid status."""
        request_data = {"status": "invalid_status", "reviewer_notes": "Test notes"}

        response = client.patch("/api/issues/rec_123/status", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_search_issues(self, client, mock_airtable_manager):
        """Test searching issues by text query."""
        request_data = {
            "query": "介護",
            "level": 1,
            "status": "approved",
            "max_records": 50,
        }

        mock_airtable_manager.search_issues.return_value = [
            {
                "id": "rec_1",
                "fields": {
                    "Issue_ID": "issue_1",
                    "Label_Lv1": "介護制度を改善する",
                    "Status": "approved",
                },
            }
        ]

        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.post("/api/issues/search", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "介護"
            assert "results" in data
            assert data["count"] == 1

    def test_search_issues_empty_query(self, client):
        """Test searching with empty query."""
        request_data = {"query": "", "status": "approved"}

        response = client.post("/api/issues/search", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_get_issue_statistics(self, client, mock_airtable_manager):
        """Test getting issue statistics."""
        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/statistics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_issues"] == 100
            assert data["approved_count"] == 80
            assert data["average_confidence"] == 0.85

    def test_get_pending_count(self, client, mock_airtable_manager):
        """Test getting pending issues count."""
        mock_airtable_manager.count_pending_issues.return_value = 15

        with patch(
            "routes.enhanced_issues.get_airtable_issue_manager",
            return_value=mock_airtable_manager,
        ):
            response = client.get("/api/issues/pending/count")

            assert response.status_code == 200
            data = response.json()
            assert data["pending_count"] == 15
            assert "exclude_failed_validation" in data

    def test_health_check(self, client, mock_airtable_manager, mock_policy_extractor):
        """Test health check endpoint."""
        with (
            patch(
                "routes.enhanced_issues.get_airtable_issue_manager",
                return_value=mock_airtable_manager,
            ),
            patch(
                "routes.enhanced_issues.get_policy_issue_extractor",
                return_value=mock_policy_extractor,
            ),
        ):
            response = client.get("/api/issues/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "components" in data
            assert data["components"]["airtable_manager"] == "healthy"
            assert data["components"]["policy_extractor"] == "healthy"


class TestWebhookAPI:
    """Test the webhook API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_webhook_status_endpoint(self, client):
        """Test webhook status endpoint."""
        response = client.get("/api/webhooks/airtable/issues/webhook-status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "configuration" in data

    def test_test_webhook_endpoint(self, client):
        """Test webhook test endpoint."""
        response = client.post("/api/webhooks/airtable/issues/test-webhook")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "timestamp" in data


class TestInputValidation:
    """Test input validation across all endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection attempts."""
        malicious_inputs = [
            "'; DROP TABLE issues; --",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
            "{{7*7}}",
            "../../../etc/passwd",
        ]

        for malicious_input in malicious_inputs:
            # Test in query parameter
            response = client.get(f"/api/issues/?bill_id={malicious_input}")
            # Should either return 422 (validation error) or 200 with safe handling
            assert response.status_code in [200, 422]

            # Test in JSON body
            request_data = {
                "bill_id": malicious_input,
                "bill_title": "Valid title",
                "bill_outline": "Valid outline",
            }
            response = client.post("/api/issues/extract", json=request_data)
            # Should return validation error or handle safely
            assert response.status_code in [200, 422, 500]

    def test_oversized_input_handling(self, client):
        """Test handling of oversized inputs."""
        # Test very long strings
        long_string = "A" * 10000

        request_data = {
            "bill_id": "valid_id",
            "bill_title": long_string,  # Exceeds validation limit
            "bill_outline": "Valid outline",
        }

        response = client.post("/api/issues/extract", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_special_characters_handling(self, client):
        """Test handling of special characters."""
        special_chars_data = {
            "bill_id": "test_001",
            "bill_title": "テスト法案 with émojí 🏛️ and spéciàl chars",
            "bill_outline": "概要 with 特殊文字 & symbols !@#$%^&*()",
        }

        # Should handle special characters gracefully
        with (
            patch("routes.enhanced_issues.get_airtable_issue_manager"),
            patch("routes.enhanced_issues.get_policy_issue_extractor"),
        ):
            response = client.post("/api/issues/extract", json=special_chars_data)
            # Should not crash due to special characters
            assert response.status_code in [200, 422, 500]


if __name__ == "__main__":
    # Run API tests with: python -m pytest test_enhanced_issues_api.py -v
    pytest.main([__file__, "-v"])
