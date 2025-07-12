"""
Article management functionality
"""
from typing import List
from pathlib import Path
from models import ArticleFile


class ArticleManager:
    """Manages article files and parsing"""
    
    def __init__(self, articles_dir: Path):
        self.articles_dir = Path(articles_dir)
    
    def get_article_files(self) -> List[ArticleFile]:
        """Get all article files (txt, md)"""
        files = []
        if self.articles_dir.exists():
            for ext in ['*.txt', '*.md']:
                files.extend([ArticleFile(f) for f in self.articles_dir.glob(ext)])
        return sorted(files, key=lambda x: x.name)
    
    def get_file_by_path(self, file_path: str) -> ArticleFile:
        """Get article file by path"""
        return ArticleFile(Path(file_path))
    
    def set_articles_directory(self, new_dir: str):
        """Change the articles directory"""
        self.articles_dir = Path(new_dir)
        self.articles_dir.mkdir(exist_ok=True)