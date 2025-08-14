#!/usr/bin/env python3
"""CLI tool for managing Airtable to Supabase migration."""

import asyncio
import click
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.logging import RichHandler

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared" / "src"))

from shared.clients.airtable import AirtableClient
from shared.clients.supabase import SupabaseClient
from shared.dal.hybrid_data_access import HybridDataAccessLayer
from shared.migration.data_migration_service import DataMigrationService
from shared.migration.sync_service import AirtableSupabaseSyncService, SyncConfig, SyncMode
from shared.migration.rollback_manager import RollbackManager, RollbackType
from shared.monitoring.metrics_collector import MetricsCollector
from shared.monitoring.dashboard import MonitoringDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

# Rich console for output
console = Console()


@click.group()
@click.option('--env-file', default='.env', help='Environment file to load')
@click.pass_context
def cli(ctx, env_file):
    """Airtable to Supabase Migration CLI Tool."""
    # Load environment variables
    if Path(env_file).exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        console.print(f"[green]✓[/green] Loaded environment from {env_file}")
    else:
        console.print(f"[yellow]⚠[/yellow] Environment file {env_file} not found")
        
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['airtable'] = AirtableClient()
    ctx.obj['supabase'] = SupabaseClient()
    ctx.obj['metrics'] = MetricsCollector()


@cli.group()
def migrate():
    """Migration operations."""
    pass


@migrate.command()
@click.option('--tables', '-t', multiple=True, help='Specific tables to migrate')
@click.option('--clean-start', is_flag=True, help='Clean existing data before migration')
@click.option('--batch-size', default=100, help='Batch size for migration')
@click.option('--dry-run', is_flag=True, help='Simulate migration without making changes')
@click.pass_context
def full(ctx, tables, clean_start, batch_size, dry_run):
    """Perform full data migration from Airtable to Supabase."""
    console.print("\n[bold blue]Starting Full Migration[/bold blue]")
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No actual changes will be made[/yellow]\n")
        
    # Confirm destructive operation
    if clean_start and not dry_run:
        if not click.confirm("⚠️  Clean start will delete existing Supabase data. Continue?"):
            console.print("[red]Migration cancelled[/red]")
            return
            
    async def run_migration():
        migration_service = DataMigrationService(
            airtable_client=ctx.obj['airtable'],
            supabase_client=ctx.obj['supabase'],
            batch_size=batch_size
        )
        
        # Tables to migrate
        tables_to_migrate = list(tables) if tables else None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            if dry_run:
                # Simulate migration
                task = progress.add_task("Analyzing tables...", total=len(tables_to_migrate or migration_service.MIGRATION_ORDER))
                
                for table in (tables_to_migrate or migration_service.MIGRATION_ORDER):
                    progress.update(task, description=f"Analyzing {table}...")
                    await asyncio.sleep(0.5)  # Simulate processing
                    progress.advance(task)
                    
                console.print("\n[green]✓[/green] Dry run completed successfully")
                
            else:
                # Perform actual migration
                stats = await migration_service.migrate_all_tables(
                    tables=tables_to_migrate,
                    clean_start=clean_start
                )
                
                # Display results
                console.print("\n[bold green]Migration Completed[/bold green]\n")
                
                table = Table(title="Migration Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Total Records", str(stats["total_records"]))
                table.add_row("Migrated", str(stats["migrated_records"]))
                table.add_row("Failed", str(stats["failed_records"]))
                table.add_row("Duration", f"{stats.get('duration_seconds', 0):.2f}s")
                
                console.print(table)
                
                # Show table-specific stats
                if stats.get("table_stats"):
                    console.print("\n[bold]Table Details:[/bold]")
                    for table_name, table_stat in stats["table_stats"].items():
                        status_icon = "✓" if table_stat["status"].value == "completed" else "✗"
                        console.print(f"  {status_icon} {table_name}: {table_stat['migrated_records']} records")
                        
    asyncio.run(run_migration())


@migrate.command()
@click.option('--table', '-t', required=True, help='Table to migrate')
@click.option('--since', help='Migrate records modified since (ISO format)')
@click.pass_context
def incremental(ctx, table, since):
    """Perform incremental migration for a specific table."""
    console.print(f"\n[bold blue]Incremental Migration: {table}[/bold blue]")
    
    async def run_incremental():
        sync_service = AirtableSupabaseSyncService(
            airtable_client=ctx.obj['airtable'],
            supabase_client=ctx.obj['supabase']
        )
        
        result = await sync_service.sync_table(table, SyncMode.INCREMENTAL)
        
        # Display results
        console.print(f"\n[green]✓[/green] Sync completed for {table}")
        console.print(f"  Records processed: {result.records_processed}")
        console.print(f"  Created: {result.records_created}")
        console.print(f"  Updated: {result.records_updated}")
        console.print(f"  Success rate: {result.success_rate:.1f}%")
        
        if result.errors:
            console.print(f"\n[yellow]⚠ Errors encountered:[/yellow]")
            for error in result.errors[:5]:
                console.print(f"  - {error}")
                
    asyncio.run(run_incremental())


@migrate.command()
@click.pass_context
def validate(ctx):
    """Validate data consistency between Airtable and Supabase."""
    console.print("\n[bold blue]Validating Data Consistency[/bold blue]\n")
    
    async def run_validation():
        migration_service = DataMigrationService(
            airtable_client=ctx.obj['airtable'],
            supabase_client=ctx.obj['supabase']
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Validating tables...", total=None)
            
            validation_results = await migration_service.validate_migration()
            
            progress.update(task, description="Validation complete")
            
        # Display results
        table = Table(title="Data Consistency Report")
        table.add_column("Table", style="cyan")
        table.add_column("Airtable", style="yellow")
        table.add_column("Supabase", style="blue")
        table.add_column("Consistency", style="green")
        table.add_column("Status", style="bold")
        
        for table_name, result in validation_results["tables"].items():
            if "error" in result:
                table.add_row(
                    table_name,
                    "Error",
                    "Error",
                    "N/A",
                    "[red]Error[/red]"
                )
            else:
                consistency = result["consistency_score"]
                status = "[green]Valid[/green]" if consistency >= 95 else "[yellow]Inconsistent[/yellow]"
                
                table.add_row(
                    table_name,
                    str(result["airtable_count"]),
                    str(result["supabase_count"]),
                    f"{consistency:.1f}%",
                    status
                )
                
        console.print(table)
        
        overall = validation_results["overall_consistency"]
        if overall >= 95:
            console.print(f"\n[green]✓[/green] Overall consistency: {overall:.1f}%")
        else:
            console.print(f"\n[yellow]⚠[/yellow] Overall consistency: {overall:.1f}%")
            
    asyncio.run(run_validation())


@cli.group()
def sync():
    """Synchronization operations."""
    pass


@sync.command()
@click.option('--mode', type=click.Choice(['incremental', 'full', 'real_time']), default='incremental')
@click.option('--interval', default=5, help='Sync interval in minutes')
@click.option('--tables', '-t', multiple=True, help='Specific tables to sync')
@click.pass_context
def start(ctx, mode, interval, tables):
    """Start synchronization service."""
    console.print(f"\n[bold blue]Starting Sync Service[/bold blue]")
    console.print(f"  Mode: {mode}")
    console.print(f"  Interval: {interval} minutes")
    console.print(f"  Tables: {', '.join(tables) if tables else 'All'}")
    
    async def run_sync():
        config = SyncConfig(
            mode=SyncMode(mode),
            interval_minutes=interval,
            tables_to_sync=list(tables) if tables else []
        )
        
        sync_service = AirtableSupabaseSyncService(
            airtable_client=ctx.obj['airtable'],
            supabase_client=ctx.obj['supabase'],
            config=config
        )
        
        await sync_service.start()
        
        console.print("\n[green]✓[/green] Sync service started")
        console.print("Press Ctrl+C to stop...")
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(60)
                status = await sync_service.get_sync_status()
                console.print(f"[dim]Queue size: {status['queue_size']} | Last sync: {status.get('last_sync_times', {})}")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping sync service...[/yellow]")
            await sync_service.stop()
            console.print("[green]✓[/green] Sync service stopped")
            
    asyncio.run(run_sync())


@sync.command()
@click.pass_context
def status(ctx):
    """Get synchronization status."""
    async def get_status():
        sync_service = AirtableSupabaseSyncService(
            airtable_client=ctx.obj['airtable'],
            supabase_client=ctx.obj['supabase']
        )
        
        status = await sync_service.get_sync_status()
        
        console.print("\n[bold]Sync Service Status[/bold]")
        console.print(f"  Running: {'Yes' if status['is_running'] else 'No'}")
        console.print(f"  Mode: {status.get('mode', 'N/A')}")
        console.print(f"  Queue Size: {status.get('queue_size', 0)}")
        
        if status.get('last_sync_times'):
            console.print("\n[bold]Last Sync Times:[/bold]")
            for table, time in status['last_sync_times'].items():
                console.print(f"  {table}: {time}")
                
    asyncio.run(get_status())


@cli.group()
def rollback():
    """Rollback operations."""
    pass


@rollback.command()
@click.option('--phase', type=int, required=True, help='Migration phase')
@click.option('--description', required=True, help='Rollback point description')
@click.option('--type', type=click.Choice(['configuration', 'data', 'schema', 'full']), default='full')
@click.pass_context
def create(ctx, phase, description, type):
    """Create a rollback point."""
    console.print(f"\n[bold blue]Creating Rollback Point[/bold blue]")
    
    async def create_rollback():
        rollback_manager = RollbackManager(
            supabase_client=ctx.obj['supabase']
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating rollback point...", total=None)
            
            point = await rollback_manager.create_rollback_point(
                phase=phase,
                description=description,
                rollback_type=RollbackType(type)
            )
            
            progress.update(task, description="Rollback point created")
            
        if point.is_valid:
            console.print(f"\n[green]✓[/green] Rollback point created: {point.id}")
            console.print(f"  Phase: {point.phase}")
            console.print(f"  Type: {point.rollback_type.value}")
            console.print(f"  Description: {point.description}")
        else:
            console.print(f"\n[red]✗[/red] Failed to create rollback point")
            if point.metadata.get("error"):
                console.print(f"  Error: {point.metadata['error']}")
                
    asyncio.run(create_rollback())


@rollback.command()
@click.option('--phase', type=int, help='Filter by phase')
@click.pass_context
def list(ctx, phase):
    """List available rollback points."""
    rollback_manager = RollbackManager()
    
    points = rollback_manager.list_rollback_points(phase=phase)
    
    if not points:
        console.print("\n[yellow]No rollback points found[/yellow]")
        return
        
    table = Table(title="Available Rollback Points")
    table.add_column("ID", style="cyan")
    table.add_column("Phase", style="yellow")
    table.add_column("Type", style="blue")
    table.add_column("Description", style="white")
    table.add_column("Created", style="green")
    table.add_column("Valid", style="bold")
    
    for point in points:
        valid = "[green]Yes[/green]" if point.is_valid else "[red]No[/red]"
        created = point.timestamp.strftime("%Y-%m-%d %H:%M")
        
        table.add_row(
            point.id,
            str(point.phase),
            point.rollback_type.value,
            point.description,
            created,
            valid
        )
        
    console.print(table)


@rollback.command()
@click.option('--point-id', required=True, help='Rollback point ID')
@click.option('--tables', '-t', multiple=True, help='Specific tables to rollback')
@click.option('--force', is_flag=True, help='Skip confirmation')
@click.pass_context
def execute(ctx, point_id, tables, force):
    """Execute rollback to a specific point."""
    if not force:
        console.print(f"\n[bold red]WARNING: This will rollback data to point {point_id}[/bold red]")
        if not click.confirm("Are you sure you want to continue?"):
            console.print("[yellow]Rollback cancelled[/yellow]")
            return
            
    async def run_rollback():
        rollback_manager = RollbackManager(
            supabase_client=ctx.obj['supabase']
        )
        
        # Validate rollback point
        if not rollback_manager.validate_rollback_point(point_id):
            console.print(f"[red]✗[/red] Invalid rollback point: {point_id}")
            return
            
        console.print(f"\n[bold blue]Executing Rollback[/bold blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Rolling back...", total=None)
            
            operation = await rollback_manager.execute_rollback(
                point_id,
                list(tables) if tables else None
            )
            
            progress.update(task, description="Rollback complete")
            
        # Display results
        if operation.status.value == "completed":
            console.print(f"\n[green]✓[/green] Rollback completed successfully")
            console.print(f"  Recovered tables: {', '.join(operation.recovered_tables)}")
            if operation.skipped_tables:
                console.print(f"  Skipped tables: {', '.join(operation.skipped_tables)}")
        else:
            console.print(f"\n[red]✗[/red] Rollback failed")
            if operation.error_message:
                console.print(f"  Error: {operation.error_message}")
                
    asyncio.run(run_rollback())


@cli.group()
def monitor():
    """Monitoring operations."""
    pass


@monitor.command()
@click.pass_context
def dashboard(ctx):
    """Display monitoring dashboard."""
    async def show_dashboard():
        metrics_collector = ctx.obj['metrics']
        dal = HybridDataAccessLayer()
        
        dashboard = MonitoringDashboard(
            metrics_collector=metrics_collector,
            hybrid_dal=dal
        )
        
        await dashboard.start()
        await dashboard.refresh()
        
        data = dashboard.get_dashboard_data()
        
        # System Overview
        console.print("\n[bold]System Overview[/bold]")
        overview = data.get("system_overview", {})
        
        status_icon = "✓" if overview.get("overall_health") else "✗"
        status_color = "green" if overview.get("overall_health") else "red"
        console.print(f"  [{status_color}]{status_icon}[/{status_color}] Overall Health")
        
        console.print(f"  Sync Status: {overview.get('sync_status', 'unknown')}")
        console.print(f"  Active Alerts: {overview.get('active_alerts', 0)}")
        console.print(f"  Error Rate: {overview.get('error_rate', 0) * 100:.2f}%")
        
        # Data Sources
        console.print("\n[bold]Data Sources[/bold]")
        for source, healthy in overview.get("data_sources", {}).items():
            icon = "✓" if healthy else "✗"
            color = "green" if healthy else "red"
            console.print(f"  [{color}]{icon}[/{color}] {source.title()}")
            
        # Key Metrics
        if data.get("key_metrics"):
            console.print("\n[bold]Key Metrics[/bold]")
            for metric in data["key_metrics"]:
                status_color = {
                    "normal": "green",
                    "warning": "yellow",
                    "critical": "red"
                }.get(metric["status"], "white")
                
                value = f"{metric['value']}{metric.get('unit', '')}"
                console.print(f"  {metric['name']}: [{status_color}]{value}[/{status_color}]")
                
        # Active Alerts
        if data.get("alerts"):
            console.print("\n[bold red]Active Alerts[/bold red]")
            for alert in data["alerts"][:5]:
                severity_color = {
                    "info": "blue",
                    "warning": "yellow",
                    "error": "red",
                    "critical": "bold red"
                }.get(alert["severity"], "white")
                
                console.print(f"  [{severity_color}]{alert['severity'].upper()}[/{severity_color}] {alert['message']}")
                
        await dashboard.stop()
        
    asyncio.run(show_dashboard())


@monitor.command()
@click.pass_context
def health(ctx):
    """Check system health."""
    async def check_health():
        dal = HybridDataAccessLayer()
        await dal.initialize()
        
        health_status = await dal.health_check()
        
        console.print("\n[bold]Health Check Results[/bold]\n")
        
        all_healthy = True
        for component, healthy in health_status.items():
            if healthy:
                console.print(f"  [green]✓[/green] {component.title()}: Healthy")
            else:
                console.print(f"  [red]✗[/red] {component.title()}: Unhealthy")
                all_healthy = False
                
        if all_healthy:
            console.print("\n[green]✓ All systems operational[/green]")
        else:
            console.print("\n[yellow]⚠ Some systems are experiencing issues[/yellow]")
            
        await dal.close()
        
    asyncio.run(check_health())


if __name__ == "__main__":
    cli()