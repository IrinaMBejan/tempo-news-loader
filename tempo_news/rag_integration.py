"""RAG integration for ingesting articles into vector database."""

from typing import List, Optional
from pathlib import Path
from rich.console import Console
import requests
import json

from .models import Article, FetchConfig
from .rag_service import RAGServiceDetector

console = Console()


class RAGIntegration:
    """Handles RAG service integration for article ingestion."""
    
    def __init__(self, config: FetchConfig):
        self.config = config
        self.detector = RAGServiceDetector(config.syftbox_config_path)
        self.service_url: Optional[str] = None
        self.is_connected = False
        self.folder_registered = False
    
    def setup_rag_connection(self) -> bool:
        """Setup connection to RAG service (always enabled)."""
        
        console.print("[blue]Setting up RAG service connection...[/blue]")
        
        # Detect RAG service
        if self.detector.detect_rag_service(
            app_name=self.config.rag_app_name,
            max_wait_time=30
        ):
            self.service_url = self.detector.get_service_url()
            self.is_connected = True
            console.print(f"[green]✓ Connected to RAG service: {self.service_url}[/green]")
            
            # Register articles folder for automatic indexing
            if self.register_articles_folder():
                console.print(f"[green]✓ Articles folder registered for automatic indexing[/green]")
            
            return True
        else:
            console.print("[yellow]RAG service not available. Articles will be saved without RAG processing.[/yellow]")
            return False
    
    def register_articles_folder(self) -> bool:
        """Register the articles folder with RAG service for automatic indexing."""
        if not self.is_connected or not self.service_url:
            return False
        
        try:
            articles_path = self.config.output_dir.absolute()
            
            # Check if folder is already registered
            if self.is_folder_registered(articles_path):
                console.print(f"[dim]Articles folder already registered: {articles_path}[/dim]")
                self.folder_registered = True
                return True
            
            # Register folder using RAG API
            response = requests.post(
                f"{self.service_url}/api/add-folder",
                json={"folder_path": str(articles_path)},
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.folder_registered = True
                console.print(f"[green]✓ Registered folder: {articles_path}[/green]")
                return True
            else:
                console.print(f"[yellow]Failed to register folder: HTTP {response.status_code}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[yellow]Error registering articles folder: {e}[/yellow]")
            return False
    
    def is_folder_registered(self, folder_path: Path) -> bool:
        """Check if folder is already in the RAG watched folders list."""
        if not self.is_connected or not self.service_url:
            return False
        
        try:
            response = requests.get(
                f"{self.service_url}/api/watched-folders",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                watched_folders = data.get("folders", [])
                return str(folder_path) in watched_folders
            else:
                return False
                
        except Exception as e:
            console.print(f"[dim]Could not check watched folders: {e}[/dim]")
            return False
    
    def get_rag_stats(self) -> dict:
        """Get RAG system statistics."""
        if not self.is_connected or not self.service_url:
            return {"total_documents": 0, "watched_folders": 0}
        
        try:
            response = requests.get(
                f"{self.service_url}/api/stats",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"total_documents": 0, "watched_folders": 0}
                
        except Exception as e:
            console.print(f"[dim]Could not get RAG stats: {e}[/dim]")
            return {"total_documents": 0, "watched_folders": 0}
    
    def get_indexing_status(self) -> dict:
        """Get current RAG indexing status."""
        if not self.is_connected or not self.service_url:
            return {"status": "disconnected", "queue_size": 0}
        
        try:
            response = requests.get(
                f"{self.service_url}/api/indexing-status",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "unknown", "queue_size": 0}
                
        except Exception as e:
            console.print(f"[dim]Could not get indexing status: {e}[/dim]")
            return {"status": "error", "queue_size": 0}
    
    def ingest_article(self, article: Article) -> bool:
        """Ingest a single article into the RAG vector database.
        
        Args:
            article: Article to ingest
            
        Returns:
            True if successfully ingested, False otherwise
        """
        if not self.is_connected or not self.service_url:
            return False
        
        try:
            # Prepare article data for RAG ingestion
            article_data = {
                "title": article.title,
                "content": article.content or article.summary or "",
                "url": str(article.url),
                "author": article.author,
                "published": article.published.isoformat() if article.published else None,
                "categories": article.categories,
                "slug": article.generate_slug()
            }
            
            # Send to RAG service
            response = requests.post(
                f"{self.service_url}/ingest",
                json=article_data,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                console.print(f"[green]✓ Ingested to RAG: {article.title}[/green]")
                return True
            else:
                console.print(f"[yellow]RAG ingestion failed for '{article.title}': {response.status_code}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[yellow]RAG ingestion error for '{article.title}': {e}[/yellow]")
            return False
    
    def ingest_articles(self, articles: List[Article]) -> dict:
        """Note: Articles are automatically indexed by RAG folder watching.
        
        Args:
            articles: List of articles (for compatibility)
            
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.is_connected:
            return {"successful": 0, "failed": 0, "skipped": len(articles)}
        
        if self.folder_registered:
            # Articles are automatically indexed when saved to the watched folder
            console.print(f"[green]✓ {len(articles)} articles will be automatically indexed by RAG folder watching[/green]")
            
            # Get current indexing status
            status = self.get_indexing_status()
            if status.get("queue_size", 0) > 0:
                console.print(f"[dim]RAG indexing queue size: {status['queue_size']}[/dim]")
            
            return {
                "successful": len(articles),
                "failed": 0,
                "skipped": 0,
                "method": "automatic_folder_watching"
            }
        else:
            console.print(f"[yellow]Articles folder not registered - automatic indexing unavailable[/yellow]")
            return {"successful": 0, "failed": 0, "skipped": len(articles)}
    
    def ingest_from_markdown_files(self, markdown_dir: Path) -> dict:
        """Ingest articles from existing markdown files.
        
        Args:
            markdown_dir: Directory containing markdown files
            
        Returns:
            Dictionary with ingestion statistics
        """
        if not self.is_connected:
            return {"successful": 0, "failed": 0, "skipped": 0}
        
        md_files = list(markdown_dir.glob("*.md"))
        console.print(f"[blue]Found {len(md_files)} markdown files to process[/blue]")
        
        successful = 0
        failed = 0
        
        for md_file in md_files:
            try:
                # Read markdown file and extract frontmatter + content
                content = md_file.read_text(encoding='utf-8')
                
                # Simple frontmatter parsing (could be enhanced)
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        import yaml
                        frontmatter = yaml.safe_load(parts[1])
                        markdown_content = parts[2].strip()
                        
                        # Create article-like data for RAG
                        article_data = {
                            "title": frontmatter.get("title", md_file.stem),
                            "content": markdown_content,
                            "url": frontmatter.get("url", ""),
                            "author": frontmatter.get("author"),
                            "published": frontmatter.get("published"),
                            "categories": frontmatter.get("categories", []),
                            "slug": frontmatter.get("slug", md_file.stem)
                        }
                        
                        # Send to RAG service
                        response = requests.post(
                            f"{self.service_url}/ingest",
                            json=article_data,
                            timeout=30,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code == 200:
                            console.print(f"[green]✓ Ingested: {md_file.name}[/green]")
                            successful += 1
                        else:
                            console.print(f"[yellow]Failed to ingest: {md_file.name} ({response.status_code})[/yellow]")
                            failed += 1
                            
            except Exception as e:
                console.print(f"[red]Error processing {md_file.name}: {e}[/red]")
                failed += 1
        
        stats = {
            "successful": successful,
            "failed": failed,
            "skipped": 0
        }
        
        console.print(f"[bold]Markdown Ingestion Summary:[/bold]")
        console.print(f"  • Successful: {successful}")
        console.print(f"  • Failed: {failed}")
        
        return stats
    
    def get_rag_status(self) -> dict:
        """Get RAG service status information."""
        if self.detector:
            return self.detector.get_service_info()
        return {
            "url": None,
            "port": None,
            "pid": None,
            "available": False,
            "healthy": False
        }
    
    def get_service_info(self) -> dict:
        """Get comprehensive service information dictionary."""
        base_info = {
            "url": self.detector.rag_service_url if self.detector else None,
            "port": self.detector.rag_service_port if self.detector else None,
            "pid": self.detector.rag_service_pid if self.detector else None,
            "available": self.is_connected,
            "healthy": self.detector.verify_service_health() if self.detector and self.is_connected else False,
            "folder_registered": self.folder_registered
        }
        
        # Add RAG stats if connected
        if self.is_connected:
            stats = self.get_rag_stats()
            indexing_status = self.get_indexing_status()
            base_info.update({
                "total_documents": stats.get("total_documents", 0),
                "watched_folders_count": stats.get("watched_folders", 0),
                "indexing_status": indexing_status.get("status", "unknown"),
                "indexing_queue_size": indexing_status.get("queue_size", 0),
                "articles_folder_path": str(self.config.output_dir.absolute())
            })
        
        return base_info