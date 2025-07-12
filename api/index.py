"""
Vercel entry point for WordPress Publisher
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Change working directory to backend
os.chdir(str(backend_dir))

# Import and expose the FastAPI app
from main import app

# Export app for Vercel
handler = app