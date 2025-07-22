#!/usr/bin/env python3
"""
Test script for House of Representatives PDF processing functionality

This script provides comprehensive testing of the HR PDF processing pipeline
including validation, error handling, and performance assessment.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pipeline.hr_data_integration import run_hr_integration_pipeline
from scraper.enhanced_hr_scraper import EnhancedHRProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_basic_hr_processing():
    """Test basic HR PDF processing functionality"""
    logger.info("=" * 60)
    logger.info("Testing Basic HR PDF Processing")
    logger.info("=" * 60)

    try:
        processor = EnhancedHRProcessor()

        # Test with a small time window
        sessions = await processor.process_enhanced_hr_data(
            days_back=3,  # Small window for testing
            max_concurrent=1,  # Conservative for testing
        )

        logger.info(f"Processed {len(sessions)} voting sessions")

        if sessions:
            # Display summary of first session
            session = sessions[0]
            logger.info(f"Sample session: {session.session_id}")
            logger.info(f"  Bill: {session.base_session.bill_title}")
            logger.info(f"  Date: {session.base_session.vote_date}")
            logger.info(f"  Members: {len(session.base_session.vote_records)}")
            logger.info(f"  Quality: {session.quality_metrics}")

        # Get processing statistics
        stats = processor.get_processing_statistics()
        logger.info(f"Processing statistics: {json.dumps(stats, indent=2)}")

        return True

    except Exception as e:
        logger.error(f"Basic HR processing test failed: {e}")
        return False


async def test_integration_pipeline():
    """Test the complete integration pipeline"""
    logger.info("=" * 60)
    logger.info("Testing HR Integration Pipeline (Dry Run)")
    logger.info("=" * 60)

    try:
        # Run pipeline in dry run mode
        result = await run_hr_integration_pipeline(
            days_back=2,
            dry_run=True,  # Important: don't modify database in test
            max_concurrent=1,
        )

        logger.info(f"Pipeline result: {json.dumps(result, indent=2, default=str)}")

        if result["success"]:
            integration_result = result.get("integration_results")
            if integration_result:
                logger.info(
                    f"Integration would have processed {integration_result.sessions_processed} sessions"
                )
                logger.info(
                    f"Integration would have created {integration_result.bills_created} bills"
                )
                logger.info(
                    f"Integration would have created {integration_result.members_created} members"
                )
                logger.info(
                    f"Integration would have created {integration_result.votes_created} votes"
                )

        return result["success"]

    except Exception as e:
        logger.error(f"Integration pipeline test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling with invalid inputs"""
    logger.info("=" * 60)
    logger.info("Testing Error Handling")
    logger.info("=" * 60)

    try:
        processor = EnhancedHRProcessor()

        # Test with impossible parameters
        sessions = await processor.process_enhanced_hr_data(
            days_back=0,  # Should handle gracefully
            max_concurrent=1,
        )

        logger.info(f"Processed {len(sessions)} sessions with days_back=0")

        # Test with very old date range (should find no PDFs)
        sessions = await processor.process_enhanced_hr_data(
            days_back=3650,  # 10 years back - should be empty
            max_concurrent=1,
        )

        logger.info(f"Processed {len(sessions)} sessions with days_back=3650")

        return True

    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False


async def test_performance():
    """Test performance characteristics"""
    logger.info("=" * 60)
    logger.info("Testing Performance")
    logger.info("=" * 60)

    try:
        processor = EnhancedHRProcessor()

        # Measure processing time
        start_time = time.time()

        sessions = await processor.process_enhanced_hr_data(
            days_back=1,  # Single day for performance test
            max_concurrent=2,
        )

        processing_time = time.time() - start_time

        logger.info(
            f"Processed {len(sessions)} sessions in {processing_time:.2f} seconds"
        )

        if sessions:
            avg_time_per_session = processing_time / len(sessions)
            logger.info(f"Average time per session: {avg_time_per_session:.2f} seconds")

        # Performance thresholds
        if processing_time > 300:  # 5 minutes
            logger.warning("Processing time exceeded 5 minutes - may need optimization")
        else:
            logger.info("Processing time within acceptable limits")

        return True

    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        return False


def save_test_results(results: dict[str, Any]):
    """Save test results to file"""
    try:
        output_file = Path(__file__).parent / "test_results.json"

        test_data = {
            "test_timestamp": datetime.now().isoformat(),
            "test_results": results,
            "test_environment": {
                "python_version": sys.version,
                "test_script": str(Path(__file__).name),
            },
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Test results saved to {output_file}")

    except Exception as e:
        logger.error(f"Failed to save test results: {e}")


async def run_comprehensive_tests():
    """Run all HR processing tests"""
    logger.info("Starting Comprehensive HR Processing Tests")
    logger.info("=" * 80)

    test_results = {}
    overall_success = True

    # Test 1: Basic processing
    logger.info("\n1. Basic HR PDF Processing Test")
    test_results["basic_processing"] = await test_basic_hr_processing()
    overall_success &= test_results["basic_processing"]

    # Test 2: Integration pipeline
    logger.info("\n2. Integration Pipeline Test")
    test_results["integration_pipeline"] = await test_integration_pipeline()
    overall_success &= test_results["integration_pipeline"]

    # Test 3: Error handling
    logger.info("\n3. Error Handling Test")
    test_results["error_handling"] = await test_error_handling()
    overall_success &= test_results["error_handling"]

    # Test 4: Performance
    logger.info("\n4. Performance Test")
    test_results["performance"] = await test_performance()
    overall_success &= test_results["performance"]

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Test Summary")
    logger.info("=" * 80)

    for test_name, result in test_results.items():
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nOverall Result: {'PASS' if overall_success else 'FAIL'}")

    # Save results
    save_test_results(test_results)

    return overall_success


if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)
