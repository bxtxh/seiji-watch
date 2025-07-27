#!/usr/bin/env python3
"""
Disable test accounts after external testing is complete.
This script disables or removes test accounts to ensure security.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

import requests


class TestAccountDisabler:
    """Manages disabling of test accounts after testing."""
    
    def __init__(self, environment: str, api_base_url: str):
        self.environment = environment
        self.api_base_url = api_base_url
        self.logger = self._setup_logging()
        
        # Validate required environment variables
        self.admin_token = os.getenv('ADMIN_API_TOKEN')
        if not self.admin_token:
            raise ValueError("ADMIN_API_TOKEN environment variable is required")
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def disable_user(self, user_email: str) -> dict[str, Any]:
        """Disable a single test user account."""
        try:
            headers = {
                'Authorization': f'Bearer {self.admin_token}',
                'Content-Type': 'application/json'
            }
            
            # Make API request to disable user
            response = requests.post(
                f'{self.api_base_url}/admin/users/disable',
                json={'email': user_email, 'reason': 'test_completed'},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Disabled test user: {user_email}")
                return {
                    'email': user_email,
                    'status': 'disabled',
                    'disabled_at': datetime.utcnow().isoformat()
                }
            else:
                self.logger.error(f"Failed to disable user {user_email}: {response.status_code}")
                return {
                    'email': user_email,
                    'status': 'failed',
                    'error': f'API error: {response.status_code}'
                }
                
        except Exception as e:
            self.logger.error(f"Error disabling user {user_email}: {str(e)}")
            return {
                'email': user_email,
                'status': 'failed',
                'error': str(e)
            }
    
    def disable_all_test_accounts(self, credentials_file: str) -> dict[str, Any]:
        """Disable all test accounts from credentials file."""
        # Load test accounts from credentials file
        try:
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load credentials file: {str(e)}")
            return {'error': f'Failed to load credentials: {str(e)}'}
        
        results = {
            'environment': self.environment,
            'disabled_at': datetime.utcnow().isoformat(),
            'accounts': {},
            'summary': {
                'total': 0,
                'disabled': 0,
                'failed': 0
            }
        }
        
        # Process each test account
        test_accounts = credentials.get('test_accounts', {})
        results['summary']['total'] = len(test_accounts)
        
        for user_id, account_data in test_accounts.items():
            email = account_data.get('email')
            if email:
                result = self.disable_user(email)
                results['accounts'][user_id] = result
                
                if result['status'] == 'disabled':
                    results['summary']['disabled'] += 1
                else:
                    results['summary']['failed'] += 1
        
        return results
    
    def generate_disable_report(self, results: dict[str, Any], output_file: str):
        """Generate report of disabled accounts."""
        report = {
            'disable_report': {
                'generated_at': datetime.utcnow().isoformat(),
                'environment': results['environment'],
                'summary': results['summary'],
                'details': results['accounts']
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Disable report saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Disable test accounts after testing')
    parser.add_argument('--environment', required=True, help='Environment (staging-external-test)')
    parser.add_argument('--api-url', help='API base URL (auto-detected if not provided)')
    parser.add_argument('--credentials', required=True, help='Test credentials JSON file')
    parser.add_argument('--output', default='test-accounts-disabled.json', help='Output report file')
    
    args = parser.parse_args()
    
    # Auto-detect API URL if not provided
    if not args.api_url:
        project_id = os.getenv('GCP_PROJECT_ID')
        if not project_id:
            print("Error: GCP_PROJECT_ID environment variable required if --api-url not provided")
            sys.exit(1)
        args.api_url = f"https://api-gateway-{args.environment}-{project_id}.a.run.app"
    
    # Create test account disabler
    disabler = TestAccountDisabler(args.environment, args.api_url)
    
    try:
        # Disable all test accounts
        results = disabler.disable_all_test_accounts(args.credentials)
        
        # Generate report
        disabler.generate_disable_report(results, args.output)
        
        # Print summary
        print(f"\nTest Account Disable Summary:")
        print(f"Total accounts: {results['summary']['total']}")
        print(f"Successfully disabled: {results['summary']['disabled']}")
        print(f"Failed: {results['summary']['failed']}")
        
        if results['summary']['failed'] > 0:
            print("\nFailed accounts:")
            for user_id, result in results['accounts'].items():
                if result['status'] == 'failed':
                    print(f"  - {user_id}: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()