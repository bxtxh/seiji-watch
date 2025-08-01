#!/usr/bin/env python3
"""Test API connection and verify endpoints are working."""

import json
import sys
from typing import Any, Dict

import requests


def test_api_connection(base_url: str = "http://localhost:8080") -> None:
    """Test API Gateway connection and key endpoints."""

    print(f"Testing API connection to: {base_url}")
    print("=" * 50)

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print(f"   Service: {health_data.get('service')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API Gateway")
        print("   Make sure the API Gateway is running:")
        print("   cd services/api-gateway && python scripts/start_api.py")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Health check error: {e}")

    print()

    # Test bills search endpoint
    try:
        search_payload = {"query": "", "max_records": 10}
        response = requests.post(
            f"{base_url}/api/bills/search",
            json=search_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Bills search endpoint working")
            print(f"   Success: {data.get('success')}")
            print(f"   Results found: {data.get('total_found', 0)}")
            if data.get("results"):
                print(
                    f"   First result: {data['results'][0].get('fields', {}).get('Name', 'N/A')[:50]}..."
                )
        else:
            print(f"❌ Bills search failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Bills search error: {e}")

    print()

    # Test categories endpoint
    try:
        response = requests.get(f"{base_url}/api/issues/categories", timeout=10)
        if response.status_code == 200:
            categories = response.json()
            print("✅ Categories endpoint working")
            print(
                f"   Categories found: {len(categories) if isinstance(categories, list) else 'N/A'}"
            )
        else:
            print(f"❌ Categories fetch failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Categories error: {e}")

    print()

    # Test CORS headers
    try:
        # Simulate a browser request
        response = requests.options(
            f"{base_url}/api/bills/search",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=5,
        )

        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get(
                "Access-Control-Allow-Origin"
            ),
            "Access-Control-Allow-Methods": response.headers.get(
                "Access-Control-Allow-Methods"
            ),
            "Access-Control-Allow-Headers": response.headers.get(
                "Access-Control-Allow-Headers"
            ),
        }

        if cors_headers["Access-Control-Allow-Origin"]:
            print("✅ CORS headers configured")
            for header, value in cors_headers.items():
                if value:
                    print(f"   {header}: {value}")
        else:
            print("❌ CORS headers not properly configured")
    except Exception as e:
        print(f"❌ CORS test error: {e}")

    print()
    print("=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test API Gateway connection")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="API Gateway base URL (default: http://localhost:8080)",
    )

    args = parser.parse_args()
    test_api_connection(args.url)
