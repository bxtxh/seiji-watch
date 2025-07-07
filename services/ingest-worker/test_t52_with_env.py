#!/usr/bin/env python3
"""
T52 test with environment variables loaded from .env.local
"""
import os
import sys
from pathlib import Path

# Load environment variables from .env.local
def load_env_file(env_file_path):
    """Load environment variables from .env file"""
    if not os.path.exists(env_file_path):
        print(f"❌ .env.local file not found: {env_file_path}")
        return False
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"\'')
                os.environ[key] = value
    return True

def check_api_keys():
    """Check if all required API keys are set"""
    required_keys = {
        'OPENAI_API_KEY': 'sk-',
        'AIRTABLE_API_KEY': 'pat',
        'AIRTABLE_BASE_ID': 'app',
        'WEAVIATE_URL': 'https://',
        'WEAVIATE_API_KEY': ''
    }
    
    print("=== API Key Configuration Check ===")
    all_set = True
    
    for key, prefix in required_keys.items():
        value = os.getenv(key, '')
        if prefix and not value.startswith(prefix):
            print(f"❌ {key}: Missing or invalid")
            all_set = False
        elif not prefix and len(value) < 10:
            print(f"❌ {key}: Missing or too short")
            all_set = False
        else:
            masked_value = value[:15] + "..." if len(value) > 15 else value
            print(f"✅ {key}: Set ({masked_value})")
    
    return all_set

async def test_external_services():
    """Test external service connectivity"""
    print("\n=== External Service Tests ===")
    
    # Test OpenAI
    try:
        import openai
        openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Simple test - just check if client initializes
        print("✅ OpenAI: Client initialized")
    except Exception as e:
        print(f"❌ OpenAI: {e}")
    
    # Test Airtable (simple check)
    airtable_key = os.getenv('AIRTABLE_API_KEY')
    airtable_base = os.getenv('AIRTABLE_BASE_ID')
    if airtable_key and airtable_base:
        print("✅ Airtable: Configuration present")
    else:
        print("❌ Airtable: Missing configuration")
    
    # Test Weaviate (simple check)
    weaviate_url = os.getenv('WEAVIATE_URL')
    weaviate_key = os.getenv('WEAVIATE_API_KEY')
    if weaviate_url and weaviate_key:
        print("✅ Weaviate: Configuration present")
    else:
        print("❌ Weaviate: Missing configuration")

async def run_t52_limited_test():
    """Run T52 limited test with real APIs"""
    print("\n=== T52 Limited Test Execution ===")
    
    # Add src to path for imports
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    
    try:
        # Test basic imports first
        from scraper.diet_scraper import DietScraper
        print("✅ DietScraper import successful")
        
        # Initialize with conservative settings
        scraper = DietScraper(enable_resilience=True)
        print("✅ DietScraper initialized")
        
        # Test basic functionality
        print("🔍 Testing basic bill collection...")
        bills = scraper.fetch_current_bills()
        print(f"✅ Successfully collected {len(bills)} bills")
        
        if bills:
            print("\n📋 Sample bills (first 3):")
            for i, bill in enumerate(bills[:3], 1):
                print(f"  {i}. {bill.bill_id}: {bill.title[:50]}...")
        
        # Test with limited scope
        limited_bills = bills[:5]  # Very limited for testing
        print(f"\n🎯 T52 Limited scope: {len(limited_bills)} bills")
        
        return True, len(limited_bills)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Check if dependencies are installed")
        return False, 0
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

async def main():
    """Main test function"""
    print("🧪 T52 Real API Test Suite")
    print(f"📅 Test Date: {os.popen('date').read().strip()}")
    
    # Load environment variables
    env_file = Path(__file__).parent / ".env.local"
    if not load_env_file(env_file):
        print("❌ Failed to load .env.local file")
        return 1
    
    print("✅ Environment file loaded")
    
    # Check API keys
    if not check_api_keys():
        print("\n❌ Missing required API keys")
        print("   Please check your .env.local file")
        return 1
    
    # Test external services
    await test_external_services()
    
    # Run T52 test
    success, count = await run_t52_limited_test()
    
    print(f"\n{'='*60}")
    print("🏁 Test Summary")
    print(f"{'='*60}")
    
    if success:
        print("✅ T52 API integration test: PASSED")
        print(f"📊 Data collected: {count} items")
        print("\n🚀 Ready for full T52 execution!")
        print("   Use POST /t52/scrape with dry_run=false")
    else:
        print("❌ T52 API integration test: FAILED")
        print("   Check error messages above")
    
    return 0 if success else 1

if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)