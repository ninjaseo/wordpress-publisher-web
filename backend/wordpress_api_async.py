"""
WordPress REST API client - Fully Async Version
Optimized for non-blocking operations
"""
from typing import List, Dict, Optional
import aiohttp
import asyncio
import mimetypes
from pathlib import Path
from models import WordPressProfile

class WordPressAPIAsync:
    """Fully async WordPress REST API client"""
    
    def __init__(self, profile: WordPressProfile):
        self.profile = profile
        self.base_url = f"{profile.url}/wp-json/wp/v2"
        self.auth = aiohttp.BasicAuth(profile.username, profile.app_password)
        self.timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=30)
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make async HTTP request with proper error handling and retries"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(
                    auth=self.auth, 
                    timeout=self.timeout,
                    connector=aiohttp.TCPConnector(
                        limit=10,
                        limit_per_host=5,
                        ttl_dns_cache=300,
                        use_dns_cache=True
                    )
                ) as session:
                    async with session.request(method, url, **kwargs) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        elif response.status in [429, 502, 503, 504]:
                            # Retry on rate limit or server errors
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                                continue
                        
                        error_text = await response.text()
                        print(f"HTTP {response.status} on attempt {attempt + 1}: {error_text}")
                        if attempt == self.max_retries - 1:
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=error_text
                            )
                        
            except asyncio.TimeoutError:
                print(f"Timeout for {method} {endpoint} on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
            except aiohttp.ClientError as e:
                print(f"Client error for {method} {endpoint} on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
            except Exception as e:
                print(f"Unexpected error for {method} {endpoint} on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        return None
    
    async def test_connection(self) -> bool:
        """Test API connection asynchronously"""
        try:
            result = await self._make_request("GET", "users/me")
            return result is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    async def get_categories(self) -> List[Dict]:
        """Get all categories asynchronously"""
        try:
            result = await self._make_request("GET", "categories", params={"per_page": 100})
            return result if result else []
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    async def get_tags(self) -> List[Dict]:
        """Get all tags asynchronously"""
        try:
            result = await self._make_request("GET", "tags", params={"per_page": 100})
            return result if result else []
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []
    
    async def upload_image(self, image_path: Path) -> Optional[int]:
        """Upload image asynchronously and return media ID"""
        try:
            mime_type, _ = mimetypes.guess_type(str(image_path))
            if not mime_type or not mime_type.startswith('image/'):
                raise ValueError("File is not a valid image")
            
            # Read file asynchronously
            image_data = await self._read_file_async(image_path)
            if not image_data:
                return None
            
            headers = {
                'Content-Disposition': f'attachment; filename="{image_path.name}"',
                'Content-Type': mime_type
            }
            
            async with aiohttp.ClientSession(
                auth=self.auth, 
                timeout=aiohttp.ClientTimeout(total=60)  # Longer timeout for uploads
            ) as session:
                async with session.post(
                    f"{self.base_url}/media",
                    headers=headers,
                    data=image_data
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        return result.get('id')
                    return None
                    
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None
    
    async def _read_file_async(self, file_path: Path) -> Optional[bytes]:
        """Read file asynchronously"""
        try:
            # Use asyncio thread pool for file I/O
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._read_file_sync, file_path)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def _read_file_sync(self, file_path: Path) -> bytes:
        """Synchronous file reading for thread pool"""
        with open(file_path, 'rb') as f:
            return f.read()
    
    async def create_post(self, title: str, content: str, status: str = 'publish',
                         categories: List[int] = None, tags: List[int] = None,
                         featured_media: int = None) -> Optional[Dict]:
        """Create a new post asynchronously"""
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
            
            result = await self._make_request("POST", "posts", json=post_data)
            return result
            
        except Exception as e:
            print(f"Error creating post: {e}")
            return None
    
    async def create_category(self, name: str, description: str = "") -> Optional[Dict]:
        """Create a new category asynchronously"""
        try:
            category_data = {
                'name': name,
                'description': description
            }
            
            result = await self._make_request("POST", "categories", json=category_data)
            return result
            
        except Exception as e:
            print(f"Error creating category: {e}")
            return None
    
    async def create_tag(self, name: str, description: str = "") -> Optional[Dict]:
        """Create a new tag asynchronously"""
        try:
            tag_data = {
                'name': name,
                'description': description
            }
            
            result = await self._make_request("POST", "tags", json=tag_data)
            return result
            
        except Exception as e:
            print(f"Error creating tag: {e}")
            return None