"""CLI entry point for gitnarrative."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(
    name="gitnarrative",
    help="Generate narrative markdown from git history using LLMs.",
    no_args_is_help=True,
)


@app.command()
def init(
    repo: Path = typer.Option(
        ".",
        help="Path to the git repository to analyze.",
    ),
    since: str = typer.Option(
        None,
        help="Start date for commit range (e.g. 2026-03-01).",
    ),
    until: str = typer.Option(
        None,
        help="End date for commit range.",
    ),
    model: str = typer.Option(
        None,
        help="Claude model to use (default: claude-haiku-4-5-20251001).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show clusters without calling LLM.",
    ),
) -> None:
    """Analyze git history and generate a narrative markdown file."""
    from gitnarrative.clusterer import cluster_commits
    from gitnarrative.git_reader import read_commits
    from gitnarrative.narrator import FeatureNarrative, narrate_all
    from gitnarrative.store import render_narrative, write_narrative

    repo = repo.resolve()
    if not (repo / ".git").exists():
        typer.echo(f"Error: {repo} is not a git repository.", err=True)
        raise typer.Exit(1)

    typer.echo(f"Reading commits from {repo}...")
    commits = read_commits(repo, since=since, until=until)
    typer.echo(f"  Found {len(commits)} commits.")

    if not commits:
        typer.echo("No commits found in the given range.")
        raise typer.Exit(0)

    typer.echo("Clustering commits...")
    clusters = cluster_commits(commits)
    typer.echo(f"  Found {len(clusters)} clusters.")

    for i, cluster in enumerate(clusters, 1):
        typer.echo(
            f"  [{i}] {cluster.name} "
            f"({len(cluster.commits)} commits, "
            f"{cluster.start:%Y-%m-%d} to {cluster.end:%Y-%m-%d})"
        )

    if dry_run:
        typer.echo("\nDry run — skipping LLM narration.")
        raise typer.Exit(0)

    typer.echo("\nGenerating narratives via Claude...")
    narratives = narrate_all(clusters, model=model)

    content = render_narrative(
        clusters=clusters,
        narratives=narratives,
        repo_path=repo,
        since=since,
        until=until,
    )

    output_file = write_narrative(content, repo)
    typer.echo(f"\nNarrative written to {output_file}")


if __name__ == "__main__":
    app()
