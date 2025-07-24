"""
Data Migration Service - Coordinates data quality auditing and completion processing.
Provides high-level interface for managing data migration and quality improvement operations.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .data_completion_processor import (
    BatchCompletionResult,
    CompletionTask,
    DataCompletionProcessor,
)
from .data_quality_auditor import DataQualityAuditor, QualityIssue, QualityReport


class MigrationPhase(Enum):
    """Migration phases"""
    AUDIT = "audit"
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    COMPLETION = "completion"


class MigrationStatus(Enum):
    """Migration status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MigrationPlan:
    """Data migration plan"""
    plan_id: str
    total_bills: int
    total_tasks: int
    estimated_time_hours: float
    priority_breakdown: dict[str, int]
    phases: list[MigrationPhase]
    completion_tasks: list[CompletionTask] = field(default_factory=list)
    quality_issues: list[QualityIssue] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.plan_id:
            self.plan_id = f"migration_{int(self.created_at.timestamp())}"


@dataclass
class MigrationExecution:
    """Migration execution tracking"""
    execution_id: str
    plan_id: str
    status: MigrationStatus
    current_phase: MigrationPhase
    started_at: datetime
    completed_at: datetime | None = None
    progress_percentage: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    errors: list[str] = field(default_factory=list)
    phase_results: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.execution_id:
            self.execution_id = f"execution_{int(self.started_at.timestamp())}"


@dataclass
class MigrationReport:
    """Comprehensive migration report"""
    plan_id: str
    execution_id: str
    migration_completed_at: datetime

    # Quality metrics
    initial_quality_report: QualityReport
    final_quality_report: QualityReport | None = None
    quality_improvement: dict[str, float] = field(default_factory=dict)

    # Completion metrics
    batch_results: list[BatchCompletionResult] = field(default_factory=list)
    total_fields_completed: int = 0
    total_bills_improved: int = 0

    # Performance metrics
    total_processing_time_ms: float = 0.0
    phases_timing: dict[str, float] = field(default_factory=dict)

    # Summary
    success_rate: float = 0.0
    recommendations: list[str] = field(default_factory=list)


class DataMigrationService:
    """High-level service for data migration operations"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.quality_auditor = DataQualityAuditor(database_url)
        self.completion_processor = DataCompletionProcessor(database_url)

        # Service configuration
        self.config = {
            'max_concurrent_migrations': 1,
            'auto_validate_after_completion': True,
            'backup_before_migration': True,
            'report_export_format': 'json',
            'cleanup_old_reports': True,
            'report_retention_days': 90
        }

        # Migration history
        self.migration_history: list[MigrationExecution] = []
        self.migration_reports: list[MigrationReport] = []

        # Create reports directory
        self.reports_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)

    def create_migration_plan(self, target_bills: list[str] | None = None) -> MigrationPlan:
        """Create comprehensive migration plan"""
        self.logger.info("Creating migration plan")

        try:
            # Conduct quality audit
            self.logger.info("Conducting quality audit...")
            audit_report = self.quality_auditor.conduct_full_audit()

            # Filter issues for target bills if specified
            if target_bills:
                filtered_issues = [
                    issue for issue in audit_report.issues
                    if issue.bill_id in target_bills
                ]
            else:
                filtered_issues = audit_report.issues

            # Generate completion tasks
            self.logger.info("Generating completion tasks...")
            completion_tasks = self.completion_processor.generate_completion_plan(filtered_issues)

            # Calculate estimates
            total_bills = len(set(issue.bill_id for issue in filtered_issues))
            total_tasks = len(completion_tasks)
            estimated_time = self._estimate_migration_time(completion_tasks)

            # Analyze priorities
            priority_breakdown = self._analyze_task_priorities(completion_tasks)

            # Define phases
            phases = [
                MigrationPhase.AUDIT,
                MigrationPhase.PLANNING,
                MigrationPhase.EXECUTION,
                MigrationPhase.VALIDATION,
                MigrationPhase.COMPLETION
            ]

            plan = MigrationPlan(
                plan_id="",  # Will be auto-generated
                total_bills=total_bills,
                total_tasks=total_tasks,
                estimated_time_hours=estimated_time,
                priority_breakdown=priority_breakdown,
                phases=phases,
                completion_tasks=completion_tasks,
                quality_issues=filtered_issues
            )

            self.logger.info(f"Migration plan created: {total_tasks} tasks for {total_bills} bills")
            return plan

        except Exception as e:
            self.logger.error(f"Error creating migration plan: {e}")
            raise

    def execute_migration(self, plan: MigrationPlan) -> MigrationExecution:
        """Execute migration plan"""
        self.logger.info(f"Starting migration execution for plan {plan.plan_id}")

        execution = MigrationExecution(
            execution_id="",  # Will be auto-generated
            plan_id=plan.plan_id,
            status=MigrationStatus.RUNNING,
            current_phase=MigrationPhase.AUDIT,
            started_at=datetime.now()
        )

        try:
            # Phase 1: Audit (already done in planning)
            self.logger.info("Phase 1: Audit completed during planning")
            execution.phase_results['audit'] = {
                'quality_issues_found': len(plan.quality_issues),
                'completion_tasks_generated': len(plan.completion_tasks)
            }

            # Phase 2: Planning (already done)
            execution.current_phase = MigrationPhase.PLANNING
            self.logger.info("Phase 2: Planning completed")
            execution.phase_results['planning'] = {
                'total_tasks': plan.total_tasks,
                'estimated_time_hours': plan.estimated_time_hours
            }

            # Phase 3: Execution
            execution.current_phase = MigrationPhase.EXECUTION
            self.logger.info("Phase 3: Starting execution")

            batch_result = self.completion_processor.execute_completion_plan(plan.completion_tasks)

            execution.tasks_completed = batch_result.completed_tasks
            execution.tasks_failed = batch_result.failed_tasks
            execution.phase_results['execution'] = {
                'batch_id': batch_result.batch_id,
                'success_rate': batch_result.success_rate,
                'processing_time_ms': batch_result.total_processing_time_ms
            }

            # Phase 4: Validation
            execution.current_phase = MigrationPhase.VALIDATION
            self.logger.info("Phase 4: Starting validation")

            if self.config['auto_validate_after_completion']:
                validation_result = self._validate_migration_results(plan, batch_result)
                execution.phase_results['validation'] = validation_result

            # Phase 5: Completion
            execution.current_phase = MigrationPhase.COMPLETION
            self.logger.info("Phase 5: Finalizing migration")

            # Generate migration report
            migration_report = self._generate_migration_report(plan, execution, batch_result)

            # Save report
            self._save_migration_report(migration_report)

            execution.phase_results['completion'] = {
                'report_generated': True,
                'final_quality_score': migration_report.final_quality_report.overall_metrics.overall_quality_score if migration_report.final_quality_report else None
            }

            # Mark as completed
            execution.status = MigrationStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.progress_percentage = 100.0

            self.logger.info(f"Migration execution completed successfully: {execution.tasks_completed}/{plan.total_tasks} tasks")

            # Store execution history
            self.migration_history.append(execution)
            self.migration_reports.append(migration_report)

            return execution

        except Exception as e:
            self.logger.error(f"Migration execution failed: {e}")

            execution.status = MigrationStatus.FAILED
            execution.errors.append(str(e))
            execution.completed_at = datetime.now()

            # Store failed execution
            self.migration_history.append(execution)

            return execution

    def _estimate_migration_time(self, tasks: list[CompletionTask]) -> float:
        """Estimate migration time in hours"""
        total_effort_seconds = sum(task.estimated_effort for task in tasks)

        # Add overhead for batch processing and validation
        overhead_factor = 1.3
        total_seconds = total_effort_seconds * overhead_factor

        # Convert to hours
        return total_seconds / 3600.0

    def _analyze_task_priorities(self, tasks: list[CompletionTask]) -> dict[str, int]:
        """Analyze task priority breakdown"""
        priority_counts = {}

        for task in tasks:
            priority = task.priority.value
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        return priority_counts

    def _validate_migration_results(self, plan: MigrationPlan, batch_result: BatchCompletionResult) -> dict[str, Any]:
        """Validate migration results"""
        try:
            self.logger.info("Validating migration results...")

            # Conduct post-migration audit
            final_audit = self.quality_auditor.conduct_full_audit()

            # Compare with initial quality
            initial_issues = len(plan.quality_issues)
            final_issues = len(final_audit.issues)

            # Calculate improvement
            issues_resolved = initial_issues - final_issues
            improvement_rate = issues_resolved / initial_issues if initial_issues > 0 else 0

            # Validate successful tasks
            successful_tasks = [r for r in batch_result.tasks_results if r.success]

            validation_result = {
                'initial_issues': initial_issues,
                'final_issues': final_issues,
                'issues_resolved': issues_resolved,
                'improvement_rate': improvement_rate,
                'successful_tasks': len(successful_tasks),
                'fields_completed': sum(len(r.fields_completed) for r in successful_tasks),
                'validation_passed': improvement_rate > 0.1  # At least 10% improvement
            }

            self.logger.info(f"Validation completed: {improvement_rate:.1%} improvement")
            return validation_result

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return {
                'validation_passed': False,
                'error': str(e)
            }

    def _generate_migration_report(self, plan: MigrationPlan, execution: MigrationExecution, batch_result: BatchCompletionResult) -> MigrationReport:
        """Generate comprehensive migration report"""
        try:
            # Get initial quality report from audit
            initial_audit = self.quality_auditor.conduct_full_audit()

            # Calculate final quality if validation was performed
            final_audit = None
            if 'validation' in execution.phase_results:
                final_audit = self.quality_auditor.conduct_full_audit()

            # Calculate quality improvement
            quality_improvement = {}
            if final_audit:
                quality_improvement = {
                    'overall_score': final_audit.overall_metrics.overall_quality_score - initial_audit.overall_metrics.overall_quality_score,
                    'completeness_rate': final_audit.overall_metrics.completeness_rate - initial_audit.overall_metrics.completeness_rate,
                    'accuracy_rate': final_audit.overall_metrics.accuracy_rate - initial_audit.overall_metrics.accuracy_rate
                }

            # Calculate completion metrics
            total_fields_completed = sum(len(r.fields_completed) for r in batch_result.tasks_results)
            total_bills_improved = len(set(r.bill_id for r in batch_result.tasks_results if r.success))

            # Calculate performance metrics
            total_processing_time = batch_result.total_processing_time_ms

            phases_timing = {
                'execution': batch_result.total_processing_time_ms,
                'validation': execution.phase_results.get('validation', {}).get('processing_time_ms', 0),
                'total': total_processing_time
            }

            # Generate recommendations
            recommendations = self._generate_migration_recommendations(batch_result, quality_improvement)

            report = MigrationReport(
                plan_id=plan.plan_id,
                execution_id=execution.execution_id,
                migration_completed_at=execution.completed_at or datetime.now(),
                initial_quality_report=initial_audit,
                final_quality_report=final_audit,
                quality_improvement=quality_improvement,
                batch_results=[batch_result],
                total_fields_completed=total_fields_completed,
                total_bills_improved=total_bills_improved,
                total_processing_time_ms=total_processing_time,
                phases_timing=phases_timing,
                success_rate=batch_result.success_rate,
                recommendations=recommendations
            )

            return report

        except Exception as e:
            self.logger.error(f"Error generating migration report: {e}")
            raise

    def _generate_migration_recommendations(self, batch_result: BatchCompletionResult, quality_improvement: dict[str, float]) -> list[str]:
        """Generate recommendations based on migration results"""
        recommendations = []

        # Success rate recommendations
        if batch_result.success_rate < 0.8:
            recommendations.append("Consider reviewing failed tasks and implementing retry mechanisms")

        # Quality improvement recommendations
        if quality_improvement and quality_improvement.get('overall_score', 0) < 0.1:
            recommendations.append("Quality improvement was minimal - consider additional enhancement strategies")

        # Performance recommendations
        if batch_result.total_processing_time_ms > 300000:  # 5 minutes
            recommendations.append("Consider optimizing batch processing for better performance")

        # Field completion recommendations
        failed_fields = {}
        for result in batch_result.tasks_results:
            for field in result.fields_failed:
                failed_fields[field] = failed_fields.get(field, 0) + 1

        if failed_fields:
            most_failed = max(failed_fields.items(), key=lambda x: x[1])
            recommendations.append(f"Field '{most_failed[0]}' failed most frequently - review extraction logic")

        return recommendations

    def _save_migration_report(self, report: MigrationReport):
        """Save migration report to file"""
        try:
            report_filename = f"migration_report_{report.execution_id}.json"
            report_path = os.path.join(self.reports_dir, report_filename)

            # Export report
            exported_report = self._export_migration_report(report)

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(exported_report, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Migration report saved to {report_path}")

        except Exception as e:
            self.logger.error(f"Error saving migration report: {e}")

    def _export_migration_report(self, report: MigrationReport) -> dict[str, Any]:
        """Export migration report to dictionary"""
        return {
            'plan_id': report.plan_id,
            'execution_id': report.execution_id,
            'migration_completed_at': report.migration_completed_at.isoformat(),
            'summary': {
                'total_fields_completed': report.total_fields_completed,
                'total_bills_improved': report.total_bills_improved,
                'success_rate': report.success_rate,
                'total_processing_time_ms': report.total_processing_time_ms
            },
            'quality_improvement': report.quality_improvement,
            'initial_quality_metrics': {
                'overall_quality_score': report.initial_quality_report.overall_metrics.overall_quality_score,
                'completeness_rate': report.initial_quality_report.overall_metrics.completeness_rate,
                'accuracy_rate': report.initial_quality_report.overall_metrics.accuracy_rate,
                'total_issues': len(report.initial_quality_report.issues)
            },
            'final_quality_metrics': {
                'overall_quality_score': report.final_quality_report.overall_metrics.overall_quality_score,
                'completeness_rate': report.final_quality_report.overall_metrics.completeness_rate,
                'accuracy_rate': report.final_quality_report.overall_metrics.accuracy_rate,
                'total_issues': len(report.final_quality_report.issues)
            } if report.final_quality_report else None,
            'batch_results': [
                {
                    'batch_id': batch.batch_id,
                    'total_tasks': batch.total_tasks,
                    'completed_tasks': batch.completed_tasks,
                    'failed_tasks': batch.failed_tasks,
                    'success_rate': batch.success_rate,
                    'processing_time_ms': batch.total_processing_time_ms
                }
                for batch in report.batch_results
            ],
            'phases_timing': report.phases_timing,
            'recommendations': report.recommendations
        }

    def get_migration_status(self, execution_id: str) -> MigrationExecution | None:
        """Get migration execution status"""
        for execution in self.migration_history:
            if execution.execution_id == execution_id:
                return execution
        return None

    def get_migration_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get migration history"""
        recent_executions = self.migration_history[-limit:] if self.migration_history else []

        return [
            {
                'execution_id': execution.execution_id,
                'plan_id': execution.plan_id,
                'status': execution.status.value,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'progress_percentage': execution.progress_percentage,
                'tasks_completed': execution.tasks_completed,
                'tasks_failed': execution.tasks_failed,
                'current_phase': execution.current_phase.value
            }
            for execution in recent_executions
        ]

    def get_migration_statistics(self, days: int = 30) -> dict[str, Any]:
        """Get migration statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_executions = [
            execution for execution in self.migration_history
            if execution.started_at > cutoff_date
        ]

        if not recent_executions:
            return {
                'period_days': days,
                'total_migrations': 0,
                'successful_migrations': 0,
                'failed_migrations': 0,
                'success_rate': 0.0
            }

        successful = len([e for e in recent_executions if e.status == MigrationStatus.COMPLETED])
        failed = len([e for e in recent_executions if e.status == MigrationStatus.FAILED])

        return {
            'period_days': days,
            'total_migrations': len(recent_executions),
            'successful_migrations': successful,
            'failed_migrations': failed,
            'success_rate': successful / len(recent_executions),
            'total_tasks_completed': sum(e.tasks_completed for e in recent_executions),
            'total_tasks_failed': sum(e.tasks_failed for e in recent_executions),
            'average_processing_time_ms': sum(
                e.phase_results.get('execution', {}).get('processing_time_ms', 0)
                for e in recent_executions
            ) / len(recent_executions) if recent_executions else 0
        }

    def cleanup_old_reports(self, retention_days: int = 90):
        """Clean up old migration reports"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Clean up report files
            for filename in os.listdir(self.reports_dir):
                if filename.startswith('migration_report_') and filename.endswith('.json'):
                    filepath = os.path.join(self.reports_dir, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        self.logger.info(f"Removed old report: {filename}")

            # Clean up in-memory history
            self.migration_history = [
                execution for execution in self.migration_history
                if execution.started_at > cutoff_date
            ]

            self.migration_reports = [
                report for report in self.migration_reports
                if report.migration_completed_at > cutoff_date
            ]

            self.logger.info(f"Cleaned up reports older than {retention_days} days")

        except Exception as e:
            self.logger.error(f"Error cleaning up old reports: {e}")

    def export_service_report(self, format: str = "json") -> dict[str, Any]:
        """Export service status report"""
        if format == "json":
            return {
                'service_info': {
                    'total_migrations': len(self.migration_history),
                    'recent_migrations': len([e for e in self.migration_history if e.started_at > datetime.now() - timedelta(days=7)]),
                    'reports_directory': self.reports_dir
                },
                'configuration': self.config,
                'recent_executions': self.get_migration_history(5),
                'statistics': self.get_migration_statistics(30)
            }
        else:
            return {'error': f'Unsupported format: {format}'}
