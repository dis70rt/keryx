# Keryx

AI-powered LinkedIn outreach orchestration pipeline. Scrape profile. Match angle. Draft connection note + DM. Update Google Sheets.

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Version](https://img.shields.io/badge/version-0.2.0-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)

## Table of Contents
- [Project Name and Description](#project-name-and-description)
- [Technology Stack](#technology-stack)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Project Name and Description

**Keryx**: Production-grade B2B outreach automation.
Automate LinkedIn research. Extract profile Data. Cross-reference personal resume/projects context. Generate hyper-personalized copy. Track results in Google Sheets.

## Technology Stack

- **Python**: `3.12`
- **Dependency Manager**: `uv`
- **Orchestration**: `LangGraph`, `LangChain`
- **Web Automation**: `playwright`, `playwright-stealth`
- **Configuration & Validation**: `pydantic`, `pydantic-settings`
- **Database Tracking**: `SQLite 3`
- **Integration**: `gspread`, `oauth2client`
- **Containerization**: `Docker`, `Docker Compose`
- **Local LLM**: `Ollama` (Gemma)

## Project Architecture

Pipeline highly decoupled.

1. **State Manager (`src/core/state.py`)**: SQLite cache (`data/cache.db`). Track processed URLs. Resume on crash. Prevent duplicate outreach.
2. **Scraper (`src/tools/scraper.py`)**: Playwright stealth automation. Fetch raw DOM text (Profile + Company). Bypass anti-bot.
3. **LangGraph Workflow (`src/core/workflow.py`)**: 
    - `Extractor`: Parse DOM to structured JSON.
    - `Matchmaker`: Find best outreach angle. Use resume + projects context.
    - `Copywriter`: Draft max 300 char connection note + ~150 word DM.
    - `Reviewer`: Quality check. Reject cliché AI text ("delve", "synergy").
4. **Google Sheets Controller (`src/tools/sheets.py`)**: Append-only 3-tab system. Batch update `Targets`, `Connection Notes`, `DM Messages`. Avoid rate limits.
5. **Local LLM Engine**: Docker Compose embeds `Ollama` instance. Auto-pull Gemma model on startup.

## Getting Started

One-click setup for macOS/Linux/Windows.

### Prerequisites
- Docker Desktop
- LinkedIn session cookies (`data/auth_state.json`) -> create manually or via Playwright script.
- Google Service Account creds (`data/google_credentials.json`)

### Setup Config
1. Copy env config:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env`. API keys stay out of git.
3. Add Google Service Account JSON to `data/google_credentials.json`.
4. Create tabs in Google Sheets: `Targets`, `Connection Notes`, `DM Messages`. 
5. Add target LinkedIn URLs in `Targets` tab (Column A = LinkedIn URL, Column D = Status).
6. Provide sender context:
   - `data/resume.tex` (LaTeX format resume)
   - `data/projects.json` (Key-value map of projects)

### Run Pipeline
Docker Compose build multi-stage agent + pull Ollama Gemma model auto. 

```bash
docker compose up --build -d
```

View logs:
```bash
docker compose logs -f agent
```

Stop pipeline:
```bash
docker compose down
```

## Project Structure

```text
keryx/
├── pipeline.py                # Main orchestration entrypoint
├── pyproject.toml             # uv/hatchling deps
├── Dockerfile                 # Multi-stage image build
├── docker-compose.yml         # Agent + Ollama infrastructure 
├── data/                      # Local data volume
│   ├── resume.tex             # LaTeX resume
│   ├── projects.json          # Sender projects context
│   └── cache.db               # SQLite crash-track cache
└── src/
    ├── core/                  # Engine logic
    │   ├── config.py          # Env validation
    │   ├── llm_client.py      # LLM factory
    │   ├── models.py          # Pydantic schema
    │   ├── state.py           # DB Manager
    │   └── workflow.py        # LangGraph routing
    ├── tools/                 # Environment interaction
    │   ├── context.py         # LaTeX/JSON loaders
    │   ├── scraper.py         # Playwright class
    │   └── sheets.py          # Google Sheets update class
    ├── agents/                # AI Nodes
    └── prompts/               # Prompt mapping
```

## Key Features

- **Fault Tolerance**: SQLite caching prevent double-scrape. Drop connection mid-run? Resume safely auto.
- **Bot Bypass**: Auto-scroll logic (`human_behavior.py`). Playwright-stealth integration. Non-linear mouse simulation.
- **Context Injection**: Latex + JSON data merge. LLM knows your exact experience.
- **Constrained Output**: 2-part message. Strict `< 300 char` note. Pydantic `with_structured_output` validation.
- **Local Embedded Inference**: Zero API cost. Ollama container bundled.

## Development Workflow

1. Branch from `main`.
2. Sync deps `uv sync`.
3. Add agent/tool modifications.
4. Pass Pydantic validations.
5. Commit atomic units.

Commits follow `git commit -m "[action] [feature]"` patterns. E.g., `init architecture`, `added tools and caching`. 

## Coding Standards

- Python `3.12` type hints. `str | None` not `Optional[str]`.
- No sys.path hacks. Use absolute `src.tools.x` imports.
- Pydantic models for structured outputs.
- Env vars validated at startup via `pydantic-settings`. Fail fast.
- No hardcoded absolute path logic. Use `pathlib.Path`.

## Testing

Test target components locally using `uv`:

```bash
# Validate config parsing
uv run python -c "from src.core.config import load_settings; load_settings()"

# Test workflow compilation
uv run python -c "from src.core.workflow import app"
```

## Contributing

1. PR strict required. 
2. Retain architecture boundaries. Extractor logic stay in `/agents`. Web interactions stay in `/tools`.
3. Provide sample data structures. 
4. Pass `flake8` or `ruff` equivalent checks. 

## License

MIT License. Open source.
