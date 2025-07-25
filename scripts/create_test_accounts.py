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
from datetime import datetime
from typing import Dict, List

import jwt
import requests


# Test user profiles for different testing scenarios
TEST_USERS = {
    "political_expert": {
        "email": "political.expert@test.diet-tracker.jp",
        "name": "政治専門家",
        "role": "expert",
        "permissions": ["view_all", "analyze_data", "export_data"],
        "description": "Political expert for data accuracy verification",
    },
    "accessibility_specialist": {
        "email": "accessibility.specialist@test.diet-tracker.jp", 
        "name": "アクセシビリティ専門家",
        "role": "accessibility_tester",
        "permissions": ["view_all", "test_accessibility"],
        "description": "Accessibility specialist for WCAG 2.1 AA compliance testing",
    },
    "general_user": {
        "email": "general.user@test.diet-tracker.jp",
        "name": "一般ユーザー",
        "role": "user",
        "permissions": ["view_public"],
        "description": "General user for usability testing",
    },
    "legal_compliance": {
        "email": "legal.compliance@test.diet-tracker.jp",
        "name": "法務専門家", 
        "role": "compliance_officer",
        "permissions": ["view_all", "audit_compliance"],
        "description": "Legal compliance specialist for election law and copyright verification",
    },
    "journalist": {
        "email": "journalist@test.diet-tracker.jp",
        "name": "ジャーナリスト",
        "role": "journalist",
        "permissions": ["view_all", "export_data", "api_access"],
        "description": "Journalist for data analysis and export functionality testing",
    },
    "researcher": {
        "email": "researcher@test.diet-tracker.jp",
        "name": "研究者",
        "role": "researcher", 
        "permissions": ["view_all", "api_access", "bulk_export"],
        "description": "Academic researcher for advanced analysis features",
    },
    "admin_tester": {
        "email": "admin.tester@test.diet-tracker.jp",
        "name": "管理者テスター",
        "role": "admin",
        "permissions": ["admin_access", "system_management"],
        "description": "Administrator for system management testing",
    }
}


class TestAccountManager:
    """Manages creation and configuration of test accounts."""
    
    def __init__(self, environment: str, api_base_url: str):
        self.environment = environment
        self.api_base_url = api_base_url
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
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
            'exp': datetime.utcnow().timestamp() + (30 * 24 * 3600),  # 30 days
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
            
            # Make API request to create user
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            response = requests.post(
                f'{self.api_base_url}/admin/users',
                json=user_payload,
                headers=headers,
                timeout=30
            )
            
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
                    'access_token': user_data['token'],
                    'login_instructions': {
                        'web_ui': f"Use email: {user_data['email']} with provided token",
                        'api_access': f"Include 'Authorization: Bearer {user_data['token']}' header",
                        'token_expiry': '30 days from creation'
                    }
                }
                
        # Add testing instructions
        credentials['testing_instructions'] = {
            'phases': [
                {
                    'phase': 1,
                    'name': 'System Foundation Testing',
                    'duration': '2 days',
                    'focus': 'Authentication, API, microservices integration',
                    'participants': ['admin_tester', 'political_expert']
                },
                {
                    'phase': 2, 
                    'name': 'Data Quality Testing',
                    'duration': '3 days',
                    'focus': 'Political data accuracy, CAP classification, neutrality',
                    'participants': ['political_expert', 'journalist', 'legal_compliance']
                },
                {
                    'phase': 3,
                    'name': 'Usability & Accessibility',
                    'duration': '3 days', 
                    'focus': 'PWA, WCAG 2.1 AA, information architecture',
                    'participants': ['accessibility_specialist', 'general_user']
                },
                {
                    'phase': 4,
                    'name': 'Performance Testing',
                    'duration': '2 days',
                    'focus': 'Load testing, Lighthouse scores, Core Web Vitals',
                    'participants': ['admin_tester', 'researcher']
                },
                {
                    'phase': 5,
                    'name': 'Security & Compliance',
                    'duration': '2 days',
                    'focus': 'Authentication, legal requirements, privacy',
                    'participants': ['legal_compliance', 'admin_tester']
                },
                {
                    'phase': 6,
                    'name': 'End-to-End Scenarios',
                    'duration': '2 days',
                    'focus': 'Complete user workflows, use cases',
                    'participants': ['all']
                }
            ],
            'contact': {
                'technical_support': 'dev-team@diet-tracker.jp',
                'test_coordination': 'test-coordinator@diet-tracker.jp',
                'emergency': 'support@diet-tracker.jp'
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Test credentials saved to: {output_file}")


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