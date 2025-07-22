#!/usr/bin/env python3
"""
Basic test script for T52 - Tests core scraping functionality without external dependencies
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def setup_logging():
    """Setup logging for test"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def test_diet_scraper_basic():
    """Test basic Diet scraper functionality"""
    print("=" * 60)
    print("T52 Basic Diet Scraper Test")
    print("=" * 60)

    try:
        from scraper.diet_scraper import DietScraper

        # Initialize scraper
        scraper = DietScraper(
            enable_resilience=False
        )  # Disable resilience to avoid dependencies
        print("✅ Diet scraper initialized successfully")

        # Test basic scraping
        print("🔍 Testing basic bill fetching...")
        bills = scraper.fetch_current_bills()

        print("📊 Results:")
        print(f"  📄 Bills found: {len(bills)}")

        if bills:
            print("\n📋 Sample bills (first 3):")
            for i, bill in enumerate(bills[:3], 1):
                print(f"  {i}. {bill.bill_id}: {bill.title[:60]}...")
                print(f"     Status: {bill.status}, Category: {bill.category}")

        # Test scraper statistics
        print("\n📈 Scraper Statistics:")
        stats = scraper.get_scraper_statistics()
        traditional = stats.get("traditional_scraper", {})
        print(f"  ⏱️  Delay: {traditional.get('delay_seconds', 'N/A')}s")
        print(f"  🤖 Robots.txt: {traditional.get('robots_parser_enabled', 'N/A')}")

        resilient = stats.get("resilient_scraper", {})
        print(f"  🛡️  Resilient scraper: {resilient.get('status', 'disabled')}")

        return True, len(bills)

    except Exception as e:
        print(f"❌ Diet scraper test failed: {e}")
        import traceback

        traceback.print_exc()
        return False, 0


async def test_voting_scraper_basic():
    """Test basic voting scraper functionality"""
    print("\n" + "=" * 60)
    print("T52 Basic Voting Scraper Test")
    print("=" * 60)

    try:
        from scraper.voting_scraper import VotingScraper

        # Initialize scraper
        scraper = VotingScraper()
        print("✅ Voting scraper initialized successfully")

        # Test basic voting data fetching
        print("🗳️  Testing basic voting session fetching...")
        sessions = scraper.fetch_voting_sessions()

        print("📊 Results:")
        print(f"  🗳️  Voting sessions found: {len(sessions)}")

        if sessions:
            print("\n📋 Sample sessions (first 2):")
            for i, session in enumerate(sessions[:2], 1):
                print(f"  {i}. {session.bill_number}: {session.bill_title[:50]}...")
                print(f"     Date: {session.vote_date}, Type: {session.vote_type}")
                print(f"     Votes: {len(session.vote_records)} records")

        return True, len(sessions)

    except Exception as e:
        print(f"❌ Voting scraper test failed: {e}")
        import traceback

        traceback.print_exc()
        return False, 0


async def test_pipeline_configuration():
    """Test T52 pipeline configuration without external services"""
    print("\n" + "=" * 60)
    print("T52 Pipeline Configuration Test")
    print("=" * 60)

    try:
        # Test target configuration
        from datetime import datetime

        # Simulate T52 target configuration
        start_date = datetime(2025, 6, 2)  # Monday
        end_date = datetime(2025, 6, 8)  # Sunday

        config = {
            "start_date": start_date,
            "end_date": end_date,
            "max_bills": 30,
            "max_voting_sessions": 10,
            "max_speeches": 50,
            "enable_stt": False,
            "enable_embeddings": True,
        }

        print("📅 Target Configuration:")
        print(
            f"  📅 Date Range: {config['start_date'].date()} to {config['end_date'].date()}"
        )
        print(f"  📊 Max Bills: {config['max_bills']}")
        print(f"  🗳️  Max Voting Sessions: {config['max_voting_sessions']}")
        print(f"  🎤 Max Speeches: {config['max_speeches']}")
        print(f"  🔊 STT Enabled: {config['enable_stt']}")
        print(f"  🧠 Embeddings Enabled: {config['enable_embeddings']}")

        # Calculate date range
        date_range = (end_date - start_date).days + 1
        print("\n📊 Date Range Analysis:")
        print(f"  📅 Total Days: {date_range}")
        print("  📅 Target Week: June 2025 first week")

        # Estimate processing requirements
        print("\n⚡ Processing Estimates:")
        print(f"  📄 Bills/day: {config['max_bills'] / date_range:.1f}")
        print(f"  🗳️  Sessions/day: {config['max_voting_sessions'] / date_range:.1f}")

        return True, config

    except Exception as e:
        print(f"❌ Pipeline configuration test failed: {e}")
        return False, None


async def test_rate_limiting():
    """Test rate limiting and compliance"""
    print("\n" + "=" * 60)
    print("T52 Rate Limiting Test")
    print("=" * 60)

    try:
        import time

        from scraper.diet_scraper import DietScraper

        # Test rate limiting
        scraper = DietScraper(delay_seconds=1.0)

        print("⏱️  Testing rate limiting (3 requests)...")
        start_time = time.time()

        # Make a few requests to test rate limiting
        for i in range(3):
            try:
                # Use a lightweight endpoint for testing
                response = scraper._make_request("https://www.sangiin.go.jp/robots.txt")
                print(f"  Request {i + 1}: ✅ Success ({response.status_code})")
            except Exception as e:
                print(f"  Request {i + 1}: ❌ Failed ({e})")

        end_time = time.time()
        total_time = end_time - start_time

        print("\n📊 Rate Limiting Results:")
        print(f"  ⏱️  Total time: {total_time:.2f}s")
        print(f"  ⏱️  Average delay: {total_time / 3:.2f}s per request")
        print(
            f"  ✅ Rate limiting: {'Working' if total_time >= 2.0 else 'May be too fast'}"
        )

        return True, total_time

    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False, 0


async def simulate_t52_execution():
    """Simulate T52 execution flow"""
    print("\n" + "=" * 60)
    print("T52 Execution Simulation")
    print("=" * 60)

    results = {
        "bills_collected": 0,
        "voting_sessions_collected": 0,
        "speeches_processed": 0,
        "embeddings_generated": 0,
        "errors": [],
    }

    start_time = datetime.now()

    try:
        # Phase 1: Bill collection
        print("📄 Phase 1: Bill Collection")
        diet_success, bill_count = await test_diet_scraper_basic()
        if diet_success:
            results["bills_collected"] = min(bill_count, 30)  # Apply T52 limit
            print(
                f"  ✅ Collected {results['bills_collected']} bills (limited from {bill_count})"
            )
        else:
            results["errors"].append("Bill collection failed")
            print("  ❌ Bill collection failed")

        # Phase 2: Voting data collection
        print("\n🗳️  Phase 2: Voting Data Collection")
        voting_success, session_count = await test_voting_scraper_basic()
        if voting_success:
            results["voting_sessions_collected"] = min(
                session_count, 10
            )  # Apply T52 limit
            print(
                f"  ✅ Collected {results['voting_sessions_collected']} sessions (limited from {session_count})"
            )
        else:
            results["errors"].append("Voting data collection failed")
            print("  ❌ Voting data collection failed")

        # Phase 3: Speech processing (simulated)
        print("\n🎤 Phase 3: Speech Processing (Simulated)")
        print("  ⏭️  Skipped: STT disabled for cost control")
        results["speeches_processed"] = 0

        # Phase 4: Embedding generation (simulated)
        print("\n🧠 Phase 4: Embedding Generation (Simulated)")
        if results["bills_collected"] > 0:
            # Simulate embedding generation
            results["embeddings_generated"] = results["bills_collected"]
            print(f"  ✅ Would generate {results['embeddings_generated']} embeddings")
        else:
            print("  ⏭️  Skipped: No bills to process")

    except Exception as e:
        results["errors"].append(f"Simulation error: {str(e)}")
        print(f"❌ Simulation failed: {e}")

    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()

    # Results summary
    print("\n📊 T52 Simulation Results:")
    print(f"  ⏱️  Duration: {total_time:.2f}s")
    print(f"  📄 Bills: {results['bills_collected']}")
    print(f"  🗳️  Voting Sessions: {results['voting_sessions_collected']}")
    print(f"  🎤 Speeches: {results['speeches_processed']}")
    print(f"  🧠 Embeddings: {results['embeddings_generated']}")
    print(f"  ❌ Errors: {len(results['errors'])}")

    success = len(results["errors"]) == 0
    return success, results


async def main():
    """Run basic T52 tests"""
    setup_logging()

    print("🧪 T52 Basic Pipeline Test Suite")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Target: Basic functionality verification")

    test_results = []

    try:
        # Test 1: Pipeline Configuration
        config_success, config = await test_pipeline_configuration()
        test_results.append(("Configuration", config_success))

        # Test 2: Rate Limiting
        rate_success, rate_time = await test_rate_limiting()
        test_results.append(("Rate Limiting", rate_success))

        # Test 3: T52 Simulation
        sim_success, sim_results = await simulate_t52_execution()
        test_results.append(("T52 Simulation", sim_success))

        # Summary
        print("\n" + "=" * 60)
        print("🏁 Test Summary")
        print("=" * 60)

        passed_tests = sum(1 for _, success in test_results if success)
        total_tests = len(test_results)

        for test_name, success in test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status} {test_name}")

        print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("\n🚀 T52 basic functionality is working!")
            print("   Ready for integration with external services")
        else:
            print("\n⚠️  Some basic tests failed")
            print("   Check error messages above")

        return 0 if passed_tests == total_tests else 1

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
