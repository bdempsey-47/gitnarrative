# gitnarrative — Claude Code Instructions

## Project Overview
- **Name:** gitnarrative
- **Purpose:** LLM-powered CLI that reads git commit history, clusters commits into features, and generates narrative markdown describing a project's evolution. Narratives are designed for both humans and LLMs (like CLAUDE.md). Think "automated Architecture Decision Records from git history."
- **Tech Stack:** Python 3.11+, Typer (CLI), Anthropic API (LLM), Jinja2 (templates), GitPython (git access), keyring (secure API key storage)
- **Status:** MVP (v0.1.0) — bootstrapped 2026-03-11, first successful LLM run 2026-03-12
- **Repo:** Private GitHub repo at `bdempsey-47/gitnarrative`

## Architecture
Three-stage pipeline:
1. **git_reader.py** — Extract commits via GitPython (SHA, date, author, message, file stats)
2. **clusterer.py** — Group commits by file co-occurrence + time proximity (pure heuristics, no LLM)
3. **narrator.py** — Send each cluster to Claude API, get structured JSON, render via Jinja templates

Key design: LLM returns JSON, templates render markdown. This separates content generation from formatting.

## Project Structure
```
gitnarrative/
├── gitnarrative/              # Package
│   ├── __init__.py            # Version string
│   ├── cli.py                 # Typer CLI entry point
│   ├── git_reader.py          # Stage 1: git log extraction
│   ├── clusterer.py           # Stage 2: heuristic clustering
│   ├── classifier.py          # Stage 2.5: major/minor classification
│   ├── narrator.py            # Stage 3: LLM narration
│   ├── synthesizer.py         # Stage 4: LLM synthesis
│   ├── store.py               # Template rendering + file output
│   └── templates/             # Jinja2 templates (inside package for distribution)
│       ├── feature.md.jinja   # Per-feature block
│       ├── minor_summary.md.jinja  # Minor changes table
│       ├── narrative.md.jinja      # Verbose top-level document
│       └── synthesized.md.jinja    # Synthesized top-level document
├── pyproject.toml             # Package config + CLI entry point
├── .gitignore
└── CLAUDE.md                  # This file
```

## Development

### Setup
```powershell
cd C:\Projects\gitnarrative
pip install -e .
```

### API Key Setup (one-time)
```powershell
gitnarrative config set-key   # prompts for key, stores in Windows Credential Manager
```
Lookup order: `ANTHROPIC_API_KEY` env var → system keyring. Env var wins if both are set.

### Running
```powershell
gitnarrative init --repo C:\Projects\MLSNextSchedule --since 2026-03-05
```

### Dry Run (no LLM calls, tests pipeline stages 1+2)
```powershell
gitnarrative init --repo C:\Projects\MLSNextSchedule --since 2026-03-05 --dry-run
```

### CLI Structure
Adding the `config` subcommand group means Typer no longer flattens — `init` is now an explicit subcommand:
```
gitnarrative init --repo <path> --since <date> [--until <date>] [--model <model>] [--max-commits N] [--dry-run]
gitnarrative config set-key
```

## Environment Variables
- `ANTHROPIC_API_KEY` — Optional; overrides keyring if set (get from https://console.anthropic.com)
- `GITNARRATIVE_MODEL` — Override default model (default: claude-haiku-4-5-20251001)

## Clustering Algorithm
- Build file co-occurrence graph (commits sharing 2+ non-trivial files are linked)
- Find connected components (BFS)
- Split components with >7 day gaps between consecutive commits
- Name extraction from commit message prefixes (feat:, fix:, etc.)
- Trivial files excluded from co-occurrence: package.json, lock files, .gitignore, README, CHANGELOG

## Security Hardening (2026-03-12)
- **Prompt injection mitigation:** Commit data wrapped in `<commit_data>` XML tags with system prompt instructing LLM to treat contents as data only. Commit messages truncated to 500 chars. See `narrator.py:_format_cluster_for_prompt()`.
- **Date input validation:** `--since` and `--until` validated against `YYYY-MM-DD` / `YYYY-MM-DDTHH:MM:SS` before reaching GitPython. Cross-validated (since < until). See `cli.py:_validate_date()`.
- **Exception handling:** `narrator.py` catches `APIError`/`JSONDecodeError` specifically, logs via `logging.warning()`, returns generic fallback (no raw error leak). `git_reader.py` catches expected stat-read errors, logs unexpected ones via `logger.debug()`. JSON fence stripping uses regex for robustness.
- **DoS limits:** `--max-commits` (default 500) caps commit ingestion. Warning printed when >50 clusters detected.

## Known Issues / Observations
- **First full run against YSS repo (113 commits, all history):** produced 65 clusters — many single-commit clusters because those commits touch unique files. The big 47-commit cluster worked well (LLM identified 3 phases and 4 key decisions). Single-commit clusters got appropriate names and complexity ratings.
- **Cluster names are generic pre-LLM:** Most clusters named "Fix" or "Feat" because name extraction only uses the commit prefix before `:`. LLM narration gives them real names (e.g., "Youth Soccer Schedules Platform").
- **Too many clusters:** 65 clusters for 113 commits is noisy. Many single-commit docs/fix clusters could be merged. Improving clustering is a priority.

## Next Steps (Priority Order)

### Immediate (next session)
1. ~~**Add Anthropic API credits** and do first real LLM test run~~ — DONE 2026-03-12
2. **Verify narrative quality** — compare generated output against manual analysis of YSS repo history
3. **Test against a public repo** — clone a small OSS project and run to validate with unfamiliar history

### Short-term Improvements
4. **Better heuristic clustering** — reduce single-commit clusters by:
   - Lowering co-occurrence threshold (1 shared file instead of 2?)
   - Adding commit message similarity (shared keywords/prefixes)
   - Merging adjacent single-commit clusters that touch the same directory
5. ~~**Add `init` as a proper subcommand**~~ — DONE (happened naturally when adding `config` subcommand group)
6. **Progress indicator** — show progress during LLM calls (65 clusters = 65 API calls)
7. ~~**Error handling** — better messages when API key missing or invalid~~ — DONE (keyring fallback + clear error message)

### Future Features
8. **Incremental updates** — `gitnarrative update` that only processes new commits since last run
9. **Configurable output** — `.gitnarrative.toml` for model choice, cluster params, template overrides
10. **Multiple output formats** — ADR (Architecture Decision Records), changelog, CLAUDE.md-style
11. **Embeddings-based clustering** — use sentence embeddings for smarter grouping (heavier dependency)
12. **Parallel LLM calls** — batch API requests for faster processing
13. **Cost estimation** — `--estimate` flag to show expected token usage before running
14. **Cross-repo narratives** — analyze multiple repos that form a system together

## Git Workflow
- Single-person project, work on main
- Private repo until past MVP
- Commit style: descriptive messages with Co-Authored-By tag
