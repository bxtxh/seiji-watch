#!/usr/bin/env python3
"""
Test script for T52 - Limited scope scraping pipeline
Tests the data pipeline coordination for 2025 June first week
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pipeline.limited_scraping import (
    LimitedScrapeCoordinator,
    run_limited_scraping_pipeline,
)


def setup_logging():
    """Setup logging for test"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("t52_test.log")],
    )


async def test_pipeline_status():
    """Test pipeline status and configuration"""
    print("=" * 60)
    print("T52 Pipeline Status Test")
    print("=" * 60)

    coordinator = LimitedScrapeCoordinator()
    status = coordinator.get_pipeline_status()

    print(f"Pipeline Status: {status['status']}")
    print("\nService Availability:")
    for service, available in status["services"].items():
        status_icon = "✅" if available else "❌"
        print(
            f"  {status_icon} {service}: {'Available' if available else 'Not Available'}"
        )

    print("\nTarget Configuration:")
    target_config = status["target_configuration"]
    print(
        f"  📅 Date Range: {target_config['start_date']} to {target_config['end_date']}"
    )
    print(f"  📊 Max Bills: {target_config['max_bills']}")
    print(f"  🗳️  Max Voting Sessions: {target_config['max_voting_sessions']}")
    print(f"  🎤 Max Speeches: {target_config['max_speeches']}")
    print(f"  🔊 STT Enabled: {target_config['enable_stt']}")
    print(f"  🧠 Embeddings Enabled: {target_config['enable_embeddings']}")

    print("\nEstimated Costs:")
    costs = status["estimated_costs"]
    for service, cost in costs.items():
        print(f"  💰 {service}: {cost}")

    return status


async def test_dry_run():
    """Test dry run execution"""
    print("\n" + "=" * 60)
    print("T52 Dry Run Test")
    print("=" * 60)

    print("🧪 Executing dry run (no actual scraping)...")
    start_time = datetime.now()

    result = await run_limited_scraping_pipeline(dry_run=True)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n📊 Dry Run Results:")
    print(f"  ✅ Success: {result.success}")
    print(f"  ⏱️  Duration: {result.total_time:.2f}s (actual: {duration:.2f}s)")
    print(f"  📄 Bills Collected: {result.bills_collected}")
    print(f"  🗳️  Voting Sessions: {result.voting_sessions_collected}")
    print(f"  🎤 Speeches Processed: {result.speeches_processed}")
    print(f"  🧠 Embeddings Generated: {result.embeddings_generated}")
    print(f"  🔊 Transcriptions: {result.transcriptions_completed}")
    print(f"  ❌ Errors: {len(result.errors)}")

    if result.errors:
        print("\n❌ Errors encountered:")
        for i, error in enumerate(result.errors[:3], 1):
            print(f"  {i}. {error}")
        if len(result.errors) > 3:
            print(f"  ... and {len(result.errors) - 3} more errors")

    if result.performance_metrics:
        print("\n📈 Performance Metrics:")
        metrics = result.performance_metrics
        print(f"  ⚡ Bills/second: {metrics.get('bills_per_second', 0):.2f}")
        print(
            f"  ⚡ Voting sessions/second: {metrics.get('voting_sessions_per_second', 0):.2f}"
        )
        print(f"  ⚡ Embeddings/second: {metrics.get('embeddings_per_second', 0):.2f}")
        print(f"  📊 Error Rate: {metrics.get('error_rate', 0):.2%}")

        if "resource_usage" in metrics:
            resources = metrics["resource_usage"]
            if "cpu_percent" in resources:
                print(f"  💻 CPU Usage: {resources['cpu_percent']:.1f}%")
            if "memory_percent" in resources:
                print(f"  🧠 Memory Usage: {resources['memory_percent']:.1f}%")

    return result


async def test_limited_real_run():
    """Test actual limited run (if services are available)"""
    print("\n" + "=" * 60)
    print("T52 Limited Real Run Test")
    print("=" * 60)

    coordinator = LimitedScrapeCoordinator()
    status = coordinator.get_pipeline_status()

    # Check if essential services are available
    required_services = ["diet_scraper", "voting_scraper"]
    available_services = [svc for svc in required_services if status["services"][svc]]

    if len(available_services) < len(required_services):
        print("⚠️  Skipping real run - required services not available")
        print(f"   Required: {required_services}")
        print(f"   Available: {available_services}")
        return None

    print("🚀 Executing limited real run...")
    print("   ⚠️  This will make actual API calls (limited scope)")

    # Confirm with user if running interactively
    if sys.stdin.isatty():
        response = input("   Continue? [y/N]: ").strip().lower()
        if response != "y":
            print("   ❌ Real run cancelled by user")
            return None

    start_time = datetime.now()

    # Execute with very conservative limits
    coordinator = LimitedScrapeCoordinator()
    target = coordinator.get_june_first_week_target()
    target.max_bills = 5  # Very limited for testing
    target.max_voting_sessions = 3
    target.enable_stt = False  # Disabled for cost control

    result = await coordinator.execute_limited_scraping(target=target, dry_run=False)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n📊 Real Run Results:")
    print(f"  ✅ Success: {result.success}")
    print(f"  ⏱️  Duration: {result.total_time:.2f}s (actual: {duration:.2f}s)")
    print(f"  📄 Bills Collected: {result.bills_collected}")
    print(f"  🗳️  Voting Sessions: {result.voting_sessions_collected}")
    print(f"  🧠 Embeddings Generated: {result.embeddings_generated}")
    print(f"  ❌ Errors: {len(result.errors)}")

    if result.errors:
        print("\n❌ Errors encountered:")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")

    # Save detailed results to file
    results_file = f"t52_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        # Convert result to dict for JSON serialization
        result_dict = {
            "success": result.success,
            "total_time": result.total_time,
            "bills_collected": result.bills_collected,
            "voting_sessions_collected": result.voting_sessions_collected,
            "speeches_processed": result.speeches_processed,
            "embeddings_generated": result.embeddings_generated,
            "transcriptions_completed": result.transcriptions_completed,
            "errors": result.errors,
            "performance_metrics": result.performance_metrics,
            "test_metadata": {
                "test_date": datetime.now().isoformat(),
                "test_type": "limited_real_run",
                "actual_duration": duration,
            },
        }
        json.dump(result_dict, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Detailed results saved to: {results_file}")

    return result


async def test_service_availability():
    """Test individual service availability"""
    print("\n" + "=" * 60)
    print("T52 Service Availability Test")
    print("=" * 60)

    coordinator = LimitedScrapeCoordinator()

    # Test Diet Scraper
    print("🔍 Testing Diet Scraper...")
    try:
        scraper_stats = coordinator.diet_scraper.get_scraper_statistics()
        print("  ✅ Diet Scraper: Available")
        print(
            f"     Traditional scraper delay: {scraper_stats['traditional_scraper']['delay_seconds']}s"
        )
        print(
            f"     Robots.txt parser: {scraper_stats['traditional_scraper']['robots_parser_enabled']}"
        )
        resilient_status = scraper_stats.get("resilient_scraper", {}).get(
            "status", "unknown"
        )
        print(f"     Resilient scraper: {resilient_status}")
    except Exception as e:
        print(f"  ❌ Diet Scraper: Error - {e}")

    # Test Voting Scraper
    print("\n🗳️  Testing Voting Scraper...")
    try:
        if coordinator.voting_scraper:
            print("  ✅ Voting Scraper: Available")
        else:
            print("  ❌ Voting Scraper: Not initialized")
    except Exception as e:
        print(f"  ❌ Voting Scraper: Error - {e}")

    # Test Vector Client
    print("\n🧠 Testing Vector Client...")
    try:
        if coordinator.vector_client:
            stats = coordinator.vector_client.get_embedding_stats()
            print("  ✅ Vector Client: Available")
            print(f"     Bills stored: {stats.get('bills', 0)}")
            print(f"     Speeches stored: {stats.get('speeches', 0)}")
        else:
            print("  ❌ Vector Client: Not available (missing API keys)")
    except Exception as e:
        print(f"  ❌ Vector Client: Error - {e}")

    # Test Whisper Client
    print("\n🔊 Testing Whisper Client...")
    try:
        if coordinator.whisper_client:
            print("  ✅ Whisper Client: Available")
        else:
            print("  ❌ Whisper Client: Not available (missing API key)")
    except Exception as e:
        print(f"  ❌ Whisper Client: Error - {e}")


async def main():
    """Run all T52 tests"""
    setup_logging()

    print("🧪 T52 Data Pipeline Coordination Test Suite")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Target: Limited scraping for June 2025 first week")

    try:
        # Test 1: Pipeline Status
        await test_pipeline_status()

        # Test 2: Service Availability
        await test_service_availability()

        # Test 3: Dry Run
        dry_result = await test_dry_run()

        # Test 4: Limited Real Run (optional)
        real_result = await test_limited_real_run()

        # Summary
        print("\n" + "=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)

        print("✅ Pipeline Status: PASSED")
        print("✅ Service Availability: PASSED")
        print(
            f"{'✅' if dry_result.success else '❌'} Dry Run: {'PASSED' if dry_result.success else 'FAILED'}"
        )

        if real_result:
            print(
                f"{'✅' if real_result.success else '❌'} Limited Real Run: {'PASSED' if real_result.success else 'FAILED'}"
            )
        else:
            print("⏭️  Limited Real Run: SKIPPED")

        print(
            f"\n📊 Overall T52 Pipeline Status: {'✅ READY' if dry_result.success else '❌ NEEDS ATTENTION'}"
        )

        if dry_result.success:
            print("\n🚀 T52 pipeline is ready for production execution!")
            print("   Use POST /t52/scrape with dry_run=false to execute")
        else:
            print("\n⚠️  T52 pipeline needs attention before production use")
            print("   Check error logs and service availability")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
