"""Stage 3: Generate narratives for each cluster using Claude API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import anthropic

from gitnarrative.clusterer import Cluster


@dataclass
class FeatureNarrative:
    feature_name: str
    summary: str
    phases: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    files_primary: list[str] = field(default_factory=list)
    complexity: str = "medium"


SYSTEM_PROMPT = """\
You are a technical writer analyzing git commit history. Given a cluster of related commits, \
produce a structured JSON object describing the feature or change they represent.

Respond with ONLY valid JSON matching this schema:
{
  "feature_name": "Short descriptive name for this feature/change",
  "summary": "2-3 sentence summary of what was built/changed and why",
  "phases": ["Phase 1 description", "Phase 2 description"],
  "decisions": ["Key architectural or design decision made"],
  "files_primary": ["path/to/main/file.ext"],
  "complexity": "low|medium|high"
}

Guidelines:
- feature_name: concise, title-case, no prefix like "feat:"
- summary: focus on the WHY and WHAT, not just listing commits
- phases: group commits into logical phases of work (1-4 phases)
- decisions: non-obvious choices the developer made (0-3 decisions)
- files_primary: the 3-5 most important files (not config/lock files)
- complexity: low=single file tweak, medium=multi-file feature, high=architectural change
"""


def _format_cluster_for_prompt(cluster: Cluster) -> str:
    """Format a cluster's commits into a prompt for the LLM."""
    lines = [f"## Cluster: {cluster.name}"]
    lines.append(f"Date range: {cluster.start:%Y-%m-%d} to {cluster.end:%Y-%m-%d}")
    lines.append(f"Total commits: {len(cluster.commits)}")
    lines.append(f"Files touched: {len(cluster.files)}")
    lines.append("")
    lines.append("### Commits (chronological):")
    for c in cluster.commits:
        file_summary = ", ".join(
            f"{f.path} (+{f.insertions}/-{f.deletions})" for f in c.files[:5]
        )
        if len(c.files) > 5:
            file_summary += f", ... and {len(c.files) - 5} more"
        lines.append(f"- [{c.sha}] {c.date:%Y-%m-%d} | {c.message}")
        if file_summary:
            lines.append(f"  Files: {file_summary}")
    return "\n".join(lines)


def narrate_cluster(
    cluster: Cluster,
    model: str | None = None,
) -> FeatureNarrative:
    """Send a cluster to Claude and get back a structured narrative."""
    model = model or os.environ.get("GITNARRATIVE_MODEL", "claude-haiku-4-5-20251001")
    client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

    prompt = _format_cluster_for_prompt(cluster)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    # Parse JSON from response, handling potential markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    data = json.loads(text)

    return FeatureNarrative(
        feature_name=data.get("feature_name", cluster.name),
        summary=data.get("summary", ""),
        phases=data.get("phases", []),
        decisions=data.get("decisions", []),
        files_primary=data.get("files_primary", []),
        complexity=data.get("complexity", "medium"),
    )


def narrate_all(
    clusters: list[Cluster],
    model: str | None = None,
) -> list[FeatureNarrative]:
    """Narrate all clusters, returning a list of feature narratives."""
    narratives: list[FeatureNarrative] = []
    for cluster in clusters:
        try:
            narrative = narrate_cluster(cluster, model=model)
            narratives.append(narrative)
        except Exception as e:
            # Fallback: create a basic narrative without LLM
            narratives.append(
                FeatureNarrative(
                    feature_name=cluster.name,
                    summary=f"[LLM unavailable: {e}] {len(cluster.commits)} commits touching {len(cluster.files)} files.",
                    phases=[c.message for c in cluster.commits],
                    files_primary=sorted(cluster.files)[:5],
                    complexity="medium",
                )
            )
    return narratives
