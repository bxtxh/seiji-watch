#!/usr/bin/env python3
"""
Migration CLI - Command-line interface for data migration operations.
Provides easy access to quality auditing and data completion functionality.
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from services.ingest_worker.src.migration.data_migration_service import (
    DataMigrationService,
)
from services.ingest_worker.src.migration.data_quality_auditor import DataQualityAuditor


def setup_logging():
    """Set up logging configuration"""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('migration.log')
        ]
    )


def get_database_url() -> str:
    """Get database URL from environment or config"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Default for development
        database_url = "postgresql://localhost:5432/seiji_watch"
    return database_url


def cmd_audit(args):
    """Run quality audit command"""
    print("🔍 Starting data quality audit...")

    database_url = get_database_url()
    auditor = DataQualityAuditor(database_url)

    try:
        # Conduct audit
        report = auditor.conduct_full_audit()

        # Display summary
        print("\n📊 Quality Audit Summary:")
        print(f"  Total bills: {report.total_bills}")
        print(f"  Overall quality score: {report.overall_metrics.overall_quality_score:.2f}")
        print(f"  Completeness rate: {report.overall_metrics.completeness_rate:.2f}")
        print(f"  Accuracy rate: {report.overall_metrics.accuracy_rate:.2f}")
        print(f"  Issues found: {len(report.issues)}")

        # Show issues by severity
        print("\n🚨 Issues by severity:")
        for severity, count in report.issues_by_severity.items():
            print(f"  {severity}: {count}")

        # Show most problematic fields
        if report.most_problematic_fields:
            print("\n📋 Most problematic fields:")
            for field in report.most_problematic_fields[:5]:
                print(f"  - {field}")

        # Show recommendations
        if report.recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")

        # Export report if requested
        if args.export:
            exported = auditor.export_report(report, args.format)
            output_file = f"quality_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{args.format}"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(exported, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n📄 Report exported to: {output_file}")

        print("\n✅ Quality audit completed successfully!")

    except Exception as e:
        print(f"❌ Error during audit: {e}")
        sys.exit(1)


def cmd_plan(args):
    """Generate migration plan command"""
    print("📋 Generating migration plan...")

    database_url = get_database_url()
    service = DataMigrationService(database_url)

    try:
        # Create migration plan
        target_bills = args.bills.split(',') if args.bills else None
        plan = service.create_migration_plan(target_bills)

        # Display plan summary
        print("\n📊 Migration Plan Summary:")
        print(f"  Plan ID: {plan.plan_id}")
        print(f"  Total bills: {plan.total_bills}")
        print(f"  Total tasks: {plan.total_tasks}")
        print(f"  Estimated time: {plan.estimated_time_hours:.2f} hours")

        # Show priority breakdown
        print("\n🎯 Task priorities:")
        for priority, count in plan.priority_breakdown.items():
            print(f"  {priority}: {count}")

        # Show phases
        print("\n📝 Migration phases:")
        for i, phase in enumerate(plan.phases, 1):
            print(f"  {i}. {phase.value}")

        # Show sample tasks
        if plan.completion_tasks:
            print("\n🔧 Sample tasks:")
            for task in plan.completion_tasks[:5]:
                print(f"  - {task.description} ({task.priority.value})")

            if len(plan.completion_tasks) > 5:
                print(f"  ... and {len(plan.completion_tasks) - 5} more tasks")

        # Export plan if requested
        if args.export:
            plan_data = {
                'plan_id': plan.plan_id,
                'created_at': plan.created_at.isoformat(),
                'total_bills': plan.total_bills,
                'total_tasks': plan.total_tasks,
                'estimated_time_hours': plan.estimated_time_hours,
                'priority_breakdown': plan.priority_breakdown,
                'phases': [phase.value for phase in plan.phases],
                'completion_tasks': [
                    {
                        'task_id': task.task_id,
                        'bill_id': task.bill_id,
                        'strategy': task.strategy.value,
                        'priority': task.priority.value,
                        'target_fields': task.target_fields,
                        'description': task.description,
                        'estimated_effort': task.estimated_effort
                    }
                    for task in plan.completion_tasks
                ]
            }

            output_file = f"migration_plan_{plan.plan_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n📄 Plan exported to: {output_file}")

        print("\n✅ Migration plan generated successfully!")

    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        sys.exit(1)


def cmd_execute(args):
    """Execute migration command"""
    print("🚀 Executing migration...")

    database_url = get_database_url()
    service = DataMigrationService(database_url)

    try:
        # Load plan if provided
        if args.plan_file:
            with open(args.plan_file, encoding='utf-8') as f:
                plan_data = json.load(f)

            # Recreate plan (simplified)
            from services.ingest_worker.src.migration.data_completion_processor import (
                CompletionPriority,
                CompletionStrategy,
                CompletionTask,
            )
            from services.ingest_worker.src.migration.data_migration_service import (
                MigrationPlan,
            )

            plan = MigrationPlan(
                plan_id=plan_data['plan_id'],
                total_bills=plan_data['total_bills'],
                total_tasks=plan_data['total_tasks'],
                estimated_time_hours=plan_data['estimated_time_hours'],
                priority_breakdown=plan_data['priority_breakdown'],
                phases=[],  # Will be set by service
                completion_tasks=[
                    CompletionTask(
                        bill_id=task['bill_id'],
                        strategy=CompletionStrategy(task['strategy']),
                        priority=CompletionPriority(task['priority']),
                        target_fields=task['target_fields'],
                        description=task['description'],
                        estimated_effort=task['estimated_effort']
                    )
                    for task in plan_data['completion_tasks']
                ]
            )

            print(f"📋 Loaded plan: {plan.plan_id}")
        else:
            # Create new plan
            target_bills = args.bills.split(',') if args.bills else None
            plan = service.create_migration_plan(target_bills)
            print(f"📋 Created new plan: {plan.plan_id}")

        # Confirm execution
        if not args.yes:
            print(f"\n⚠️  About to execute migration with {plan.total_tasks} tasks")
            print(f"   Estimated time: {plan.estimated_time_hours:.2f} hours")

            if input("Continue? (y/N): ").lower() != 'y':
                print("Migration cancelled.")
                return

        # Execute migration
        execution = service.execute_migration(plan)

        # Display execution summary
        print("\n📊 Migration Execution Summary:")
        print(f"  Execution ID: {execution.execution_id}")
        print(f"  Status: {execution.status.value}")
        print(f"  Tasks completed: {execution.tasks_completed}")
        print(f"  Tasks failed: {execution.tasks_failed}")
        print(f"  Progress: {execution.progress_percentage:.1f}%")

        if execution.completed_at:
            duration = execution.completed_at - execution.started_at
            print(f"  Duration: {duration.total_seconds():.1f} seconds")

        # Show phase results
        if execution.phase_results:
            print("\n📝 Phase results:")
            for phase, results in execution.phase_results.items():
                print(f"  {phase}: {results}")

        # Show errors if any
        if execution.errors:
            print("\n❌ Errors:")
            for error in execution.errors:
                print(f"  - {error}")

        if execution.status.value == 'completed':
            print("\n✅ Migration completed successfully!")
        else:
            print(f"\n⚠️  Migration ended with status: {execution.status.value}")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        sys.exit(1)


def cmd_status(args):
    """Show migration status command"""
    print("📊 Migration system status...")

    database_url = get_database_url()
    service = DataMigrationService(database_url)

    try:
        # Get service report
        report = service.export_service_report()

        print("\n📋 Service Information:")
        print(f"  Total migrations: {report['service_info']['total_migrations']}")
        print(f"  Recent migrations: {report['service_info']['recent_migrations']}")
        print(f"  Reports directory: {report['service_info']['reports_directory']}")

        # Show configuration
        print("\n⚙️  Configuration:")
        for key, value in report['configuration'].items():
            print(f"  {key}: {value}")

        # Show recent executions
        if report['recent_executions']:
            print("\n📈 Recent executions:")
            for exec_data in report['recent_executions']:
                status = exec_data['status']
                completed = exec_data['tasks_completed']
                failed = exec_data['tasks_failed']
                print(f"  {exec_data['execution_id']}: {status} ({completed} completed, {failed} failed)")

        # Show statistics
        stats = report['statistics']
        print("\n📊 Statistics (last 30 days):")
        print(f"  Total migrations: {stats['total_migrations']}")
        print(f"  Successful migrations: {stats['successful_migrations']}")
        print(f"  Failed migrations: {stats['failed_migrations']}")
        print(f"  Success rate: {stats['success_rate']:.2f}")
        print(f"  Total tasks completed: {stats['total_tasks_completed']}")
        print(f"  Total tasks failed: {stats['total_tasks_failed']}")

        print("\n✅ Status retrieved successfully!")

    except Exception as e:
        print(f"❌ Error retrieving status: {e}")
        sys.exit(1)


def cmd_cleanup(args):
    """Cleanup old reports command"""
    print("🧹 Cleaning up old reports...")

    database_url = get_database_url()
    service = DataMigrationService(database_url)

    try:
        retention_days = args.days
        service.cleanup_old_reports(retention_days)

        print(f"✅ Cleaned up reports older than {retention_days} days")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)


def cmd_trend(args):
    """Show quality trend command"""
    print("📈 Analyzing quality trends...")

    database_url = get_database_url()
    auditor = DataQualityAuditor(database_url)

    try:
        days = args.days
        trend = auditor.get_quality_trend(days)

        print(f"\n📊 Quality Trend (last {days} days):")
        print(f"  Trend: {trend['trend']}")

        if 'overall_average' in trend:
            print(f"  Overall average: {trend['overall_average']:.2f}")

        if 'total_bills' in trend:
            print(f"  Total bills analyzed: {trend['total_bills']}")

        if 'message' in trend:
            print(f"  Message: {trend['message']}")

        print("\n✅ Quality trend analysis completed!")

    except Exception as e:
        print(f"❌ Error analyzing trend: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Data Migration CLI - Quality auditing and data completion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run quality audit
  python migration_cli.py audit --export

  # Generate migration plan
  python migration_cli.py plan --bills=bill1,bill2 --export

  # Execute migration
  python migration_cli.py execute --plan-file=migration_plan.json

  # Show system status
  python migration_cli.py status

  # Clean up old reports
  python migration_cli.py cleanup --days=30

  # Show quality trend
  python migration_cli.py trend --days=30
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Run data quality audit')
    audit_parser.add_argument('--export', action='store_true', help='Export audit report')
    audit_parser.add_argument('--format', default='json', choices=['json'], help='Export format')
    audit_parser.set_defaults(func=cmd_audit)

    # Plan command
    plan_parser = subparsers.add_parser('plan', help='Generate migration plan')
    plan_parser.add_argument('--bills', help='Comma-separated list of bill IDs to target')
    plan_parser.add_argument('--export', action='store_true', help='Export migration plan')
    plan_parser.set_defaults(func=cmd_plan)

    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute migration')
    execute_parser.add_argument('--plan-file', help='Path to migration plan file')
    execute_parser.add_argument('--bills', help='Comma-separated list of bill IDs to target')
    execute_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    execute_parser.set_defaults(func=cmd_execute)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show migration system status')
    status_parser.set_defaults(func=cmd_status)

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old reports')
    cleanup_parser.add_argument('--days', type=int, default=90, help='Report retention days')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # Trend command
    trend_parser = subparsers.add_parser('trend', help='Show quality trend')
    trend_parser.add_argument('--days', type=int, default=30, help='Analysis period in days')
    trend_parser.set_defaults(func=cmd_trend)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    setup_logging()

    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
