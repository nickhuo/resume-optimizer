# Semi-Apply: Intelligent Job Application Automation

A semi-automated job application pipeline for 2025 North American Software Development Engineer (SDE), AI Engineer, Data Science (DS), and Data Engineering (DE) positions.

## 🎯 Project Overview

Semi-Apply streamlines the job application process by combining intelligent automation with human oversight. The system integrates multiple layers of technology to maximize efficiency while maintaining quality and compliance.

**Key Features:**
- **Centralized Data Management**: Notion database for job descriptions and application tracking
- **Intelligent Automation**: Playwright scripts handle 80%+ of form filling automatically
- **AI-Powered Content**: OpenAI API integration for resume-job matching, keyword optimization, and bullet point customization
- **Comprehensive Monitoring**: Complete audit trail with Notion logging, screenshots, and error tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Notion API Token
- OpenAI API Key (required for Phase 1+)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/semi-apply.git
cd semi-apply
```

2. **Set up virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env file with your Notion Token and Database ID
```

### Basic Usage

#### View Configuration
```bash
python jobbot.py ingest config
```

#### List Pending Jobs
```bash
python jobbot.py ingest list --status TODO
```

#### Detect Job Site Type
```bash
python jobbot.py ingest detect "https://boards.greenhouse.io/company/jobs/123456"
```

#### Test All Components
```bash
python jobbot.py ingest test
```

## 📁 Project Architecture

```
semi-apply/
├── ingestion/              # Data collection module
│   ├── cli.py             # Command-line interface
│   ├── settings.py        # Configuration management
│   ├── models/            # Data models
│   │   └── job.py         # Job data model
│   ├── services/          # Service layer
│   │   └── notion_service.py  # Notion API wrapper
│   ├── parsers/           # Site parsers (planned)
│   └── utils/             # Utility functions
│       └── site_detector.py   # Site detection utility
├── data/                  # Data storage
│   └── raw/              # Raw job description JSON files
├── logs/                  # Application logs
├── jobbot.py             # Main CLI entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## ⚙️ Configuration

### Notion Setup

1. **Create Notion Integration**: Visit https://www.notion.so/my-integrations
2. **Get Integration Token**: Copy the token from your integration
3. **Share Database**: Add your integration to the target database
4. **Get Database ID**: Extract from your Notion database URL

### Environment Variables

```env
# Notion Configuration
NOTION_TOKEN=your_notion_integration_token
DATABASE_ID=your_notion_database_id

# Application Settings
LOG_LEVEL=INFO
REQUEST_TIMEOUT=10
```

## 📊 Notion Database Schema

| Field | Description | Type |
|-------|-------------|------|
| JD_ID | Unique job identifier in database | Number |
| JD_Link | Original job posting URL | URL |
| Company | Company name | Text |
| Title | Job title | Text |
| Status | Application status (TODO/Processing/Parsed/Error/Filling/Submitted/Failed) | Select |
| LLM_Notes | AI-generated insights and recommendations | Rich Text |
| Last_Error | Most recent error message | Rich Text |
| My_Notes | Personal notes and observations | Rich Text |
| Created_Time | Record creation timestamp | Date |

## 🛠️ Development Roadmap

### Phase 0: Foundation ✅
- [x] Configuration management (settings.py)
- [x] Notion SDK integration
- [x] CLI framework
- [x] Site detection utility

### Phase 1: Content Intelligence MVP 🚧
- [ ] Job description parsers (Greenhouse, Workday)
- [ ] GPT service integration
- [ ] Resume template rendering
- [ ] PDF generation pipeline

### Phase 2: Automated Form Filling 📋
- [ ] Playwright automation framework
- [ ] CSS selector mapping configuration
- [ ] Fallback chain implementation
- [ ] Cross-platform browser support

### Phase 3: Reliability & Notifications 🔔
- [ ] LLM-powered selector self-healing
- [ ] Exception handling with screenshots
- [ ] Notification system integration
- [ ] CI/CD pipeline setup

## 🔒 Compliance & Ethics

**Important**: This tool is designed for educational and personal use only. Users must:
- Respect all job site terms of service
- Maintain reasonable application rates
- Provide accurate information in all applications
- Follow applicable employment laws and regulations

## 🤝 Contributing

We welcome contributions to improve Semi-Apply! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure compatibility with Python 3.11+

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Nick Huo**

For questions, suggestions, or collaboration opportunities, please open an issue or reach out directly.

---

**Disclaimer**: This tool is for educational and personal use only. Please respect all job site terms of service and applicable laws when using this software.
