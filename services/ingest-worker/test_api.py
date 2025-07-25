#!/usr/bin/env python3
"""
API Test for EPIC 2 implementation
"""

import asyncio
import sys

sys.path.append("src")


async def test_scheduler_api():
    """Test scheduler API functionality"""
    print("Testing Scheduler API...")

    try:
        from scheduler.scheduler import IngestionScheduler, SchedulerConfig

        config = SchedulerConfig(project_id="", location="asia-northeast1")
        scheduler = IngestionScheduler(config)

        # Test getting task status
        status = scheduler.get_task_status()
        print(f"✓ Scheduler status: {len(status['scheduled_tasks'])} tasks configured")

        # Test getting specific task
        if status["scheduled_tasks"]:
            task_id = status["scheduled_tasks"][0]["task_id"]
            scheduler.get_task_status(task_id)
            print(f"✓ Individual task status for {task_id}")

        return True
    except Exception as e:
        print(f"✗ Scheduler API test failed: {e}")
        return False


async def test_batch_processor_api():
    """Test batch processor API functionality"""
    print("\nTesting Batch Processor API...")

    try:
        from batch_queue.batch_processor import (
            BatchConfig,
            BatchProcessor,
            TaskPriority,
            TaskType,
        )

        config = BatchConfig(enable_persistence=False, max_concurrent_tasks=1)
        processor = BatchProcessor(config)

        # Test adding a simple task
        task_id = await processor.add_task(
            task_type=TaskType.CUSTOM,
            payload={"test": "data"},
            priority=TaskPriority.NORMAL,
        )
        print(f"✓ Added task: {task_id}")

        # Test getting task status
        task_status = processor.get_task_status(task_id)
        if task_status:
            print(f"✓ Task status retrieved: {task_status['status']}")

        # Test queue status
        queue_status = processor.get_queue_status()
        print(
            f"✓ Queue status: {queue_status['total_queued']} queued, {queue_status['active_tasks']} active"
        )

        return True
    except Exception as e:
        print(f"✗ Batch processor API test failed: {e}")
        return False


async def test_resilient_scraper_api():
    """Test resilient scraper functionality"""
    print("\nTesting Resilient Scraper API...")

    try:
        from scraper.resilience import CacheConfig, RateLimitConfig, ResilientScraper

        rate_config = RateLimitConfig(requests_per_second=1.0)
        cache_config = CacheConfig(enabled=False)  # Disable for testing

        scraper = ResilientScraper(rate_config, cache_config)

        # Test creating a job
        job = scraper.create_job("test_job", "http://example.com")
        print(f"✓ Created job: {job.job_id}")

        # Test getting job status
        job_status = scraper.get_job_status(job.job_id)
        if job_status:
            print(f"✓ Job status retrieved: {job_status['status']}")

        # Test getting statistics
        stats = scraper.get_statistics()
        print(
            f"✓ Statistics: {stats['total_requests']} requests, {stats['success_rate_percent']}% success"
        )

        return True
    except Exception as e:
        print(f"✗ Resilient scraper API test failed: {e}")
        return False


async def test_pdf_processor_basic():
    """Test PDF processor basic functionality"""
    print("\nTesting PDF Processor...")

    try:
        from scraper.pdf_processor import MemberNameMatcher, PDFProcessor

        processor = PDFProcessor()
        matcher = MemberNameMatcher()

        # Test name normalization
        test_name = "田中太郎君"
        normalized = matcher.normalize_name(test_name)
        print(f"✓ Name normalization: '{test_name}' -> '{normalized}'")

        # Test name matching
        test_names = ["田中太郎", "佐藤花子", "鈴木一郎"]
        match, confidence = matcher.find_best_match("田中", test_names)
        if match:
            print(
                f"✓ Name matching: '田中' -> '{match}' (confidence: {confidence:.2f})"
            )

        # Test statistics
        processor.get_processing_statistics()
        print("✓ PDF processor statistics available")

        return True
    except Exception as e:
        print(f"✗ PDF processor test failed: {e}")
        return False


async def main():
    """Run all API tests"""
    print("EPIC 2 API Functionality Test")
    print("=" * 50)

    results = []

    # Run tests
    results.append(await test_scheduler_api())
    results.append(await test_batch_processor_api())
    results.append(await test_resilient_scraper_api())
    results.append(await test_pdf_processor_basic())

    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 All EPIC 2 API tests passed!")
    else:
        print("⚠️  Some tests failed - check implementations")


if __name__ == "__main__":
    asyncio.run(main())
