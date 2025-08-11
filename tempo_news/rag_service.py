"""RAG service detection and integration using syft-core."""

import time
from pathlib import Path
from typing import Optional
from rich.console import Console

from syft_core import Client

console = Console()


class RAGServiceDetector:
    """Detects and connects to RAG service using syft-core."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize RAG service detector.
        
        Args:
            config_path: Path to SyftBox config. If None, uses default location.
        """
        self.config_path = config_path or Path.home() / ".syftbox" / "config.json"
        self.rag_service_url: Optional[str] = None
        self.rag_service_port: Optional[str] = None
        self.rag_service_pid: Optional[str] = None
        self.client: Optional[Client] = None
    
    def detect_rag_service(self, 
                          app_name: str = "com.github.openmined.local-rag",
                          max_wait_time: int = 30) -> bool:
        """Detect if RAG service is running and get its URL.
        
        Args:
            app_name: Name of the RAG app in SyftBox apps directory
            max_wait_time: Maximum time to wait for service detection (seconds)
            
        Returns:
            True if service is detected and URL is set, False otherwise
        """
        try:
            # Load syft-core client
            if not self.config_path.exists():
                console.print(f"[yellow]Warning: SyftBox config.json not found at {self.config_path}[/yellow]")
                return False
            
            console.print(f"[blue]Loading SyftBox client from: {self.config_path}[/blue]")
            self.client = Client.load(self.config_path)
            
            # Get app folder path following SyftBox structure
            app_folder = self.client.workspace.data_dir / "apps" / app_name
            app_pid_file = app_folder / "data" / "app.pid"
            app_port_file = app_folder / "data" / "app.port"
            
            console.print(f"[blue]Looking for RAG service at: {app_folder}[/blue]")
            
            if not app_folder.exists():
                console.print(f"[yellow]RAG app directory not found: {app_folder}[/yellow]")
                return False
            
            # Wait for service to be ready (similar to spawn_services.py lines 289-304)
            start_time = time.time()
            console.print(f"[blue]Waiting for RAG service (max {max_wait_time}s)...[/blue]")
            
            while time.time() - start_time < max_wait_time:
                if app_port_file.exists() and app_pid_file.exists():
                    try:
                        # Read port and PID
                        self.rag_service_port = app_port_file.read_text().strip()
                        self.rag_service_pid = app_pid_file.read_text().strip()
                        
                        # Construct service URL
                        self.rag_service_url = f"http://localhost:{self.rag_service_port}"
                        
                        console.print(f"[green]✓ RAG service detected![/green]")
                        console.print(f"  URL: {self.rag_service_url}")
                        console.print(f"  PID: {self.rag_service_pid}")
                        
                        return True
                        
                    except Exception as e:
                        console.print(f"[red]Error reading service metadata: {e}[/red]")
                        return False
                
                time.sleep(1)
            
            console.print(f"[yellow]RAG service not detected within {max_wait_time} seconds[/yellow]")
            return False
            
        except Exception as e:
            console.print(f"[red]Error detecting RAG service: {e}[/red]")
            return False
    
    def is_service_available(self) -> bool:
        """Check if RAG service URL is available."""
        return self.rag_service_url is not None
    
    def get_service_url(self) -> Optional[str]:
        """Get the RAG service URL."""
        return self.rag_service_url
    
    def verify_service_health(self) -> bool:
        """Verify RAG service is responding (basic health check)."""
        if not self.rag_service_url:
            return False
        
        try:
            import requests
            response = requests.get(f"{self.rag_service_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            console.print(f"[yellow]RAG service health check failed: {e}[/yellow]")
            return False
    
    def get_service_info(self) -> dict:
        """Get service information dictionary."""
        return {
            "url": self.rag_service_url,
            "port": self.rag_service_port,
            "pid": self.rag_service_pid,
            "available": self.is_service_available(),
            "healthy": self.verify_service_health() if self.is_service_available() else False
        }