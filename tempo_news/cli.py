"""Command line interface for Tempo News fetcher."""

import click
from pathlib import Path
from typing import Optional
from rich.console import Console

from .models import FetchConfig
from .fetcher import RSSFetcher
from .markdown_writer import MarkdownWriter
from .rag_integration import RAGIntegration

console = Console()


@click.command()
@click.option(
    '--url', 
    default="https://rss.tempo.co/",
    help='RSS feed URL to fetch from'
)
@click.option(
    '--output-dir', 
    default="articles",
    help='Output directory for markdown files',
    type=click.Path(path_type=Path)
)
@click.option(
    '--max-articles', 
    default=50,
    help='Maximum number of articles to fetch',
    type=int
)
@click.option(
    '--no-content', 
    is_flag=True,
    help='Skip fetching full article content'
)
@click.option(
    '--rate-limit', 
    default=1.0,
    help='Delay between requests in seconds',
    type=float
)
@click.option(
    '--user-agent', 
    default="The Tempo News Fetcher 1.0",
    help='User agent string for requests'
)
@click.option(
    '--rag-app-name',
    default="com.github.openmined.local-rag",
    help='Name of the RAG app in SyftBox'
)
@click.option(
    '--syftbox-config',
    help='Path to SyftBox config file',
    type=click.Path(exists=True, path_type=Path)
)
def main(url: str, output_dir: Path, max_articles: int, no_content: bool, 
         rate_limit: float, user_agent: str, rag_app_name: str,
         syftbox_config: Optional[Path]):
    """Fetch news articles from Tempo RSS feed and save as markdown files."""
    
    console.print(f"[bold blue]Tempo News Fetcher[/bold blue]")
    console.print(f"RSS URL: {url}")
    console.print(f"Output Directory: {output_dir}")
    console.print(f"Max Articles: {max_articles}")
    console.print(f"Fetch Full Content: {not no_content}")
    console.print()
    
    # Create configuration
    config = FetchConfig(
        rss_url=url,
        output_dir=output_dir,
        max_articles=max_articles,
        user_agent=user_agent,
        rate_limit_delay=rate_limit,
        fetch_full_content=not no_content,
        enable_rag=True,
        rag_app_name=rag_app_name,
        syftbox_config_path=syftbox_config
    )
    
    try:
        # Initialize fetcher, writer, and RAG integration
        fetcher = RSSFetcher(config)
        writer = MarkdownWriter(config.output_dir)
        rag_integration = RAGIntegration(config)
        
        # Setup RAG connection (always enabled)
        console.print(f"RAG App Name: {rag_app_name}")
        rag_connected = rag_integration.setup_rag_connection()
        
        # Check if RAG server is recognized and running - skip news fetching if not
        if not rag_connected:
            console.print("[yellow]RAG server not recognized or not running. Skipping news fetching workflow.[/yellow]")
            console.print("[dim]News articles will only be fetched when RAG server is available and tagged as running.[/dim]")
            return
        
        console.print(f"[dim]Articles will be automatically indexed by RAG when saved[/dim]")
        
        # Fetch articles (only if RAG server is available)
        console.print("[bold]Fetching articles...[/bold]")
        articles = fetcher.fetch_articles()
        
        if not articles:
            console.print("[red]No articles found![/red]")
            return
        
        # Write articles to markdown
        console.print(f"\n[bold]Writing {len(articles)} articles to markdown...[/bold]")
        written_files = writer.write_articles(articles)
        
        # RAG integration happens automatically via folder watching
        if rag_integration.is_connected and rag_integration.folder_registered:
            console.print(f"[dim]New articles will be automatically indexed by RAG[/dim]")
        
        if written_files:
            console.print(f"\n[bold green]✓ Successfully processed articles![/bold green]")
            console.print(f"Articles saved to: {output_dir.absolute()}")
        else:
            console.print(f"\n[yellow]No new articles to process.[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option(
    '--output-dir', 
    default="articles",
    help='Articles directory to examine',
    type=click.Path(exists=True, path_type=Path)
)
def stats(output_dir: Path):
    """Show statistics about fetched articles."""
    
    console.print(f"[bold blue]Article Statistics[/bold blue]")
    console.print(f"Directory: {output_dir.absolute()}")
    console.print()
    
    # Count markdown files
    md_files = list(output_dir.glob("*.md"))
    console.print(f"Total articles: {len(md_files)}")
    
    if md_files:
        console.print(f"\nRecent articles:")
        # Sort by modification time to show most recent first
        sorted_files = sorted(md_files, key=lambda f: f.stat().st_mtime, reverse=True)
        for file_path in sorted_files[:10]:  # Show last 10 articles
            console.print(f"  • {file_path.stem}")


@click.group()
def cli():
    """Tempo News RSS Fetcher."""
    pass


cli.add_command(main, name="fetch")
cli.add_command(stats)




if __name__ == "__main__":
    cli()