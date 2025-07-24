"""
Data Completion Processor - Batch processing system for completing missing bill data.
Implements intelligent data completion strategies using existing scrapers and enhanced processing.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ...shared.src.shared.models.bill import Bill
from ...shared.src.shared.models.bill_process_history import (
    BillProcessHistory,
    HistoryChangeType,
    HistoryEventType,
)
from ..processor.bill_data_validator import BillDataValidator
from ..scraper.enhanced_diet_scraper import EnhancedDietScraper
from ..scraper.shugiin_scraper import ShugiinScraper
from .data_quality_auditor import DataQualityAuditor, QualityIssue, QualityIssueType


class CompletionStrategy(Enum):
    """Data completion strategies"""
    SCRAPE_MISSING = "scrape_missing"
    ENHANCE_EXISTING = "enhance_existing"
    VALIDATE_AND_FIX = "validate_and_fix"
    BULK_UPDATE = "bulk_update"


class CompletionPriority(Enum):
    """Completion priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CompletionTask:
    """Represents a data completion task"""
    bill_id: str
    strategy: CompletionStrategy
    priority: CompletionPriority
    target_fields: list[str]
    description: str
    estimated_effort: int  # Processing time in seconds
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self.task_id = f"{self.bill_id}_{self.strategy.value}_{int(self.created_at.timestamp())}"


@dataclass
class CompletionResult:
    """Result of a completion task"""
    task_id: str
    bill_id: str
    success: bool
    fields_completed: list[str]
    fields_failed: list[str]
    processing_time_ms: float
    error_message: str | None = None
    quality_improvement: float | None = None
    completed_at: datetime = field(default_factory=datetime.now)


@dataclass
class BatchCompletionResult:
    """Result of batch completion processing"""
    batch_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    total_processing_time_ms: float
    success_rate: float
    tasks_results: list[CompletionResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.now)


class DataCompletionProcessor:
    """Batch processor for completing missing bill data"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.quality_auditor = DataQualityAuditor(database_url)
        self.validator = BillDataValidator()
        self.sangiin_scraper = EnhancedDietScraper()
        self.shugiin_scraper = ShugiinScraper()

        # Processing configuration
        self.config = {
            'batch_size': 50,
            'max_concurrent_tasks': 10,
            'retry_attempts': 3,
            'retry_delay_seconds': 5,
            'timeout_seconds': 300,
            'quality_threshold': 0.8,
            'rate_limit_delay': 2.0  # Seconds between scraper requests
        }

        # Field completion priorities
        self.field_priorities = {
            'bill_outline': 1,
            'background_context': 2,
            'expected_effects': 3,
            'key_provisions': 4,
            'submitter_details': 5,
            'committee_assignments': 6
        }

        # Task execution history
        self.execution_history: list[BatchCompletionResult] = []
        self.max_history_entries = 100

    def generate_completion_plan(self, quality_issues: list[QualityIssue] | None = None) -> list[CompletionTask]:
        """Generate comprehensive completion plan based on quality issues"""
        self.logger.info("Generating data completion plan")

        try:
            # Get quality issues if not provided
            if quality_issues is None:
                audit_report = self.quality_auditor.conduct_full_audit()
                quality_issues = audit_report.issues

            # Group issues by bill and strategy
            completion_tasks = []
            bill_issues = self._group_issues_by_bill(quality_issues)

            for bill_id, issues in bill_issues.items():
                tasks = self._create_completion_tasks(bill_id, issues)
                completion_tasks.extend(tasks)

            # Sort tasks by priority and dependencies
            completion_tasks = self._prioritize_tasks(completion_tasks)

            self.logger.info(f"Generated {len(completion_tasks)} completion tasks")
            return completion_tasks

        except Exception as e:
            self.logger.error(f"Error generating completion plan: {e}")
            raise

    def execute_completion_plan(self, tasks: list[CompletionTask]) -> BatchCompletionResult:
        """Execute completion plan with batch processing"""
        batch_id = f"batch_{int(datetime.now().timestamp())}"
        self.logger.info(f"Executing completion plan {batch_id} with {len(tasks)} tasks")

        start_time = time.time()

        try:
            # Process tasks in batches
            batch_results = []

            for i in range(0, len(tasks), self.config['batch_size']):
                batch_tasks = tasks[i:i + self.config['batch_size']]
                self.logger.info(f"Processing batch {i//self.config['batch_size'] + 1} with {len(batch_tasks)} tasks")

                # Process batch with concurrency
                batch_result = self._process_batch(batch_tasks)
                batch_results.extend(batch_result)

                # Rate limiting between batches
                if i + self.config['batch_size'] < len(tasks):
                    time.sleep(self.config['rate_limit_delay'])

            # Compile results
            processing_time = (time.time() - start_time) * 1000

            completed_tasks = len([r for r in batch_results if r.success])
            failed_tasks = len([r for r in batch_results if not r.success])
            success_rate = completed_tasks / len(tasks) if tasks else 0

            result = BatchCompletionResult(
                batch_id=batch_id,
                total_tasks=len(tasks),
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                skipped_tasks=0,
                total_processing_time_ms=processing_time,
                success_rate=success_rate,
                tasks_results=batch_results,
                performance_metrics=self._calculate_performance_metrics(batch_results)
            )

            # Store execution history
            self._store_execution_history(result)

            self.logger.info(f"Batch completion finished: {completed_tasks}/{len(tasks)} tasks completed")
            return result

        except Exception as e:
            self.logger.error(f"Error executing completion plan: {e}")

            # Return failed result
            return BatchCompletionResult(
                batch_id=batch_id,
                total_tasks=len(tasks),
                completed_tasks=0,
                failed_tasks=len(tasks),
                skipped_tasks=0,
                total_processing_time_ms=(time.time() - start_time) * 1000,
                success_rate=0,
                errors=[str(e)]
            )

    def _group_issues_by_bill(self, issues: list[QualityIssue]) -> dict[str, list[QualityIssue]]:
        """Group quality issues by bill ID"""
        bill_issues = {}
        for issue in issues:
            if issue.bill_id not in bill_issues:
                bill_issues[issue.bill_id] = []
            bill_issues[issue.bill_id].append(issue)
        return bill_issues

    def _create_completion_tasks(self, bill_id: str, issues: list[QualityIssue]) -> list[CompletionTask]:
        """Create completion tasks for a bill based on its issues"""
        tasks = []

        # Group issues by type
        missing_fields = []
        inconsistent_fields = []
        poor_quality_fields = []

        for issue in issues:
            if issue.issue_type in [QualityIssueType.MISSING_REQUIRED_FIELD, QualityIssueType.EMPTY_FIELD]:
                missing_fields.append(issue.field_name)
            elif issue.issue_type == QualityIssueType.INCONSISTENT_DATA:
                inconsistent_fields.append(issue.field_name)
            elif issue.issue_type == QualityIssueType.POOR_JAPANESE_TEXT:
                poor_quality_fields.append(issue.field_name)

        # Create tasks based on issue types
        if missing_fields:
            priority = self._determine_task_priority(missing_fields)
            tasks.append(CompletionTask(
                bill_id=bill_id,
                strategy=CompletionStrategy.SCRAPE_MISSING,
                priority=priority,
                target_fields=missing_fields,
                description=f"Scrape missing fields: {', '.join(missing_fields)}",
                estimated_effort=len(missing_fields) * 10,
                metadata={'issue_types': ['missing_field']}
            ))

        if inconsistent_fields:
            tasks.append(CompletionTask(
                bill_id=bill_id,
                strategy=CompletionStrategy.VALIDATE_AND_FIX,
                priority=CompletionPriority.HIGH,
                target_fields=inconsistent_fields,
                description=f"Fix inconsistent fields: {', '.join(inconsistent_fields)}",
                estimated_effort=len(inconsistent_fields) * 5,
                metadata={'issue_types': ['inconsistent_data']}
            ))

        if poor_quality_fields:
            tasks.append(CompletionTask(
                bill_id=bill_id,
                strategy=CompletionStrategy.ENHANCE_EXISTING,
                priority=CompletionPriority.MEDIUM,
                target_fields=poor_quality_fields,
                description=f"Enhance text quality: {', '.join(poor_quality_fields)}",
                estimated_effort=len(poor_quality_fields) * 8,
                metadata={'issue_types': ['poor_quality']}
            ))

        return tasks

    def _determine_task_priority(self, fields: list[str]) -> CompletionPriority:
        """Determine task priority based on fields"""
        if not fields:
            return CompletionPriority.LOW

        # Check if any critical fields are missing
        critical_fields = ['bill_outline', 'title', 'status']
        if any(field in critical_fields for field in fields):
            return CompletionPriority.CRITICAL

        # Check field priorities
        min_priority = min(self.field_priorities.get(field, 10) for field in fields)

        if min_priority <= 2:
            return CompletionPriority.HIGH
        elif min_priority <= 4:
            return CompletionPriority.MEDIUM
        else:
            return CompletionPriority.LOW

    def _prioritize_tasks(self, tasks: list[CompletionTask]) -> list[CompletionTask]:
        """Sort tasks by priority and dependencies"""
        # Sort by priority first
        priority_order = {
            CompletionPriority.CRITICAL: 0,
            CompletionPriority.HIGH: 1,
            CompletionPriority.MEDIUM: 2,
            CompletionPriority.LOW: 3
        }

        return sorted(tasks, key=lambda t: (priority_order[t.priority], t.estimated_effort))

    def _process_batch(self, tasks: list[CompletionTask]) -> list[CompletionResult]:
        """Process a batch of tasks with concurrency"""
        results = []

        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=self.config['max_concurrent_tasks']) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._execute_task, task): task
                for task in tasks
            }

            # Collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result(timeout=self.config['timeout_seconds'])
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Task {task.task_id} failed: {e}")
                    results.append(CompletionResult(
                        task_id=task.task_id,
                        bill_id=task.bill_id,
                        success=False,
                        fields_completed=[],
                        fields_failed=task.target_fields,
                        processing_time_ms=0,
                        error_message=str(e)
                    ))

        return results

    def _execute_task(self, task: CompletionTask) -> CompletionResult:
        """Execute a single completion task"""
        start_time = time.time()

        try:
            self.logger.debug(f"Executing task {task.task_id}")

            # Get current bill data
            with self.SessionLocal() as session:
                bill = session.execute(
                    select(Bill).where(Bill.bill_id == task.bill_id)
                ).scalar_one_or_none()

                if not bill:
                    return CompletionResult(
                        task_id=task.task_id,
                        bill_id=task.bill_id,
                        success=False,
                        fields_completed=[],
                        fields_failed=task.target_fields,
                        processing_time_ms=0,
                        error_message="Bill not found"
                    )

                # Execute strategy
                if task.strategy == CompletionStrategy.SCRAPE_MISSING:
                    result = self._scrape_missing_data(bill, task.target_fields)
                elif task.strategy == CompletionStrategy.ENHANCE_EXISTING:
                    result = self._enhance_existing_data(bill, task.target_fields)
                elif task.strategy == CompletionStrategy.VALIDATE_AND_FIX:
                    result = self._validate_and_fix_data(bill, task.target_fields)
                else:
                    result = self._bulk_update_data(bill, task.target_fields)

                # Calculate processing time
                processing_time = (time.time() - start_time) * 1000

                # Create result
                completion_result = CompletionResult(
                    task_id=task.task_id,
                    bill_id=task.bill_id,
                    success=result['success'],
                    fields_completed=result['completed_fields'],
                    fields_failed=result['failed_fields'],
                    processing_time_ms=processing_time,
                    error_message=result.get('error'),
                    quality_improvement=result.get('quality_improvement')
                )

                # Record completion in history
                if result['success']:
                    self._record_completion_history(bill, task, completion_result)

                return completion_result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(f"Task execution failed: {e}")

            return CompletionResult(
                task_id=task.task_id,
                bill_id=task.bill_id,
                success=False,
                fields_completed=[],
                fields_failed=task.target_fields,
                processing_time_ms=processing_time,
                error_message=str(e)
            )

    def _scrape_missing_data(self, bill: Bill, target_fields: list[str]) -> dict[str, Any]:
        """Scrape missing data for specified fields"""
        try:
            completed_fields = []
            failed_fields = []

            # Determine which scraper to use
            if bill.house_of_origin == "参議院":
                scraper = self.sangiin_scraper
            else:
                scraper = self.shugiin_scraper

            # Scrape enhanced data
            enhanced_data = scraper.scrape_enhanced_bill_data(bill.bill_id)

            if enhanced_data:
                # Update fields
                for field in target_fields:
                    if field in enhanced_data and enhanced_data[field]:
                        setattr(bill, field, enhanced_data[field])
                        completed_fields.append(field)
                    else:
                        failed_fields.append(field)

                # Update quality score
                if hasattr(bill, 'data_quality_score'):
                    bill.data_quality_score = self._calculate_quality_score(bill)

                return {
                    'success': True,
                    'completed_fields': completed_fields,
                    'failed_fields': failed_fields,
                    'quality_improvement': 0.1 * len(completed_fields)  # Rough estimate
                }
            else:
                return {
                    'success': False,
                    'completed_fields': [],
                    'failed_fields': target_fields,
                    'error': 'Scraping failed'
                }

        except Exception as e:
            return {
                'success': False,
                'completed_fields': [],
                'failed_fields': target_fields,
                'error': str(e)
            }

    def _enhance_existing_data(self, bill: Bill, target_fields: list[str]) -> dict[str, Any]:
        """Enhance existing data quality"""
        try:
            completed_fields = []
            failed_fields = []

            for field in target_fields:
                current_value = getattr(bill, field, None)

                if current_value and isinstance(current_value, str):
                    # Enhance text quality
                    enhanced_value = self._enhance_text_quality(current_value)

                    if enhanced_value != current_value:
                        setattr(bill, field, enhanced_value)
                        completed_fields.append(field)
                    else:
                        failed_fields.append(field)
                else:
                    failed_fields.append(field)

            return {
                'success': len(completed_fields) > 0,
                'completed_fields': completed_fields,
                'failed_fields': failed_fields,
                'quality_improvement': 0.05 * len(completed_fields)
            }

        except Exception as e:
            return {
                'success': False,
                'completed_fields': [],
                'failed_fields': target_fields,
                'error': str(e)
            }

    def _validate_and_fix_data(self, bill: Bill, target_fields: list[str]) -> dict[str, Any]:
        """Validate and fix data inconsistencies"""
        try:
            completed_fields = []
            failed_fields = []

            # Validate bill
            validation_result = self.validator.validate_bill(bill.__dict__)

            # Fix validation issues
            for issue in validation_result.issues:
                if issue.field_name in target_fields:
                    fix_applied = self._apply_validation_fix(bill, issue)
                    if fix_applied:
                        completed_fields.append(issue.field_name)
                    else:
                        failed_fields.append(issue.field_name)

            return {
                'success': len(completed_fields) > 0,
                'completed_fields': completed_fields,
                'failed_fields': failed_fields,
                'quality_improvement': 0.08 * len(completed_fields)
            }

        except Exception as e:
            return {
                'success': False,
                'completed_fields': [],
                'failed_fields': target_fields,
                'error': str(e)
            }

    def _bulk_update_data(self, bill: Bill, target_fields: list[str]) -> dict[str, Any]:
        """Perform bulk data updates"""
        try:
            completed_fields = []
            failed_fields = []

            # Apply bulk updates based on field type
            for field in target_fields:
                if self._apply_bulk_update(bill, field):
                    completed_fields.append(field)
                else:
                    failed_fields.append(field)

            return {
                'success': len(completed_fields) > 0,
                'completed_fields': completed_fields,
                'failed_fields': failed_fields,
                'quality_improvement': 0.03 * len(completed_fields)
            }

        except Exception as e:
            return {
                'success': False,
                'completed_fields': [],
                'failed_fields': target_fields,
                'error': str(e)
            }

    def _enhance_text_quality(self, text: str) -> str:
        """Enhance Japanese text quality"""
        # Basic text enhancement
        enhanced = text.strip()

        # Remove duplicate spaces
        enhanced = ' '.join(enhanced.split())

        # Ensure proper Japanese punctuation
        enhanced = enhanced.replace('。。', '。').replace('、、', '、')

        return enhanced

    def _apply_validation_fix(self, bill: Bill, issue) -> bool:
        """Apply validation fix for a specific issue"""
        try:
            # Apply field-specific fixes
            if issue.field_name == 'status':
                # Fix status values
                current_status = getattr(bill, 'status', None)
                if current_status:
                    fixed_status = self._fix_status_value(current_status)
                    if fixed_status != current_status:
                        setattr(bill, 'status', fixed_status)
                        return True

            elif issue.field_name == 'submitted_date':
                # Fix date formatting
                current_date = getattr(bill, 'submitted_date', None)
                if current_date:
                    fixed_date = self._fix_date_value(current_date)
                    if fixed_date != current_date:
                        setattr(bill, 'submitted_date', fixed_date)
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Error applying validation fix: {e}")
            return False

    def _apply_bulk_update(self, bill: Bill, field: str) -> bool:
        """Apply bulk update for a field"""
        try:
            # Field-specific bulk updates
            if field == 'data_quality_score':
                score = self._calculate_quality_score(bill)
                setattr(bill, field, score)
                return True

            elif field == 'source_house':
                # Set source house based on house_of_origin
                if hasattr(bill, 'house_of_origin') and bill.house_of_origin:
                    setattr(bill, field, bill.house_of_origin)
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error applying bulk update: {e}")
            return False

    def _fix_status_value(self, status: str) -> str:
        """Fix status value formatting"""
        status_mapping = {
            '提出済み': '提出',
            '審議中': '審議中',
            '可決済み': '可決',
            '否決済み': '否決',
            '成立済み': '成立',
            '廃案済み': '廃案'
        }
        return status_mapping.get(status, status)

    def _fix_date_value(self, date_value: Any) -> Any:
        """Fix date value formatting"""
        # This would implement date fixing logic
        return date_value

    def _calculate_quality_score(self, bill: Bill) -> float:
        """Calculate quality score for a bill"""
        score = 0.0
        max_score = 0.0

        # Score based on field completeness and quality
        for field, weight in self.field_priorities.items():
            max_score += weight
            value = getattr(bill, field, None)

            if value is not None:
                if isinstance(value, str) and len(value.strip()) > 10:
                    score += weight
                elif not isinstance(value, str):
                    score += weight
                else:
                    score += weight * 0.5  # Partial credit

        return score / max_score if max_score > 0 else 0.0

    def _record_completion_history(self, bill: Bill, task: CompletionTask, result: CompletionResult):
        """Record completion in bill history"""
        try:
            with self.SessionLocal() as session:
                # Create history record
                history_record = BillProcessHistory(
                    bill_id=bill.bill_id,
                    event_type=HistoryEventType.DATA_COMPLETION,
                    change_type=HistoryChangeType.DATA_ENHANCEMENT,
                    recorded_at=datetime.now(),
                    change_summary=f"Data completion: {task.description}",
                    confidence_score=0.9,
                    source_system="data_completion_processor",
                    previous_values={},
                    new_values={
                        'completed_fields': result.fields_completed,
                        'strategy': task.strategy.value
                    },
                    metadata={
                        'task_id': task.task_id,
                        'processing_time_ms': result.processing_time_ms,
                        'quality_improvement': result.quality_improvement
                    }
                )

                session.add(history_record)
                session.commit()

        except Exception as e:
            self.logger.error(f"Error recording completion history: {e}")

    def _calculate_performance_metrics(self, results: list[CompletionResult]) -> dict[str, Any]:
        """Calculate performance metrics from results"""
        if not results:
            return {}

        total_time = sum(r.processing_time_ms for r in results)
        avg_time = total_time / len(results)

        quality_improvements = [r.quality_improvement for r in results if r.quality_improvement]
        avg_quality_improvement = sum(quality_improvements) / len(quality_improvements) if quality_improvements else 0

        return {
            'average_processing_time_ms': avg_time,
            'total_processing_time_ms': total_time,
            'average_quality_improvement': avg_quality_improvement,
            'fields_completed_total': sum(len(r.fields_completed) for r in results),
            'fields_failed_total': sum(len(r.fields_failed) for r in results)
        }

    def _store_execution_history(self, result: BatchCompletionResult):
        """Store execution history"""
        self.execution_history.append(result)

        # Keep only recent entries
        if len(self.execution_history) > self.max_history_entries:
            self.execution_history.pop(0)

    def get_completion_statistics(self, days: int = 30) -> dict[str, Any]:
        """Get completion statistics for the specified period"""
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_results = [
            result for result in self.execution_history
            if result.completed_at > cutoff_date
        ]

        if not recent_results:
            return {
                'period_days': days,
                'total_batches': 0,
                'total_tasks': 0,
                'success_rate': 0.0
            }

        total_batches = len(recent_results)
        total_tasks = sum(r.total_tasks for r in recent_results)
        completed_tasks = sum(r.completed_tasks for r in recent_results)

        return {
            'period_days': days,
            'total_batches': total_batches,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': sum(r.failed_tasks for r in recent_results),
            'success_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'average_processing_time_ms': sum(r.total_processing_time_ms for r in recent_results) / total_batches,
            'total_processing_time_ms': sum(r.total_processing_time_ms for r in recent_results)
        }

    def get_recent_completions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent completion results"""
        recent_results = self.execution_history[-limit:] if self.execution_history else []

        return [
            {
                'batch_id': result.batch_id,
                'completed_at': result.completed_at.isoformat(),
                'total_tasks': result.total_tasks,
                'completed_tasks': result.completed_tasks,
                'success_rate': result.success_rate,
                'processing_time_ms': result.total_processing_time_ms
            }
            for result in recent_results
        ]

    def export_completion_report(self, batch_result: BatchCompletionResult, format: str = "json") -> dict[str, Any]:
        """Export completion report"""
        if format == "json":
            return {
                'batch_id': batch_result.batch_id,
                'completed_at': batch_result.completed_at.isoformat(),
                'summary': {
                    'total_tasks': batch_result.total_tasks,
                    'completed_tasks': batch_result.completed_tasks,
                    'failed_tasks': batch_result.failed_tasks,
                    'success_rate': batch_result.success_rate,
                    'total_processing_time_ms': batch_result.total_processing_time_ms
                },
                'performance_metrics': batch_result.performance_metrics,
                'task_results': [
                    {
                        'task_id': result.task_id,
                        'bill_id': result.bill_id,
                        'success': result.success,
                        'fields_completed': result.fields_completed,
                        'fields_failed': result.fields_failed,
                        'processing_time_ms': result.processing_time_ms,
                        'quality_improvement': result.quality_improvement,
                        'error_message': result.error_message
                    }
                    for result in batch_result.tasks_results
                ],
                'errors': batch_result.errors
            }
        else:
            return {'error': f'Unsupported format: {format}'}
