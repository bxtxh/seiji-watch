"""
History Recording Scheduler - Manages scheduled execution of bill history recording.
Provides periodic change detection and recording with configurable intervals.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import schedule
import time
from threading import Thread, Event
import json

from ..processor.bill_history_recorder import (
    BillHistoryRecorder, 
    ChangeDetectionMode, 
    HistoryRecordingResult
)


class ScheduleFrequency(Enum):
    """Scheduling frequency options"""
    EVERY_MINUTE = "every_minute"
    EVERY_5_MINUTES = "every_5_minutes"
    EVERY_15_MINUTES = "every_15_minutes"
    EVERY_30_MINUTES = "every_30_minutes"
    HOURLY = "hourly"
    EVERY_2_HOURS = "every_2_hours"
    EVERY_4_HOURS = "every_4_hours"
    EVERY_6_HOURS = "every_6_hours"
    EVERY_12_HOURS = "every_12_hours"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class ScheduleConfig:
    """Configuration for scheduled history recording"""
    frequency: ScheduleFrequency
    detection_mode: ChangeDetectionMode = ChangeDetectionMode.INCREMENTAL
    max_execution_time_minutes: int = 30
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 300
    
    # Advanced options
    enable_full_scan_weekly: bool = True
    full_scan_day: str = "sunday"
    full_scan_time: str = "02:00"
    
    # Monitoring options
    enable_metrics: bool = True
    alert_on_errors: bool = True
    max_consecutive_failures: int = 5


@dataclass
class ScheduleStatus:
    """Status of scheduled history recording"""
    is_running: bool = False
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    consecutive_failures: int = 0
    
    # Performance metrics
    average_execution_time_ms: float = 0.0
    last_execution_time_ms: float = 0.0
    total_changes_recorded: int = 0
    
    # Recent results
    recent_results: List[HistoryRecordingResult] = field(default_factory=list)


class HistoryRecordingScheduler:
    """Scheduler for automatic bill history recording"""
    
    def __init__(self, database_url: str, config: Optional[ScheduleConfig] = None):
        self.database_url = database_url
        self.config = config or ScheduleConfig(
            frequency=ScheduleFrequency.EVERY_30_MINUTES,
            detection_mode=ChangeDetectionMode.INCREMENTAL
        )
        
        self.logger = logging.getLogger(__name__)
        self.history_recorder = BillHistoryRecorder(database_url)
        
        # Scheduler state
        self.status = ScheduleStatus()
        self.stop_event = Event()
        self.scheduler_thread: Optional[Thread] = None
        
        # Metrics tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.max_history_entries = 1000
        
        # Initialize schedule
        self._setup_schedule()
    
    def _setup_schedule(self):
        """Set up the scheduled tasks"""
        schedule.clear()
        
        # Main incremental recording schedule
        if self.config.frequency == ScheduleFrequency.EVERY_MINUTE:
            schedule.every().minute.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_5_MINUTES:
            schedule.every(5).minutes.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_15_MINUTES:
            schedule.every(15).minutes.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_30_MINUTES:
            schedule.every(30).minutes.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.HOURLY:
            schedule.every().hour.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_2_HOURS:
            schedule.every(2).hours.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_4_HOURS:
            schedule.every(4).hours.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_6_HOURS:
            schedule.every(6).hours.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.EVERY_12_HOURS:
            schedule.every(12).hours.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.DAILY:
            schedule.every().day.do(self._execute_history_recording)
        elif self.config.frequency == ScheduleFrequency.WEEKLY:
            schedule.every().week.do(self._execute_history_recording)
        
        # Optional weekly full scan
        if self.config.enable_full_scan_weekly:
            if self.config.full_scan_day.lower() == "sunday":
                schedule.every().sunday.at(self.config.full_scan_time).do(
                    self._execute_full_scan
                )
            elif self.config.full_scan_day.lower() == "monday":
                schedule.every().monday.at(self.config.full_scan_time).do(
                    self._execute_full_scan
                )
            elif self.config.full_scan_day.lower() == "saturday":
                schedule.every().saturday.at(self.config.full_scan_time).do(
                    self._execute_full_scan
                )
        
        # Daily cleanup task
        schedule.every().day.at("01:00").do(self._cleanup_old_data)
        
        self.logger.info(f"Scheduled history recording every {self.config.frequency.value}")
    
    def start(self):
        """Start the scheduler"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.warning("Scheduler is already running")
            return
        
        self.stop_event.clear()
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("History recording scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        
        self.logger.info("History recording scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while not self.stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _execute_history_recording(self):
        """Execute history recording task"""
        if self.status.is_running:
            self.logger.warning("History recording is already running, skipping execution")
            return
        
        start_time = datetime.now()
        self.status.is_running = True
        self.status.last_execution = start_time
        
        try:
            self.logger.info("Starting scheduled history recording")
            
            # Execute with retry logic
            result = self._execute_with_retry(
                lambda: self.history_recorder.detect_and_record_changes(
                    mode=self.config.detection_mode
                )
            )
            
            # Update status
            self.status.successful_executions += 1
            self.status.consecutive_failures = 0
            self.status.total_changes_recorded += result.changes_detected
            
            # Update performance metrics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.status.last_execution_time_ms = execution_time
            self._update_average_execution_time(execution_time)
            
            # Store result
            self.status.recent_results.append(result)
            if len(self.status.recent_results) > 10:
                self.status.recent_results.pop(0)
            
            # Log result
            self.logger.info(
                f"History recording completed successfully: "
                f"{result.changes_detected} changes detected, "
                f"{result.history_records_created} records created in {execution_time:.1f}ms"
            )
            
            # Store detailed execution history
            self._store_execution_history(True, result, execution_time)
            
        except Exception as e:
            self.logger.error(f"History recording failed: {e}")
            
            # Update failure status
            self.status.failed_executions += 1
            self.status.consecutive_failures += 1
            
            # Store failure history
            self._store_execution_history(False, None, 0, str(e))
            
            # Check if we need to alert
            if (self.config.alert_on_errors and 
                self.status.consecutive_failures >= self.config.max_consecutive_failures):
                self._send_failure_alert()
        
        finally:
            self.status.is_running = False
            self.status.total_executions += 1
    
    def _execute_full_scan(self):
        """Execute full scan history recording"""
        self.logger.info("Starting weekly full scan history recording")
        
        start_time = datetime.now()
        
        try:
            # Use full scan mode
            result = self.history_recorder.detect_and_record_changes(
                mode=ChangeDetectionMode.FULL_SCAN
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.logger.info(
                f"Full scan completed: {result.changes_detected} changes detected, "
                f"{result.history_records_created} records created in {execution_time:.1f}ms"
            )
            
            # Store full scan history
            self._store_execution_history(True, result, execution_time, execution_type="full_scan")
            
        except Exception as e:
            self.logger.error(f"Full scan failed: {e}")
            self._store_execution_history(False, None, 0, str(e), execution_type="full_scan")
    
    def _execute_with_retry(self, operation) -> HistoryRecordingResult:
        """Execute operation with retry logic"""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return operation()
            except Exception as e:
                last_error = e
                
                if attempt < self.config.max_retries:
                    self.logger.warning(
                        f"History recording attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {self.config.retry_delay_seconds} seconds..."
                    )
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    self.logger.error(f"All {self.config.max_retries + 1} attempts failed")
        
        # If we get here, all retries failed
        raise last_error
    
    def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            self.logger.info("Starting daily cleanup of old history data")
            
            # Clean up old snapshots
            self.history_recorder.cleanup_old_snapshots()
            
            # Clean up old execution history
            cutoff_date = datetime.now() - timedelta(days=30)
            self.execution_history = [
                entry for entry in self.execution_history 
                if entry['timestamp'] > cutoff_date
            ]
            
            self.logger.info("Daily cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error in daily cleanup: {e}")
    
    def _update_average_execution_time(self, execution_time: float):
        """Update average execution time"""
        if self.status.average_execution_time_ms == 0:
            self.status.average_execution_time_ms = execution_time
        else:
            # Simple moving average
            self.status.average_execution_time_ms = (
                self.status.average_execution_time_ms * 0.9 + 
                execution_time * 0.1
            )
    
    def _store_execution_history(
        self, 
        success: bool, 
        result: Optional[HistoryRecordingResult], 
        execution_time: float,
        error_message: Optional[str] = None,
        execution_type: str = "regular"
    ):
        """Store execution history for monitoring"""
        history_entry = {
            'timestamp': datetime.now(),
            'success': success,
            'execution_time_ms': execution_time,
            'execution_type': execution_type,
            'error_message': error_message
        }
        
        if result:
            history_entry.update({
                'total_bills_checked': result.total_bills_checked,
                'changes_detected': result.changes_detected,
                'history_records_created': result.history_records_created,
                'changes_by_type': result.changes_by_type,
                'changes_by_significance': result.changes_by_significance
            })
        
        self.execution_history.append(history_entry)
        
        # Keep only recent entries
        if len(self.execution_history) > self.max_history_entries:
            self.execution_history.pop(0)
    
    def _send_failure_alert(self):
        """Send alert for consecutive failures"""
        self.logger.critical(
            f"History recording has failed {self.status.consecutive_failures} "
            f"consecutive times. Manual intervention may be required."
        )
        
        # In a real implementation, this would send notifications
        # via email, Slack, PagerDuty, etc.
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        next_run = None
        if schedule.jobs:
            next_run = min(job.next_run for job in schedule.jobs)
        
        return {
            'is_running': self.status.is_running,
            'last_execution': self.status.last_execution.isoformat() if self.status.last_execution else None,
            'next_execution': next_run.isoformat() if next_run else None,
            'total_executions': self.status.total_executions,
            'successful_executions': self.status.successful_executions,
            'failed_executions': self.status.failed_executions,
            'consecutive_failures': self.status.consecutive_failures,
            'success_rate': (
                self.status.successful_executions / self.status.total_executions 
                if self.status.total_executions > 0 else 0
            ),
            'average_execution_time_ms': self.status.average_execution_time_ms,
            'last_execution_time_ms': self.status.last_execution_time_ms,
            'total_changes_recorded': self.status.total_changes_recorded,
            'configuration': {
                'frequency': self.config.frequency.value,
                'detection_mode': self.config.detection_mode.value,
                'max_execution_time_minutes': self.config.max_execution_time_minutes,
                'retry_on_failure': self.config.retry_on_failure,
                'max_retries': self.config.max_retries,
                'enable_full_scan_weekly': self.config.enable_full_scan_weekly
            }
        }
    
    def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution results"""
        recent_history = self.execution_history[-limit:] if self.execution_history else []
        return [
            {
                'timestamp': entry['timestamp'].isoformat(),
                'success': entry['success'],
                'execution_time_ms': entry['execution_time_ms'],
                'execution_type': entry.get('execution_type', 'regular'),
                'changes_detected': entry.get('changes_detected', 0),
                'history_records_created': entry.get('history_records_created', 0),
                'error_message': entry.get('error_message')
            }
            for entry in recent_history
        ]
    
    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get performance metrics for the specified period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter recent history
        recent_history = [
            entry for entry in self.execution_history 
            if entry['timestamp'] > cutoff_date
        ]
        
        if not recent_history:
            return {
                'period_days': days,
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'success_rate': 0.0,
                'average_execution_time_ms': 0.0,
                'total_changes_detected': 0,
                'total_records_created': 0
            }
        
        successful = [entry for entry in recent_history if entry['success']]
        failed = [entry for entry in recent_history if not entry['success']]
        
        return {
            'period_days': days,
            'total_executions': len(recent_history),
            'successful_executions': len(successful),
            'failed_executions': len(failed),
            'success_rate': len(successful) / len(recent_history),
            'average_execution_time_ms': (
                sum(entry['execution_time_ms'] for entry in successful) / len(successful)
                if successful else 0
            ),
            'total_changes_detected': sum(
                entry.get('changes_detected', 0) for entry in successful
            ),
            'total_records_created': sum(
                entry.get('history_records_created', 0) for entry in successful
            ),
            'most_recent_error': (
                failed[-1]['error_message'] if failed else None
            )
        }
    
    def force_execution(self) -> Dict[str, Any]:
        """Force immediate execution of history recording"""
        self.logger.info("Forcing immediate history recording execution")
        
        start_time = datetime.now()
        
        try:
            result = self.history_recorder.detect_and_record_changes(
                mode=self.config.detection_mode
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Store forced execution history
            self._store_execution_history(True, result, execution_time, execution_type="manual")
            
            return {
                'success': True,
                'execution_time_ms': execution_time,
                'changes_detected': result.changes_detected,
                'history_records_created': result.history_records_created,
                'bills_checked': result.total_bills_checked
            }
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self._store_execution_history(False, None, execution_time, str(e), execution_type="manual")
            
            return {
                'success': False,
                'execution_time_ms': execution_time,
                'error_message': str(e)
            }
    
    def update_config(self, new_config: ScheduleConfig):
        """Update scheduler configuration"""
        self.config = new_config
        self._setup_schedule()
        self.logger.info(f"Scheduler configuration updated: {new_config.frequency.value}")
    
    def get_change_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get change statistics from the history recorder"""
        return self.history_recorder.get_change_statistics(days)