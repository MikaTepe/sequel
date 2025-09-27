#!/usr/bin/env python3
# apps/backend/run.py

"""
Development server runner for Sequel Backend

This script provides an easy way to start the development server
without import issues.
"""

import os
import sys
import uvicorn

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the app
from app.main import app

if __name__ == "__main__":
    # Load environment variables
    from app.core.config import get_settings

    settings = get_settings()

    print("🚀 Starting Sequel Backend Development Server")
    print(f"📊 Environment: {settings.environment}")
    print(f"🌐 Host: {settings.host}:{settings.port}")
    print(f"📚 API Docs: http://{settings.host}:{settings.port}/docs")
    print(f"🏥 Health Check: http://{settings.host}:{settings.port}/health")
    print("=" * 50)

    # Start the server
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )