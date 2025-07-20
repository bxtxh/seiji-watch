#!/usr/bin/env python3
"""
API Bearer Token Generator
Uses the generated JWT_SECRET_KEY to create API bearer tokens for CI/CD.
"""

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
    
    # トークンに入れる情報（ペイロード）
    payload = {
        "sub": "ci-bot",  # 誰のトークンか（任意の文字列でOK）
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=hours),  # 有効期限
        "iat": datetime.datetime.utcnow(),  # 発行時刻
        "role": "ci",  # 役割（任意）
        "scopes": ["read", "write", "admin"],  # 権限スコープ
        "type": "access_token"  # トークンタイプ
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
        
        print(f"\n📋 Generated API Bearer Tokens:")
        print(f"1. Short-term (1 hour):  {tokens['1hour']}")
        print(f"2. Medium-term (24 hours): {tokens['24hours']}")
        print(f"3. Long-term (7 days):   {tokens['7days']}")
        
        print(f"\n✅ Recommended for GitHub Secrets:")
        print(f"   Name: API_BEARER_TOKEN")
        print(f"   Value: {tokens['24hours']}")
        
        print(f"\n🧪 Test your token:")
        print(f"   curl -H \"Authorization: Bearer {tokens['1hour'][:50]}...\" \\")
        print(f"        http://localhost:8000/api/issues/")
        
        print(f"\n📝 How to add to GitHub Secrets:")
        print(f"   1. Go to: https://github.com/YOUR_REPO/settings/secrets/actions")
        print(f"   2. Click 'New repository secret'")
        print(f"   3. Name: API_BEARER_TOKEN")
        print(f"   4. Value: {tokens['24hours']}")
        print(f"   5. Click 'Add secret'")
        
    except Exception as e:
        print(f"❌ Error generating tokens: {e}")

    print(f"\n🔒 Security Reminders:")
    print(f"   - These tokens expire automatically")
    print(f"   - Use the 24-hour token for CI/CD")
    print(f"   - Generate new tokens when secrets are rotated")
    print(f"   - Never expose tokens in logs or code")