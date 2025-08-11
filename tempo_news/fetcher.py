"""RSS feed fetcher for Tempo NYC."""

import feedparser
import requests
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin
from dateutil import parser as date_parser
from rich.console import Console
from rich.progress import Progress, TaskID

from .models import Article, FetchConfig

console = Console()


class RSSFetcher:
    """Fetches articles from RSS feeds."""
    
    def __init__(self, config: FetchConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.user_agent
        })
    
    def fetch_rss_feed(self) -> List[Article]:
        """Fetch and parse RSS feed."""
        console.print(f"[blue]Fetching RSS feed from: {self.config.rss_url}[/blue]")
        
        try:
            feed = feedparser.parse(self.config.rss_url)
            
            if feed.bozo:
                console.print(f"[yellow]Warning: Feed parsing errors: {feed.bozo_exception}[/yellow]")
            
            console.print(f"[green]Found {len(feed.entries)} articles in RSS feed[/green]")
            
            articles = []
            for entry in feed.entries[:self.config.max_articles]:
                article = self._parse_rss_entry(entry)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            console.print(f"[red]Error fetching RSS feed: {e}[/red]")
            return []
    
    def _parse_rss_entry(self, entry) -> Optional[Article]:
        """Parse RSS entry into Article model."""
        try:
            # Parse publication date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'published'):
                try:
                    published = date_parser.parse(entry.published)
                except:
                    pass
            
            # Extract categories
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.term for tag in entry.tags]
            
            # Get author
            author = getattr(entry, 'author', None)
            
            # Get summary
            summary = getattr(entry, 'summary', None)
            if summary:
                # Clean HTML from summary
                from bs4 import BeautifulSoup
                summary = BeautifulSoup(summary, 'html.parser').get_text().strip()
            
            article = Article(
                title=entry.title,
                url=entry.link,
                author=author,
                published=published,
                summary=summary,
                categories=categories
            )
            
            return article
            
        except Exception as e:
            console.print(f"[red]Error parsing RSS entry: {e}[/red]")
            return None
    
    def fetch_article_content(self, article: Article) -> Article:
        """Fetch full article content."""
        if not self.config.fetch_full_content:
            return article
        
        try:
            console.print(f"[dim]Fetching content for: {article.title}[/dim]")
            
            response = self.session.get(str(article.url), timeout=10)
            response.raise_for_status()
            
            from newspaper import Article as NewsArticle
            
            news_article = NewsArticle(str(article.url))
            news_article.download(input_html=response.text)
            news_article.parse()
            
            if news_article.text:
                article.content = news_article.text
            
            # Update other fields if they weren't in RSS
            if not article.author and news_article.authors:
                article.author = ', '.join(news_article.authors)
            
            if not article.published and news_article.publish_date:
                article.published = news_article.publish_date
            
            return article
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch content for {article.url}: {e}[/yellow]")
            return article
    
    def fetch_articles(self) -> List[Article]:
        """Fetch articles from RSS feed with content."""
        articles = self.fetch_rss_feed()
        
        if not articles:
            return []
        
        console.print(f"[blue]Fetching full content for {len(articles)} articles...[/blue]")
        
        with Progress() as progress:
            task = progress.add_task("Fetching articles...", total=len(articles))
            
            for i, article in enumerate(articles):
                articles[i] = self.fetch_article_content(article)
                progress.update(task, advance=1)
                
                # Rate limiting
                if i < len(articles) - 1:  # Don't delay after last article
                    import time
                    time.sleep(self.config.rate_limit_delay)
        
        return articles