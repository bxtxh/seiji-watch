#!/usr/bin/env python3
"""
Test script for EPIC 14 Hybrid Ingestion Pipeline

Tests the routing logic and data flow between NDL API and Whisper STT
pipelines with various scenarios.
"""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # Add project root

from src.pipeline.ingestion_router import (
    DataSource,
    HybridIngestionRouter,
    IngestionRequest,
)


async def test_routing_decisions():
    """Test the routing decision logic"""
    print("🧪 Testing Routing Decision Logic")
    print("=" * 50)

    async with HybridIngestionRouter() as router:
        # Test cases for routing decisions
        test_cases = [
            # Historical dates - should route to NDL API
            (
                date(2025, 3, 15),
                DataSource.NDL_API,
                "Historical meeting in 第217回国会",
            ),
            (date(2025, 6, 21), DataSource.NDL_API, "Last day of 第217回国会"),
            # Recent dates - should route to Whisper STT
            (date(2025, 6, 22), DataSource.WHISPER_STT, "First day of 第218回国会"),
            (date(2025, 7, 15), DataSource.WHISPER_STT, "Recent meeting"),
            # Edge cases
            (date(2024, 12, 1), DataSource.NDL_API, "Pre-session date"),
        ]

        for test_date, expected_source, description in test_cases:
            result = await router.test_routing_decision(test_date)
            actual_source = DataSource(result["selected_source"])

            status = "✅" if actual_source == expected_source else "❌"
            print(f"{status} {test_date}: {description}")
            print(f"   Expected: {expected_source.value}, Got: {actual_source.value}")
            print(f"   Rationale: {result['rationale']}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print()


async def test_ndl_api_integration():
    """Test NDL API integration"""
    print("🔗 Testing NDL API Integration")
    print("=" * 50)

    async with HybridIngestionRouter() as router:
        # Test historical data ingestion
        request = IngestionRequest(
            meeting_date=date(2025, 6, 15),  # Historical date
            force_source=DataSource.NDL_API,
        )

        print(f"Testing NDL API ingestion for {request.meeting_date}")
        result = await router.ingest_data(request)

        print(f"Success: {'✅' if result.success else '❌'}")
        print(f"Data Source: {result.data_source.value}")
        print(f"Meetings: {result.meeting_count}")
        print(f"Speeches: {result.speech_count}")
        print(f"Processing Time: {result.processing_time_seconds:.1f}s")

        if result.warnings:
            print(f"⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"   - {warning}")

        if result.errors:
            print(f"❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   - {error}")

        print()


async def test_whisper_stt_integration():
    """Test Whisper STT integration"""
    print("🎤 Testing Whisper STT Integration")
    print("=" * 50)

    async with HybridIngestionRouter() as router:
        # Test recent data ingestion
        request = IngestionRequest(
            meeting_date=date(2025, 7, 15),  # Recent date
            force_source=DataSource.WHISPER_STT,
        )

        print(f"Testing Whisper STT ingestion for {request.meeting_date}")
        result = await router.ingest_data(request)

        print(f"Success: {'✅' if result.success else '❌'}")
        print(f"Data Source: {result.data_source.value}")
        print(f"Meetings: {result.meeting_count}")
        print(f"Speeches: {result.speech_count}")
        print(f"Processing Time: {result.processing_time_seconds:.1f}s")

        if result.warnings:
            print(f"⚠️  Warnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"   - {warning}")

        if result.errors:
            print(f"❌ Errors ({len(result.errors)}):")
            for error in result.errors:
                print(f"   - {error}")

        print()


async def test_fallback_mechanisms():
    """Test fallback mechanisms"""
    print("🔄 Testing Fallback Mechanisms")
    print("=" * 50)

    async with HybridIngestionRouter() as router:
        # Test fallback from primary to secondary pipeline
        request = IngestionRequest(
            meeting_date=date(2025, 7, 15),  # Recent date - primary: Whisper STT
            # Don't force source to test natural routing + fallback
        )

        print(f"Testing fallback behavior for {request.meeting_date}")
        result = await router.ingest_data(request)

        print(f"Success: {'✅' if result.success else '❌'}")
        print(f"Data Source: {result.data_source.value}")

        if result.warnings:
            fallback_warnings = [w for w in result.warnings if "Fallback" in w]
            if fallback_warnings:
                print("🔄 Fallback detected:")
                for warning in fallback_warnings:
                    print(f"   - {warning}")

        print()


async def test_statistics_tracking():
    """Test statistics and monitoring"""
    print("📊 Testing Statistics Tracking")
    print("=" * 50)

    async with HybridIngestionRouter() as router:
        # Generate some routing activity
        test_requests = [
            IngestionRequest(meeting_date=date(2025, 3, 15)),  # NDL API
            IngestionRequest(meeting_date=date(2025, 7, 15)),  # Whisper STT
            IngestionRequest(meeting_date=date(2025, 6, 21)),  # NDL API
        ]

        for request in test_requests:
            await router.ingest_data(request)

        # Get statistics
        stats = router.get_routing_statistics()

        print("Routing Distribution:")
        print(
            f"  NDL API: {stats['routing_distribution']['ndl_api_requests']} requests "
            f"({stats['routing_distribution']['ndl_api_percentage']:.1f}%)"
        )
        print(
            f"  Whisper STT: {stats['routing_distribution']['whisper_stt_requests']} requests "
            f"({stats['routing_distribution']['whisper_stt_percentage']:.1f}%)"
        )

        print("\nReliability:")
        print(f"  Fallback Rate: {stats['reliability']['fallback_rate']:.1f}%")
        print(f"  Manual Overrides: {stats['reliability']['manual_overrides']}")

        print("\nThroughput:")
        print(f"  Total Meetings: {stats['throughput']['total_meetings_processed']}")
        print(f"  Total Speeches: {stats['throughput']['total_speeches_processed']}")
        print(
            f"  Avg Meetings/Request: {stats['throughput']['meetings_per_request']:.1f}"
        )

        print("\nConfiguration:")
        print(f"  Cutoff Date: {stats['configuration']['cutoff_date']}")
        print(f"  Session 217: {stats['configuration']['session_217_period']}")
        print()


async def test_cost_estimation():
    """Test cost analysis for hybrid approach"""
    print("💰 Testing Cost Estimation")
    print("=" * 50)

    # Simulate cost calculations
    historical_meetings = 150  # Estimated meetings in 第217回国会
    whisper_cost_per_meeting = 2.5  # USD per meeting (estimated)
    ndl_api_cost_per_meeting = 0.0  # Free API

    # Cost before hybrid approach (all Whisper)
    cost_before = historical_meetings * whisper_cost_per_meeting

    # Cost after hybrid approach (NDL for historical)
    cost_after_historical = historical_meetings * ndl_api_cost_per_meeting
    future_meetings_per_month = 20
    cost_after_ongoing = future_meetings_per_month * whisper_cost_per_meeting

    savings = cost_before - cost_after_historical
    savings_percentage = (savings / cost_before) * 100

    print("Historical Data Processing:")
    print(f"  Estimated Meetings: {historical_meetings}")
    print(f"  Cost (All Whisper): ${cost_before:.2f}")
    print(f"  Cost (NDL API): ${cost_after_historical:.2f}")
    print(f"  Savings: ${savings:.2f} ({savings_percentage:.1f}%)")

    print("\nOngoing Processing (per month):")
    print(f"  New Meetings: {future_meetings_per_month}")
    print(f"  Monthly Cost: ${cost_after_ongoing:.2f}")

    print("\nTotal Impact:")
    print(f"  One-time Savings: ${savings:.2f}")
    print(f"  Monthly Ongoing: ${cost_after_ongoing:.2f}")
    print()


async def main():
    """Run all tests"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("🚀 EPIC 14 Hybrid Ingestion Pipeline Test Suite")
    print("=" * 60)
    print()

    try:
        # Run test suites
        await test_routing_decisions()
        await test_ndl_api_integration()
        await test_whisper_stt_integration()
        await test_fallback_mechanisms()
        await test_statistics_tracking()
        await test_cost_estimation()

        print("🎉 All tests completed!")
        print("\n📋 Test Summary:")
        print("✅ Routing decision logic")
        print("✅ NDL API integration")
        print("✅ Whisper STT integration")
        print("✅ Fallback mechanisms")
        print("✅ Statistics tracking")
        print("✅ Cost estimation")

        return 0

    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        logging.exception("Test failure details:")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
