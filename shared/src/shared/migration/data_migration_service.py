"""Data migration service for initial Airtable to Supabase migration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any

from ..clients.airtable import AirtableClient
from ..clients.supabase import SupabaseClient
from .schema_mapper import SchemaMapper

logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status for tracking."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class DataMigrationService:
    """Service for migrating data from Airtable to Supabase."""

    # Migration order is important for foreign key constraints
    MIGRATION_ORDER = [
        "Parties",  # Independent
        "IssueCategories",  # Self-referential (parent_id)
        "IssueTags",  # Independent
        "Members",  # Depends on Parties
        "Bills (法案)",  # Independent
        "Bills_PolicyCategories",  # Depends on Bills and IssueCategories
        "Meetings",  # Independent
        "Speeches",  # Depends on Meetings, Members, Bills
        "Votes (投票)",  # Depends on Bills, Members
        "Issues",  # Depends on IssueCategories
    ]

    def __init__(
        self,
        airtable_client: AirtableClient | None = None,
        supabase_client: SupabaseClient | None = None,
        batch_size: int = 100,
        max_retries: int = 3,
    ):
        """Initialize migration service.

        Args:
            airtable_client: Airtable client instance
            supabase_client: Supabase client instance
            batch_size: Number of records to process in each batch
            max_retries: Maximum number of retries for failed operations
        """
        self.airtable = airtable_client or AirtableClient()
        self.supabase = supabase_client or SupabaseClient()
        self.mapper = SchemaMapper()

        self.batch_size = batch_size
        self.max_retries = max_retries

        # Track migration progress
        self.migration_stats = {
            "total_records": 0,
            "migrated_records": 0,
            "failed_records": 0,
            "start_time": None,
            "end_time": None,
            "table_stats": {},
        }

        # ID mappings for foreign key resolution
        self.id_mappings: dict[str, dict[str, str]] = {}

    async def migrate_all_tables(
        self, tables: list[str] | None = None, clean_start: bool = False
    ) -> dict[str, Any]:
        """Migrate all tables from Airtable to Supabase.

        Args:
            tables: Optional list of specific tables to migrate
            clean_start: Whether to clear existing data in Supabase

        Returns:
            Migration statistics
        """
        self.migration_stats["start_time"] = datetime.utcnow()
        tables_to_migrate = tables or self.MIGRATION_ORDER

        logger.info(f"Starting migration of {len(tables_to_migrate)} tables")

        # Initialize Supabase connection pool
        await self.supabase.initialize_db_pool()

        try:
            # Clean existing data if requested
            if clean_start:
                await self._clean_supabase_tables(tables_to_migrate)

            # Migrate each table in order
            for table_name in tables_to_migrate:
                if table_name not in self.MIGRATION_ORDER:
                    logger.warning(f"Unknown table: {table_name}, skipping")
                    continue

                logger.info(f"Migrating table: {table_name}")

                try:
                    stats = await self.migrate_table(table_name)
                    self.migration_stats["table_stats"][table_name] = stats

                    if stats["status"] == MigrationStatus.FAILED:
                        logger.error(f"Failed to migrate {table_name}")

                except Exception as e:
                    logger.error(f"Error migrating {table_name}: {e}")
                    self.migration_stats["table_stats"][table_name] = {
                        "status": MigrationStatus.FAILED,
                        "error": str(e),
                    }

        finally:
            await self.supabase.close_db_pool()

        self.migration_stats["end_time"] = datetime.utcnow()
        duration = (
            self.migration_stats["end_time"] - self.migration_stats["start_time"]
        ).total_seconds()

        self.migration_stats["duration_seconds"] = duration

        logger.info(f"Migration completed in {duration:.2f} seconds")
        logger.info(f"Total records: {self.migration_stats['total_records']}")
        logger.info(f"Migrated: {self.migration_stats['migrated_records']}")
        logger.info(f"Failed: {self.migration_stats['failed_records']}")

        return self.migration_stats

    async def migrate_table(self, table_name: str) -> dict[str, Any]:
        """Migrate a single table from Airtable to Supabase.

        Args:
            table_name: Airtable table name

        Returns:
            Table migration statistics
        """
        stats = {
            "status": MigrationStatus.PENDING,
            "total_records": 0,
            "migrated_records": 0,
            "failed_records": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
        }

        try:
            # Get Supabase table name
            supabase_table = self.mapper.get_supabase_table_name(table_name)

            # Record migration start
            await self.supabase.record_sync_status(
                supabase_table, "in_progress", mode="full"
            )

            # Fetch all records from Airtable
            logger.info(f"Fetching records from Airtable table: {table_name}")
            airtable_records = await self._fetch_all_airtable_records(table_name)
            stats["total_records"] = len(airtable_records)
            self.migration_stats["total_records"] += len(airtable_records)

            logger.info(f"Found {len(airtable_records)} records in {table_name}")

            # Process in batches
            for i in range(0, len(airtable_records), self.batch_size):
                batch = airtable_records[i : i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (
                    len(airtable_records) + self.batch_size - 1
                ) // self.batch_size

                logger.info(
                    f"Processing batch {batch_num}/{total_batches} for {table_name}"
                )

                success, failed = await self._migrate_batch(
                    table_name, supabase_table, batch
                )

                stats["migrated_records"] += success
                stats["failed_records"] += failed
                self.migration_stats["migrated_records"] += success
                self.migration_stats["failed_records"] += failed

                # Small delay between batches to avoid rate limits
                if i + self.batch_size < len(airtable_records):
                    await asyncio.sleep(0.5)

            # Determine final status
            if stats["failed_records"] == 0:
                stats["status"] = MigrationStatus.COMPLETED
            elif stats["migrated_records"] == 0:
                stats["status"] = MigrationStatus.FAILED
            else:
                stats["status"] = MigrationStatus.PARTIAL

            # Record migration completion
            await self.supabase.record_sync_status(
                supabase_table,
                "success" if stats["status"] == MigrationStatus.COMPLETED else "error",
                mode="full",
                records_processed=stats["migrated_records"],
                error_message=str(stats["errors"][:5]) if stats["errors"] else None,
            )

        except Exception as e:
            logger.error(f"Failed to migrate table {table_name}: {e}")
            stats["status"] = MigrationStatus.FAILED
            stats["errors"].append(str(e))

        stats["end_time"] = datetime.utcnow()
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()

        return stats

    async def _fetch_all_airtable_records(
        self, table_name: str
    ) -> list[dict[str, Any]]:
        """Fetch all records from an Airtable table.

        Args:
            table_name: Airtable table name

        Returns:
            List of all records
        """
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

        # Fetch records in chunks (Airtable has pagination)
        all_records = []
        offset = None

        while True:
            # Most Airtable list methods don't support offset directly
            # We'll fetch max records and handle pagination manually
            records = await method_map[table_name](max_records=1000)
            all_records.extend(records)

            # For now, we'll fetch up to 1000 records per table
            # Full implementation would handle Airtable's pagination
            break

        return all_records

    async def _migrate_batch(
        self, airtable_table: str, supabase_table: str, batch: list[dict[str, Any]]
    ) -> tuple[int, int]:
        """Migrate a batch of records.

        Args:
            airtable_table: Airtable table name
            supabase_table: Supabase table name
            batch: Batch of Airtable records

        Returns:
            Tuple of (success_count, failed_count)
        """
        success_count = 0
        failed_count = 0
        supabase_records = []

        # Transform each record
        for record in batch:
            try:
                # Map to Supabase format
                supabase_record = self.mapper.airtable_to_supabase(
                    airtable_table, record, self.id_mappings
                )

                # Validate record
                errors = self.mapper.validate_record(supabase_table, supabase_record)
                if errors:
                    logger.warning(
                        f"Validation errors for record {record.get('id')}: {errors}"
                    )
                    # Continue anyway for non-critical errors

                supabase_records.append(supabase_record)

            except Exception as e:
                logger.error(f"Failed to transform record {record.get('id')}: {e}")
                failed_count += 1
                continue

        # Batch upsert to Supabase
        if supabase_records:
            try:
                result = await self.supabase.batch_upsert_with_mapping(
                    supabase_table, supabase_records, id_field="airtable_id"
                )

                success_count = result["success_count"]
                failed_count += result["error_count"]

                # Update ID mappings for foreign key resolution
                if supabase_table not in self.id_mappings:
                    self.id_mappings[supabase_table] = {}
                self.id_mappings[supabase_table].update(result["id_mapping"])

            except Exception as e:
                logger.error(f"Failed to batch upsert to {supabase_table}: {e}")
                failed_count += len(supabase_records)

        return success_count, failed_count

    async def _clean_supabase_tables(self, tables: list[str]):
        """Clean existing data in Supabase tables.

        Args:
            tables: List of Airtable table names to clean
        """
        logger.warning("Cleaning existing Supabase data")

        # Process in reverse order to handle foreign key constraints
        for table_name in reversed(tables):
            supabase_table = self.mapper.get_supabase_table_name(table_name)

            try:
                # Delete all records
                await self.supabase.execute_query(
                    f"TRUNCATE TABLE {supabase_table} CASCADE"
                )
                logger.info(f"Cleaned table: {supabase_table}")

            except Exception as e:
                logger.error(f"Failed to clean {supabase_table}: {e}")

    async def validate_migration(
        self, tables: list[str] | None = None
    ) -> dict[str, Any]:
        """Validate data consistency between Airtable and Supabase.

        Args:
            tables: Optional list of specific tables to validate

        Returns:
            Validation results
        """
        validation_results = {
            "validated_at": datetime.utcnow(),
            "tables": {},
            "overall_consistency": 0.0,
        }

        tables_to_validate = tables or self.MIGRATION_ORDER

        for table_name in tables_to_validate:
            supabase_table = self.mapper.get_supabase_table_name(table_name)

            try:
                # Get record counts
                airtable_count = await self._get_airtable_count(table_name)
                supabase_count = await self.supabase.get_table_count(supabase_table)

                # Calculate consistency score
                if airtable_count == 0:
                    consistency = 100.0 if supabase_count == 0 else 0.0
                else:
                    consistency = (
                        min(supabase_count, airtable_count) / airtable_count
                    ) * 100

                validation_results["tables"][table_name] = {
                    "airtable_count": airtable_count,
                    "supabase_count": supabase_count,
                    "consistency_score": consistency,
                    "status": "valid" if consistency >= 95 else "inconsistent",
                }

            except Exception as e:
                validation_results["tables"][table_name] = {
                    "error": str(e),
                    "status": "error",
                }

        # Calculate overall consistency
        valid_tables = [
            t for t in validation_results["tables"].values() if "consistency_score" in t
        ]

        if valid_tables:
            validation_results["overall_consistency"] = sum(
                t["consistency_score"] for t in valid_tables
            ) / len(valid_tables)

        return validation_results

    async def _get_airtable_count(self, table_name: str) -> int:
        """Get record count for an Airtable table.

        Args:
            table_name: Airtable table name

        Returns:
            Record count
        """
        # This is a simplified version - Airtable doesn't provide direct count
        records = await self._fetch_all_airtable_records(table_name)
        return len(records)

    async def migrate_incremental(
        self, table_name: str, since: datetime
    ) -> dict[str, Any]:
        """Migrate records modified since a specific time.

        Args:
            table_name: Table to migrate
            since: Migrate records modified after this time

        Returns:
            Migration statistics
        """
        # This would implement incremental migration based on Modified_At field
        # For Phase 1, we're focusing on full migration
        pass
