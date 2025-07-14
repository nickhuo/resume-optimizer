"""
CLI commands for the ingestion module.
"""
import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

import json
from pathlib import Path

from .settings import Settings
from .services.notion_service import get_notion_service
from .utils.site_detector import detect_site, JobSite
from .parsers.factory import ParserFactory
from .parsers.base import ParserException

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
    status: Optional[str] = typer.Option(None, help="Filter by job status (TODO, Processing, etc.). If not specified, shows all jobs."),
    limit: int = typer.Option(20, help="Maximum number of jobs to list")
):
    """List jobs from Notion database."""
    try:
        # Validate configuration
        Settings.validate()
        
        # Fetch jobs
        status_msg = f"status '{status}'" if status else "all statuses"
        with console.status(f"Fetching jobs with {status_msg}..."):
            notion = get_notion_service()
            jobs = notion.fetch_jobs(status=status, limit=limit)
        
        if not jobs:
            rprint(f"No jobs found with {status_msg}")
            return
        
        # Create table
        title = f"Jobs with status: {status}" if status else "All Jobs"
        table = Table(title=title)
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


@app.command()
def parse(
    url: str,
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path for JSON result"),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Pretty print JSON output"),
    debug: bool = typer.Option(False, "--debug", help="Save extracted content to debug file")
):
    """Parse a job posting URL and extract structured data using universal parser."""
    try:
        # Parse the job posting
        with console.status(f"Parsing job posting from {url}..."):
            parser = ParserFactory.get_parser(url)
            
            # For debug mode, save extracted content
            if debug:
                html = parser.fetch_page(url)
                content = parser._extract_clean_content(html)
                
                debug_file = Path("debug_content.txt")
                debug_file.write_text(content, encoding='utf-8')
                rprint(f"[blue]💾 Saved extracted content to {debug_file}[/blue]")
            
            jd_model = parser.parse(url)
        
        # Prepare JSON output
        jd_dict = jd_model.model_dump(exclude_none=True)
        
        # Display results
        rprint("\n[bold green]✅ Successfully parsed job posting![/bold green]\n")
        
        # Show summary
        table = Table(title="Job Details", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Company", jd_dict.get("company", "N/A"))
        table.add_row("Title", jd_dict.get("title", "N/A"))
        table.add_row("Location", jd_dict.get("location", "N/A"))
        table.add_row("Job Type", jd_dict.get("job_type", "N/A"))
        table.add_row("Requirements", str(len(jd_dict.get("requirements", []))))
        table.add_row("Nice to Have", str(len(jd_dict.get("nice_to_have", []))))
        table.add_row("Responsibilities", str(len(jd_dict.get("responsibilities", []))))
        table.add_row("Skills Found", str(len(jd_dict.get("skills", []))))
        
        console.print(table)
        
        # Show extracted skills
        if jd_dict.get("skills"):
            rprint("\n[bold]Extracted Skills/Keywords:[/bold]")
            for skill in jd_dict["skills"]:
                rprint(f"  • {skill}")
        
        # Save to file if requested
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            indent = 2 if pretty else None
            output.write_text(json.dumps(jd_dict, indent=indent, ensure_ascii=False))
            rprint(f"\n[green]💾 Saved to {output}[/green]")
        
    except ParserException as e:
        rprint(f"[red]❌ Parser error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def pull(
    page_id: str,
    save: bool = typer.Option(False, "--save", "-s", help="Save parsed data to file"),
    update_notion: bool = typer.Option(True, "--update/--no-update", help="Update Notion status")
):
    """Pull and parse a job from Notion by page ID."""
    try:
        # Validate configuration
        Settings.validate()
        
        # Fetch job from Notion
        with console.status(f"Fetching job {page_id} from Notion..."):
            notion = get_notion_service()
            jobs = notion.fetch_jobs(page_id=page_id)
            
            if not jobs:
                rprint(f"[red]❌ Job with ID {page_id} not found[/red]")
                raise typer.Exit(1)
            
            job = jobs[0]
        
        if not job.jd_link:
            rprint(f"[red]❌ Job has no JD link[/red]")
            raise typer.Exit(1)
        
        # Update status to Processing
        if update_notion:
            notion.update_job(page_id, status="Processing")
        
        # Parse the job posting
        url = str(job.jd_link)
        with console.status(f"Parsing job posting from {url}..."):
            parser = ParserFactory.get_parser(url)
            jd_model = parser.parse(url)
        
        # Display results
        rprint(f"\n[bold green]✅ Successfully parsed job from {job.company}![/bold green]\n")
        
        # Show summary
        jd_dict = jd_model.model_dump(exclude_none=True)
        table = Table(title="Parsed Job Details", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Page ID", page_id[:8])
        table.add_row("Company", jd_dict.get("company", "N/A"))
        table.add_row("Title", jd_dict.get("title", "N/A"))
        table.add_row("Location", jd_dict.get("location", "N/A"))
        table.add_row("Job Type", jd_dict.get("job_type", "N/A"))
        table.add_row("Requirements", str(len(jd_dict.get("requirements", []))))
        table.add_row("Nice to Have", str(len(jd_dict.get("nice_to_have", []))))
        table.add_row("Responsibilities", str(len(jd_dict.get("responsibilities", []))))
        table.add_row("Skills Found", str(len(jd_dict.get("skills", []))))
        
        console.print(table)
        
        # Save to file if requested
        if save:
            # Create data directory if it doesn't exist
            data_dir = Path("data/raw")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save JSON file
            filename = f"jd_{page_id}.json"
            filepath = data_dir / filename
            filepath.write_text(json.dumps(jd_dict, indent=2, ensure_ascii=False))
            rprint(f"\n[green]💾 Saved to {filepath}[/green]")
        
        # Update Notion status
        if update_notion:
            notion.update_job(page_id, status="Parsed")
            rprint(f"\n[green]✅ Updated Notion status to 'Parsed'[/green]")
        
    except ParserException as e:
        if update_notion:
            try:
                notion = get_notion_service()
                notion.update_job(page_id, status="Error", last_error=str(e))
            except:
                pass  # Don't fail if we can't update Notion
        rprint(f"[red]❌ Parser error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        if update_notion:
            try:
                notion = get_notion_service()
                notion.update_job(page_id, status="Error", last_error=str(e))
            except:
                pass  # Don't fail if we can't update Notion
        rprint(f"[red]❌ Unexpected error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
