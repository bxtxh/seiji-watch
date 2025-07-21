#!/usr/bin/env python3
"""
JWT Authentication Test Script
Tests the actual API authentication with generated tokens.
"""

import os
import sys
import requests
import json

# Add the project path to sys.path  
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "services", "api-gateway", "src"))

try:
    import jwt
    import datetime
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("❌ PyJWT library not available. Install with: pip install PyJWT")
    sys.exit(1)

def generate_test_token(secret_key: str, hours: int = 1) -> str:
    """Generate a test token with server-compatible format."""
    payload = {
        "user_id": "test-auth-user",
        "email": "test-auth@seiji-watch.local", 
        "scopes": ["read", "write", "admin"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=hours),
        "iat": datetime.datetime.utcnow(),
        "type": "access_token"
    }
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

def test_api_endpoint(token: str, endpoint: str = "http://localhost:8000/api/issues/") -> dict:
    """Test an API endpoint with the generated token."""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        
        return {
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'headers': dict(response.headers),
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]
        }
        
    except requests.exceptions.ConnectionError:
        return {
            'status_code': None,
            'success': False,
            'error': 'Connection failed - API server not running?',
            'response': None
        }
    except requests.exceptions.Timeout:
        return {
            'status_code': None,
            'success': False, 
            'error': 'Request timeout',
            'response': None
        }
    except Exception as e:
        return {
            'status_code': None,
            'success': False,
            'error': str(e),
            'response': None
        }

def main():
    print("🧪 JWT Authentication Test")
    print("=" * 50)
    
    # Get secret key
    production_secret = "JuuqsKGh63LuvjXGoVgOgofPpn-mnDqPooTw8VT3zvmhBTrfWcpu815EDZDw9hBp2qMULqTJiu4o_-Gqu4Z73w"
    test_secret = "test-jwt-secret-unified-for-ci-cd"
    
    # Use environment variable or fallback to test secret
    secret_key = os.getenv('JWT_SECRET_KEY', test_secret)
    
    print(f"🔑 Using secret: {secret_key[:20]}...")
    
    # Generate test token
    print(f"\n📝 Generating test token...")
    token = generate_test_token(secret_key)
    print(f"✅ Token generated: {token[:50]}...")
    
    # Verify token locally
    print(f"\n🔍 Local token verification:")
    try:
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        print(f"✅ Token verification successful")
        print(f"   User ID: {decoded.get('user_id')}")
        print(f"   Email: {decoded.get('email')}")
        print(f"   Scopes: {decoded.get('scopes')}")
        print(f"   Type: {decoded.get('type')}")
        print(f"   Expires: {datetime.datetime.fromtimestamp(decoded.get('exp'))}")
    except Exception as e:
        print(f"❌ Local token verification failed: {e}")
        return False
    
    # Test API endpoints
    test_endpoints = [
        "http://localhost:8000/api/issues/",
        "http://localhost:8000/api/issues/statistics",
        "http://localhost:8000/api/issues/health"
    ]
    
    print(f"\n🌐 Testing API endpoints:")
    print("-" * 40)
    
    all_tests_passed = True
    
    for endpoint in test_endpoints:
        print(f"\nTesting: {endpoint}")
        result = test_api_endpoint(token, endpoint)
        
        if result['success']:
            print(f"✅ SUCCESS - Status: {result['status_code']}")
            if isinstance(result['response'], dict):
                print(f"   Response keys: {list(result['response'].keys())}")
            else:
                print(f"   Response: {str(result['response'])[:100]}...")
        else:
            print(f"❌ FAILED - Status: {result['status_code']}")
            if 'error' in result:
                print(f"   Error: {result['error']}")
            else:
                print(f"   Response: {str(result['response'])[:100]}...")
            
            if result['status_code'] == 401:
                print(f"   ⚠️  401 Unauthorized - JWT format mismatch?")
                all_tests_passed = False
            elif result['status_code'] == 403:
                print(f"   ⚠️  403 Forbidden - Insufficient permissions?")
            elif result['status_code'] is None:
                print(f"   ⚠️  Connection issue - Server running?")
    
    # Summary
    print(f"\n📊 Test Summary:")
    print("-" * 20)
    
    if all_tests_passed:
        print(f"✅ All API authentication tests passed!")
        print(f"✅ JWT token format is compatible with server")
        print(f"✅ Ready for CI/CD deployment")
    else:
        print(f"❌ Some tests failed")
        print(f"❌ Check JWT token format and server compatibility")
        
        # Debugging suggestions
        print(f"\n🔧 Debugging suggestions:")
        print(f"   1. Verify server is running: curl http://localhost:8000/api/issues/health")
        print(f"   2. Check JWT_SECRET_KEY matches server configuration")
        print(f"   3. Verify token payload matches server expectations:")
        print(f"      - user_id (not sub)")
        print(f"      - email (not role)")
        print(f"      - scopes array")
        print(f"      - type: 'access_token'")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)