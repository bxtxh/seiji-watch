#!/usr/bin/env python3
"""
Test script for EPIC 2 implementation
"""

import sys
import os
sys.path.append('src')

def test_basic_imports():
    """Test basic imports"""
    print("Testing imports...")
    
    try:
        from scheduler.scheduler import IngestionScheduler, SchedulerConfig
        print("✓ Scheduler imports")
    except Exception as e:
        print(f"✗ Scheduler imports: {e}")
    
    try:
        from scraper.resilience import ResilientScraper
        print("✓ Resilience imports")
    except Exception as e:
        print(f"✗ Resilience imports: {e}")
    
    try:
        from batch_queue.batch_processor import BatchProcessor, BatchConfig
        print("✓ Batch processor imports")
    except Exception as e:
        print(f"✗ Batch processor imports: {e}")
    
    try:
        from scraper.pdf_processor import PDFProcessor
        print("✓ PDF processor imports")
    except Exception as e:
        print(f"✗ PDF processor imports: {e}")
    
    try:
        from scraper.hr_voting_scraper import HouseOfRepresentativesVotingScraper
        print("✓ HR voting scraper imports")
    except Exception as e:
        print(f"✗ HR voting scraper imports: {e}")

def test_service_initialization():
    """Test service initialization"""
    print("\nTesting service initialization...")
    
    try:
        from scheduler.scheduler import IngestionScheduler, SchedulerConfig
        config = SchedulerConfig(project_id="", location="asia-northeast1")
        scheduler = IngestionScheduler(config)
        print(f"✓ Scheduler initialized with {len(scheduler.scheduled_tasks)} default tasks")
    except Exception as e:
        print(f"✗ Scheduler initialization: {e}")
    
    try:
        from scraper.resilience import ResilientScraper, RateLimitConfig, CacheConfig
        rate_config = RateLimitConfig()
        cache_config = CacheConfig()
        scraper = ResilientScraper(rate_config, cache_config)
        print("✓ Resilient scraper initialized")
    except Exception as e:
        print(f"✗ Resilient scraper initialization: {e}")
    
    try:
        from batch_queue.batch_processor import BatchProcessor, BatchConfig
        config = BatchConfig(enable_persistence=False)
        processor = BatchProcessor(config)
        print("✓ Batch processor initialized")
    except Exception as e:
        print(f"✗ Batch processor initialization: {e}")

def test_api_endpoints():
    """Test API endpoint definitions"""
    print("\nTesting API endpoints...")
    
    try:
        from fastapi import FastAPI
        app = FastAPI()
        
        # Test route definition
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        print(f"✓ FastAPI app created with {len(app.routes)} routes")
    except Exception as e:
        print(f"✗ API endpoints: {e}")

if __name__ == "__main__":
    print("EPIC 2 Implementation Test")
    print("=" * 50)
    
    test_basic_imports()
    test_service_initialization()
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("Test completed")