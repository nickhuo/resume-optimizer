# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Semi-Apply is a semi-automated job application pipeline for North American tech positions (SDE/AI/DS/DE). The system integrates Notion as a unified data source, uses Playwright for 80%+ form automation, leverages OpenAI for intelligent content matching (JD⇆resume optimization), and includes comprehensive logging with screenshot/error capture back to Notion.

## Development Commands

### Setup and Environment
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Core CLI Commands

The main entry point is `jobbot` (or `python jobbot.py`):

```bash
# Show configuration and validate settings
python jobbot.py ingest config

# List jobs from Notion with various filters
python jobbot.py ingest list --status TODO --limit 10
python jobbot.py ingest list  # List all jobs

# Parse job descriptions (saves to data/raw/)
python jobbot.py ingest parse "https://boards.greenhouse.io/company/jobs/123" --output jd.json --debug
python jobbot.py ingest pull <notion-page-id> --save --update

# Site detection utility
python jobbot.py ingest detect "https://boards.greenhouse.io/company/jobs/123456"

# Test all ingestion components
python jobbot.py ingest test

# Resume building and optimization
python jobbot.py resume build <notion-page-id> --output resume.pdf --save-tex
python jobbot.py resume build-from-notion --status TODO --limit 5 --output-dir ./resumes
python jobbot.py resume preview <notion-page-id>  # Preview optimization without generating PDF

# Full application workflow (planned)
python jobbot.py apply <notion-page-id> --dry-run
python jobbot.py batch --limit 10 --status TODO
```

### Testing and Quality

```bash
# Run tests (when implemented)
pytest

# Code formatting and linting
black .
isort .
flake8 .
```

## Architecture Overview

### Core Modules

**jobbot.py**: Main CLI orchestrator that ties together ingestion and resume building workflows

**ingestion/**: Job data collection and parsing pipeline
- `models/job.py`: JobRow (Notion) and JDModel (parsed) data structures
- `services/notion_service.py`: Notion API integration for CRUD operations
- `parsers/`: Website-specific and universal LLM-based content extraction
- `utils/site_detector.py`: Auto-detect job sites (Greenhouse, Workday, Lever, LinkedIn)

**resume_builder/**: LaTeX-based resume generation with AI optimization
- `models/resume_models.py`: ResumeData, OptimizationRequest, OptimizationResult structures
- `services/resume_optimizer.py`: OpenAI-powered resume optimization for specific jobs
- `services/latex_renderer.py`: Jinja2 LaTeX template rendering
- `utils/latex_compiler.py`: PDF compilation from LaTeX source

### Data Flow

1. **Job Collection**: Browser extension → Notion database (JD links + metadata)
2. **Content Parsing**: CLI pulls from Notion → Universal LLM parser → Structured JDModel → Cache in data/raw/
3. **Resume Optimization**: JDModel + base resume → OpenAI optimization → Personalized bullets/keywords
4. **PDF Generation**: Optimized resume data → LaTeX template → Compiled PDF
5. **Form Automation**: (Future) Playwright automation → Form filling → Status updates to Notion

### Key Design Patterns

**Factory Pattern**: `ParserFactory.get_parser(url)` auto-selects appropriate parser based on URL
**Command Pattern**: CLI structured with Typer sub-commands for clean separation
**Data Models**: Pydantic models throughout for validation and serialization
**Templating**: Jinja2 for LaTeX resume generation with context injection
**Error Handling**: Comprehensive exception handling with Notion status updates

## Configuration

### Required Environment Variables (.env)
```bash
# Notion Configuration
NOTION_TOKEN=your_notion_integration_token
DATABASE_ID=your_notion_database_id

# OpenAI Configuration  
OPENAI_API_KEY=your_openai_api_key

# Application Settings
LOG_LEVEL=INFO
REQUEST_TIMEOUT=10
```

### Notion Database Schema
The system expects a Notion database with these properties:
- `JD_ID` (Number): Auto-incrementing job ID
- `JD_Link` (URL): Original job posting URL
- `Company` (Text): Company name
- `Title` (Text): Position title
- `Status` (Select): TODO/Processing/Parsed/Error/Filling/Submitted/Failed
- `LLM_Notes` (Rich Text): AI-generated insights
- `Last_Error` (Rich Text): Error tracking
- `My_Notes` (Rich Text): Personal notes
- `Created_Time` (Date): Record creation timestamp

## Development Guidelines

### File Organization
- Keep parsers in `ingestion/parsers/` with consistent interface via `BaseParser`
- Resume components belong in `resume_builder/` with clear service/model separation
- Configuration centralized in `ingestion/settings.py` with environment validation
- Data artifacts go in `data/raw/` for caching and debugging

### Error Handling Strategy
- Always update Notion status on failures with error details in `Last_Error` field
- Use ParserException for parsing-specific errors with context
- Comprehensive logging throughout with structured log levels
- Save debug artifacts (HTML extracts, screenshots) for troubleshooting

### LLM Integration Patterns
- Universal parser uses GPT-4o-mini for cost-effective content extraction
- Resume optimizer uses structured prompts with JSON response format
- Implement retries and fallback strategies for API failures
- Cache LLM results where possible to reduce costs

### Testing Approach
- Use `jobbot ingest test` for component validation
- Test with real job posting URLs for parser validation
- Validate against Notion database connectivity
- Verify LaTeX compilation and PDF generation end-to-end

## Common Workflows

**Parse and optimize for a single job**:
```bash
python jobbot.py ingest pull <page-id> --save
python jobbot.py resume build <page-id> --output-dir ./output
```

**Batch process TODO jobs**:
```bash
python jobbot.py resume build-from-notion --status TODO --limit 5 --output-dir ./batch_resumes
```

**Debug parsing issues**:
```bash
python jobbot.py ingest parse <url> --debug  # Saves extracted content
python jobbot.py ingest detect <url>  # Check site detection
```

**Preview optimization without PDF generation**:
```bash
python jobbot.py resume preview <page-id>  # Shows keyword analysis and suggestions
```