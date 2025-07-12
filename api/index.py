"""
Vercel entry point for WordPress Publisher
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set environment variables for proper path resolution
os.environ['BASE_DIR'] = str(Path(__file__).parent.parent)

try:
    # Import and expose the FastAPI app
    from main import app
    handler = app
except Exception as e:
    # Fallback minimal app
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    handler = FastAPI()
    
    @handler.get("/")
    async def root():
        return JSONResponse({"error": f"Failed to load app: {str(e)}"})
    
    @handler.get("/api/health")
    async def health():
        return JSONResponse({"status": "error", "error": str(e)})