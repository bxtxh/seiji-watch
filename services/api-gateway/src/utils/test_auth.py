"""
Test Authentication Utilities
Provides JWT token generation for CI/CD and testing environments.
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import List

def generate_test_token(
    user_id: str = "test_user", 
    email: str = "test@example.com", 
    scopes: List[str] = None,
    secret_key: str = None
) -> str:
    """Generate a test JWT token for CI/CD and testing."""
    
    if scopes is None:
        scopes = ['read', 'write', 'admin']  # Full permissions for testing
    
    if secret_key is None:
        secret_key = os.getenv('JWT_SECRET_KEY', 'test-jwt-secret-unified-for-ci-cd')
    
    payload = {
        'user_id': user_id,
        'email': email,
        'scopes': scopes,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow(),
        'type': 'access_token'
    }
    
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token

def get_auth_headers(token: str = None) -> dict:
    """Get authorization headers for API requests."""
    if token is None:
        token = generate_test_token()
    
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

def get_api_bearer_token() -> str:
    """Get API bearer token from environment or generate test token."""
    # First try to get from environment (for CI/CD)
    api_token = os.getenv('API_BEARER_TOKEN')
    if api_token:
        return api_token
    
    # Fallback to JWT generation for testing
    return generate_test_token()

def make_authenticated_request(url: str, method: str = 'GET', **kwargs) -> dict:
    """Make an authenticated API request with proper error handling."""
    import requests
    
    token = get_api_bearer_token()
    headers = get_auth_headers(token)
    
    # Merge with any existing headers
    if 'headers' in kwargs:
        headers.update(kwargs['headers'])
    kwargs['headers'] = headers
    
    try:
        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 401:
            raise RuntimeError(f"Authentication failed: {response.json()}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")

if __name__ == "__main__":
    # Generate a test token and print it
    token = generate_test_token()
    print(f"Test JWT Token: {token}")
    print(f"Auth Headers: {get_auth_headers(token)}")
    
    # Test API bearer token
    api_token = get_api_bearer_token()
    print(f"API Bearer Token: {api_token[:20]}..." if len(api_token) > 20 else api_token)