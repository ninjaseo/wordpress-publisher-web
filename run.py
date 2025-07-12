#!/usr/bin/env python3
"""
Simple launcher for WordPress Publisher Web App
"""
import uvicorn
import sys
import os
from pathlib import Path

# Change to backend directory
backend_dir = Path(__file__).parent / "backend"
os.chdir(backend_dir)

# Add backend to Python path
sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    print("🚀 Starting WordPress Publisher Web Application...")
    print("=" * 60)
    print("📱 Open your browser and go to: http://localhost:8000")
    print("📝 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )