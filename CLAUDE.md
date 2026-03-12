# gitnarrative — Claude Code Instructions

## Project Overview
- **Name:** gitnarrative
- **Purpose:** LLM-powered CLI that reads git commit history, clusters commits into features, and generates narrative markdown
- **Tech Stack:** Python 3.11+, Typer (CLI), Anthropic API (LLM), Jinja2 (templates), GitPython (git access)
- **Status:** MVP (v0.1.0)

## Architecture
Three-stage pipeline:
1. **git_reader.py** — Extract commits via GitPython (SHA, date, author, message, file stats)
2. **clusterer.py** — Group commits by file co-occurrence + time proximity (pure heuristics, no LLM)
3. **narrator.py** — Send each cluster to Claude API, get structured JSON, render via Jinja templates

Key design: LLM returns JSON, templates render markdown. This separates content generation from formatting.

## Project Structure
```
gitnarrative/
├── gitnarrative/         # Package
│   ├── cli.py            # Typer CLI entry point
│   ├── git_reader.py     # Stage 1: git log extraction
│   ├── clusterer.py      # Stage 2: heuristic clustering
│   ├── narrator.py       # Stage 3: LLM narration
│   └── store.py          # Template rendering + file output
├── templates/            # Jinja2 templates
│   ├── feature.md.jinja  # Per-feature block
│   └── narrative.md.jinja # Top-level document
└── pyproject.toml        # Package config + CLI entry point
```

## Development
```bash
# Install in dev mode
pip install -e .

# Run CLI
gitnarrative init --repo /path/to/repo --since 2026-03-01

# Dry run (no LLM calls)
gitnarrative init --repo /path/to/repo --since 2026-03-01 --dry-run
```

## Environment Variables
- `ANTHROPIC_API_KEY` — Required for LLM narration
- `GITNARRATIVE_MODEL` — Override default model (default: claude-haiku-4-5-20251001)

## Clustering Algorithm
- Build file co-occurrence graph (commits sharing 2+ non-trivial files are linked)
- Find connected components (BFS)
- Split components with >7 day gaps between consecutive commits
- Name extraction from commit message prefixes (feat:, fix:, etc.)

## Future Work
- Incremental updates (only process new commits since last run)
- Embeddings-based clustering for better grouping
- Multiple output formats (ADR, changelog)
- Config file (.gitnarrative.toml)
