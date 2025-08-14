"""Synchronization service for ongoing Airtable to Supabase sync."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..clients.airtable import AirtableClient
from ..clients.supabase import SupabaseClient
from .schema_mapper import SchemaMapper

logger = logging.getLogger(__name__)


class SyncMode(Enum):
    """Synchronization mode."""

    INCREMENTAL = "incremental"
    FULL = "full"
    REAL_TIME = "real_time"


class ConflictResolution(Enum):
    """Conflict resolution strategy."""

    AIRTABLE_PRIORITY = "airtable_priority"
    SUPABASE_PRIORITY = "supabase_priority"
    LATEST_WINS = "latest_wins"
    MANUAL = "manual"


@dataclass
class SyncConfig:
    """Configuration for sync service."""

    mode: SyncMode = SyncMode.INCREMENTAL
    interval_minutes: int = 5
    conflict_resolution: ConflictResolution = ConflictResolution.AIRTABLE_PRIORITY
    batch_size: int = 100
    max_retries: int = 3
    tables_to_sync: list[str] = field(default_factory=list)
    enable_bidirectional: bool = False


@dataclass
class ChangeRecord:
    """Represents a data change to be synced."""

    table: str
    record_id: str
    operation: str  # CREATE, UPDATE, DELETE
    data: dict[str, Any]
    timestamp: datetime
    source: str  # airtable or supabase


@dataclass
class SyncResult:
    """Result of a sync operation."""

    table: str
    mode: SyncMode
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    conflicts_resolved: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate sync duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.records_processed == 0:
            return 100.0
        failed = len(self.errors)
        return ((self.records_processed - failed) / self.records_processed) * 100


class AirtableSupabaseSyncService:
    """Service for synchronizing data between Airtable and Supabase."""

    def __init__(
        self,
        airtable_client: AirtableClient | None = None,
        supabase_client: SupabaseClient | None = None,
        config: SyncConfig | None = None,
    ):
        """Initialize sync service.

        Args:
            airtable_client: Airtable client instance
            supabase_client: Supabase client instance
            config: Sync configuration
        """
        self.airtable = airtable_client or AirtableClient()
        self.supabase = supabase_client or SupabaseClient()
        self.mapper = SchemaMapper()

        # Load config from environment or use provided
        self.config = config or self._load_config_from_env()

        # Track sync state
        self.is_running = False
        self.last_sync_times: dict[str, datetime] = {}
        self.sync_task: asyncio.Task | None = None

        # ID mappings cache
        self.id_mappings: dict[str, dict[str, str]] = {}

        # Change detection
        self.change_queue: list[ChangeRecord] = []

    def _load_config_from_env(self) -> SyncConfig:
        """Load sync configuration from environment variables."""
        return SyncConfig(
            mode=SyncMode(os.getenv("SYNC_SERVICE_MODE", "incremental")),
            interval_minutes=int(os.getenv("SYNC_SERVICE_INTERVAL_MINUTES", 5)),
            conflict_resolution=ConflictResolution(
                os.getenv("SYNC_SERVICE_CONFLICT_RESOLUTION", "airtable_priority")
            ),
            batch_size=int(os.getenv("SUPABASE_MIGRATION_BATCH_SIZE", 100)),
            max_retries=int(os.getenv("SUPABASE_MIGRATION_MAX_RETRIES", 3)),
            enable_bidirectional=os.getenv(
                "SYNC_SERVICE_BIDIRECTIONAL", "false"
            ).lower()
            == "true",
        )

    async def start(self):
        """Start the sync service."""
        if self.is_running:
            logger.warning("Sync service is already running")
            return

        self.is_running = True
        logger.info(f"Starting sync service with mode: {self.config.mode}")

        # Initialize Supabase connection pool
        await self.supabase.initialize_db_pool()

        # Load ID mappings
        await self._load_id_mappings()

        # Start sync loop based on mode
        if self.config.mode == SyncMode.REAL_TIME:
            self.sync_task = asyncio.create_task(self._real_time_sync_loop())
        else:
            self.sync_task = asyncio.create_task(self._periodic_sync_loop())

    async def stop(self):
        """Stop the sync service."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping sync service")

        # Cancel sync task
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

        # Close connections
        await self.supabase.close_db_pool()

    async def _periodic_sync_loop(self):
        """Main sync loop for periodic synchronization."""
        while self.is_running:
            try:
                # Determine tables to sync
                tables = self.config.tables_to_sync or self._get_default_tables()

                # Sync each table
                for table in tables:
                    if not self.is_running:
                        break

                    try:
                        result = await self.sync_table(table, self.config.mode)

                        # Log sync result
                        logger.info(
                            f"Synced {table}: {result.records_processed} records, "
                            f"{result.success_rate:.1f}% success rate"
                        )

                        # Record sync status
                        await self._record_sync_status(result)

                    except Exception as e:
                        logger.error(f"Failed to sync {table}: {e}")

                # Wait for next sync interval
                await asyncio.sleep(self.config.interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _real_time_sync_loop(self):
        """Real-time sync loop using change detection."""
        logger.info("Starting real-time sync loop")

        while self.is_running:
            try:
                # Process change queue
                if self.change_queue:
                    changes = self.change_queue[: self.config.batch_size]
                    self.change_queue = self.change_queue[self.config.batch_size :]

                    await self._process_changes(changes)

                # Poll for changes (in production, this would use webhooks)
                await self._poll_for_changes()

                # Short sleep to prevent CPU spinning
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Real-time sync error: {e}")
                await asyncio.sleep(5)

    async def sync_table(
        self, table_name: str, mode: SyncMode = SyncMode.INCREMENTAL
    ) -> SyncResult:
        """Sync a single table.

        Args:
            table_name: Airtable table name
            mode: Sync mode

        Returns:
            Sync result
        """
        result = SyncResult(table=table_name, mode=mode)
        supabase_table = self.mapper.get_supabase_table_name(table_name)

        try:
            if mode == SyncMode.FULL:
                await self._full_sync(table_name, supabase_table, result)
            else:
                await self._incremental_sync(table_name, supabase_table, result)

        except Exception as e:
            logger.error(f"Sync failed for {table_name}: {e}")
            result.errors.append(str(e))

        result.end_time = datetime.utcnow()
        return result

    async def _full_sync(
        self, airtable_table: str, supabase_table: str, result: SyncResult
    ):
        """Perform full table sync."""
        logger.info(f"Starting full sync for {airtable_table}")

        # Fetch all Airtable records
        airtable_records = await self._fetch_all_airtable_records(airtable_table)

        # Fetch all Supabase records
        supabase_records = await self.supabase.select(
            supabase_table, columns="id, airtable_id, updated_at"
        )

        # Create lookup maps
        airtable_map = {r["id"]: r for r in airtable_records}
        supabase_map = {r["airtable_id"]: r for r in supabase_records}

        # Find changes
        to_create = []
        to_update = []
        to_delete = []

        # Check each Airtable record
        for at_id, at_record in airtable_map.items():
            if at_id not in supabase_map:
                # Record doesn't exist in Supabase
                to_create.append(at_record)
            else:
                # Check if update needed
                if self._needs_update(at_record, supabase_map[at_id]):
                    to_update.append(at_record)

        # Check for deletions (records in Supabase but not Airtable)
        for sb_record in supabase_records:
            if sb_record["airtable_id"] not in airtable_map:
                to_delete.append(sb_record)

        # Process changes
        await self._process_sync_changes(
            airtable_table, supabase_table, to_create, to_update, to_delete, result
        )

    async def _incremental_sync(
        self, airtable_table: str, supabase_table: str, result: SyncResult
    ):
        """Perform incremental sync based on last modified time."""
        logger.info(f"Starting incremental sync for {airtable_table}")

        # Get last sync time
        last_sync = self.last_sync_times.get(airtable_table)
        if not last_sync:
            # Get from database
            sync_status = await self.supabase.get_last_sync_status(supabase_table)
            if sync_status and sync_status.get("last_sync_at"):
                last_sync = datetime.fromisoformat(sync_status["last_sync_at"])
            else:
                # Default to 24 hours ago
                last_sync = datetime.utcnow() - timedelta(hours=24)

        # Fetch changed records from Airtable
        # Note: Airtable doesn't have direct "modified since" filter
        # We need to fetch all and filter manually
        all_records = await self._fetch_all_airtable_records(airtable_table)

        changed_records = []
        for record in all_records:
            modified_time = record.get("fields", {}).get("Updated_At")
            if modified_time:
                try:
                    record_time = datetime.fromisoformat(
                        modified_time.replace("Z", "+00:00")
                    )
                    if record_time > last_sync:
                        changed_records.append(record)
                except:
                    pass

        logger.info(f"Found {len(changed_records)} changed records in {airtable_table}")

        # Process changed records
        if changed_records:
            await self._process_sync_changes(
                airtable_table,
                supabase_table,
                changed_records,
                [],  # Updates handled in create (upsert)
                [],  # No deletions in incremental
                result,
            )

        # Update last sync time
        self.last_sync_times[airtable_table] = datetime.utcnow()

    async def _process_sync_changes(
        self,
        airtable_table: str,
        supabase_table: str,
        to_create: list[dict[str, Any]],
        to_update: list[dict[str, Any]],
        to_delete: list[dict[str, Any]],
        result: SyncResult,
    ):
        """Process sync changes."""
        # Process creations/updates (using upsert)
        all_changes = to_create + to_update

        for i in range(0, len(all_changes), self.config.batch_size):
            batch = all_changes[i : i + self.config.batch_size]

            # Transform records
            supabase_records = []
            for record in batch:
                try:
                    mapped = self.mapper.airtable_to_supabase(
                        airtable_table, record, self.id_mappings
                    )
                    supabase_records.append(mapped)
                    result.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to map record {record.get('id')}: {e}")
                    result.errors.append(str(e))

            # Upsert batch
            if supabase_records:
                try:
                    response = await self.supabase.upsert(
                        supabase_table, supabase_records, on_conflict="airtable_id"
                    )

                    # Update counts
                    for record in response:
                        if record.get("airtable_id") in [r["id"] for r in to_create]:
                            result.records_created += 1
                        else:
                            result.records_updated += 1

                    # Update ID mappings
                    for record in response:
                        if supabase_table not in self.id_mappings:
                            self.id_mappings[supabase_table] = {}
                        self.id_mappings[supabase_table][record["airtable_id"]] = (
                            record["id"]
                        )

                except Exception as e:
                    logger.error(f"Failed to upsert batch: {e}")
                    result.errors.append(str(e))

        # Process deletions
        for record in to_delete:
            try:
                await self.supabase.delete(supabase_table, {"id": record["id"]})
                result.records_deleted += 1

            except Exception as e:
                logger.error(f"Failed to delete record {record['id']}: {e}")
                result.errors.append(str(e))

    async def _process_changes(self, changes: list[ChangeRecord]):
        """Process a batch of changes."""
        # Group changes by table
        by_table: dict[str, list[ChangeRecord]] = {}
        for change in changes:
            if change.table not in by_table:
                by_table[change.table] = []
            by_table[change.table].append(change)

        # Process each table's changes
        for table, table_changes in by_table.items():
            supabase_table = self.mapper.get_supabase_table_name(table)

            for change in table_changes:
                try:
                    if change.operation == "CREATE":
                        await self._apply_create(supabase_table, change)
                    elif change.operation == "UPDATE":
                        await self._apply_update(supabase_table, change)
                    elif change.operation == "DELETE":
                        await self._apply_delete(supabase_table, change)

                except Exception as e:
                    logger.error(f"Failed to apply {change.operation} to {table}: {e}")

    async def _apply_create(self, table: str, change: ChangeRecord):
        """Apply a create operation."""
        await self.supabase.insert(table, change.data)

    async def _apply_update(self, table: str, change: ChangeRecord):
        """Apply an update operation."""
        await self.supabase.update(
            table, change.data, {"airtable_id": change.record_id}
        )

    async def _apply_delete(self, table: str, change: ChangeRecord):
        """Apply a delete operation."""
        await self.supabase.delete(table, {"airtable_id": change.record_id})

    async def resolve_conflict(
        self, airtable_record: dict[str, Any], supabase_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve a data conflict between Airtable and Supabase.

        Args:
            airtable_record: Airtable record
            supabase_record: Supabase record

        Returns:
            Resolved record
        """
        strategy = self.config.conflict_resolution

        if strategy == ConflictResolution.AIRTABLE_PRIORITY:
            return airtable_record

        elif strategy == ConflictResolution.SUPABASE_PRIORITY:
            return supabase_record

        elif strategy == ConflictResolution.LATEST_WINS:
            # Compare timestamps
            at_time = airtable_record.get("fields", {}).get("Updated_At")
            sb_time = supabase_record.get("updated_at")

            if not at_time:
                return supabase_record
            if not sb_time:
                return airtable_record

            at_dt = datetime.fromisoformat(at_time.replace("Z", "+00:00"))
            sb_dt = datetime.fromisoformat(sb_time)

            return airtable_record if at_dt > sb_dt else supabase_record

        elif strategy == ConflictResolution.MANUAL:
            # Record conflict for manual resolution
            await self.supabase.record_sync_conflict(
                self.mapper.get_supabase_table_name(
                    airtable_record.get("table", "unknown")
                ),
                airtable_record.get("id", ""),
                airtable_record,
                supabase_record,
                "data_mismatch",
            )

            # Return Airtable as default
            return airtable_record

        return airtable_record

    async def _poll_for_changes(self):
        """Poll for changes in Airtable (webhook alternative)."""
        # This is a simplified polling mechanism
        # In production, you'd use Airtable webhooks or automation

        tables = self.config.tables_to_sync or self._get_default_tables()

        for table in tables:
            try:
                # Get recent changes
                last_check = self.last_sync_times.get(
                    table, datetime.utcnow() - timedelta(minutes=1)
                )

                # Fetch records modified since last check
                all_records = await self._fetch_all_airtable_records(table)

                for record in all_records:
                    modified_time = record.get("fields", {}).get("Updated_At")
                    if modified_time:
                        try:
                            record_time = datetime.fromisoformat(
                                modified_time.replace("Z", "+00:00")
                            )
                            if record_time > last_check:
                                # Add to change queue
                                self.change_queue.append(
                                    ChangeRecord(
                                        table=table,
                                        record_id=record["id"],
                                        operation="UPDATE",
                                        data=record,
                                        timestamp=record_time,
                                        source="airtable",
                                    )
                                )
                        except:
                            pass

                self.last_sync_times[table] = datetime.utcnow()

            except Exception as e:
                logger.error(f"Failed to poll changes for {table}: {e}")

    async def _fetch_all_airtable_records(
        self, table_name: str
    ) -> list[dict[str, Any]]:
        """Fetch all records from an Airtable table."""
        method_map = {
            "Parties": self.airtable.list_parties,
            "Members": self.airtable.list_members,
            "Bills (法案)": self.airtable.list_bills,
            "IssueCategories": self.airtable.list_issue_categories,
            "Bills_PolicyCategories": self.airtable.list_bill_policy_category_relationships,
            "Meetings": self.airtable.list_meetings,
            "Speeches": self.airtable.list_speeches,
            "Votes (投票)": self.airtable.list_votes,
            "Issues": self.airtable.list_issues,
            "IssueTags": self.airtable.list_issue_tags,
        }

        if table_name not in method_map:
            raise ValueError(f"Unknown table: {table_name}")

        return await method_map[table_name](max_records=1000)

    def _needs_update(
        self, airtable_record: dict[str, Any], supabase_record: dict[str, Any]
    ) -> bool:
        """Check if a record needs updating."""
        # Compare timestamps
        at_time = airtable_record.get("fields", {}).get("Updated_At")
        sb_time = supabase_record.get("updated_at")

        if not at_time or not sb_time:
            return True

        try:
            at_dt = datetime.fromisoformat(at_time.replace("Z", "+00:00"))
            sb_dt = datetime.fromisoformat(sb_time)
            return at_dt > sb_dt
        except:
            return True

    async def _load_id_mappings(self):
        """Load ID mappings from Supabase."""
        tables = [
            "parties",
            "members",
            "bills",
            "policy_categories",
            "meetings",
            "issues",
            "issue_tags",
        ]

        for table in tables:
            try:
                records = await self.supabase.select(table, columns="id, airtable_id")

                self.id_mappings[table] = {r["airtable_id"]: r["id"] for r in records}

                logger.info(f"Loaded {len(records)} ID mappings for {table}")

            except Exception as e:
                logger.error(f"Failed to load ID mappings for {table}: {e}")

    async def _record_sync_status(self, result: SyncResult):
        """Record sync status to database."""
        supabase_table = self.mapper.get_supabase_table_name(result.table)

        await self.supabase.record_sync_status(
            supabase_table,
            "success" if not result.errors else "error",
            mode=result.mode.value,
            records_processed=result.records_processed,
            error_message="; ".join(result.errors[:5]) if result.errors else None,
        )

    def _get_default_tables(self) -> list[str]:
        """Get default tables to sync."""
        return [
            "Parties",
            "IssueCategories",
            "IssueTags",
            "Members",
            "Bills (法案)",
            "Bills_PolicyCategories",
            "Meetings",
            "Speeches",
            "Votes (投票)",
            "Issues",
        ]

    async def get_sync_status(self) -> dict[str, Any]:
        """Get current sync status."""
        return {
            "is_running": self.is_running,
            "mode": self.config.mode.value,
            "last_sync_times": {
                table: time.isoformat() for table, time in self.last_sync_times.items()
            },
            "queue_size": len(self.change_queue),
            "id_mappings_loaded": len(self.id_mappings),
        }
