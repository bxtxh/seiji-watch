#!/usr/bin/env python3
"""Migration worker service for continuous data migration."""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared" / "src"))

from shared.clients.airtable import AirtableClient
from shared.clients.supabase import SupabaseClient
from shared.migration.data_migration_service import DataMigrationService
from shared.migration.sync_service import AirtableSupabaseSyncService, SyncMode, SyncConfig
from shared.monitoring.metrics_collector import MetricsCollector, AlertSeverity
from shared.migration.rollback_manager import RollbackManager

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/migration_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MigrationWorker:
    """Worker service for managing data migration tasks."""
    
    def __init__(self):
        """Initialize migration worker."""
        self.airtable_client = AirtableClient()
        self.supabase_client = SupabaseClient()
        self.migration_service = DataMigrationService(
            self.airtable_client,
            self.supabase_client
        )
        self.metrics_collector = MetricsCollector()
        self.rollback_manager = RollbackManager(self.supabase_client)
        
        self.running = False
        self.phase = int(os.getenv("MIGRATION_PHASE", "1"))
        self.check_interval = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))  # 5 minutes
        self.batch_size = int(os.getenv("BATCH_SIZE", "100"))
        
        # Track migration state
        self.last_full_migration = None
        self.last_validation = None
        
    async def initialize(self):
        """Initialize worker connections and state."""
        logger.info("Initializing migration worker...")
        
        try:
            # Test connections
            await self.airtable_client.initialize()
            await self.supabase_client.initialize()
            
            # Check if initial migration is needed
            if await self._needs_initial_migration():
                logger.info("Initial migration required")
                await self._run_initial_migration()
            
            logger.info("Migration worker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            self.metrics_collector.create_alert(
                "migration_worker_init_failed",
                f"Worker initialization failed: {e}",
                AlertSeverity.CRITICAL
            )
            raise
            
    async def _needs_initial_migration(self) -> bool:
        """Check if initial migration is needed."""
        try:
            # Check if Supabase has data
            for table in self.migration_service.MIGRATION_ORDER:
                count = await self.supabase_client.get_table_count(
                    self.migration_service._get_supabase_table_name(table)
                )
                if count == 0:
                    logger.info(f"Table {table} is empty, initial migration needed")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return True
            
    async def _run_initial_migration(self):
        """Run initial full migration."""
        logger.info("Starting initial full migration...")
        
        try:
            # Create rollback point
            rollback_point = await self.rollback_manager.create_rollback_point(
                phase=self.phase,
                description="Before initial migration",
                rollback_type="full"
            )
            logger.info(f"Created rollback point: {rollback_point.id}")
            
            # Run migration
            stats = await self.migration_service.migrate_all_tables(
                clean_start=False,
                batch_size=self.batch_size
            )
            
            # Record metrics
            self.metrics_collector.record_migration_operation(
                operation="initial_migration",
                phase=self.phase,
                tables_count=len(stats.get("table_stats", {})),
                records_count=stats.get("total_records", 0),
                duration=stats.get("duration_seconds", 0),
                status="success" if stats.get("status") == "completed" else "failed"
            )
            
            self.last_full_migration = datetime.utcnow()
            
            logger.info(f"Initial migration completed: {stats}")
            
        except Exception as e:
            logger.error(f"Initial migration failed: {e}")
            self.metrics_collector.create_alert(
                "initial_migration_failed",
                f"Initial migration failed: {e}",
                AlertSeverity.CRITICAL
            )
            raise
            
    async def run_validation(self):
        """Run data validation between Airtable and Supabase."""
        logger.info("Running data validation...")
        
        try:
            validation_results = await self.migration_service.validate_migration()
            
            overall_consistency = validation_results.get("overall_consistency", 0)
            
            # Check consistency threshold
            if overall_consistency < 95:
                self.metrics_collector.create_alert(
                    "data_inconsistency",
                    f"Data consistency below threshold: {overall_consistency:.1f}%",
                    AlertSeverity.WARNING if overall_consistency >= 90 else AlertSeverity.ERROR
                )
                
                # Trigger re-sync for inconsistent tables
                for table_name, result in validation_results["tables"].items():
                    if result.get("consistency_score", 100) < 95:
                        logger.warning(f"Table {table_name} inconsistent, scheduling re-sync")
                        await self._schedule_table_resync(table_name)
            
            # Record metrics
            self.metrics_collector.record_validation_result(
                overall_consistency=overall_consistency,
                table_results=validation_results["tables"]
            )
            
            self.last_validation = datetime.utcnow()
            
            logger.info(f"Validation completed: {overall_consistency:.1f}% consistent")
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.metrics_collector.record_error(
                "migration_worker",
                "validation_error",
                str(e)
            )
            
    async def _schedule_table_resync(self, table_name: str):
        """Schedule a table for re-synchronization."""
        try:
            # Queue table for sync (would integrate with sync worker)
            logger.info(f"Scheduling re-sync for table: {table_name}")
            
            # For now, run immediate incremental sync
            stats = await self.migration_service.migrate_table(
                table_name,
                incremental=True
            )
            
            logger.info(f"Re-sync completed for {table_name}: {stats}")
            
        except Exception as e:
            logger.error(f"Failed to re-sync table {table_name}: {e}")
            
    async def check_migration_health(self):
        """Check overall migration health."""
        try:
            # Check Airtable connection
            airtable_healthy = await self.airtable_client.health_check()
            self.metrics_collector.update_health_status(
                "airtable",
                airtable_healthy,
                "Connected" if airtable_healthy else "Connection failed"
            )
            
            # Check Supabase connection
            supabase_healthy = await self.supabase_client.health_check()
            self.metrics_collector.update_health_status(
                "supabase",
                supabase_healthy,
                "Connected" if supabase_healthy else "Connection failed"
            )
            
            # Check if validation is needed
            if self.last_validation is None or \
               (datetime.utcnow() - self.last_validation) > timedelta(hours=1):
                await self.run_validation()
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
    async def run(self):
        """Main worker loop."""
        logger.info(f"Starting migration worker (Phase {self.phase})...")
        
        self.running = True
        
        try:
            await self.initialize()
            
            while self.running:
                try:
                    # Check migration health
                    await self.check_migration_health()
                    
                    # Sleep until next check
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in worker loop: {e}")
                    await asyncio.sleep(30)  # Brief pause before retry
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Gracefully shutdown the worker."""
        logger.info("Shutting down migration worker...")
        
        self.running = False
        
        # Close connections
        await self.airtable_client.close()
        await self.supabase_client.close()
        
        # Final metrics flush
        self.metrics_collector.flush_metrics()
        
        logger.info("Migration worker stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run worker
    worker = MigrationWorker()
    
    # Run async event loop
    try:
        asyncio.run(worker.run())
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)