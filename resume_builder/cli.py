"""
CLI commands for resume building and optimization.
"""
import json
import logging
from pathlib import Path
from typing import Optional
import tempfile

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .models.resume_models import ResumeData, OptimizationRequest, OptimizationResult
from .services.resume_optimizer import ResumeOptimizer
from .services.latex_renderer import LatexRenderer
from .utils.latex_compiler import LatexCompiler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Resume builder and optimization commands")
console = Console()


@app.command()
def build(
    page_id: str = typer.Argument(..., help="Notion page ID of the job to optimize resume for"),
    resume_file: Path = typer.Option(None, "--resume", "-r", help="Path to resume data JSON file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PDF file path"),
    save_tex: bool = typer.Option(False, "--save-tex", help="Save intermediate .tex file"),
    save_report: bool = typer.Option(True, "--save-report/--no-report", help="Save optimization report")
):
    """Build an optimized resume for a specific job posting."""
    try:
        # Import ingestion services
        from ingestion.services.notion_service import get_notion_service
        from ingestion.models.job import JDModel
        
        # 1. Fetch JD data
        with console.status(f"Fetching job data from Notion..."):
            # Check if we have a parsed JD file
            jd_file = Path(f"data/raw/jd_{page_id}.json")
            if jd_file.exists():
                with open(jd_file, 'r') as f:
                    jd_data = json.load(f)
                jd_model = JDModel(**jd_data)
                rprint(f"[green]✓[/green] Loaded parsed JD from cache")
            else:
                rprint(f"[red]✗[/red] No parsed JD found for page {page_id}")
                rprint("Please run 'jobbot ingest pull' first to parse the job description")
                raise typer.Exit(1)
        
        # 2. Load resume data
        if resume_file and resume_file.exists():
            with console.status("Loading resume data..."):
                resume_data = ResumeData.parse_file(resume_file)
                rprint(f"[green]✓[/green] Loaded resume from {resume_file}")
        else:
            # Load default resume data from existing LaTeX file
            rprint("[yellow]![/yellow] No resume file provided, using default data")
            resume_data = _load_default_resume()
        
        # 3. Create optimization request
        optimization_request = OptimizationRequest(
            resume_data=resume_data,
            job_requirements=jd_model.requirements,
            nice_to_have=jd_model.nice_to_have,
            job_skills=jd_model.skills,
            company=jd_model.company,
            title=jd_model.title,
            job_type=jd_model.job_type
        )
        
        # 4. Optimize resume
        with console.status("Optimizing resume with AI..."):
            optimizer = ResumeOptimizer()
            result = optimizer.optimize(optimization_request)
            rprint(f"[green]✓[/green] Resume optimized (relevance score: {result.relevance_score:.2f})")
        
        # 5. Display optimization summary
        _display_optimization_summary(result, jd_model)
        
        # 6. Render LaTeX
        with console.status("Rendering LaTeX template..."):
            renderer = LatexRenderer()
            latex_content = renderer.render(
                resume_data=result.optimized_resume,
                additional_context={
                    "company": jd_model.company,
                    "title": jd_model.title
                }
            )
            
            # Save .tex file if requested
            if save_tex:
                tex_path = output.with_suffix('.tex') if output else Path(f"resume_{page_id}.tex")
                renderer.save_tex_file(latex_content, tex_path)
                rprint(f"[green]✓[/green] Saved LaTeX file to {tex_path}")
            else:
                # Use temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
                    f.write(latex_content)
                    tex_path = Path(f.name)
        
        # 7. Compile PDF
        with console.status("Compiling PDF..."):
            compiler = LatexCompiler()
            output_path = output or Path(f"resume_{jd_model.company.replace(' ', '_')}_{page_id}.pdf")
            pdf_path = compiler.compile(tex_path, output_dir=output_path.parent)
            
            # Rename to desired output name
            if pdf_path.name != output_path.name:
                final_path = output_path.parent / output_path.name
                pdf_path.rename(final_path)
                pdf_path = final_path
            
            rprint(f"[green]✓[/green] Generated PDF: {pdf_path}")
        
        # 8. Save optimization report if requested
        if save_report:
            report_path = output_path.with_suffix('.json') if output else Path(f"resume_report_{page_id}.json")
            report_data = {
                "job": {
                    "company": jd_model.company,
                    "title": jd_model.title,
                    "page_id": page_id
                },
                "optimization": {
                    "relevance_score": result.relevance_score,
                    "keyword_matches": result.keyword_matches,
                    "suggestions": result.suggestions,
                    "report": result.optimization_report
                }
            }
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2)
            rprint(f"[green]✓[/green] Saved optimization report to {report_path}")
        
        # Clean up temp file if not saving .tex
        if not save_tex and tex_path.exists():
            try:
                tex_path.unlink()
                logger.debug(f"Cleaned up temporary LaTeX file: {tex_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {tex_path}: {e}")
        
        rprint(f"\n[bold green]✨ Resume optimization complete![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("build-from-notion")
def build_from_notion(
    status: str = typer.Option("TODO", "--status", "-s", help="Status filter for Notion jobs"),
    limit: int = typer.Option(1, "--limit", "-l", help="Maximum number of jobs to process"),
    resume_file: Path = typer.Option(None, "--resume", "-r", help="Path to resume data JSON file"),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-d", help="Output directory for generated files"),
    save_tex: bool = typer.Option(False, "--save-tex", help="Save intermediate .tex files"),
    save_report: bool = typer.Option(True, "--save-report/--no-report", help="Save optimization reports")
):
    """Fetch TODO jobs from Notion and build optimized resumes for them."""
    try:
        # Import ingestion services
        from ingestion.services.notion_service import get_notion_service
        from ingestion.models.job import JDModel
        from ingestion.parsers.factory import ParserFactory
        
        # 1. Get Notion service and fetch jobs
        with console.status(f"Fetching {status} jobs from Notion..."):
            notion_service = get_notion_service()
            jobs = notion_service.fetch_jobs(status=status, limit=limit)
            
            if not jobs:
                rprint(f"[yellow]![/yellow] No {status} jobs found in Notion database")
                return
            
            rprint(f"[green]✓[/green] Found {len(jobs)} {status} job(s) to process")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Process each job
        for i, job in enumerate(jobs, 1):
            rprint(f"\n[bold]Processing Job {i}/{len(jobs)}: {job.company} - {job.title}[/bold]")
            
            try:
                # Check if we already have parsed JD
                jd_file = Path(f"data/raw/jd_{job.page_id}.json")
                
                if jd_file.exists():
                    with open(jd_file, 'r') as f:
                        jd_data = json.load(f)
                    jd_model = JDModel(**jd_data)
                    rprint(f"[green]✓[/green] Loaded parsed JD from cache")
                else:
                    # Parse the JD first
                    with console.status(f"Parsing job description for {job.company}..."):
                        if not job.jd_link:
                            rprint(f"[red]✗[/red] No JD link found for {job.company} - {job.title}")
                            continue
                        
                        # Update status to Processing
                        notion_service.update_job(job.page_id, status="Processing")
                        
                        # Parse JD using the factory
                        parser = ParserFactory.get_parser(str(job.jd_link))
                        jd_model = parser.parse(str(job.jd_link))
                        
                        # Save parsed JD
                        jd_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(jd_file, 'w') as f:
                            json.dump(jd_model.model_dump(), f, indent=2)
                        
                        rprint(f"[green]✓[/green] Parsed and cached JD")
                
                # Load resume data
                if resume_file and resume_file.exists():
                    resume_data = ResumeData.parse_file(resume_file)
                else:
                    resume_data = _load_default_resume()
                
                # Create optimization request
                optimization_request = OptimizationRequest(
                    resume_data=resume_data,
                    job_requirements=jd_model.requirements,
                    nice_to_have=jd_model.nice_to_have,
                    job_skills=jd_model.skills,
                    company=jd_model.company,
                    title=jd_model.title,
                    job_type=jd_model.job_type
                )
                
                # Optimize resume
                with console.status(f"Optimizing resume for {job.company}..."):
                    optimizer = ResumeOptimizer()
                    result = optimizer.optimize(optimization_request)
                    rprint(f"[green]✓[/green] Resume optimized (relevance: {result.relevance_score:.2%})")
                
                # Generate output filenames
                safe_company = jd_model.company.replace(' ', '_').replace('/', '_')
                base_filename = f"resume_{safe_company}_{job.page_id}"
                
                # Render LaTeX and compile PDF
                with console.status(f"Generating PDF for {job.company}..."):
                    renderer = LatexRenderer()
                    latex_content = renderer.render(
                        resume_data=result.optimized_resume,
                        additional_context={
                            "company": jd_model.company,
                            "title": jd_model.title
                        }
                    )
                    
                    # Handle LaTeX file
                    if save_tex:
                        tex_path = output_dir / f"{base_filename}.tex"
                        renderer.save_tex_file(latex_content, tex_path)
                        rprint(f"[green]✓[/green] Saved LaTeX: {tex_path}")
                    else:
                        # Use temporary file
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
                            f.write(latex_content)
                            tex_path = Path(f.name)
                    
                    # Compile PDF
                    compiler = LatexCompiler()
                    pdf_path = compiler.compile(tex_path, output_dir=output_dir)
                    
                    # Rename to desired output name
                    final_pdf_path = output_dir / f"{base_filename}.pdf"
                    if pdf_path != final_pdf_path:
                        pdf_path.rename(final_pdf_path)
                        pdf_path = final_pdf_path
                    
                    rprint(f"[green]✓[/green] Generated PDF: {pdf_path}")
                
                # Save optimization report
                if save_report:
                    report_path = output_dir / f"{base_filename}_report.json"
                    report_data = {
                        "job": {
                            "company": jd_model.company,
                            "title": jd_model.title,
                            "page_id": job.page_id,
                            "jd_link": str(job.jd_link) if job.jd_link else None
                        },
                        "optimization": {
                            "relevance_score": result.relevance_score,
                            "keyword_matches": result.keyword_matches,
                            "suggestions": result.suggestions,
                            "report": result.optimization_report
                        }
                    }
                    with open(report_path, 'w') as f:
                        json.dump(report_data, f, indent=2)
                    rprint(f"[green]✓[/green] Saved report: {report_path}")
                
                # Clean up temp LaTeX file
                if not save_tex and tex_path.exists():
                    try:
                        tex_path.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file: {e}")
                
                # Update Notion status to Parsed
                notion_service.update_job(job.page_id, status="Parsed")
                
                # Display summary
                _display_optimization_summary(result, jd_model)
                
            except Exception as e:
                error_msg = f"Failed to process {job.company}: {str(e)}"
                rprint(f"[red]✗[/red] {error_msg}")
                logger.error(error_msg, exc_info=True)
                
                # Update Notion with error
                try:
                    notion_service.update_job(job.page_id, status="Error", last_error=str(e))
                except Exception:
                    logger.error(f"Failed to update Notion status for {job.page_id}")
                
                continue
        
        rprint(f"\n[bold green]✨ Processed {len(jobs)} job(s) successfully![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error(f"Build from Notion failed: {e}", exc_info=True)
        raise typer.Exit(1)


@app.command()
def preview(
    page_id: str = typer.Argument(..., help="Notion page ID of the job"),
    resume_file: Optional[Path] = typer.Option(None, "--resume", "-r", help="Path to resume data JSON file")
):
    """Preview optimization suggestions without generating PDF."""
    try:
        # Similar to build but only shows analysis
        from ingestion.models.job import JDModel
        
        # Load JD
        jd_file = Path(f"data/raw/jd_{page_id}.json")
        if not jd_file.exists():
            rprint(f"[red]✗[/red] No parsed JD found for page {page_id}")
            raise typer.Exit(1)
        
        with open(jd_file, 'r') as f:
            jd_model = JDModel(**json.load(f))
        
        # Load resume
        if resume_file and resume_file.exists():
            resume_data = ResumeData.parse_file(resume_file)
        else:
            resume_data = _load_default_resume()
        
        # Create request
        request = OptimizationRequest(
            resume_data=resume_data,
            job_requirements=jd_model.requirements,
            nice_to_have=jd_model.nice_to_have,
            job_skills=jd_model.skills,
            company=jd_model.company,
            title=jd_model.title,
            job_type=jd_model.job_type
        )
        
        # Analyze only (don't optimize bullets)
        optimizer = ResumeOptimizer()
        keyword_matches = optimizer._analyze_keywords(request)
        suggestions = optimizer._generate_suggestions(
            resume_data, 
            jd_model.requirements, 
            keyword_matches
        )
        relevance_score = optimizer._calculate_relevance_score(
            keyword_matches,
            jd_model.skills,
            jd_model.requirements
        )
        
        # Display analysis
        console.print(f"\n[bold]Job Analysis: {jd_model.title} at {jd_model.company}[/bold]\n")
        
        # Keyword matches
        if keyword_matches:
            table = Table(title="Keyword Matches")
            table.add_column("Skill", style="cyan")
            table.add_column("Count", style="green")
            
            for skill, count in sorted(keyword_matches.items(), key=lambda x: x[1], reverse=True):
                table.add_row(skill.title(), str(count))
            
            console.print(table)
        
        # Missing skills
        missing_skills = [s for s in jd_model.skills if s.lower() not in keyword_matches]
        if missing_skills:
            console.print("\n[yellow]Missing Skills:[/yellow]")
            for skill in missing_skills:
                console.print(f"  • {skill}")
        
        # Suggestions
        if suggestions:
            console.print("\n[bold]Optimization Suggestions:[/bold]")
            for i, suggestion in enumerate(suggestions, 1):
                console.print(f"  {i}. {suggestion}")
        
        # Score
        console.print(f"\n[bold]Relevance Score:[/bold] {relevance_score:.2f}/1.00")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _load_default_resume() -> ResumeData:
    """Load default resume data from the existing LaTeX file."""
    # This is a simplified version - in production, you'd parse the LaTeX or have a JSON version
    return ResumeData(
        name="Jiajun (Nick) Huo",
        email="jiajunhuo726@gmail.com",
        phone="267-777-8518",
        github="github.com/nickhuo",
        website="nickhuo.com",
        education=[
            {
                "school": "University of Illinois Urbana Champaign",
                "degree": "Master of Science",
                "field": "Information Science (STEM)",
                "location": "Urbana, IL",
                "start_date": "Aug 2024",
                "end_date": "May 2026",
                "highlights": [
                    "GPA 3.9/4.0 · Applied Machine Learning & Database Systems (both A) · Program #1 in Info Systems (U.S. News)"
                ]
            },
            {
                "school": "Shenzhen University",
                "degree": "Bachelor of Science",
                "field": "Mathematics",
                "location": "Shenzhen",
                "start_date": "Sep 2019",
                "end_date": "Jun 2023",
                "highlights": [
                    "GPA: 3.79/4.50 (Top 10%) · Multiple scholarships · 4 ML modeling wins in supply chain, finance, and computer vision"
                ]
            }
        ],
        experience=[
            {
                "company": "Donut Labs",
                "title": "Software Engineer Intern",
                "location": "",
                "start_date": "Jun 2025",
                "end_date": "Aug 2025",
                "description": "Agentic Browser Backed by Sequoia Capital",
                "bullets": [
                    "Engineered GPT-seeded ANN sentiment pipeline parsing 50k tweets/day, slashing inference cost 19× to 0.003¢ per tweet",
                    "Implemented prompt-tagged Pinecone vector DB, labeled 82% tweets and cut GPT calls 80% with equal accuracy",
                    "Architected 18-endpoint RESTful FastAPI microservice for LLM inference & content ops: QPS ↑3× with P95 220ms; auto-Swagger cut frontend integration 66%, and Pydantic validation trimmed 4xx/5xx errors 40%",
                    "Rolled out LangSmith observability across agent stack; engineered a closed-loop LLM evaluation harness with automated BLEU/BERTScore gates plus human adjudication, achieving 100% PR coverage and surfacing regressions within 24h."
                ],
                "technologies": ["Python", "FastAPI", "Pinecone", "LangSmith", "GPT"]
            },
            {
                "company": "Sonic SVM",
                "title": "Software Engineer - Data Solutions",
                "location": "",
                "start_date": "Mar 2023",
                "end_date": "Jul 2024",
                "description": "Bitkraft-backed SaaS for 50+ Game Studios, $100M valuation",
                "bullets": [
                    "Led the development of data governance system, drove 3 C-level strategic decisions with quant insights, report to CPO",
                    "Scaled data sources by 2x and architected ETL pipelines on GCP, ensuring 99.9% accuracy with optimized SQL queries",
                    "Automated API log extraction workflow from PostgreSQL to BigQuery using Airflow, reducing 43.2% processing time",
                    "Built a Pub/Sub → Dataflow streaming pipeline, surfacing in-game KPIs to BI dashboards with <5s latency",
                    "Launched Looker Studio dashboards consumed by 7 members; cut insight turnaround from 2 days → 30 min"
                ],
                "technologies": ["GCP", "BigQuery", "Airflow", "PostgreSQL", "Looker"]
            }
        ],
        projects=[
            {
                "name": "ReplicaGenie",
                "bullets": [
                    "Architected 4-service LLM platform; modular microservices allow independent scaling, isolated failures & fast rollouts",
                    "Automated LinkedIn/GitHub scraping via Selenium on AWS Lambda; parsed & stored structured data in MongoDB",
                    "Built MongoDB → RabbitMQ CDC stream pushing changes to feature store in <1s, enabling real-time personalization",
                    "Delivered 4-bit LoRA fine-tuning on SageMaker, trimming GPU training cost 77% and guaranteeing reproducibility",
                    "Integrated Opik tracing and auto-eval, detecting hallucination & relevance and lifting LangChain-SageMaker reliability",
                    "Orchestrated 6-service Docker stack-MongoDB replica, RabbitMQ, Qdrant—delivering production-ready RAG"
                ],
                "technologies": ["Python", "MongoDB", "RabbitMQ", "AWS", "Docker", "LangChain"]
            },
            {
                "name": "BiteMatch",
                "bullets": [
                    "Led a 4-member Agile squad, grooming backlog and delivering on 2-week sprints with 100% sprint goal hit rate",
                    "Top 10% in course. Developed smart recipe app to personalize meal choices using React, Node.js, and MySQL",
                    "Created RESTful API with 12+ endpoints handling user auth, recipe CRUD, video search, and review system",
                    "Reduced YouTube API calls by caching videos in DB and using a quota-aware fetch logic to avoid exceeding limits",
                    "Containerized services with Docker & GitHub Actions; push-to-prod cycle shrank from 20 min to <5 min"
                ],
                "technologies": ["React", "Node.js", "MySQL", "Docker", "GitHub Actions"]
            }
        ],
        skills={
            "Programming": ["Python", "TypeScript", "Go", "JavaScript", "SQL", "Zsh & Bash", "Node.js", "React"],
            "Frameworks": ["React", "Next.js", "Jenkins", "Tailwind CSS", "Vite", "Node.js", "Django", "Express.js", "MongoDB", "Redis"],
            "DevOps": ["AWS", "Docker", "Terraform", "GitHub Actions", "Vercel", "Airflow", "Linux/Unix", "Git"]
        },
        footnote="Actively seeking Fall 2025 intern opportunities. Willing to relocate. Authorized to work in the US"
    )


def _display_optimization_summary(result: OptimizationResult, jd_model):
    """Display a summary of the optimization results."""
    console.print("\n[bold]Optimization Summary[/bold]\n")
    
    # Create summary table
    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Company", jd_model.company)
    table.add_row("Position", jd_model.title)
    table.add_row("Relevance Score", f"{result.relevance_score:.2%}")
    table.add_row("Matched Keywords", str(len(result.keyword_matches)))
    table.add_row("Total Keywords", str(len(jd_model.skills)))
    
    console.print(table)
    
    # Show top suggestions
    if result.suggestions:
        console.print("\n[yellow]Top Suggestions:[/yellow]")
        for i, suggestion in enumerate(result.suggestions[:3], 1):
            console.print(f"  {i}. {suggestion}")


if __name__ == "__main__":
    app()

