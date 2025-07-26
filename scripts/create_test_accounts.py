#!/usr/bin/env python3
"""
Create test accounts for external user testing.
This script creates various user roles and test data for comprehensive testing.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List

import jwt
import requests


# Test user profiles for external user testing (starting with 1 reviewer)
# Email addresses should be provided via environment variables or config file
TEST_USERS = {
    "external_reviewer_1": {
        "email": os.getenv("EXTERNAL_REVIEWER_1_EMAIL", "reviewer1@example.com"),
        "name": "外部レビュワー１",
        "role": "external_reviewer", 
        "permissions": ["view_all", "browser_testing"],
        "description": "External reviewer for browser-based usability testing",
    }
    # Note: 残り2名のアカウントは後日追加予定
}


class TestAccountManager:
    """Manages creation and configuration of test accounts."""
    
    def __init__(self, environment: str, api_base_url: str):
        self.environment = environment
        self.api_base_url = api_base_url
        
        # Validate required environment variables
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET_KEY environment variable is required")
            
        # Validate other required environment variables
        required_vars = ['GCP_PROJECT_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
        
    def create_jwt_token(self, user_data: Dict) -> str:
        """Create JWT token for test user."""
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET_KEY environment variable not set")
            
        payload = {
            'sub': user_data['email'],
            'name': user_data['name'],
            'role': user_data['role'],
            'permissions': user_data['permissions'],
            'iat': datetime.utcnow().timestamp(),
            'exp': datetime.utcnow().timestamp() + (7 * 24 * 3600),  # 7 days for testing
            'iss': f'diet-tracker-{self.environment}',
            'aud': 'external-testing'
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        
    def create_test_user(self, user_id: str, user_data: Dict) -> Dict:
        """Create a single test user account."""
        try:
            # Generate JWT token
            token = self.create_jwt_token(user_data)
            
            # Create user account via API
            user_payload = {
                'email': user_data['email'],
                'name': user_data['name'],
                'role': user_data['role'],
                'permissions': user_data['permissions'],
                'environment': self.environment,
                'test_account': True,
                'created_for': 'external_user_testing'
            }
            
            # Make API request with retry logic
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            
            max_retries = 3
            retry_delay = 2  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f'{self.api_base_url}/admin/users',
                        json=user_payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    # If successful or client error (4xx), don't retry
                    if response.status_code < 500:
                        break
                        
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Request timeout for {user_id}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise
                except requests.exceptions.ConnectionError as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Connection error for {user_id}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise
            
            if response.status_code == 201:
                self.logger.info(f"Created test user: {user_id} ({user_data['email']})")
                return {
                    'user_id': user_id,
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'role': user_data['role'],
                    'token': token,
                    'api_endpoint': self.api_base_url,
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'created'
                }
            else:
                self.logger.error(f"Failed to create user {user_id}: {response.status_code} - {response.text}")
                return {
                    'user_id': user_id,
                    'error': f'API error: {response.status_code}',
                    'status': 'failed'
                }
                
        except Exception as e:
            self.logger.error(f"Error creating user {user_id}: {str(e)}")
            return {
                'user_id': user_id,
                'error': str(e),
                'status': 'failed'
            }
            
    def create_all_test_users(self) -> Dict:
        """Create all test user accounts."""
        results = {
            'environment': self.environment,
            'api_base_url': self.api_base_url,
            'created_at': datetime.utcnow().isoformat(),
            'users': {},
            'summary': {
                'total': len(TEST_USERS),
                'created': 0,
                'failed': 0
            }
        }
        
        for user_id, user_data in TEST_USERS.items():
            result = self.create_test_user(user_id, user_data)
            results['users'][user_id] = result
            
            if result['status'] == 'created':
                results['summary']['created'] += 1
            else:
                results['summary']['failed'] += 1
                
        self.logger.info(f"Test account creation complete: {results['summary']['created']}/{results['summary']['total']} successful")
        return results
        
    def generate_test_credentials_file(self, results: Dict, output_file: str):
        """Generate credentials file for external testers."""
        credentials = {
            'testing_environment': {
                'name': 'Diet Issue Tracker - External User Testing',
                'environment': self.environment,
                'frontend_url': self.api_base_url.replace('api-gateway', 'web-frontend'),
                'api_base_url': self.api_base_url,
                'created_at': results['created_at']
            },
            'test_accounts': {}
        }
        
        for user_id, user_data in results['users'].items():
            if user_data['status'] == 'created':
                credentials['test_accounts'][user_id] = {
                    'description': TEST_USERS[user_id]['description'],
                    'email': user_data['email'], 
                    'name': user_data['name'],
                    'role': user_data['role'],
                    'access_token': '[REDACTED - Contact admin for token]',
                    'login_instructions': {
                        'web_ui': f"Use email: {user_data['email']} with secure token",
                        'api_access': "Include 'Authorization: Bearer <token>' header",
                        'token_expiry': '7 days from creation',
                        'note': 'Actual tokens are stored securely. Contact admin for access.'
                    }
                }
                
                # Store the actual token in a secure location (e.g., environment variable or secret manager)
                # This is just a placeholder - implement secure storage based on your infrastructure
                secure_token_key = f"TEST_TOKEN_{user_id.upper()}"
                self.logger.info(f"Secure token should be stored as: {secure_token_key}={user_data['token'][:10]}...")
                
        # Add testing instructions (pilot test with 1 reviewer)
        credentials['testing_instructions'] = {
            'pilot_test_note': '1名での先行テスト実施中。残り2名は後日参加予定。',
            'phases': [
                {
                    'phase': 1,
                    'name': '基本機能検証',
                    'duration': '1日',
                    'focus': 'ログイン・ナビゲーション・基本操作',
                    'participants': ['external_reviewer_1']
                },
                {
                    'phase': 2, 
                    'name': '実用シナリオ検証',
                    'duration': '2日',
                    'focus': '法案検索・詳細閲覧・データ理解度',
                    'participants': ['external_reviewer_1']
                },
                {
                    'phase': 3,
                    'name': 'ユーザビリティ評価',
                    'duration': '1日', 
                    'focus': '使いやすさ・情報の見つけやすさ',
                    'participants': ['external_reviewer_1']
                },
                {
                    'phase': 4,
                    'name': '総合評価・初期フィードバック',
                    'duration': '1日',
                    'focus': '全体的な使い勝手・改善提案・初期評価',
                    'participants': ['external_reviewer_1']
                }
            ],
            'contact': {
                'technical_support': 'dev-team@diet-tracker.jp',
                'test_coordination': 'test-coordinator@diet-tracker.jp',
                'emergency': 'support@diet-tracker.jp'
            }
        }
        
        # Write credentials file (without sensitive tokens)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Test credentials saved to: {output_file}")
        
        # Store tokens directly in Secret Manager - never write to filesystem
        try:
            from google.cloud import secretmanager
            
            # Initialize Secret Manager client
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv('GCP_PROJECT_ID')
            
            if not project_id:
                raise ValueError("GCP_PROJECT_ID environment variable required for Secret Manager")
            
            # Prepare secure token data
            secure_data = {
                'created_at': datetime.utcnow().isoformat(),
                'environment': self.environment,
                'tokens': {}
            }
            
            for user_id, user_data in results['users'].items():
                if user_data['status'] == 'created':
                    secure_data['tokens'][user_id] = {
                        'email': user_data['email'],
                        'token': user_data['token'],
                        'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
                    }
            
            # Create or update secret
            secret_id = f"external-test-tokens-{self.environment}"
            parent = f"projects/{project_id}"
            
            try:
                # Try to create the secret
                secret = client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {
                            "replication": {
                                "automatic": {}
                            }
                        }
                    }
                )
                self.logger.info(f"Created new secret: {secret_id}")
            except Exception:
                # Secret already exists, that's fine
                self.logger.info(f"Using existing secret: {secret_id}")
            
            # Add new secret version
            secret_name = f"{parent}/secrets/{secret_id}"
            secret_payload = json.dumps(secure_data, indent=2).encode('UTF-8')
            
            version = client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {
                        "data": secret_payload
                    }
                }
            )
            
            self.logger.info(f"Tokens securely stored in Secret Manager: {version.name}")
            
            print(f"\n✅ Tokens securely stored in Google Secret Manager")
            print(f"Secret ID: {secret_id}")
            print(f"Version: {version.name.split('/')[-1]}")
            print(f"\nTo retrieve tokens:")
            print(f"gcloud secrets versions access latest --secret={secret_id}")
            
        except ImportError:
            self.logger.error("google-cloud-secret-manager not installed. Tokens NOT saved.")
            print("\n❌ ERROR: Cannot store tokens securely without google-cloud-secret-manager")
            print("Install with: pip install google-cloud-secret-manager")
            raise
        except Exception as e:
            self.logger.error(f"Failed to store tokens in Secret Manager: {str(e)}")
            print(f"\n❌ ERROR: Failed to store tokens securely: {str(e)}")
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Create test accounts for external user testing')
    parser.add_argument('--environment', required=True, help='Environment (staging-external-test)')
    parser.add_argument('--api-url', help='API base URL (auto-detected if not provided)')
    parser.add_argument('--output', default='external-test-credentials.json', help='Output credentials file')
    parser.add_argument('--accounts', help='Existing accounts JSON file to update')
    
    args = parser.parse_args()
    
    # Auto-detect API URL if not provided
    if not args.api_url:
        project_id = os.getenv('GCP_PROJECT_ID')
        if not project_id:
            print("Error: GCP_PROJECT_ID environment variable required if --api-url not provided")
            sys.exit(1)
        args.api_url = f"https://api-gateway-{args.environment}-{project_id}.a.run.app"
    
    # Validate GCP_PROJECT_ID matches terraform configuration if provided
    expected_project_id = os.getenv('TERRAFORM_PROJECT_ID', os.getenv('GCP_PROJECT_ID'))
    actual_project_id = os.getenv('GCP_PROJECT_ID')
    if expected_project_id and actual_project_id and expected_project_id != actual_project_id:
        print(f"Warning: GCP_PROJECT_ID mismatch - Expected: {expected_project_id}, Actual: {actual_project_id}")
        print("This may cause deployment issues. Please verify your configuration.")
    
    # Create test account manager
    manager = TestAccountManager(args.environment, args.api_url)
    
    try:
        # Create all test users
        results = manager.create_all_test_users()
        
        # Generate credentials file
        manager.generate_test_credentials_file(results, args.output)
        
        # Print summary
        print(f"\n✅ Test Account Creation Summary:")
        print(f"   Environment: {args.environment}")
        print(f"   API URL: {args.api_url}")
        print(f"   Created: {results['summary']['created']}/{results['summary']['total']} accounts")
        print(f"   Credentials: {args.output}")
        
        if results['summary']['failed'] > 0:
            print(f"\n⚠️  {results['summary']['failed']} account(s) failed to create")
            for user_id, user_data in results['users'].items():
                if user_data['status'] == 'failed':
                    print(f"   - {user_id}: {user_data.get('error', 'Unknown error')}")
        
        print(f"\n📋 Next Steps:")
        print(f"   1. Share {args.output} with external testing participants")
        print(f"   2. Verify all accounts can access the system")
        print(f"   3. Begin Phase 1 testing (System Foundation)")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()