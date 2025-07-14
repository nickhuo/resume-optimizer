# LLM-Enhanced Job Description Parsing

This module now supports LLM-based parsing for more robust extraction of job requirements and nice-to-have items.

## Features

- **Intelligent Extraction**: Uses OpenAI's GPT-4o-mini model to accurately identify and extract requirements
- **Original Text Preservation**: The LLM is instructed to preserve the exact wording from job descriptions
- **Automatic Fallback**: If LLM parsing fails or returns empty results, the system falls back to traditional rule-based parsing
- **Section Recognition**: Automatically distinguishes between requirements, nice-to-have items, and benefits

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

## Usage

### Enable LLM parsing (default):
```python
from ingestion.parsers.greenhouse import GreenhouseParser
from ingestion.parsers.workday import WorkdayParser

# LLM is enabled by default
parser = GreenhouseParser()  # or WorkdayParser()
result = parser.parse(url)
```

### Disable LLM parsing:
```python
# Use traditional parsing only
parser = GreenhouseParser(use_llm=False)
result = parser.parse(url)
```

## How It Works

1. **Description Extraction**: The parser first extracts the job description text from the HTML
2. **LLM Processing**: If LLM is enabled, the description is sent to GPT-4o-mini with specific instructions to:
   - Identify requirements (mandatory qualifications)
   - Identify nice-to-have items (preferred qualifications)
   - Preserve exact wording
   - Ignore benefits and perks
3. **Fallback Logic**: If LLM fails or returns no results, traditional pattern-based parsing is used

## Advantages of LLM Parsing

- **Better Context Understanding**: LLM can understand context and implicit requirements
- **Format Agnostic**: Works with various formatting styles (bullets, semicolons, paragraphs)
- **Section Detection**: Better at identifying section boundaries
- **Reduced False Positives**: Less likely to misclassify benefits as requirements

## Cost Considerations

- Uses GPT-4o-mini model for cost efficiency
- Typical job description parsing costs < $0.01 per request
- Consider caching results for duplicate job postings

## Testing

Run the test script to see LLM parsing in action:
```bash
python test_llm_parser.py
```

This will demonstrate:
1. LLM parsing with Greenhouse format
2. LLM parsing with Workday format
3. Traditional parsing (with LLM disabled)
