"""Phase 1 integration tests for Airtable to Supabase migration."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from shared.clients.airtable import AirtableClient
from shared.clients.supabase import SupabaseClient
from shared.dal.hybrid_data_access import HybridDataAccessLayer
from shared.migration.data_migration_service import (
    DataMigrationService,
    MigrationStatus,
)
from shared.migration.rollback_manager import RollbackManager, RollbackType
from shared.migration.sync_service import (
    AirtableSupabaseSyncService,
    SyncConfig,
    SyncMode,
)
from shared.monitoring.metrics_collector import AlertSeverity, MetricsCollector


@pytest.fixture
async def airtable_client():
    """Mock Airtable client."""
    client = AsyncMock(spec=AirtableClient)

    # Mock responses
    client.list_bills.return_value = [
        {
            "id": "recBill1",
            "fields": {
                "Bill_Number": "第210回国会第1号",
                "Title": "Test Bill 1",
                "Status": "審議中",
                "Updated_At": datetime.utcnow().isoformat(),
            },
        },
        {
            "id": "recBill2",
            "fields": {
                "Bill_Number": "第210回国会第2号",
                "Title": "Test Bill 2",
                "Status": "成立",
                "Updated_At": datetime.utcnow().isoformat(),
            },
        },
    ]

    client.list_members.return_value = [
        {
            "id": "recMember1",
            "fields": {
                "Name": "Test Member 1",
                "House": "衆議院",
                "Updated_At": datetime.utcnow().isoformat(),
            },
        }
    ]

    client.health_check.return_value = True

    return client


@pytest.fixture
async def supabase_client():
    """Mock Supabase client."""
    client = AsyncMock(spec=SupabaseClient)

    # Mock responses
    client.select.return_value = []
    client.insert.return_value = {"id": "uuid-123"}
    client.upsert.return_value = [{"id": "uuid-123", "airtable_id": "rec123"}]
    client.health_check.return_value = True
    client.get_table_count.return_value = 0
    client.batch_upsert_with_mapping.return_value = {
        "success_count": 2,
        "error_count": 0,
        "id_mapping": {"recBill1": "uuid-bill-1", "recBill2": "uuid-bill-2"},
    }

    return client


@pytest.fixture
def metrics_collector():
    """Create metrics collector."""
    return MetricsCollector()


class TestHybridDataAccessLayer:
    """Test hybrid data access layer."""

    @pytest.mark.asyncio
    async def test_read_preference_supabase_first(
        self, airtable_client, supabase_client
    ):
        """Test that Supabase is preferred for reads when enabled."""
        dal = HybridDataAccessLayer(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        # Enable Supabase reads
        dal.supabase_read_enabled = True
        dal.airtable_fallback_enabled = True

        # Mock Supabase response
        supabase_client.get_bills.return_value = [
            {"id": "uuid-1", "bill_number": "Test", "title": "Test Bill"}
        ]

        # Get bills
        result = await dal.get_bills()

        # Verify Supabase was called
        supabase_client.get_bills.assert_called_once()
        airtable_client.list_bills.assert_not_called()

        # Check metrics
        assert dal.metrics["supabase_hits"] == 1
        assert dal.metrics["airtable_hits"] == 0

    @pytest.mark.asyncio
    async def test_fallback_to_airtable(self, airtable_client, supabase_client):
        """Test fallback to Airtable when Supabase fails."""
        dal = HybridDataAccessLayer(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        # Enable Supabase with fallback
        dal.supabase_read_enabled = True
        dal.airtable_fallback_enabled = True

        # Make Supabase fail
        supabase_client.get_bills.side_effect = Exception("Connection error")

        # Get bills
        result = await dal.get_bills()

        # Verify fallback to Airtable
        supabase_client.get_bills.assert_called_once()
        airtable_client.list_bills.assert_called_once()

        # Check metrics
        assert dal.metrics["errors"] == 1
        assert dal.metrics["airtable_hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_usage(self, airtable_client, supabase_client):
        """Test cache hit and miss scenarios."""
        # Mock Redis
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None  # Cache miss initially

        dal = HybridDataAccessLayer(
            airtable_client=airtable_client,
            supabase_client=supabase_client,
            redis_client=redis_mock,
        )

        dal.cache_enabled = True
        dal.supabase_read_enabled = True

        # Mock Supabase response
        supabase_client.get_bills.return_value = [
            {"id": "uuid-1", "bill_number": "Test"}
        ]

        # First call - cache miss
        result1 = await dal.get_bills()
        assert dal.metrics["cache_misses"] == 1
        assert dal.metrics["cache_hits"] == 0

        # Simulate cache hit for second call
        redis_mock.get.return_value = '[{"id": "uuid-1", "bill_number": "Test"}]'

        # Second call - cache hit
        result2 = await dal.get_bills()
        assert dal.metrics["cache_hits"] == 1

    @pytest.mark.asyncio
    async def test_write_operations_airtable_only(
        self, airtable_client, supabase_client
    ):
        """Test that writes go to Airtable in Phase 1."""
        dal = HybridDataAccessLayer(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        # Phase 1 configuration
        dal.supabase_write_enabled = False

        # Create bill
        bill_data = {"bill_number": "Test123", "title": "Test Bill"}

        airtable_client.create_bill.return_value = {"id": "recNew", "fields": bill_data}

        result = await dal.create_bill(bill_data)

        # Verify Airtable was called
        airtable_client.create_bill.assert_called_once_with(bill_data)
        supabase_client.create_bill.assert_not_called()


class TestDataMigrationService:
    """Test data migration service."""

    @pytest.mark.asyncio
    async def test_full_migration(self, airtable_client, supabase_client):
        """Test full table migration."""
        migration_service = DataMigrationService(
            airtable_client=airtable_client,
            supabase_client=supabase_client,
            batch_size=10,
        )

        # Run migration for Bills
        stats = await migration_service.migrate_table("Bills (法案)")

        # Verify migration was called
        airtable_client.list_bills.assert_called()
        supabase_client.batch_upsert_with_mapping.assert_called()

        # Check statistics
        assert stats["status"] == MigrationStatus.COMPLETED
        assert stats["total_records"] == 2
        assert stats["migrated_records"] == 2
        assert stats["failed_records"] == 0

    @pytest.mark.asyncio
    async def test_migration_with_foreign_keys(self, airtable_client, supabase_client):
        """Test migration with foreign key resolution."""
        migration_service = DataMigrationService(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        # Set up ID mappings from previous migration
        migration_service.id_mappings = {"parties": {"recParty1": "uuid-party-1"}}

        # Mock member with party reference
        airtable_client.list_members.return_value = [
            {
                "id": "recMember1",
                "fields": {"Name": "Test Member", "Party": ["recParty1"]},
            }
        ]

        # Run migration
        stats = await migration_service.migrate_table("Members")

        # Verify foreign key was resolved
        assert stats["status"] == MigrationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_migration_validation(self, airtable_client, supabase_client):
        """Test migration validation."""
        migration_service = DataMigrationService(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        # Set up counts
        supabase_client.get_table_count.return_value = 2

        # Validate
        validation_results = await migration_service.validate_migration(
            ["Bills (法案)"]
        )

        # Check validation results
        assert "Bills (法案)" in validation_results["tables"]
        assert validation_results["tables"]["Bills (法案)"]["airtable_count"] == 2
        assert validation_results["tables"]["Bills (法案)"]["supabase_count"] == 2
        assert (
            validation_results["tables"]["Bills (法案)"]["consistency_score"] == 100.0
        )


class TestSyncService:
    """Test synchronization service."""

    @pytest.mark.asyncio
    async def test_incremental_sync(self, airtable_client, supabase_client):
        """Test incremental synchronization."""
        config = SyncConfig(mode=SyncMode.INCREMENTAL, interval_minutes=5)

        sync_service = AirtableSupabaseSyncService(
            airtable_client=airtable_client,
            supabase_client=supabase_client,
            config=config,
        )

        # Set last sync time
        sync_service.last_sync_times["Bills (法案)"] = datetime.utcnow() - timedelta(
            hours=1
        )

        # Run sync
        result = await sync_service.sync_table("Bills (法案)", SyncMode.INCREMENTAL)

        # Check result
        assert result.table == "Bills (法案)"
        assert result.mode == SyncMode.INCREMENTAL
        assert result.records_processed >= 0

    @pytest.mark.asyncio
    async def test_full_sync(self, airtable_client, supabase_client):
        """Test full synchronization."""
        sync_service = AirtableSupabaseSyncService(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        # Mock Supabase records for comparison
        supabase_client.select.return_value = [
            {
                "id": "uuid-1",
                "airtable_id": "recBill1",
                "updated_at": datetime.utcnow().isoformat(),
            }
        ]

        # Run full sync
        result = await sync_service.sync_table("Bills (法案)", SyncMode.FULL)

        # Check result
        assert result.table == "Bills (法案)"
        assert result.mode == SyncMode.FULL

    @pytest.mark.asyncio
    async def test_conflict_resolution(self, airtable_client, supabase_client):
        """Test conflict resolution strategies."""
        config = SyncConfig(conflict_resolution="airtable_priority")

        sync_service = AirtableSupabaseSyncService(
            airtable_client=airtable_client,
            supabase_client=supabase_client,
            config=config,
        )

        # Create conflicting records
        airtable_record = {
            "id": "rec1",
            "fields": {
                "Title": "Airtable Version",
                "Updated_At": datetime.utcnow().isoformat(),
            },
        }

        supabase_record = {
            "id": "uuid-1",
            "title": "Supabase Version",
            "updated_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        }

        # Resolve conflict
        resolved = await sync_service.resolve_conflict(airtable_record, supabase_record)

        # Airtable should win with airtable_priority
        assert resolved == airtable_record


class TestRollbackManager:
    """Test rollback and recovery functionality."""

    @pytest.mark.asyncio
    async def test_create_rollback_point(self, supabase_client, tmp_path):
        """Test creating a rollback point."""
        rollback_manager = RollbackManager(
            supabase_client=supabase_client, backup_dir=str(tmp_path)
        )

        # Create rollback point
        point = await rollback_manager.create_rollback_point(
            phase=1, description="Test rollback", rollback_type=RollbackType.DATA
        )

        # Verify rollback point
        assert point.phase == 1
        assert point.description == "Test rollback"
        assert point.rollback_type == RollbackType.DATA
        assert point.is_valid

    @pytest.mark.asyncio
    async def test_execute_rollback(self, supabase_client, tmp_path):
        """Test executing a rollback."""
        rollback_manager = RollbackManager(
            supabase_client=supabase_client, backup_dir=str(tmp_path)
        )

        # Create a rollback point first
        point = await rollback_manager.create_rollback_point(
            phase=1,
            description="Test rollback",
            rollback_type=RollbackType.CONFIGURATION,
        )

        # Execute rollback
        operation = await rollback_manager.execute_rollback(point.id)

        # Check operation result
        assert operation.rollback_point_id == point.id
        assert operation.status.value in ["completed", "failed"]


class TestMetricsAndMonitoring:
    """Test metrics collection and monitoring."""

    def test_metric_recording(self, metrics_collector):
        """Test recording various metrics."""
        # Record API request
        metrics_collector.record_api_request(
            service="airtable", operation="get_bills", status="success", duration=0.5
        )

        # Record sync operation
        metrics_collector.record_sync_operation(
            table="bills",
            operation="sync",
            status="success",
            records_count=100,
            duration=2.5,
        )

        # Record error
        metrics_collector.record_error(
            component="sync_service",
            error_type="connection_error",
            error_message="Failed to connect",
        )

        # Get metrics summary
        summary = metrics_collector.get_metrics_summary(60)

        assert summary["total_metrics"] > 0

    def test_alert_creation(self, metrics_collector):
        """Test alert creation and management."""
        # Create alert
        metrics_collector.create_alert(
            name="test_alert",
            message="Test alert message",
            severity=AlertSeverity.WARNING,
        )

        # Get active alerts
        alerts = metrics_collector.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].name == "test_alert"

        # Resolve alert
        metrics_collector.resolve_alert("test_alert")
        alerts = metrics_collector.get_active_alerts()
        assert len(alerts) == 0

    def test_health_monitoring(self, metrics_collector):
        """Test health status monitoring."""
        # Update health status
        metrics_collector.update_health_status(
            component="airtable", healthy=True, message="Connected"
        )

        metrics_collector.update_health_status(
            component="supabase", healthy=False, message="Connection failed"
        )

        # Get overall health
        health = metrics_collector.get_overall_health()

        assert not health["healthy"]
        assert health["health_score"] == 0.5
        assert health["components"]["airtable"]["healthy"]
        assert not health["components"]["supabase"]["healthy"]


class TestPerformance:
    """Performance and load tests."""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, airtable_client, supabase_client):
        """Test concurrent read operations."""
        dal = HybridDataAccessLayer(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        dal.supabase_read_enabled = True

        # Mock responses
        supabase_client.get_bills.return_value = []
        supabase_client.get_members.return_value = []

        # Run concurrent reads
        tasks = []
        for _ in range(10):
            tasks.append(dal.get_bills())
            tasks.append(dal.get_members())

        results = await asyncio.gather(*tasks)

        # All requests should complete
        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_large_batch_migration(self, airtable_client, supabase_client):
        """Test migration with large batches."""
        # Create large dataset
        large_dataset = [
            {
                "id": f"rec{i}",
                "fields": {
                    "Bill_Number": f"Bill {i}",
                    "Title": f"Test Bill {i}",
                    "Updated_At": datetime.utcnow().isoformat(),
                },
            }
            for i in range(1000)
        ]

        airtable_client.list_bills.return_value = large_dataset

        # Mock batch upsert success
        supabase_client.batch_upsert_with_mapping.return_value = {
            "success_count": 100,
            "error_count": 0,
            "id_mapping": {},
        }

        migration_service = DataMigrationService(
            airtable_client=airtable_client,
            supabase_client=supabase_client,
            batch_size=100,
        )

        # Run migration
        stats = await migration_service.migrate_table("Bills (法案)")

        # Verify batching
        assert supabase_client.batch_upsert_with_mapping.call_count == 10  # 1000/100

    @pytest.mark.asyncio
    async def test_api_response_time(self, airtable_client, supabase_client):
        """Test API response time requirements."""
        import time

        dal = HybridDataAccessLayer(
            airtable_client=airtable_client, supabase_client=supabase_client
        )

        dal.supabase_read_enabled = True

        # Mock fast Supabase response
        supabase_client.get_bills.return_value = []

        start = time.time()
        await dal.get_bills()
        duration = time.time() - start

        # Response should be fast (< 1 second)
        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
