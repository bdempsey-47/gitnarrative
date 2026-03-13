"""Post-narration synthesis: condense verbose per-feature narratives into a concise document."""

from __future__ import annotations

import logging
import os
from collections import Counter

import anthropic

from gitnarrative.git_reader import Commit
from gitnarrative.narrator import _resolve_api_key

logger = logging.getLogger(__name__)

SYNTHESIS_MODEL = "claude-sonnet-4-6"

SYNTHESIS_SYSTEM_PROMPT = """\
You are a technical writer condensing a verbose project narrative into a \
concise onboarding document for an LLM or developer encountering this \
codebase for the first time.

Given individual feature narrations from git history analysis, produce a \
single hierarchical markdown document with these sections:

Do NOT start your output with a top-level heading (# ...) — the template \
already provides one.

## Project Overview
1-2 paragraphs synthesized from the most significant feature(s). Cover: \
what the project is, key tech stack, architectural approach, and current state.

## Key Features & Milestones
Full treatment ONLY for genuinely significant work (multi-commit features, \
architectural changes, infrastructure milestones). Keep: summary, key \
decisions, primary files. Combine closely related items into one section.
Include the date range after each feature heading, e.g.:
### Feature Name (Mar 5–9, 2026)
Only include development phases when they reveal a deliberate pivot or \
abandoned approach (e.g., "initially computed server-side, switched to \
proxy because X"). Omit chronological build sequences.

## Traps & Gotchas
Only include items where the current behavior is non-obvious or \
counterintuitive — things that look wrong but are intentional, subtle \
edge cases, or behaviors that would break if someone "cleaned up" the \
code without context. Each item should explain WHY the non-obvious \
choice was made.
Format as:
- **Short label** — Explanation of what looks wrong and why it's actually \
correct. (`relevant_file`)
Example:
- **Team name trimming at both layers** — Applied at both ingestion and \
presentation defensively because upstream data has inconsistent whitespace. \
Removing either layer will cause display bugs. (`ingest.py`, `display.py`)
If no genuine traps/gotchas exist, omit this section entirely.

## Hotspots
Identify files with unusually high commit frequency from the file hotspot \
data provided. For each hotspot, note the file path, approximate commit \
count, and infer WHY it's churning (fragile external API contract, rapid \
feature iteration, poor factoring, etc.).
Format as:
- **`file_path`** (N commits) — Inferred reason for churn.
If no clear hotspots exist, omit this section.

OMIT entirely:
- CSS-only tweaks (alignment, spacing, font size fixes)
- Single-property fixes with no architectural significance
- Debug logging additions
- Documentation-only updates
- Changes that repeat the same fix iteratively (keep only the final state)

Keep only what a developer would need to understand the codebase's current \
state and the reasoning behind non-obvious design choices.
"""


def _compute_file_hotspots(commits: list[Commit], min_count: int = 3, max_files: int = 10) -> dict[str, int]:
    """Compute file → commit count mapping, filtered to high-churn files."""
    file_counts: Counter[str] = Counter()
    for commit in commits:
        seen: set[str] = set()
        for fstat in commit.files:
            if fstat.path not in seen:
                file_counts[fstat.path] += 1
                seen.add(fstat.path)
    # Filter to files appearing in at least min_count commits, take top max_files
    hotspots = {f: c for f, c in file_counts.most_common() if c >= min_count}
    return dict(list(hotspots.items())[:max_files])


def synthesize(
    feature_blocks: list[str],
    repo_name: str,
    commits: list[Commit] | None = None,
) -> str:
    """Make a single LLM call to condense all narrations into a hierarchical document.

    Args:
        feature_blocks: List of rendered per-feature markdown blocks.
        repo_name: Name of the repository being analyzed.
        commits: Raw commit list for computing file hotspot data.

    Returns:
        Synthesized markdown body (without header/footer — template handles those).
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError(
            "No Anthropic API key found. Set ANTHROPIC_API_KEY env var or run: gitnarrative config set-key"
        )

    client = anthropic.Anthropic(api_key=api_key)

    user_prompt_parts = [
        f"Repository: {repo_name}",
        "",
        "=== INDIVIDUAL FEATURE NARRATIONS ===",
        "",
    ]
    for i, block in enumerate(feature_blocks, 1):
        user_prompt_parts.append(f"--- Feature {i} ---")
        user_prompt_parts.append(block)
        user_prompt_parts.append("")

    if commits:
        hotspots = _compute_file_hotspots(commits)
        if hotspots:
            user_prompt_parts.append("=== FILE HOTSPOTS ===")
            user_prompt_parts.append("Files with highest commit frequency:")
            for filepath, count in hotspots.items():
                user_prompt_parts.append(f"  {filepath}: {count} commits")
            user_prompt_parts.append("")

    user_prompt = "\n".join(user_prompt_parts)

    response = client.messages.create(
        model=SYNTHESIS_MODEL,
        max_tokens=4096,
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()
