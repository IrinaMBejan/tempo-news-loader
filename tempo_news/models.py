"""Data models for news articles."""

from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, field_validator


class Article(BaseModel):
    """Represents a news article."""
    
    title: str
    url: HttpUrl
    author: Optional[str] = None
    published: Optional[datetime] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    categories: List[str] = []
    slug: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def clean_title(cls, v: str) -> str:
        """Clean and normalize title."""
        return v.strip().replace('\n', ' ').replace('\r', ' ')
    
    def generate_slug(self) -> str:
        """Generate URL-friendly slug from title."""
        import re
        if self.slug:
            return self.slug
        
        slug = self.title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        return slug[:100]  # Limit length
    
    def get_file_path(self, base_dir: Path) -> Path:
        """Get the file path for saving this article."""
        filename = f"{self.generate_slug()}.md"
        return base_dir / filename


class FetchConfig(BaseModel):
    """Configuration for RSS fetching."""
    
    rss_url: str = "https://rss.tempo.co/"
    output_dir: Path = Path("articles")
    max_articles: int = 50
    user_agent: str = "Tempo News Fetcher 1.0"
    rate_limit_delay: float = 1.0
    fetch_full_content: bool = True
    enable_rag: bool = True
    rag_app_name: str = "com.github.openmined.local-rag"
    syftbox_config_path: Optional[Path] = None