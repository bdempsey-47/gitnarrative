"""Write narrative output to .gitnarrative/ directory."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gitnarrative.clusterer import Cluster
from gitnarrative.narrator import FeatureNarrative

# Locate templates inside this package
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_feature_blocks(
    clusters: list[Cluster],
    narratives: list[FeatureNarrative],
) -> list[str]:
    """Render individual feature markdown blocks (used as synthesis input)."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    feature_template = env.get_template("feature.md.jinja")

    blocks: list[str] = []
    for cluster, narrative in zip(clusters, narratives):
        rendered = feature_template.render(
            feature=narrative,
            cluster=cluster,
        )
        blocks.append(rendered)
    return blocks


def render_minor_table(minor_clusters: list[Cluster]) -> str:
    """Render the minor changes table."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )
    minor_template = env.get_template("minor_summary.md.jinja")
    return minor_template.render(minor_clusters=minor_clusters)


def _compute_stats(
    clusters: list[Cluster],
    minor_clusters: list[Cluster] | None,
) -> tuple[int, int, int]:
    """Return (total_commits, num_files, num_all_clusters)."""
    all_clusters = list(clusters) + (minor_clusters or [])
    total_commits = sum(len(c.commits) for c in all_clusters)
    all_files: set[str] = set()
    for c in all_clusters:
        all_files.update(c.files)
    return total_commits, len(all_files), len(all_clusters)


def render_narrative(
    clusters: list[Cluster],
    narratives: list[FeatureNarrative],
    repo_path: Path,
    since: str | None = None,
    until: str | None = None,
    minor_clusters: list[Cluster] | None = None,
    synthesized_content: str | None = None,
) -> str:
    """Render the full narrative markdown from clusters and their narratives.

    If synthesized_content is provided, uses the synthesized template instead
    of the verbose per-feature layout.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )

    total_commits, num_files, num_all_clusters = _compute_stats(clusters, minor_clusters)

    if synthesized_content is not None:
        synth_template = env.get_template("synthesized.md.jinja")
        return synth_template.render(
            repo_name=repo_path.name,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            since=since or "beginning",
            until=until or "now",
            num_commits=total_commits,
            num_files=num_files,
            synthesized_body=synthesized_content,
        )

    # Original verbose rendering
    features_md = render_feature_blocks(clusters, narratives)

    # Render minor summary if present
    minor_summary = ""
    if minor_clusters:
        minor_summary = render_minor_table(minor_clusters)

    narrative_template = env.get_template("narrative.md.jinja")
    result = narrative_template.render(
        repo_name=repo_path.name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        since=since or "beginning",
        until=until or "now",
        num_clusters=num_all_clusters,
        num_commits=total_commits,
        num_files=num_files,
        features="\n".join(features_md),
        minor_summary=minor_summary,
    )
    return result


def write_narrative(
    content: str,
    repo_path: Path,
) -> Path:
    """Write the narrative to .gitnarrative/narrative.md in the target repo."""
    output_dir = repo_path / ".gitnarrative"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "narrative.md"
    output_file.write_text(content, encoding="utf-8")
    return output_file
