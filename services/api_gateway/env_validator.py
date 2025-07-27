"""
Environment variable validation for API Gateway
"""

import os
import sys
from typing import Dict, List, Optional, Tuple


class EnvironmentValidator:
    """Validates required environment variables at startup"""
    
    REQUIRED_VARS = {
        "AIRTABLE_PAT": "Airtable Personal Access Token",
        "AIRTABLE_BASE_ID": "Airtable Base ID",
    }
    
    OPTIONAL_VARS = {
        "ENVIRONMENT": ("staging", "Environment name (development, staging, production)"),
        "ALLOWED_CORS_ORIGINS": ("", "Comma-separated list of allowed CORS origins"),
        "JWT_SECRET_KEY": ("", "JWT signing secret key"),
        "DEBUG_API_TOKEN": ("", "Debug endpoint access token"),
        "LOG_LEVEL": ("INFO", "Logging level (DEBUG, INFO, WARNING, ERROR)"),
        "CACHE_TTL": ("300", "Cache TTL in seconds"),
        "MAX_CONNECTIONS": ("10", "Maximum HTTP connections"),
        "CONNECTION_TIMEOUT": ("30", "Connection timeout in seconds"),
    }
    
    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """
        Validate environment variables
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required variables
        for var_name, description in cls.REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value:
                errors.append(f"Missing required environment variable: {var_name} ({description})")
        
        # Check optional variables and set defaults
        for var_name, (default, description) in cls.OPTIONAL_VARS.items():
            value = os.getenv(var_name)
            if value is None:
                os.environ[var_name] = default
                print(f"Using default value for {var_name}: {default}")
        
        # Validate specific variable formats
        errors.extend(cls._validate_formats())
        
        return len(errors) == 0, errors
    
    @classmethod
    def _validate_formats(cls) -> List[str]:
        """Validate specific environment variable formats"""
        errors = []
        
        # Validate LOG_LEVEL
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            errors.append(f"Invalid LOG_LEVEL: {log_level}. Must be one of: DEBUG, INFO, WARNING, ERROR")
        
        # Validate ENVIRONMENT
        environment = os.getenv("ENVIRONMENT", "staging")
        if environment not in ["development", "staging", "staging-external-test", "production"]:
            errors.append(f"Invalid ENVIRONMENT: {environment}. Must be one of: development, staging, staging-external-test, production")
        
        # Validate numeric values
        try:
            cache_ttl = int(os.getenv("CACHE_TTL", "300"))
            if cache_ttl < 0:
                errors.append("CACHE_TTL must be a positive integer")
        except ValueError:
            errors.append("CACHE_TTL must be a valid integer")
        
        try:
            max_conn = int(os.getenv("MAX_CONNECTIONS", "10"))
            if max_conn < 1:
                errors.append("MAX_CONNECTIONS must be at least 1")
        except ValueError:
            errors.append("MAX_CONNECTIONS must be a valid integer")
        
        try:
            timeout = int(os.getenv("CONNECTION_TIMEOUT", "30"))
            if timeout < 1:
                errors.append("CONNECTION_TIMEOUT must be at least 1 second")
        except ValueError:
            errors.append("CONNECTION_TIMEOUT must be a valid integer")
        
        # Validate CORS origins format
        cors_origins = os.getenv("ALLOWED_CORS_ORIGINS", "")
        if cors_origins:
            origins = cors_origins.split(",")
            for origin in origins:
                origin = origin.strip()
                if not origin.startswith(("http://", "https://")):
                    errors.append(f"Invalid CORS origin: {origin}. Must start with http:// or https://")
        
        return errors
    
    @classmethod
    def get_config(cls) -> Dict[str, any]:
        """Get validated configuration as a dictionary"""
        return {
            "airtable_pat": os.getenv("AIRTABLE_PAT"),
            "airtable_base_id": os.getenv("AIRTABLE_BASE_ID"),
            "environment": os.getenv("ENVIRONMENT", "staging"),
            "cors_origins": os.getenv("ALLOWED_CORS_ORIGINS", "").split(",") if os.getenv("ALLOWED_CORS_ORIGINS") else [],
            "jwt_secret_key": os.getenv("JWT_SECRET_KEY"),
            "debug_token": os.getenv("DEBUG_API_TOKEN"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "cache_ttl": int(os.getenv("CACHE_TTL", "300")),
            "max_connections": int(os.getenv("MAX_CONNECTIONS", "10")),
            "connection_timeout": int(os.getenv("CONNECTION_TIMEOUT", "30")),
        }
    
    @classmethod
    def print_config(cls, mask_secrets: bool = True):
        """Print current configuration for debugging"""
        config = cls.get_config()
        print("\n=== API Gateway Configuration ===")
        for key, value in config.items():
            if mask_secrets and any(secret in key for secret in ["pat", "secret", "token", "key"]):
                if value:
                    masked_value = value[:4] + "..." if len(str(value)) > 4 else "***"
                    print(f"{key}: {masked_value} (masked)")
                else:
                    print(f"{key}: Not set")
            else:
                print(f"{key}: {value}")
        print("================================\n")