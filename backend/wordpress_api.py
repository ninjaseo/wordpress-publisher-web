"""
WordPress REST API client for the web application
"""
from typing import List, Dict, Optional
import requests
import mimetypes
from pathlib import Path
from models import WordPressProfile


class WordPressAPI:
    """WordPress REST API client"""
    
    def __init__(self, profile: WordPressProfile):
        self.profile = profile
        self.base_url = f"{profile.url}/wp-json/wp/v2"
        self.auth = (profile.username, profile.app_password)
    
    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = requests.get(f"{self.base_url}/users/me", auth=self.auth, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_categories(self) -> List[Dict]:
        """Get all categories"""
        try:
            response = requests.get(f"{self.base_url}/categories?per_page=100", 
                                  auth=self.auth, timeout=15)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    async def get_tags(self) -> List[Dict]:
        """Get all tags"""
        try:
            response = requests.get(f"{self.base_url}/tags?per_page=100", 
                                  auth=self.auth, timeout=15)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    async def upload_image(self, image_path: Path) -> Optional[int]:
        """Upload image and return media ID"""
        try:
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type or not mime_type.startswith('image/'):
                raise ValueError("File is not a valid image")
            
            headers = {
                'Content-Disposition': f'attachment; filename="{image_path.name}"',
                'Content-Type': mime_type
            }
            
            with open(image_path, 'rb') as f:
                response = requests.post(
                    f"{self.base_url}/media",
                    headers=headers,
                    data=f.read(),
                    auth=self.auth,
                    timeout=30
                )
            
            if response.status_code == 201:
                return response.json()['id']
            return None
        except Exception:
            return None
    
    async def create_post(self, title: str, content: str, status: str = 'publish',
                         categories: List[int] = None, tags: List[int] = None,
                         featured_media: int = None) -> Optional[Dict]:
        """Create a new post"""
        try:
            post_data = {
                'title': title,
                'content': content,
                'status': status
            }
            
            if categories:
                post_data['categories'] = categories
            if tags:
                post_data['tags'] = tags
            if featured_media:
                post_data['featured_media'] = featured_media
            
            response = requests.post(f"{self.base_url}/posts", 
                                   json=post_data, auth=self.auth, timeout=30)
            
            if response.status_code == 201:
                return response.json()
            return None
        except Exception:
            return None