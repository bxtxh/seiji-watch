#!/usr/bin/env python3
"""
API Bearer Token Generator
Uses the generated JWT_SECRET_KEY to create API bearer tokens for CI/CD.
"""

import os

try:
    import jwt
    import datetime
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️  PyJWT library not available. Install with: pip install PyJWT")

# 本番用: GitHub Secretsに登録するJWT_SECRET_KEY
PRODUCTION_SECRET_KEY = "JuuqsKGh63LuvjXGoVgOgofPpn-mnDqPooTw8VT3zvmhBTrfWcpu815EDZDw9hBp2qMULqTJiu4o_-Gqu4Z73w"

# テスト用: CI/CDで使用する統一されたJWT_SECRET_KEY  
TEST_SECRET_KEY = "test-jwt-secret-unified-for-ci-cd"

# 使用する秘密鍵を選択（環境変数から取得、フォールバックはテスト用）
SECRET_KEY = os.getenv('JWT_SECRET_KEY', TEST_SECRET_KEY)

def generate_ci_bearer_token(secret_key: str, hours: int = 24) -> str:
    """Generate a bearer token for CI/CD use."""
    if not JWT_AVAILABLE:
        raise ImportError("PyJWT library is required. Install with: pip install PyJWT")
    
    # サーバー側が期待するペイロード形式（auth.pyのcreate_access_token()と同じ）
    payload = {
        "user_id": "ci-bot",  # 必須: サーバーが期待するuser_id
        "email": "ci-bot@seiji-watch.local",  # 必須: サーバーが期待するemail
        "scopes": ["read", "write", "admin"],  # 必須: 権限スコープ配列
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=hours),  # 必須: 有効期限
        "iat": datetime.datetime.utcnow(),  # 必須: 発行時刻
        "type": "access_token"  # 必須: トークンタイプ（固定値）
    }

    # JWTトークンを生成
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

def generate_multiple_tokens(secret_key: str) -> dict:
    """Generate tokens with different expiration times."""
    tokens = {}
    
    # 1時間有効なトークン
    tokens['1hour'] = generate_ci_bearer_token(secret_key, hours=1)
    
    # 24時間有効なトークン
    tokens['24hours'] = generate_ci_bearer_token(secret_key, hours=24)
    
    # 7日間有効なトークン
    tokens['7days'] = generate_ci_bearer_token(secret_key, hours=24*7)
    
    return tokens

def decode_and_verify_token(token: str, secret_key: str) -> dict:
    """Decode and verify a JWT token for debugging."""
    try:
        # Decode without verification first (for debugging)
        unverified = jwt.decode(token, options={"verify_signature": False})
        print(f"🔍 Token payload (unverified): {unverified}")
        
        # Now verify with secret
        verified = jwt.decode(token, secret_key, algorithms=["HS256"])
        print(f"✅ Token verification successful")
        
        # Check server requirements
        required_fields = ['user_id', 'email', 'scopes', 'exp', 'iat', 'type']
        missing_fields = [field for field in required_fields if field not in verified]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
        else:
            print(f"✅ All required fields present")
            
        # Check token type
        if verified.get('type') != 'access_token':
            print(f"❌ Invalid token type: {verified.get('type')}")
        else:
            print(f"✅ Valid token type: access_token")
            
        # Check expiration
        exp = verified.get('exp')
        if exp:
            exp_time = datetime.datetime.fromtimestamp(exp)
            now = datetime.datetime.utcnow()
            if exp_time > now:
                time_left = exp_time - now
                print(f"✅ Token valid for: {time_left}")
            else:
                print(f"❌ Token expired {now - exp_time} ago")
        
        return verified
        
    except jwt.ExpiredSignatureError:
        print(f"❌ Token has expired")
        return None
    except jwt.InvalidSignatureError:
        print(f"❌ Invalid signature - JWT_SECRET_KEY mismatch")
        return None
    except jwt.JWTError as e:
        print(f"❌ JWT Error: {e}")
        return None

if __name__ == "__main__":
    print("🎫 API Bearer Token Generator")
    print("=" * 50)
    
    if not JWT_AVAILABLE:
        print("❌ PyJWT library not available.")
        print("   Install with: pip install PyJWT")
        print("   Or run: poetry add PyJWT")
        exit(1)
    
    print(f"🔑 Using SECRET_KEY: {SECRET_KEY[:20]}...")
    
    try:
        # Generate tokens
        tokens = generate_multiple_tokens(SECRET_KEY)
        
        print(f"\n📋 Generated API Bearer Tokens (Server-Compatible Format):")
        print(f"1. Short-term (1 hour):  {tokens['1hour']}")
        print(f"2. Medium-term (24 hours): {tokens['24hours']}")
        print(f"3. Long-term (7 days):   {tokens['7days']}")
        
        print(f"\n✅ Recommended for GitHub Secrets:")
        print(f"   Name: API_BEARER_TOKEN")
        print(f"   Value: {tokens['24hours']}")
        
        # Verify the generated token
        print(f"\n🔍 Token Verification:")
        print("-" * 40)
        decode_and_verify_token(tokens['24hours'], SECRET_KEY)
        
        print(f"\n🧪 Test your token:")
        print(f"   curl -H \"Authorization: Bearer {tokens['24hours'][:50]}...\" \\")
        print(f"        http://localhost:8000/api/issues/")
        
        print(f"\n📝 Server Expected Payload Structure:")
        print(f"   user_id: 'ci-bot'")
        print(f"   email: 'ci-bot@seiji-watch.local'")
        print(f"   scopes: ['read', 'write', 'admin']")
        print(f"   type: 'access_token'")
        print(f"   exp: {datetime.datetime.utcnow() + datetime.timedelta(hours=24)}")
        print(f"   iat: {datetime.datetime.utcnow()}")
        
        print(f"\n📝 How to add to GitHub Secrets:")
        print(f"   1. Go to: https://github.com/YOUR_REPO/settings/secrets/actions")
        print(f"   2. Click 'New repository secret'")
        print(f"   3. Name: API_BEARER_TOKEN")
        print(f"   4. Value: {tokens['24hours']}")
        print(f"   5. Click 'Add secret'")
        
    except Exception as e:
        print(f"❌ Error generating tokens: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n🔒 Security Reminders:")
    print(f"   - These tokens use server-compatible payload format")
    print(f"   - Tokens expire automatically")
    print(f"   - Use the 24-hour token for CI/CD")
    print(f"   - Generate new tokens when secrets are rotated")
    print(f"   - Never expose tokens in logs or code")