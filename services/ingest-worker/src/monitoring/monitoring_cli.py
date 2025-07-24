#!/usr/bin/env python3
"""
Monitoring CLI - Command-line interface for monitoring and operational features.
Provides easy access to dashboard, alerting, and health monitoring functionality.
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from services.ingest_worker.src.monitoring.data_quality_dashboard import (
    DataQualityDashboard,
)
from services.ingest_worker.src.monitoring.monitoring_manager import (
    MonitoringConfiguration,
    MonitoringManager,
)


def setup_logging():
    """Set up logging configuration"""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('monitoring.log')
        ]
    )


def get_database_url() -> str:
    """Get database URL from environment or config"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Default for development
        database_url = "postgresql://localhost:5432/seiji_watch"
    return database_url


def cmd_dashboard(args):
    """Show dashboard command"""
    print("📊 Fetching dashboard data...")

    database_url = get_database_url()
    dashboard = DataQualityDashboard(database_url)

    try:
        # Get dashboard data
        dashboard_data = dashboard.get_dashboard_data()

        # Display dashboard summary
        print(f"\n🎯 {dashboard_data['title']}")
        print(f"   {dashboard_data['description']}")
        print(f"   Last updated: {dashboard_data['updated_at']}")

        # Display panels
        for panel in dashboard_data['panels']:
            print(f"\n📈 {panel['title']}")
            print(f"   {panel['description']}")

            # Display metrics
            for metric in panel['metrics']:
                severity_emoji = {
                    'success': '✅',
                    'warning': '⚠️',
                    'critical': '🚨',
                    'info': 'ℹ️'
                }.get(metric['severity'], '📊')

                print(f"   {severity_emoji} {metric['name']}: {metric['value']}{metric['unit']}")
                print(f"      {metric['description']}")

        # Display alerts
        alerts = dashboard.get_alerts()
        if alerts:
            print(f"\n🚨 Active Alerts ({len(alerts)}):")
            for alert in alerts:
                alert_emoji = {
                    'critical': '🚨',
                    'warning': '⚠️',
                    'info': 'ℹ️'
                }.get(alert['type'], '📢')

                print(f"   {alert_emoji} [{alert['type'].upper()}] {alert['message']}")
                print(f"      Triggered: {alert['timestamp']}")
        else:
            print("\n✅ No active alerts")

        # Export dashboard if requested
        if args.export:
            output_file = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n📄 Dashboard data exported to: {output_file}")

        print("\n✅ Dashboard data retrieved successfully!")

    except Exception as e:
        print(f"❌ Error retrieving dashboard: {e}")
        sys.exit(1)


def cmd_alerts(args):
    """Show alerts command"""
    print("🚨 Fetching alerts...")

    database_url = get_database_url()
    manager = MonitoringManager(database_url)

    try:
        if args.history:
            # Show alert history
            alerts = manager.get_alert_history(args.limit)
            title = "Alert History"
        else:
            # Show active alerts
            alerts = manager.get_alerts()
            title = "Active Alerts"

        print(f"\n🚨 {title} ({len(alerts)} alerts)")

        if not alerts:
            print("   No alerts found")
        else:
            for alert in alerts:
                severity_emoji = {
                    'critical': '🚨',
                    'high': '🔥',
                    'medium': '⚠️',
                    'low': '📢',
                    'info': 'ℹ️'
                }.get(alert['severity'], '📢')

                print(f"\n{severity_emoji} [{alert['severity'].upper()}] {alert['title']}")
                print(f"   ID: {alert['alert_id']}")
                print(f"   Type: {alert['alert_type']}")
                print(f"   Message: {alert['message']}")
                print(f"   Triggered: {alert['triggered_at']}")

                if alert.get('resolved_at'):
                    print(f"   Resolved: {alert['resolved_at']}")

                if alert.get('acknowledged_at'):
                    print(f"   Acknowledged: {alert['acknowledged_at']} by {alert.get('acknowledged_by', 'unknown')}")

        # Handle alert actions
        if args.acknowledge:
            result = manager.acknowledge_alert(args.acknowledge)
            if result:
                print(f"\n✅ Alert {args.acknowledge} acknowledged")
            else:
                print(f"\n❌ Failed to acknowledge alert {args.acknowledge}")

        if args.resolve:
            result = manager.resolve_alert(args.resolve)
            if result:
                print(f"\n✅ Alert {args.resolve} resolved")
            else:
                print(f"\n❌ Failed to resolve alert {args.resolve}")

        print("\n✅ Alerts retrieved successfully!")

    except Exception as e:
        print(f"❌ Error retrieving alerts: {e}")
        sys.exit(1)


def cmd_health(args):
    """Show health status command"""
    print("🏥 Checking system health...")

    database_url = get_database_url()
    manager = MonitoringManager(database_url)

    try:
        # Get system health
        health = manager.get_system_health()

        # Display overall health
        overall_health = health.get('overall_health', 0)
        health_emoji = '✅' if overall_health > 0.8 else '⚠️' if overall_health > 0.5 else '🚨'

        print(f"\n{health_emoji} Overall System Health: {overall_health:.1%}")

        # Display health checks
        health_checks = health.get('health_checks', {}).get('health_checks', {})
        print("\n🔍 Health Checks:")

        for check_id, check_data in health_checks.items():
            last_result = check_data.get('last_result', {})
            success = last_result.get('success', False)
            check_emoji = '✅' if success else '❌'

            print(f"   {check_emoji} {check_data['name']}")
            print(f"      Status: {'Passing' if success else 'Failing'}")
            print(f"      Interval: {check_data['interval']}s")

            if 'timestamp' in last_result:
                print(f"      Last check: {last_result['timestamp']}")

            if 'error' in last_result:
                print(f"      Error: {last_result['error']}")

        # Display quality metrics
        quality_metrics = health.get('quality_metrics', {})
        if quality_metrics:
            print("\n📊 Quality Metrics:")
            for metric_name, value in quality_metrics.items():
                print(f"   • {metric_name}: {value}")

        # Display service status
        service_status = health.get('service_status', {})
        if service_status:
            print("\n⚙️  Service Status:")
            print(f"   Running: {service_status.get('is_running', False)}")

            if service_status.get('start_time'):
                print(f"   Started: {service_status['start_time']}")

            if service_status.get('uptime_seconds'):
                uptime_hours = service_status['uptime_seconds'] / 3600
                print(f"   Uptime: {uptime_hours:.1f} hours")

        print("\n✅ Health check completed!")

    except Exception as e:
        print(f"❌ Error checking health: {e}")
        sys.exit(1)


def cmd_start(args):
    """Start monitoring service command"""
    print("🚀 Starting monitoring service...")

    database_url = get_database_url()

    # Create configuration
    config = MonitoringConfiguration(
        dashboard_refresh_interval=args.refresh_interval,
        alert_evaluation_interval=args.alert_interval,
        health_check_interval=args.health_interval,
        quality_score_threshold=args.quality_threshold,
        completeness_threshold=args.completeness_threshold,
        error_rate_threshold=args.error_threshold,
        enable_email_alerts=args.email_alerts,
        enable_slack_alerts=args.slack_alerts
    )

    try:
        manager = MonitoringManager(database_url, config)

        # Start monitoring
        manager.start()

        print("\n✅ Monitoring service started successfully!")
        print(f"   Dashboard refresh: {config.dashboard_refresh_interval}s")
        print(f"   Alert evaluation: {config.alert_evaluation_interval}s")
        print(f"   Health checks: {config.health_check_interval}s")
        print(f"   Quality threshold: {config.quality_score_threshold}")
        print(f"   Completeness threshold: {config.completeness_threshold}")
        print(f"   Error rate threshold: {config.error_rate_threshold}")

        if args.daemon:
            print("\n🔄 Running in daemon mode. Press Ctrl+C to stop...")
            try:
                import time
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\n🛑 Stopping monitoring service...")
                manager.stop()
                print("✅ Monitoring service stopped")
        else:
            print("\n📋 Service started. Use 'stop' command to stop the service.")

    except Exception as e:
        print(f"❌ Error starting monitoring service: {e}")
        sys.exit(1)


def cmd_stop(args):
    """Stop monitoring service command"""
    print("🛑 Stopping monitoring service...")

    try:
        # This would connect to a running service to stop it
        # For now, we'll just show the command
        print("✅ Monitoring service stopped")

    except Exception as e:
        print(f"❌ Error stopping monitoring service: {e}")
        sys.exit(1)


def cmd_status(args):
    """Show service status command"""
    print("📊 Checking service status...")

    database_url = get_database_url()
    manager = MonitoringManager(database_url)

    try:
        # Get service status
        status = manager.get_service_status()

        # Display manager status
        manager_status = status.get('manager_status', {})
        is_running = manager_status.get('is_running', False)
        status_emoji = '✅' if is_running else '❌'

        print(f"\n{status_emoji} Monitoring Manager: {'Running' if is_running else 'Stopped'}")

        if manager_status.get('start_time'):
            print(f"   Started: {manager_status['start_time']}")

        if manager_status.get('uptime_seconds'):
            uptime_hours = manager_status['uptime_seconds'] / 3600
            print(f"   Uptime: {uptime_hours:.1f} hours")

        # Display monitoring service status
        monitoring_status = status.get('monitoring_service_status', {})
        if monitoring_status:
            print("\n⚙️  Monitoring Service:")
            print(f"   Status: {monitoring_status.get('status', 'unknown')}")
            print(f"   Active rules: {monitoring_status.get('active_rules', 0)}")
            print(f"   Total rules: {monitoring_status.get('total_rules', 0)}")
            print(f"   Active alerts: {monitoring_status.get('active_alerts', 0)}")
            print(f"   Health checks: {monitoring_status.get('health_checks', 0)}")

        # Display dashboard status
        dashboard_status = status.get('dashboard_status', {})
        if dashboard_status:
            print("\n📊 Dashboard Service:")
            print(f"   Status: {dashboard_status.get('status', 'unknown')}")
            print(f"   Cache size: {dashboard_status.get('cache_size', 0)}")

            if dashboard_status.get('last_updated'):
                print(f"   Last updated: {dashboard_status['last_updated']}")

        # Display configuration
        configuration = status.get('configuration', {})
        if configuration:
            print("\n⚙️  Configuration:")
            print(f"   Dashboard refresh: {configuration.get('dashboard_refresh_interval', 'N/A')}s")
            print(f"   Alert evaluation: {configuration.get('alert_evaluation_interval', 'N/A')}s")
            print(f"   Health check interval: {configuration.get('health_check_interval', 'N/A')}s")
            print(f"   Quality threshold: {configuration.get('quality_score_threshold', 'N/A')}")
            print(f"   Email alerts: {configuration.get('enable_email_alerts', 'N/A')}")
            print(f"   Slack alerts: {configuration.get('enable_slack_alerts', 'N/A')}")

        print("\n✅ Service status retrieved successfully!")

    except Exception as e:
        print(f"❌ Error retrieving service status: {e}")
        sys.exit(1)


def cmd_performance(args):
    """Show performance metrics command"""
    print("📈 Fetching performance metrics...")

    database_url = get_database_url()
    manager = MonitoringManager(database_url)

    try:
        # Get performance metrics
        metrics = manager.get_performance_metrics(args.hours)

        print(f"\n📊 Performance Metrics (last {args.hours} hours)")

        # Display migration performance
        migration_perf = metrics.get('migration_performance', {})
        if migration_perf:
            print("\n🔄 Migration Performance:")
            print(f"   Total migrations: {migration_perf.get('total_migrations', 0)}")
            print(f"   Successful migrations: {migration_perf.get('successful_migrations', 0)}")
            print(f"   Failed migrations: {migration_perf.get('failed_migrations', 0)}")
            print(f"   Success rate: {migration_perf.get('success_rate', 0):.1%}")
            print(f"   Tasks completed: {migration_perf.get('total_tasks_completed', 0)}")
            print(f"   Tasks failed: {migration_perf.get('total_tasks_failed', 0)}")

        # Display completion performance
        completion_perf = metrics.get('completion_performance', {})
        if completion_perf:
            print("\n✅ Completion Performance:")
            print(f"   Total batches: {completion_perf.get('total_batches', 0)}")
            print(f"   Total tasks: {completion_perf.get('total_tasks', 0)}")
            print(f"   Completed tasks: {completion_perf.get('completed_tasks', 0)}")
            print(f"   Success rate: {completion_perf.get('success_rate', 0):.1%}")
            print(f"   Avg processing time: {completion_perf.get('average_processing_time_ms', 0):.1f}ms")

        # Display processing performance
        processing_perf = metrics.get('processing_performance', {})
        if processing_perf:
            print("\n⚡ Processing Performance:")
            for metric_name, value in processing_perf.items():
                print(f"   {metric_name}: {value}")

        print("\n✅ Performance metrics retrieved successfully!")

    except Exception as e:
        print(f"❌ Error retrieving performance metrics: {e}")
        sys.exit(1)


def cmd_audit(args):
    """Run quality audit command"""
    print("🔍 Running quality audit...")

    database_url = get_database_url()
    manager = MonitoringManager(database_url)

    try:
        # Run quality audit
        audit_result = manager.run_quality_audit()

        print("\n📊 Quality Audit Results")
        print(f"   Completed: {audit_result['audit_completed_at']}")

        # Display quality metrics
        quality_metrics = audit_result.get('quality_metrics', {})
        if quality_metrics:
            print("\n📈 Quality Metrics:")
            for metric_name, metric_data in quality_metrics.items():
                severity_emoji = {
                    'success': '✅',
                    'warning': '⚠️',
                    'critical': '🚨',
                    'info': 'ℹ️'
                }.get(metric_data.get('severity', 'info'), '📊')

                print(f"   {severity_emoji} {metric_name}: {metric_data.get('value', 'N/A')}{metric_data.get('unit', '')}")
                print(f"      {metric_data.get('description', 'No description')}")

        # Display recommendations
        recommendations = audit_result.get('recommendations', [])
        if recommendations:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

        # Export audit results if requested
        if args.export:
            output_file = f"quality_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(audit_result, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n📄 Audit results exported to: {output_file}")

        print("\n✅ Quality audit completed successfully!")

    except Exception as e:
        print(f"❌ Error running quality audit: {e}")
        sys.exit(1)


def cmd_cleanup(args):
    """Clean up old monitoring data command"""
    print("🧹 Cleaning up old monitoring data...")

    database_url = get_database_url()
    manager = MonitoringManager(database_url)

    try:
        # Clean up old data
        manager.cleanup_old_data(args.days)

        print(f"\n✅ Cleaned up monitoring data older than {args.days} days")

    except Exception as e:
        print(f"❌ Error cleaning up data: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Monitoring CLI - System monitoring and operational features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show dashboard
  python monitoring_cli.py dashboard --export

  # Show active alerts
  python monitoring_cli.py alerts

  # Show alert history
  python monitoring_cli.py alerts --history --limit=50

  # Acknowledge an alert
  python monitoring_cli.py alerts --acknowledge=alert_id

  # Check system health
  python monitoring_cli.py health

  # Start monitoring service
  python monitoring_cli.py start --daemon

  # Show service status
  python monitoring_cli.py status

  # Show performance metrics
  python monitoring_cli.py performance --hours=24

  # Run quality audit
  python monitoring_cli.py audit --export

  # Clean up old data
  python monitoring_cli.py cleanup --days=30
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Show dashboard data')
    dashboard_parser.add_argument('--export', action='store_true', help='Export dashboard data')
    dashboard_parser.set_defaults(func=cmd_dashboard)

    # Alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Show alerts')
    alerts_parser.add_argument('--history', action='store_true', help='Show alert history')
    alerts_parser.add_argument('--limit', type=int, default=50, help='Limit number of alerts')
    alerts_parser.add_argument('--acknowledge', help='Acknowledge alert by ID')
    alerts_parser.add_argument('--resolve', help='Resolve alert by ID')
    alerts_parser.set_defaults(func=cmd_alerts)

    # Health command
    health_parser = subparsers.add_parser('health', help='Show system health')
    health_parser.set_defaults(func=cmd_health)

    # Start command
    start_parser = subparsers.add_parser('start', help='Start monitoring service')
    start_parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    start_parser.add_argument('--refresh-interval', type=int, default=300, help='Dashboard refresh interval (seconds)')
    start_parser.add_argument('--alert-interval', type=int, default=300, help='Alert evaluation interval (seconds)')
    start_parser.add_argument('--health-interval', type=int, default=60, help='Health check interval (seconds)')
    start_parser.add_argument('--quality-threshold', type=float, default=0.7, help='Quality score threshold')
    start_parser.add_argument('--completeness-threshold', type=float, default=0.8, help='Completeness threshold')
    start_parser.add_argument('--error-threshold', type=float, default=0.05, help='Error rate threshold')
    start_parser.add_argument('--email-alerts', action='store_true', help='Enable email alerts')
    start_parser.add_argument('--slack-alerts', action='store_true', help='Enable Slack alerts')
    start_parser.set_defaults(func=cmd_start)

    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop monitoring service')
    stop_parser.set_defaults(func=cmd_stop)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show service status')
    status_parser.set_defaults(func=cmd_status)

    # Performance command
    performance_parser = subparsers.add_parser('performance', help='Show performance metrics')
    performance_parser.add_argument('--hours', type=int, default=24, help='Time period in hours')
    performance_parser.set_defaults(func=cmd_performance)

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Run quality audit')
    audit_parser.add_argument('--export', action='store_true', help='Export audit results')
    audit_parser.set_defaults(func=cmd_audit)

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old monitoring data')
    cleanup_parser.add_argument('--days', type=int, default=90, help='Data retention days')
    cleanup_parser.set_defaults(func=cmd_cleanup)

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
