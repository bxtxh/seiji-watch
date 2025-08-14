"""Rollback and recovery management for Airtable to Supabase migration."""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from ..clients.supabase import SupabaseClient
from ..dal.hybrid_data_access import HybridDataAccessLayer

logger = logging.getLogger(__name__)


class RollbackType(Enum):
    """Type of rollback operation."""

    CONFIGURATION = "configuration"
    DATA = "data"
    SCHEMA = "schema"
    FULL = "full"


class RecoveryStatus(Enum):
    """Status of recovery operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class RollbackPoint:
    """Represents a rollback point."""

    id: str
    phase: int
    timestamp: datetime
    description: str
    rollback_type: RollbackType
    metadata: dict[str, Any] = field(default_factory=dict)
    file_path: str | None = None
    is_valid: bool = True


@dataclass
class RecoveryOperation:
    """Represents a recovery operation."""

    id: str
    rollback_point_id: str
    status: RecoveryStatus
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    recovered_tables: list[str] = field(default_factory=list)
    skipped_tables: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    """Manages rollback and recovery operations for migration."""

    def __init__(
        self,
        supabase_client: SupabaseClient | None = None,
        hybrid_dal: HybridDataAccessLayer | None = None,
        backup_dir: str | None = None,
    ):
        """Initialize rollback manager.

        Args:
            supabase_client: Supabase client instance
            hybrid_dal: Hybrid DAL instance
            backup_dir: Directory for storing backups
        """
        self.supabase = supabase_client or SupabaseClient()
        self.dal = hybrid_dal

        # Backup configuration
        self.backup_dir = Path(
            backup_dir or os.getenv("ROLLBACK_BACKUP_DIR", "./backups")
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Rollback points storage
        self.rollback_points: list[RollbackPoint] = []
        self.recovery_operations: list[RecoveryOperation] = []

        # Configuration backup
        self.config_backup_dir = self.backup_dir / "config"
        self.config_backup_dir.mkdir(parents=True, exist_ok=True)

        # Data backup
        self.data_backup_dir = self.backup_dir / "data"
        self.data_backup_dir.mkdir(parents=True, exist_ok=True)

        # Schema backup
        self.schema_backup_dir = self.backup_dir / "schema"
        self.schema_backup_dir.mkdir(parents=True, exist_ok=True)

        # Load existing rollback points
        self._load_rollback_points()

    def _load_rollback_points(self):
        """Load existing rollback points from disk."""
        manifest_path = self.backup_dir / "rollback_manifest.json"

        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                for point_data in manifest.get("rollback_points", []):
                    point = RollbackPoint(
                        id=point_data["id"],
                        phase=point_data["phase"],
                        timestamp=datetime.fromisoformat(point_data["timestamp"]),
                        description=point_data["description"],
                        rollback_type=RollbackType(point_data["rollback_type"]),
                        metadata=point_data.get("metadata", {}),
                        file_path=point_data.get("file_path"),
                        is_valid=point_data.get("is_valid", True),
                    )
                    self.rollback_points.append(point)

                logger.info(f"Loaded {len(self.rollback_points)} rollback points")

            except Exception as e:
                logger.error(f"Failed to load rollback manifest: {e}")

    def _save_rollback_points(self):
        """Save rollback points to disk."""
        manifest_path = self.backup_dir / "rollback_manifest.json"

        manifest = {
            "rollback_points": [
                {
                    "id": point.id,
                    "phase": point.phase,
                    "timestamp": point.timestamp.isoformat(),
                    "description": point.description,
                    "rollback_type": point.rollback_type.value,
                    "metadata": point.metadata,
                    "file_path": point.file_path,
                    "is_valid": point.is_valid,
                }
                for point in self.rollback_points
            ],
            "last_updated": datetime.utcnow().isoformat(),
        }

        try:
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save rollback manifest: {e}")

    # =====================================================
    # Creating Rollback Points
    # =====================================================

    async def create_rollback_point(
        self,
        phase: int,
        description: str,
        rollback_type: RollbackType = RollbackType.FULL,
    ) -> RollbackPoint:
        """Create a new rollback point.

        Args:
            phase: Migration phase number
            description: Description of the rollback point
            rollback_type: Type of rollback to create

        Returns:
            Created rollback point
        """
        rollback_id = f"rollback_{phase}_{int(datetime.utcnow().timestamp())}"

        logger.info(f"Creating rollback point: {rollback_id}")

        point = RollbackPoint(
            id=rollback_id,
            phase=phase,
            timestamp=datetime.utcnow(),
            description=description,
            rollback_type=rollback_type,
            metadata={},
        )

        try:
            # Create backups based on type
            if rollback_type in [RollbackType.CONFIGURATION, RollbackType.FULL]:
                await self._backup_configuration(point)

            if rollback_type in [RollbackType.DATA, RollbackType.FULL]:
                await self._backup_data(point)

            if rollback_type in [RollbackType.SCHEMA, RollbackType.FULL]:
                await self._backup_schema(point)

            # Mark as valid
            point.is_valid = True

            # Add to list and save
            self.rollback_points.append(point)
            self._save_rollback_points()

            logger.info(f"Successfully created rollback point: {rollback_id}")

        except Exception as e:
            logger.error(f"Failed to create rollback point: {e}")
            point.is_valid = False
            point.metadata["error"] = str(e)

        return point

    async def _backup_configuration(self, point: RollbackPoint):
        """Backup configuration files."""
        config_backup = self.config_backup_dir / point.id
        config_backup.mkdir(parents=True, exist_ok=True)

        # Backup environment files
        env_files = [
            ".env",
            ".env.development",
            ".env.supabase",
            ".env.example",
        ]

        for env_file in env_files:
            source = Path(env_file)
            if source.exists():
                destination = config_backup / env_file
                shutil.copy2(source, destination)

        # Backup feature flags
        feature_flags = {
            "FEATURE_SUPABASE_READ_ENABLED": os.getenv("FEATURE_SUPABASE_READ_ENABLED"),
            "FEATURE_SUPABASE_WRITE_ENABLED": os.getenv(
                "FEATURE_SUPABASE_WRITE_ENABLED"
            ),
            "FEATURE_AIRTABLE_FALLBACK_ENABLED": os.getenv(
                "FEATURE_AIRTABLE_FALLBACK_ENABLED"
            ),
            "FEATURE_CACHE_ENABLED": os.getenv("FEATURE_CACHE_ENABLED"),
            "SYNC_SERVICE_MODE": os.getenv("SYNC_SERVICE_MODE"),
            "SYNC_SERVICE_INTERVAL_MINUTES": os.getenv("SYNC_SERVICE_INTERVAL_MINUTES"),
        }

        with open(config_backup / "feature_flags.json", "w") as f:
            json.dump(feature_flags, f, indent=2)

        point.metadata["config_backup_path"] = str(config_backup)

    async def _backup_data(self, point: RollbackPoint):
        """Backup Supabase data."""
        data_backup = self.data_backup_dir / point.id
        data_backup.mkdir(parents=True, exist_ok=True)

        # Tables to backup
        tables = [
            "parties",
            "members",
            "bills",
            "policy_categories",
            "bills_policy_categories",
            "meetings",
            "speeches",
            "votes",
            "issues",
            "issue_tags",
            "sync_status",
        ]

        # Initialize connection pool
        await self.supabase.initialize_db_pool()

        try:
            for table in tables:
                try:
                    # Export table data
                    logger.info(f"Backing up table: {table}")

                    # Get all records
                    records = await self.supabase.select(table)

                    # Save to JSON file
                    backup_file = data_backup / f"{table}.json"
                    with open(backup_file, "w") as f:
                        json.dump(records, f, indent=2, default=str)

                    point.metadata[f"{table}_count"] = len(records)

                except Exception as e:
                    logger.error(f"Failed to backup table {table}: {e}")
                    point.metadata[f"{table}_error"] = str(e)

        finally:
            await self.supabase.close_db_pool()

        point.metadata["data_backup_path"] = str(data_backup)

    async def _backup_schema(self, point: RollbackPoint):
        """Backup database schema."""
        schema_backup = self.schema_backup_dir / point.id
        schema_backup.mkdir(parents=True, exist_ok=True)

        # Initialize connection pool
        await self.supabase.initialize_db_pool()

        try:
            # Export schema
            schema_query = """
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """

            schema_data = await self.supabase.execute_query(schema_query)

            # Save schema
            with open(schema_backup / "schema.json", "w") as f:
                json.dump(schema_data, f, indent=2, default=str)

            # Export indexes
            index_query = """
                SELECT 
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
            """

            index_data = await self.supabase.execute_query(index_query)

            with open(schema_backup / "indexes.json", "w") as f:
                json.dump(index_data, f, indent=2, default=str)

            point.metadata["schema_backup_path"] = str(schema_backup)

        except Exception as e:
            logger.error(f"Failed to backup schema: {e}")
            point.metadata["schema_error"] = str(e)

        finally:
            await self.supabase.close_db_pool()

    # =====================================================
    # Executing Rollback
    # =====================================================

    async def execute_rollback(
        self, rollback_point_id: str, tables_to_rollback: list[str] | None = None
    ) -> RecoveryOperation:
        """Execute rollback to a specific point.

        Args:
            rollback_point_id: ID of the rollback point
            tables_to_rollback: Optional list of specific tables to rollback

        Returns:
            Recovery operation result
        """
        # Find rollback point
        point = next(
            (p for p in self.rollback_points if p.id == rollback_point_id), None
        )

        if not point:
            raise ValueError(f"Rollback point not found: {rollback_point_id}")

        if not point.is_valid:
            raise ValueError(f"Rollback point is invalid: {rollback_point_id}")

        # Create recovery operation
        operation = RecoveryOperation(
            id=f"recovery_{int(datetime.utcnow().timestamp())}",
            rollback_point_id=rollback_point_id,
            status=RecoveryStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )

        self.recovery_operations.append(operation)

        logger.info(f"Starting rollback to point: {rollback_point_id}")

        try:
            # Execute rollback based on type
            if point.rollback_type in [RollbackType.CONFIGURATION, RollbackType.FULL]:
                await self._restore_configuration(point, operation)

            if point.rollback_type in [RollbackType.DATA, RollbackType.FULL]:
                await self._restore_data(point, operation, tables_to_rollback)

            if point.rollback_type in [RollbackType.SCHEMA, RollbackType.FULL]:
                await self._restore_schema(point, operation)

            # Clear caches if DAL is available
            if self.dal:
                await self.dal.invalidate_cache("*")

            operation.status = RecoveryStatus.COMPLETED
            operation.completed_at = datetime.utcnow()

            logger.info(f"Successfully completed rollback to: {rollback_point_id}")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            operation.status = RecoveryStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()

        return operation

    async def _restore_configuration(
        self, point: RollbackPoint, operation: RecoveryOperation
    ):
        """Restore configuration from backup."""
        config_backup = Path(point.metadata.get("config_backup_path", ""))

        if not config_backup.exists():
            raise ValueError(f"Configuration backup not found: {config_backup}")

        # Restore feature flags
        feature_flags_file = config_backup / "feature_flags.json"
        if feature_flags_file.exists():
            with open(feature_flags_file) as f:
                feature_flags = json.load(f)

            for key, value in feature_flags.items():
                if value is not None:
                    os.environ[key] = str(value)

            operation.statistics["restored_flags"] = len(feature_flags)

        logger.info("Configuration restored successfully")

    async def _restore_data(
        self,
        point: RollbackPoint,
        operation: RecoveryOperation,
        tables_to_restore: list[str] | None = None,
    ):
        """Restore data from backup."""
        data_backup = Path(point.metadata.get("data_backup_path", ""))

        if not data_backup.exists():
            raise ValueError(f"Data backup not found: {data_backup}")

        # Default to all tables if not specified
        if not tables_to_restore:
            tables_to_restore = [
                "parties",
                "members",
                "bills",
                "policy_categories",
                "bills_policy_categories",
                "meetings",
                "speeches",
                "votes",
                "issues",
                "issue_tags",
            ]

        # Initialize connection pool
        await self.supabase.initialize_db_pool()

        try:
            # Restore in reverse order to handle foreign keys
            for table in reversed(tables_to_restore):
                backup_file = data_backup / f"{table}.json"

                if not backup_file.exists():
                    logger.warning(f"Backup file not found for {table}")
                    operation.skipped_tables.append(table)
                    continue

                try:
                    logger.info(f"Restoring table: {table}")

                    # Load backup data
                    with open(backup_file) as f:
                        records = json.load(f)

                    # Clear existing data
                    await self.supabase.execute_query(f"TRUNCATE TABLE {table} CASCADE")

                    # Restore data in batches
                    batch_size = 100
                    for i in range(0, len(records), batch_size):
                        batch = records[i : i + batch_size]
                        await self.supabase.insert_many(table, batch)

                    operation.recovered_tables.append(table)
                    operation.statistics[f"{table}_restored"] = len(records)

                except Exception as e:
                    logger.error(f"Failed to restore table {table}: {e}")
                    operation.statistics[f"{table}_error"] = str(e)

        finally:
            await self.supabase.close_db_pool()

        logger.info(f"Data restored for {len(operation.recovered_tables)} tables")

    async def _restore_schema(self, point: RollbackPoint, operation: RecoveryOperation):
        """Restore schema from backup."""
        # Schema restoration is complex and risky
        # For Phase 1, we'll just validate schema consistency

        schema_backup = Path(point.metadata.get("schema_backup_path", ""))

        if not schema_backup.exists():
            logger.warning("Schema backup not found, skipping schema restore")
            return

        # Load expected schema
        with open(schema_backup / "schema.json") as f:
            expected_schema = json.load(f)

        # Get current schema
        await self.supabase.initialize_db_pool()

        try:
            current_schema_query = """
                SELECT 
                    table_name,
                    column_name,
                    data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """

            current_schema = await self.supabase.execute_query(current_schema_query)

            # Compare schemas
            schema_differences = self._compare_schemas(expected_schema, current_schema)

            if schema_differences:
                logger.warning(f"Schema differences detected: {schema_differences}")
                operation.statistics["schema_differences"] = schema_differences
            else:
                logger.info("Schema validation passed")

        finally:
            await self.supabase.close_db_pool()

    def _compare_schemas(
        self, expected: list[dict[str, Any]], current: list[dict[str, Any]]
    ) -> list[str]:
        """Compare two schemas and return differences."""
        differences = []

        # Create lookup maps
        expected_map = {f"{r['table_name']}.{r['column_name']}": r for r in expected}

        current_map = {f"{r['table_name']}.{r['column_name']}": r for r in current}

        # Check for missing columns
        for key in expected_map:
            if key not in current_map:
                differences.append(f"Missing column: {key}")

        # Check for extra columns
        for key in current_map:
            if key not in expected_map:
                differences.append(f"Extra column: {key}")

        # Check for type differences
        for key in expected_map:
            if key in current_map:
                if expected_map[key]["data_type"] != current_map[key]["data_type"]:
                    differences.append(
                        f"Type mismatch for {key}: "
                        f"{expected_map[key]['data_type']} vs {current_map[key]['data_type']}"
                    )

        return differences

    # =====================================================
    # Rollback Management
    # =====================================================

    def list_rollback_points(
        self, phase: int | None = None, rollback_type: RollbackType | None = None
    ) -> list[RollbackPoint]:
        """List available rollback points."""
        points = self.rollback_points

        if phase is not None:
            points = [p for p in points if p.phase == phase]

        if rollback_type:
            points = [p for p in points if p.rollback_type == rollback_type]

        # Sort by timestamp (newest first)
        points.sort(key=lambda p: p.timestamp, reverse=True)

        return points

    def get_rollback_point(self, rollback_id: str) -> RollbackPoint | None:
        """Get a specific rollback point."""
        return next((p for p in self.rollback_points if p.id == rollback_id), None)

    def validate_rollback_point(self, rollback_id: str) -> bool:
        """Validate that a rollback point is still usable."""
        point = self.get_rollback_point(rollback_id)

        if not point:
            return False

        # Check if backup files exist
        if point.metadata.get("config_backup_path"):
            if not Path(point.metadata["config_backup_path"]).exists():
                point.is_valid = False

        if point.metadata.get("data_backup_path"):
            if not Path(point.metadata["data_backup_path"]).exists():
                point.is_valid = False

        # Check age (rollback points older than 30 days might be invalid)
        age = datetime.utcnow() - point.timestamp
        if age > timedelta(days=30):
            logger.warning(f"Rollback point {rollback_id} is {age.days} days old")

        self._save_rollback_points()

        return point.is_valid

    def cleanup_old_rollbacks(self, days: int = 30):
        """Clean up old rollback points."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        for point in self.rollback_points[:]:
            if point.timestamp < cutoff:
                logger.info(f"Removing old rollback point: {point.id}")

                # Remove backup files
                for path_key in [
                    "config_backup_path",
                    "data_backup_path",
                    "schema_backup_path",
                ]:
                    if path_key in point.metadata:
                        path = Path(point.metadata[path_key])
                        if path.exists():
                            shutil.rmtree(path)

                # Remove from list
                self.rollback_points.remove(point)

        self._save_rollback_points()

    def get_recovery_status(self, recovery_id: str) -> RecoveryOperation | None:
        """Get status of a recovery operation."""
        return next(
            (op for op in self.recovery_operations if op.id == recovery_id), None
        )
