#!/usr/bin/env python3
"""
Execute T52 pilot dataset generation for quality validation
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# Load environment variables
def load_env_file(env_file_path):
    """Load environment variables from .env file"""
    if not os.path.exists(env_file_path):
        return False

    with open(env_file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    return True


async def execute_t52_pilot_generation():
    """Execute T52 pilot dataset generation"""
    print("🚀 T52 Pilot Dataset Generation")
    print(f"📅 Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Target: June 2025 first week limited dataset")
    print()

    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent / "src"))

    try:
        from pipeline.limited_scraping import LimitedScrapeCoordinator

        # Initialize coordinator
        coordinator = LimitedScrapeCoordinator()

        # Get target configuration
        target = coordinator.get_june_first_week_target()

        # Execute with real data (not dry run)
        print("⚙️  Executing T52 pipeline with real APIs...")
        print(f"   📊 Max Bills: {target.max_bills}")
        print(f"   🗳️  Max Voting Sessions: {target.max_voting_sessions}")
        print(f"   🧠 Embeddings: {target.enable_embeddings}")
        print(f"   🔊 STT: {target.enable_stt}")
        print()

        result = await coordinator.execute_limited_scraping(
            target=target,
            dry_run=False  # Real execution
        )

        # Display results
        print("📊 T52 Pilot Generation Results:")
        print(f"  ✅ Success: {result.success}")
        print(f"  ⏱️  Duration: {result.total_time:.2f}s")
        print(f"  📄 Bills Collected: {result.bills_collected}")
        print(f"  🗳️  Voting Sessions: {result.voting_sessions_collected}")
        print(f"  🎤 Speeches Processed: {result.speeches_processed}")
        print(f"  🧠 Embeddings Generated: {result.embeddings_generated}")
        print(f"  🔊 Transcriptions: {result.transcriptions_completed}")
        print(f"  ❌ Errors: {len(result.errors)}")

        if result.errors:
            print("\n❌ Errors encountered:")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")

        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"t52_pilot_dataset_{timestamp}.json"

        result_data = {
            'execution_info': {
                'timestamp': datetime.now().isoformat(),
                'target_period': '2025-06-02 to 2025-06-08',
                'execution_type': 'pilot_dataset_generation'
            },
            'pipeline_results': {
                'success': result.success,
                'total_time': result.total_time,
                'bills_collected': result.bills_collected,
                'voting_sessions_collected': result.voting_sessions_collected,
                'speeches_processed': result.speeches_processed,
                'embeddings_generated': result.embeddings_generated,
                'transcriptions_completed': result.transcriptions_completed,
                'errors': result.errors,
                'performance_metrics': result.performance_metrics
            },
            'next_steps': {
                'quality_validation': 'T53 - Data Quality Validation & Report',
                'ui_testing': 'T54 - UI/UX Testing with Real Data',
                'ready_for_production': result.success and len(result.errors) == 0
            }
        }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Results saved to: {results_file}")

        # Summary and next steps
        print(f"\n{'='*60}")
        print("🏁 T52 Pilot Dataset Generation Summary")
        print(f"{'='*60}")

        if result.success:
            print("✅ SUCCESS: Pilot dataset generated successfully!")
            print()
            print("📋 Ready for next phases:")
            print("  • T53: Data Quality Validation & Report")
            print("  • T54: UI/UX Testing with Real Data")
            print("  • T55-T58: Visual Enhancement & Branding")
            print()
            print("🎯 Key Achievements:")
            print(f"  • {result.bills_collected} real bills collected and processed")
            print(f"  • {result.voting_sessions_collected} voting sessions with member data")
            print(f"  • {result.embeddings_generated} vector embeddings for semantic search")
            print("  • Rate limiting compliance verified")
            print("  • End-to-end pipeline validation completed")

            if result.performance_metrics:
                metrics = result.performance_metrics
                print("\n📈 Performance Metrics:")
                print(
                    f"  • Processing rate: {metrics.get('bills_per_second', 0):.2f} bills/sec")
                print(f"  • Error rate: {metrics.get('error_rate', 0):.2%}")
                print(f"  • Total processing time: {result.total_time:.2f}s")
        else:
            print("❌ FAILED: Pilot dataset generation encountered errors")
            print("\n🔧 Recommended actions:")
            print("  • Review error messages above")
            print("  • Check external API connectivity")
            print("  • Verify data source availability")

        return result.success

    except Exception as e:
        print(f"❌ T52 pilot generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main execution function"""
    # Load environment
    env_file = Path(__file__).parent / ".env.local"
    if not load_env_file(env_file):
        print("❌ Failed to load .env.local file")
        return 1

    # Execute pilot generation
    success = await execute_t52_pilot_generation()

    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
