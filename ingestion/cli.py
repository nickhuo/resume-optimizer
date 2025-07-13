"""
CLI commands for the ingestion module.
"""
import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .settings import Settings
from .services.notion_service import get_notion_service
from .utils.site_detector import detect_site, JobSite

# Setup logging
logging.basicConfig(
    level=getattr(logging, Settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = typer.Typer(help="Job ingestion commands")
console = Console()


@app.command()
def config():
    """Show current configuration."""
    Settings.print_config()
    try:
        Settings.validate()
        rprint("\n✅ Configuration is valid!")
    except ValueError as e:
        rprint(f"\n❌ {e}")
        raise typer.Exit(1)


@app.command()
def list(
    status: str = typer.Option("TODO", help="Filter by job status"),
    limit: int = typer.Option(20, help="Maximum number of jobs to list")
):
    """List jobs from Notion database."""
    try:
        # Validate configuration
        Settings.validate()
        
        # Fetch jobs
        with console.status(f"Fetching jobs with status '{status}'..."):
            notion = get_notion_service()
            jobs = notion.fetch_jobs(status=status, limit=limit)
        
        if not jobs:
            rprint(f"No jobs found with status '{status}'")
            return
        
        # Create table
        table = Table(title=f"Jobs with status: {status}")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Company", style="magenta")
        table.add_column("Title", style="green")
        table.add_column("Site", style="yellow")
        table.add_column("URL", style="blue", overflow="fold")
        
        # Add rows
        for job in jobs:
            site = detect_site(str(job.jd_link))
            site_name = site.value.upper() if site != JobSite.UNKNOWN else "❓"
            
            table.add_row(
                job.page_id[:8],
                job.company,
                job.title,
                site_name,
                str(job.jd_link)
            )
        
        console.print(table)
        rprint(f"\nTotal: {len(jobs)} jobs")
        
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def detect(url: str):
    """Detect job site from URL."""
    site = detect_site(url)
    
    if site == JobSite.UNKNOWN:
        rprint(f"[yellow]⚠️  Unknown job site for URL:[/yellow] {url}")
    else:
        rprint(f"[green]✅ Detected site:[/green] {site.value.upper()}")
        rprint(f"[blue]Parser class:[/blue] {site.value.capitalize()}Parser")


@app.command()
def test():
    """Test ingestion components."""
    console.print("[bold]Testing Ingestion Components[/bold]\n")
    
    # Test 1: Configuration
    console.print("1. Testing configuration...")
    try:
        Settings.validate()
        rprint("   [green]✅ Configuration valid[/green]")
    except ValueError as e:
        rprint(f"   [red]❌ Configuration error: {e}[/red]")
        return
    
    # Test 2: Notion connection
    console.print("\n2. Testing Notion connection...")
    try:
        notion = get_notion_service()
        jobs = notion.fetch_jobs(limit=1)
        rprint(f"   [green]✅ Connected to Notion (found {len(jobs)} jobs)[/green]")
    except Exception as e:
        rprint(f"   [red]❌ Notion error: {e}[/red]")
        return
    
    # Test 3: Site detection
    console.print("\n3. Testing site detection...")
    test_urls = [
        ("https://boards.greenhouse.io/company/jobs/123", JobSite.GREENHOUSE),
        ("https://company.wd5.myworkdayjobs.com/job/123", JobSite.WORKDAY),
        ("https://jobs.lever.co/company/123", JobSite.LEVER),
        ("https://www.linkedin.com/jobs/view/123", JobSite.LINKEDIN),
        ("https://example.com/careers", JobSite.UNKNOWN),
    ]
    
    all_passed = True
    for url, expected in test_urls:
        detected = detect_site(url)
        if detected == expected:
            rprint(f"   [green]✅ {url[:50]}... → {detected.value}[/green]")
        else:
            rprint(f"   [red]❌ {url[:50]}... → {detected.value} (expected {expected.value})[/red]")
            all_passed = False
    
    if all_passed:
        console.print("\n[bold green]All tests passed! 🎉[/bold green]")
    else:
        console.print("\n[bold red]Some tests failed![/bold red]")


if __name__ == "__main__":
    app()
