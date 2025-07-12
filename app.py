#!/usr/bin/env python3
"""
Main application entry point for WordPress Publisher Web App
"""
import uvicorn
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from main import app

if __name__ == "__main__":
    print("🚀 Starting WordPress Publisher Web Application...")
    print("=" * 60)
    print("📱 Open your browser and go to: http://localhost:8000")
    print("📝 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )