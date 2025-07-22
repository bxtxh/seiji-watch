#!/usr/bin/env python3
"""
Startup script for API Gateway with proper Python path configuration.
"""

import os
import sys

# Add project root and shared package to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
shared_src = os.path.join(project_root, "shared", "src")

sys.path.insert(0, project_root)
sys.path.insert(0, shared_src)

# Add current directory for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import and run the main application
if __name__ == "__main__":
    import uvicorn
    from src.main import app

    port = int(os.getenv("PORT", 8080))
    print(f"Starting API Gateway on port {port}")
    print(f"Python path includes: {sys.path[:3]}")

    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
