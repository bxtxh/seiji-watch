#!/usr/bin/env python3
"""Sync worker service for continuous data synchronization."""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared" / "src"))

from shared.clients.airtable import AirtableClient
from shared.clients.supabase import SupabaseClient
from shared.migration.sync_service import AirtableSupabaseSyncService, SyncMode, SyncConfig
from shared.monitoring.metrics_collector import MetricsCollector, AlertSeverity

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/sync_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SyncWorker:
    """Worker service for continuous data synchronization."""
    
    def __init__(self):
        """Initialize sync worker."""
        # Initialize clients
        self.airtable_client = AirtableClient()
        self.supabase_client = SupabaseClient()
        
        # Configure sync service
        self.config = SyncConfig(
            mode=SyncMode(os.getenv("SYNC_MODE", "incremental")),
            interval_minutes=int(os.getenv("SYNC_INTERVAL_MINUTES", "5")),
            batch_size=int(os.getenv("SYNC_BATCH_SIZE", "100")),
            conflict_resolution=os.getenv("CONFLICT_RESOLUTION", "airtable_priority")
        )
        
        self.sync_service = AirtableSupabaseSyncService(
            self.airtable_client,
            self.supabase_client,
            self.config
        )
        
        self.metrics_collector = MetricsCollector()
        
        # Worker state
        self.running = False
        self.sync_stats: Dict[str, Dict] = {}
        self.last_sync_times: Dict[str, datetime] = {}
        self.sync_errors: Dict[str, List[str]] = {}
        
    async def initialize(self):
        """Initialize worker connections and state."""
        logger.info("Initializing sync worker...")
        
        try:
            # Initialize clients
            await self.airtable_client.initialize()
            await self.supabase_client.initialize()
            
            # Load sync state
            await self._load_sync_state()
            
            logger.info(f"Sync worker initialized (mode: {self.config.mode.value})")
            
        except Exception as e:
            logger.error(f"Failed to initialize sync worker: {e}")
            self.metrics_collector.create_alert(
                "sync_worker_init_failed",
                f"Sync worker initialization failed: {e}",
                AlertSeverity.CRITICAL
            )
            raise
            
    async def _load_sync_state(self):
        """Load previous sync state from database."""
        try:
            # Query sync_status table for last sync times
            sync_status = await self.supabase_client.select(
                "sync_status",
                filters={"status": "completed"},
                order_by="created_at desc",
                limit=100
            )
            
            # Build last sync times map
            for status in sync_status:
                table = status.get("table_name")
                if table and table not in self.last_sync_times:
                    self.last_sync_times[table] = datetime.fromisoformat(
                        status.get("created_at")
                    )
                    
            logger.info(f"Loaded sync state for {len(self.last_sync_times)} tables")
            
        except Exception as e:
            logger.warning(f"Could not load sync state: {e}")
            # Continue with empty state
            
    async def sync_table(self, table_name: str, mode: Optional[SyncMode] = None):
        """Sync a specific table."""
        start_time = datetime.utcnow()
        mode = mode or self.config.mode
        
        logger.info(f"Starting {mode.value} sync for {table_name}")
        
        try:
            # Perform sync
            result = await self.sync_service.sync_table(table_name, mode)
            
            # Update stats
            self.sync_stats[table_name] = {
                "last_sync": start_time,
                "duration": (datetime.utcnow() - start_time).total_seconds(),
                "records_processed": result.records_processed,
                "records_created": result.records_created,
                "records_updated": result.records_updated,
                "success_rate": result.success_rate,
                "mode": mode.value
            }
            
            # Update last sync time
            self.last_sync_times[table_name] = start_time
            
            # Clear errors for this table
            if table_name in self.sync_errors:
                del self.sync_errors[table_name]
                
            # Record metrics
            self.metrics_collector.record_sync_operation(
                table=table_name,
                operation=f"sync_{mode.value}",
                status="success",
                records_count=result.records_processed,
                duration=(datetime.utcnow() - start_time).total_seconds()
            )
            
            # Check for issues
            if result.success_rate < 100:
                self.metrics_collector.create_alert(
                    f"sync_partial_failure_{table_name}",
                    f"Sync for {table_name} had {100 - result.success_rate:.1f}% failure rate",
                    AlertSeverity.WARNING
                )
                
            logger.info(
                f"Completed sync for {table_name}: "
                f"{result.records_processed} processed, "
                f"{result.success_rate:.1f}% success"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Sync failed for {table_name}: {e}")
            
            # Track errors
            if table_name not in self.sync_errors:
                self.sync_errors[table_name] = []
            self.sync_errors[table_name].append(str(e))
            
            # Record error metrics
            self.metrics_collector.record_error(
                "sync_worker",
                f"sync_error_{table_name}",
                str(e)
            )
            
            # Create alert if multiple failures
            if len(self.sync_errors[table_name]) >= 3:
                self.metrics_collector.create_alert(
                    f"sync_repeated_failure_{table_name}",
                    f"Table {table_name} has failed sync {len(self.sync_errors[table_name])} times",
                    AlertSeverity.ERROR
                )
                
            raise
            
    async def run_sync_cycle(self):
        """Run a complete sync cycle for all tables."""
        logger.info(f"Starting sync cycle (mode: {self.config.mode.value})")
        
        cycle_start = datetime.utcnow()
        tables_synced = 0
        tables_failed = 0
        
        # Determine tables to sync
        tables_to_sync = self.config.tables_to_sync or self.sync_service.SYNC_ORDER
        
        for table_name in tables_to_sync:
            try:
                # Check if sync is needed
                if not self._should_sync_table(table_name):
                    logger.debug(f"Skipping {table_name} - recently synced")
                    continue
                    
                # Perform sync
                await self.sync_table(table_name)
                tables_synced += 1
                
                # Brief pause between tables
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to sync {table_name}: {e}")
                tables_failed += 1
                
        # Log cycle summary
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        logger.info(
            f"Sync cycle completed in {cycle_duration:.1f}s: "
            f"{tables_synced} synced, {tables_failed} failed"
        )
        
        # Record cycle metrics
        self.metrics_collector.record_sync_cycle(
            tables_synced=tables_synced,
            tables_failed=tables_failed,
            duration=cycle_duration
        )
        
        # Alert on failures
        if tables_failed > 0:
            self.metrics_collector.create_alert(
                "sync_cycle_failures",
                f"Sync cycle had {tables_failed} table failures",
                AlertSeverity.WARNING if tables_failed <= 2 else AlertSeverity.ERROR
            )
            
    def _should_sync_table(self, table_name: str) -> bool:
        """Check if a table should be synced."""
        # Always sync if never synced
        if table_name not in self.last_sync_times:
            return True
            
        # Check time since last sync
        time_since_sync = datetime.utcnow() - self.last_sync_times[table_name]
        
        # Different intervals for different modes
        if self.config.mode == SyncMode.REAL_TIME:
            return time_since_sync > timedelta(minutes=1)
        elif self.config.mode == SyncMode.INCREMENTAL:
            return time_since_sync > timedelta(minutes=self.config.interval_minutes)
        else:  # FULL
            return time_since_sync > timedelta(hours=1)
            
    async def monitor_sync_lag(self):
        """Monitor sync lag for all tables."""
        try:
            for table_name in self.last_sync_times:
                lag = (datetime.utcnow() - self.last_sync_times[table_name]).total_seconds() / 60
                
                # Record lag metric
                self.metrics_collector.record_sync_lag(table_name, lag)
                
                # Alert if lag is too high
                if lag > 30:  # 30 minutes
                    self.metrics_collector.create_alert(
                        f"high_sync_lag_{table_name}",
                        f"Table {table_name} has sync lag of {lag:.1f} minutes",
                        AlertSeverity.WARNING if lag < 60 else AlertSeverity.ERROR
                    )
                    
        except Exception as e:
            logger.error(f"Failed to monitor sync lag: {e}")
            
    async def run(self):
        """Main worker loop."""
        logger.info("Starting sync worker...")
        
        self.running = True
        
        try:
            await self.initialize()
            
            # Start sync service
            await self.sync_service.start()
            
            while self.running:
                try:
                    # Run sync cycle
                    await self.run_sync_cycle()
                    
                    # Monitor sync lag
                    await self.monitor_sync_lag()
                    
                    # Wait for next cycle
                    await asyncio.sleep(self.config.interval_minutes * 60)
                    
                except Exception as e:
                    logger.error(f"Error in sync loop: {e}")
                    await asyncio.sleep(30)  # Brief pause before retry
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.shutdown()
            
    async def shutdown(self):
        """Gracefully shutdown the worker."""
        logger.info("Shutting down sync worker...")
        
        self.running = False
        
        # Stop sync service
        await self.sync_service.stop()
        
        # Close connections
        await self.airtable_client.close()
        await self.supabase_client.close()
        
        # Final metrics flush
        self.metrics_collector.flush_metrics()
        
        # Log final stats
        logger.info(f"Final sync stats: {self.sync_stats}")
        
        logger.info("Sync worker stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run worker
    worker = SyncWorker()
    
    # Run async event loop
    try:
        asyncio.run(worker.run())
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)