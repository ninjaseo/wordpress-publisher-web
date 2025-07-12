"""
Data models for the WordPress Publisher application
"""
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime
from cryptography.fernet import Fernet


class WordPressProfile:
    """Represents a WordPress site profile with credentials"""
    
    def __init__(self, name: str, url: str, username: str, app_password: str):
        self.name = name
        self.url = url.rstrip('/')
        self.username = username
        self.app_password = app_password
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'url': self.url,
            'username': self.username,
            'app_password': self.app_password
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WordPressProfile':
        return cls(
            name=data['name'],
            url=data['url'],
            username=data['username'],
            app_password=data['app_password']
        )


class SecureStorage:
    """Handles secure storage of WordPress credentials"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.key_file = self.storage_path / 'key.key'
        self.profiles_file = self.storage_path / 'profiles.enc'
        self._ensure_storage_dir()
        self._key = self._load_or_create_key()
    
    def _ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        self.storage_path.mkdir(exist_ok=True)
    
    def _load_or_create_key(self) -> bytes:
        """Load existing key or create new one"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key
    
    def save_profiles(self, profiles: List[WordPressProfile]):
        """Save profiles to encrypted file"""
        profiles_data = [profile.to_dict() for profile in profiles]
        json_data = json.dumps(profiles_data)
        
        fernet = Fernet(self._key)
        encrypted_data = fernet.encrypt(json_data.encode())
        
        with open(self.profiles_file, 'wb') as f:
            f.write(encrypted_data)
    
    def load_profiles(self) -> List[WordPressProfile]:
        """Load profiles from encrypted file"""
        if not self.profiles_file.exists():
            return []
        
        try:
            with open(self.profiles_file, 'rb') as f:
                encrypted_data = f.read()
            
            fernet = Fernet(self._key)
            decrypted_data = fernet.decrypt(encrypted_data)
            profiles_data = json.loads(decrypted_data.decode())
            
            return [WordPressProfile.from_dict(profile_data) for profile_data in profiles_data]
        except Exception as e:
            print(f"Error loading profiles: {e}")
            return []


class ArticleFile:
    """Represents an article file"""
    
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        if path.exists():
            stat = path.stat()
            self.size = stat.st_size
            self.modified = datetime.fromtimestamp(stat.st_mtime)
        else:
            self.size = 0
            self.modified = datetime.now()
        self.title = None
        self.content = None
    
    def parse(self) -> tuple[str, str]:
        """Parse article file and return (title, content)"""
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Use filename as title by default
            title = self.path.stem
            
            # Check if first line looks like a title (starts with # for markdown)
            lines = content.split('\n', 1)
            if lines[0].startswith('#'):
                title = lines[0].lstrip('#').strip()
                content = lines[1].strip() if len(lines) > 1 else ''
            elif len(lines[0]) < 100 and len(lines) > 1:
                # If first line is short, treat as title
                title = lines[0].strip()
                content = lines[1].strip()
            
            self.title = title
            self.content = content
            return title, content
        except Exception as e:
            raise Exception(f"Error reading file {self.path}: {e}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'path': str(self.path),
            'name': self.name,
            'size': self.size,
            'modified': self.modified.isoformat(),
            'title': self.title,
            'content': self.content
        }


class PublicationResult:
    """Represents the result of publishing an article"""
    
    def __init__(self, filename: str, success: bool, details: str, url: Optional[str] = None):
        self.filename = filename
        self.success = success
        self.details = details
        self.url = url
    
    def to_dict(self) -> dict:
        return {
            'filename': self.filename,
            'success': self.success,
            'details': self.details,
            'url': self.url
        }