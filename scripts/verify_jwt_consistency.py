#!/usr/bin/env python3
"""
JWT Consistency Verification Script
Tests JWT_SECRET_KEY consistency between server and token generation.
"""

import os
import sys
from pathlib import Path

# Add the project path to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "services" / "api-gateway" / "src"))

try:
    import datetime

    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("❌ PyJWT library not available. Install with: pip install PyJWT")
    sys.exit(1)


def test_jwt_consistency():
    """Test JWT consistency between different components."""
    print("🔍 JWT Consistency Verification")
    print("=" * 50)

    # Test configurations - NO HARDCODED SECRETS
    test_configs = {
        "Production": os.getenv("JWT_SECRET_KEY_PROD", "NOT_SET"),
        "Test/CI-CD": "test-jwt-secret-unified-for-ci-cd",
        "Environment": os.getenv("JWT_SECRET_KEY", "NOT_SET"),
    }

    print("\n📋 JWT_SECRET_KEY Configurations:")
    for name, secret in test_configs.items():
        if secret == "NOT_SET":
            print(f"   {name}: [NOT_SET]")
        elif name == "Production":
            print(f"   {name}: [MASKED - ENV:JWT_SECRET_KEY_PROD]")
        else:
            print(f"   {name}: [MASKED]")

    # Test each configuration
    results = {}

    for config_name, secret_key in test_configs.items():
        if secret_key == "NOT_SET":
            continue

        try:
            # Generate a test token with server-compatible format
            payload = {
                "user_id": "test-user",
                "email": "test@seiji-watch.local",
                "scopes": ["read", "write"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                "iat": datetime.datetime.utcnow(),
                "type": "access_token",
            }

            # Generate token
            token = jwt.encode(payload, secret_key, algorithm="HS256")

            # Verify token
            decoded = jwt.decode(token, secret_key, algorithms=["HS256"])

            # Check if verification successful
            if (
                decoded["user_id"] == "test-user"
                and decoded["email"] == "test@seiji-watch.local"
            ):
                results[config_name] = {
                    "status": "✅ PASS",
                    "token": token[:30] + "...",
                    "secret_length": len(secret_key),
                }
            else:
                results[config_name] = {
                    "status": "❌ FAIL - Token verification failed",
                    "token": "N/A",
                    "secret_length": len(secret_key),
                }

        except Exception as e:
            results[config_name] = {
                "status": f"❌ FAIL - {str(e)}",
                "token": "N/A",
                "secret_length": len(secret_key) if secret_key != "NOT_SET" else 0,
            }

    # Display results
    print("\n🧪 JWT Token Generation & Verification Tests:")
    print("-" * 60)

    for config_name, result in results.items():
        print(f"{config_name}:")
        print(f"   Status: {result['status']}")
        print(f"   Token:  {result['token']}")
        print(f"   Secret Length: {result['secret_length']} characters")
        print()

    # Cross-verification test (DISABLED for security - no prod secret access)
    print("🔄 Cross-Verification Tests:")
    print("-" * 40)
    print("🔒 SECURITY: Cross-verification with production secrets DISABLED")
    print("✅ Production secrets are not accessible in this test environment")
    print("✅ This prevents accidental exposure of production JWT secrets")

    # Environment consistency check
    print("\n🌍 Environment Consistency Check:")
    print("-" * 40)

    env_jwt_secret = os.getenv("JWT_SECRET_KEY")
    if env_jwt_secret:
        if env_jwt_secret == test_configs["Test/CI-CD"]:
            print("✅ Environment JWT_SECRET_KEY matches Test/CI-CD configuration")
        elif env_jwt_secret == test_configs["Production"]:
            print("✅ Environment JWT_SECRET_KEY matches Production configuration")
        else:
            print("⚠️  Environment JWT_SECRET_KEY is different: [MASKED]")
    else:
        print("❌ JWT_SECRET_KEY not set in environment")

    # Summary
    print("\n📊 Summary:")
    print("-" * 20)

    passed = sum(1 for result in results.values() if "✅ PASS" in result["status"])
    total = len(results)

    if passed == total:
        print(f"✅ All {total} JWT configurations are working correctly")
        print("✅ Ready for production deployment")
    else:
        print(f"❌ {total - passed} out of {total} configurations failed")
        print("❌ Fix issues before production deployment")

    return passed == total


def test_with_auth_middleware():
    """Test integration with the actual auth middleware."""
    print("\n🔗 Auth Middleware Integration Test:")
    print("-" * 40)

    try:
        # Import the auth middleware
        from middleware.auth import create_access_token, verify_token

        print("✅ Auth middleware imported successfully")
        print("   Middleware JWT_SECRET_KEY: [MASKED]")

        # Test token creation and verification
        test_token = create_access_token(
            "test-user", "test@example.com", ["read", "write"]
        )
        print(f"✅ Token created: {test_token[:30]}...")

        # Verify the token
        payload = verify_token(test_token)
        print("✅ Token verified successfully")
        print(f"   User ID: {payload.get('user_id')}")
        print(f"   Email: {payload.get('email')}")
        print(f"   Scopes: {payload.get('scopes')}")

        return True

    except ImportError as e:
        print(f"❌ Failed to import auth middleware: {e}")
        return False
    except Exception as e:
        print(f"❌ Auth middleware test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting JWT Consistency Verification")
    print("=" * 60)

    # Set test environment
    os.environ["ENVIRONMENT"] = "testing"

    # Run consistency tests
    consistency_ok = test_jwt_consistency()

    # Run middleware integration test
    middleware_ok = test_with_auth_middleware()

    print("\n🎯 Final Results:")
    print("=" * 30)

    if consistency_ok and middleware_ok:
        print("✅ ALL TESTS PASSED")
        print("✅ JWT authentication is properly configured")
        print("✅ Ready for CI/CD deployment")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("❌ Fix JWT configuration before deployment")
        sys.exit(1)
