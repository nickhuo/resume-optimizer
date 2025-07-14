#!/usr/bin/env python3
"""
Main CLI entry point for the Semi-Apply job automation tool.
"""
import typer
from rich import print as rprint


from ingestion.cli import app as ingestion_app
from resume_builder.cli import app as resume_app

# Create main app
app = typer.Typer(
    name="jobbot",
    help="Semi-automated job application pipeline for North American tech positions.",
    no_args_is_help=True
)

# Add sub-commands
app.add_typer(ingestion_app, name="ingest", help="Job ingestion commands")
app.add_typer(resume_app, name="resume", help="Resume building and optimization commands")


@app.command()
def version():
    """Show version information."""
    rprint("[bold]Semi-Apply Job Bot[/bold]")
    rprint("Version: 0.1.0")
    rprint("Python: 3.11+")


@app.command()
def apply(
    notion_page_id: str,
    dry_run: bool = typer.Option(False, "--dry-run", help="Print JD without applying")
):
    """Apply to a job from Notion database."""
    if dry_run:
        rprint(f"[yellow]Dry run mode - would apply to job: {notion_page_id}[/yellow]")
        # TODO: Implement full application flow
    else:
        rprint(f"[red]Full application flow not yet implemented[/red]")
        raise typer.Exit(1)


@app.command()
def batch(
    limit: int = typer.Option(10, help="Maximum number of jobs to process"),
    status: str = typer.Option("TODO", help="Filter by job status")
):
    """Batch process multiple job applications."""
    rprint(f"[yellow]Batch processing {limit} jobs with status '{status}'[/yellow]")
    rprint("[red]Batch processing not yet implemented[/red]")
    raise typer.Exit(1)


def main():
    """Entry point for the jobbot CLI."""
    app()


if __name__ == "__main__":
    main()
