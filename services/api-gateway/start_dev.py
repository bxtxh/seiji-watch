#!/usr/bin/env python3
"""Development server startup script with proper environment setup."""

import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
api_gateway_root = Path(__file__).parent
shared_src = project_root / "shared" / "src"

sys.path.insert(0, str(api_gateway_root))
sys.path.insert(0, str(shared_src))

# Load environment variables from .env.development
env_file = api_gateway_root / ".env.development"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove comments and whitespace
                    value = value.split("#")[0].strip()
                    os.environ[key.strip()] = value

# Ensure critical environment variables are set
required_vars = ["JWT_SECRET_KEY", "AIRTABLE_PAT", "AIRTABLE_BASE_ID"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"Missing required environment variables: {missing_vars}")
    sys.exit(1)

# Start the server
if __name__ == "__main__":
    import uvicorn

    print("Starting API Gateway on port 8081...")
    print(f"AIRTABLE_PAT: {'*' * 10 if os.getenv('AIRTABLE_PAT') else 'NOT SET'}")
    print(f"AIRTABLE_BASE_ID: {os.getenv('AIRTABLE_BASE_ID', 'NOT SET')}")

    uvicorn.run(
        "src.main:app", host="0.0.0.0", port=8081, reload=True, log_level="info"
    )
