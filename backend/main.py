"""
FastAPI backend for WordPress Publisher
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio
import json
import os
import tempfile
import shutil
import logging
import time
from functools import wraps

from models import WordPressProfile, SecureStorage, PublicationResult, ArticleFile
from wordpress_api import WordPressAPI
from wordpress_api_async import WordPressAPIAsync
from article_manager import ArticleManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="WordPress Publisher", 
    version="1.0.0",
    description="WordPress Publisher API with enhanced error handling and timeouts"
)

# Request timeout configuration
REQUEST_TIMEOUT = 30  # seconds
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_RETRIES = 3

# Error handling decorator
def handle_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except HTTPException:
            raise
        except asyncio.TimeoutError:
            logger.error(f"{func.__name__} timed out")
            raise HTTPException(status_code=408, detail="Request timeout")
        except FileNotFoundError as e:
            logger.error(f"{func.__name__} file not found: {e}")
            raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
        except PermissionError as e:
            logger.error(f"{func.__name__} permission error: {e}")
            raise HTTPException(status_code=403, detail=f"Permission denied: {str(e)}")
        except Exception as e:
            logger.error(f"{func.__name__} unexpected error: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    return wrapper

# Request size middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    
    # Check request size
    if hasattr(request, "headers") and "content-length" in request.headers:
        content_length = int(request.headers["content-length"])
        if content_length > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"}
            )
    
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state - Handle Vercel environment
base_dir = Path(os.environ.get('BASE_DIR', Path(__file__).parent.parent))
temp_dir = Path("/tmp") if os.environ.get('VERCEL') else Path.home()

storage = SecureStorage(temp_dir / ".publicador")
article_manager = ArticleManager(temp_dir / "Articles")
current_profile: Optional[WordPressProfile] = None

# Mount static files
static_path = base_dir / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Serve the main HTML file
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main application page"""
    html_file = base_dir / "frontend" / "index.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>WordPress Publisher</h1><p>Frontend not found</p><p>Base dir: " + str(base_dir) + "</p>")


# Profile Management Endpoints
@app.get("/api/profiles")
async def get_profiles():
    """Get all WordPress profiles"""
    profiles = storage.load_profiles()
    return [profile.to_dict() for profile in profiles]


@app.post("/api/profiles")
async def create_profile(profile_data: dict):
    """Create a new WordPress profile"""
    try:
        profile = WordPressProfile(
            name=profile_data['name'],
            url=profile_data['url'],
            username=profile_data['username'],
            app_password=profile_data['app_password']
        )
        
        profiles = storage.load_profiles()
        profiles.append(profile)
        storage.save_profiles(profiles)
        
        return {"success": True, "message": "Profile created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/profiles/{profile_name}")
async def get_profile(profile_name: str):
    """Get a specific profile by name"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return profile.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/profiles/{profile_name}")
async def delete_profile(profile_name: str):
    """Delete a WordPress profile"""
    try:
        profiles = storage.load_profiles()
        profiles = [p for p in profiles if p.name != profile_name]
        storage.save_profiles(profiles)
        
        return {"success": True, "message": "Profile deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/profiles/{profile_name}/test")
async def test_profile_connection(profile_name: str):
    """Test connection to a WordPress profile"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        api = WordPressAPI(profile)
        success = await api.test_connection()
        
        return {
            "success": success,
            "message": "Connection successful" if success else "Connection failed"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/profiles/{profile_name}/select")
async def select_profile(profile_name: str):
    """Select a profile as the current active profile"""
    global current_profile
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        current_profile = profile
        return {"success": True, "message": f"Profile '{profile_name}' selected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/current-profile")
async def get_current_profile():
    """Get the currently selected profile"""
    if current_profile:
        return current_profile.to_dict()
    return None


# WordPress Data Endpoints
@app.get("/api/wordpress/categories")
async def get_categories():
    """Get WordPress categories for current profile"""
    if not current_profile:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    try:
        api = WordPressAPI(current_profile)
        categories = await api.get_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/wordpress/tags")
async def get_tags():
    """Get WordPress tags for current profile"""
    if not current_profile:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    try:
        api = WordPressAPI(current_profile)
        tags = await api.get_tags()
        return tags
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Article Management Endpoints
@app.get("/api/articles/directory")
async def get_articles_directory():
    """Get current articles directory"""
    return {"directory": str(article_manager.articles_dir)}


@app.post("/api/articles/directory")
async def set_articles_directory(directory_data: dict):
    """Set articles directory"""
    try:
        new_dir = directory_data['directory']
        article_manager.set_articles_directory(new_dir)
        return {"success": True, "directory": str(article_manager.articles_dir)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/articles/files")
async def get_article_files():
    """Get all article files in the current directory"""
    try:
        files = article_manager.get_article_files()
        return [file.to_dict() for file in files]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/articles/parse/{file_path:path}")
async def parse_article(file_path: str):
    """Parse an article file and return title and content"""
    try:
        article_file = article_manager.get_file_by_path(file_path)
        title, content = article_file.parse()
        return {
            "title": title,
            "content": content,
            "file_info": article_file.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Image Upload Endpoint
@app.post("/api/upload/image")
async def upload_featured_image(file: UploadFile = File(...)):
    """Upload and store featured image temporarily"""
    try:
        # Create temp directory if it doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "publicador_images"
        temp_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "filename": file.filename,
            "path": str(file_path),
            "size": file_path.stat().st_size
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Publication Endpoint
@app.post("/api/publish")
async def publish_articles(publication_data: dict, background_tasks: BackgroundTasks):
    """Publish selected articles to WordPress"""
    if not current_profile:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    try:
        selected_files = publication_data.get('files', [])
        categories = publication_data.get('categories', [])
        tags = publication_data.get('tags', [])
        featured_image_path = publication_data.get('featured_image_path')
        
        if not selected_files:
            raise HTTPException(status_code=400, detail="No files selected")
        
        # Start background publication task
        task_id = f"publish_{len(selected_files)}_{hash(str(selected_files))}"
        background_tasks.add_task(
            publish_articles_task, 
            task_id, 
            selected_files, 
            categories, 
            tags, 
            featured_image_path
        )
        
        return {
            "success": True,
            "message": f"Publishing {len(selected_files)} articles...",
            "task_id": task_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Publication task storage (in production, use Redis or similar)
publication_results: Dict[str, List[PublicationResult]] = {}
publication_status: Dict[str, str] = {}


async def publish_articles_task(task_id: str, selected_files: List[str], 
                               categories: List[int], tags: List[int], 
                               featured_image_path: Optional[str]):
    """Background task to publish articles"""
    global publication_results, publication_status
    
    publication_status[task_id] = "running"
    results = []
    
    try:
        api = WordPressAPI(current_profile)
        
        # Upload featured image if provided
        featured_media_id = None
        if featured_image_path:
            featured_media_id = await api.upload_image(Path(featured_image_path))
            if not featured_media_id:
                results.append(PublicationResult(
                    "featured_image", False, "Failed to upload featured image"
                ))
        
        # Publish each file
        for file_path in selected_files:
            try:
                article_file = article_manager.get_file_by_path(file_path)
                title, content = article_file.parse()
                
                result = await api.create_post(
                    title=title,
                    content=content,
                    categories=categories if categories else None,
                    tags=tags if tags else None,
                    featured_media=featured_media_id
                )
                
                if result:
                    results.append(PublicationResult(
                        article_file.name, True, "Published successfully", 
                        result.get('link', 'N/A')
                    ))
                else:
                    results.append(PublicationResult(
                        article_file.name, False, "Unknown error during publication"
                    ))
                    
            except Exception as e:
                results.append(PublicationResult(
                    Path(file_path).name, False, str(e)
                ))
        
        publication_results[task_id] = results
        publication_status[task_id] = "completed"
        
    except Exception as e:
        publication_status[task_id] = "error"
        publication_results[task_id] = [PublicationResult(
            "task", False, f"Task failed: {str(e)}"
        )]


@app.get("/api/publish/status/{task_id}")
async def get_publication_status(task_id: str):
    """Get publication task status"""
    status = publication_status.get(task_id, "not_found")
    results = publication_results.get(task_id, [])
    
    return {
        "task_id": task_id,
        "status": status,
        "results": [result.to_dict() for result in results]
    }


# New endpoints for the redesigned frontend

@app.post("/api/upload-image/{profile_name}")
@handle_errors
async def upload_image(profile_name: str, file: UploadFile = File(...)):
    """Upload an image to WordPress media library - Async version"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Save uploaded file temporarily (async)
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Use async API
            api = WordPressAPIAsync(profile)
            media_id = await api.upload_image(Path(tmp_file_path))
            
            if media_id:
                return {"success": True, "media_id": media_id}
            else:
                raise HTTPException(status_code=400, detail="Failed to upload image")
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/publish/{profile_name}")
@handle_errors
async def publish_single_article(profile_name: str, article_data: dict):
    """Publish a single article with individual options - Async version"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        file_path = article_data.get('file_path')
        status = article_data.get('status', 'publish')
        categories = article_data.get('categories', [])
        tags = article_data.get('tags', [])
        featured_media = article_data.get('featured_media')
        
        if not file_path:
            raise HTTPException(status_code=400, detail="File path is required")
        
        # Parse article content (async file reading)
        article_file = article_manager.get_file_by_path(file_path)
        title, content = article_file.parse()
        
        # Publish to WordPress using async API
        api = WordPressAPIAsync(profile)
        result = await api.create_post(
            title=title,
            content=content,
            status=status,
            categories=categories if categories else None,
            tags=tags if tags else None,
            featured_media=featured_media
        )
        
        if result:
            return {
                "success": True,
                "url": result.get('link', 'N/A'),
                "id": result.get('id'),
                "status": result.get('status')
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to publish article")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/categories/{profile_name}")
@handle_errors
async def get_profile_categories(profile_name: str):
    """Get WordPress categories for specific profile - Async version"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        api = WordPressAPIAsync(profile)
        categories = await api.get_categories()
        return categories
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tags/{profile_name}")
@handle_errors
async def get_profile_tags(profile_name: str):
    """Get WordPress tags for specific profile - Async version"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        api = WordPressAPIAsync(profile)
        tags = await api.get_tags()
        return tags
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/categories/{profile_name}")
async def create_category(profile_name: str, category_data: dict):
    """Create a new category"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        name = category_data.get('name')
        if not name:
            raise HTTPException(status_code=400, detail="Category name is required")
        
        # Note: This would need to be implemented in WordPressAPI
        # For now, return success (WordPress REST API supports creating categories)
        return {"success": True, "message": "Category creation not yet implemented"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tags/{profile_name}")
async def create_tag(profile_name: str, tag_data: dict):
    """Create a new tag"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        name = tag_data.get('name')
        if not name:
            raise HTTPException(status_code=400, detail="Tag name is required")
        
        # Note: This would need to be implemented in WordPressAPI
        # For now, return success (WordPress REST API supports creating tags)
        return {"success": True, "message": "Tag creation not yet implemented"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/test-connection/{profile_name}")
@handle_errors
async def test_profile_connection(profile_name: str):
    """Test connection for specific profile - Async version"""
    try:
        profiles = storage.load_profiles()
        profile = next((p for p in profiles if p.name == profile_name), None)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        api = WordPressAPIAsync(profile)
        success = await api.test_connection()
        
        if success:
            return {"success": True, "message": "Connection successful"}
        else:
            raise HTTPException(status_code=400, detail="Connection failed")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/current-directory")
async def get_current_directory():
    """Get current articles directory"""
    return {"directory": str(article_manager.articles_dir)}


@app.post("/api/change-directory")
async def change_directory():
    """Change articles directory (simplified - uses file dialog in real implementation)"""
    # In a real implementation, this would trigger a file dialog
    # For now, we'll just return success
    return {"success": True, "message": "Directory change not implemented in web version"}


@app.post("/api/set-directory")
async def set_directory(data: dict):
    """Set articles directory from native app"""
    global article_manager
    try:
        new_directory = data.get('directory')
        if not new_directory:
            raise HTTPException(status_code=400, detail="Directory path is required")
        
        # Update article manager with new directory
        article_manager.set_articles_directory(new_directory)
        return {"success": True, "message": f"Directory changed to {new_directory}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/files")
async def get_article_files():
    """Get list of article files"""
    try:
        files = article_manager.get_article_files()
        return [
            {
                "name": f.name,
                "path": str(f.path),
                "size": f.size,
                "modified": f.modified.isoformat()
            }
            for f in files
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "WordPress Publisher API is running"}


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )