"""Markdown file writer for articles."""

import json
import unicodedata
from pathlib import Path
from typing import List, Set
from datetime import datetime
from rich.console import Console

from .models import Article

console = Console()


class MarkdownWriter:
    """Writes articles as markdown files."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.metadata_file = self.output_dir / ".metadata.json"
        self._ensure_output_dir()
        self._load_existing_urls()
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_existing_urls(self) -> Set[str]:
        """Load existing article URLs from metadata."""
        self.existing_urls = set()
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                    self.existing_urls = set(metadata.get('processed_urls', []))
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load metadata: {e}[/yellow]")
        return self.existing_urls
    
    def _save_metadata(self, new_urls: List[str]):
        """Save metadata with processed URLs."""
        try:
            metadata = {
                'last_updated': datetime.now().isoformat(),
                'processed_urls': list(self.existing_urls.union(new_urls))
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save metadata: {e}[/yellow]")
    
    def is_article_processed(self, article: Article) -> bool:
        """Check if article has already been processed."""
        return str(article.url) in self.existing_urls
    
    def write_article(self, article: Article) -> Path:
        """Write article to markdown file."""
        file_path = article.get_file_path(self.output_dir)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate markdown content
        markdown_content = self._generate_markdown(article)
        
        # Write to file (using ASCII-compatible encoding)
        with open(file_path, 'w', encoding='ascii', errors='replace') as f:
            f.write(markdown_content)
        
        console.print(f"[green]✓[/green] Saved: {file_path.relative_to(self.output_dir)}")
        return file_path
    
    def _generate_markdown(self, article: Article) -> str:
        """Generate markdown content for article."""
        lines = []
        
        # Frontmatter
        lines.append("---")
        lines.append(f"title: \"{self._escape_yaml(self._normalize_text(article.title))}\"")
        lines.append(f"url: {article.url}")
        
        if article.author:
            lines.append(f"author: \"{self._escape_yaml(self._normalize_text(article.author))}\"")
        
        if article.published:
            lines.append(f"published: {article.published.isoformat()}")
            lines.append(f"date: {article.published.strftime('%Y-%m-%d')}")
        
        if article.categories:
            lines.append("categories:")
            for category in article.categories:
                lines.append(f"  - \"{self._escape_yaml(self._normalize_text(category))}\"")
        
        lines.append(f"slug: {article.generate_slug()}")
        lines.append("---")
        lines.append("")
        
        # Title
        lines.append(f"# {self._normalize_text(article.title)}")
        lines.append("")
        
        # Metadata
        if article.author or article.published:
            metadata_parts = []
            if article.author:
                metadata_parts.append(f"**By:** {self._normalize_text(article.author)}")
            if article.published:
                metadata_parts.append(f"**Published:** {article.published.strftime('%B %d, %Y')}")
            
            lines.append(" | ".join(metadata_parts))
            lines.append("")
        
        # Categories
        if article.categories:
            category_tags = [f"`{self._normalize_text(cat)}`" for cat in article.categories]
            lines.append(f"**Categories:** {' '.join(category_tags)}")
            lines.append("")
        
        # Source URL
        lines.append(f"**Source:** [{article.url}]({article.url})")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Summary
        if article.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(self._normalize_text(article.summary))
            lines.append("")
        
        # Content
        if article.content:
            lines.append("## Article Content")
            lines.append("")
            lines.append(self._clean_content(self._normalize_text(article.content)))
        else:
            lines.append("*Full article content not available. Please visit the source URL above.*")
        
        return "\n".join(lines)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize unicode text to ASCII-compatible characters."""
        if not text:
            return ""
        
        # Normalize unicode characters to their closest ASCII equivalents
        # NFD = decomposed form, then filter out combining characters
        normalized = unicodedata.normalize('NFD', text)
        ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        # Replace common unicode punctuation with ASCII equivalents
        replacements = {
            '\u2013': '-',    # en dash
            '\u2014': '--',   # em dash
            '\u2018': "'",    # left single quotation mark
            '\u2019': "'",    # right single quotation mark
            '\u201c': '"',    # left double quotation mark
            '\u201d': '"',    # right double quotation mark
            '\u2026': '...',  # horizontal ellipsis
            '\u00a0': ' ',    # non-breaking space
            '\u2022': '*',    # bullet point
            '\u00ab': '<<',   # left-pointing double angle quotation mark
            '\u00bb': '>>',   # right-pointing double angle quotation mark
        }
        
        for unicode_char, ascii_char in replacements.items():
            ascii_text = ascii_text.replace(unicode_char, ascii_char)
        
        # Remove any remaining non-ASCII characters
        ascii_text = ascii_text.encode('ascii', errors='replace').decode('ascii')
        
        return ascii_text
    
    def _escape_yaml(self, text: str) -> str:
        """Escape text for YAML frontmatter."""
        if not text:
            return ""
        return text.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
    
    def _clean_content(self, content: str) -> str:
        """Clean and format article content."""
        if not content:
            return ""
        
        # Basic cleaning
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n\n'.join(cleaned_lines)
    
    def write_articles(self, articles: List[Article]) -> List[Path]:
        """Write multiple articles, skipping duplicates."""
        written_files = []
        new_urls = []
        skipped_count = 0
        
        for article in articles:
            if self.is_article_processed(article):
                skipped_count += 1
                console.print(f"[dim]Skipping (already processed): {article.title}[/dim]")
                continue
            
            try:
                file_path = self.write_article(article)
                written_files.append(file_path)
                new_urls.append(str(article.url))
            except Exception as e:
                console.print(f"[red]Error writing article '{article.title}': {e}[/red]")
        
        # Update metadata
        if new_urls:
            self._save_metadata(new_urls)
        
        console.print(f"\n[bold green]Summary:[/bold green]")
        console.print(f"  • Written: {len(written_files)} articles")
        console.print(f"  • Skipped: {skipped_count} articles (already processed)")
        
        return written_files