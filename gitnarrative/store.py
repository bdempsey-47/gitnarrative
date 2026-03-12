"""Write narrative output to .gitnarrative/ directory."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gitnarrative.clusterer import Cluster
from gitnarrative.narrator import FeatureNarrative

# Locate templates relative to this package
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_narrative(
    clusters: list[Cluster],
    narratives: list[FeatureNarrative],
    repo_path: Path,
    since: str | None = None,
    until: str | None = None,
) -> str:
    """Render the full narrative markdown from clusters and their narratives."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
    )

    feature_template = env.get_template("feature.md.jinja")
    narrative_template = env.get_template("narrative.md.jinja")

    features_md: list[str] = []
    for cluster, narrative in zip(clusters, narratives):
        rendered = feature_template.render(
            feature=narrative,
            cluster=cluster,
        )
        features_md.append(rendered)

    total_commits = sum(len(c.commits) for c in clusters)
    all_files = set()
    for c in clusters:
        all_files.update(c.files)

    result = narrative_template.render(
        repo_name=repo_path.name,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        since=since or "beginning",
        until=until or "now",
        num_clusters=len(clusters),
        num_commits=total_commits,
        num_files=len(all_files),
        features="\n".join(features_md),
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
