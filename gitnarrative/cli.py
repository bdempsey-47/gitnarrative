"""CLI entry point for gitnarrative."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer


_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S")


def _validate_date(value: str | None, label: str) -> None:
    """Validate a date string against accepted formats, or raise typer.Exit."""
    if value is None:
        return
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return
        except ValueError:
            continue
    typer.echo(
        f"Error: Invalid {label} date '{value}'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS.",
        err=True,
    )
    raise typer.Exit(1)

app = typer.Typer(
    name="gitnarrative",
    help="Generate narrative markdown from git history using LLMs.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Manage gitnarrative configuration.")
app.add_typer(config_app, name="config")


@config_app.command("set-key")
def config_set_key() -> None:
    """Store your Anthropic API key in the system keyring."""
    import keyring
    from gitnarrative.narrator import KEY_ACCOUNT, SERVICE_NAME

    api_key = typer.prompt("Anthropic API key", hide_input=True)
    if not api_key.strip():
        typer.echo("Error: API key cannot be empty.", err=True)
        raise typer.Exit(1)
    keyring.set_password(SERVICE_NAME, KEY_ACCOUNT, api_key.strip())
    typer.echo("API key stored in system keyring.")


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
    max_commits: int = typer.Option(
        500,
        "--max-commits",
        help="Maximum number of commits to process (default: 500).",
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

    _validate_date(since, "--since")
    _validate_date(until, "--until")
    if since and until:
        # Both already validated; compare as strings (ISO format sorts correctly)
        if since > until:
            typer.echo("Error: --since date must be before --until date.", err=True)
            raise typer.Exit(1)

    typer.echo(f"Reading commits from {repo}...")
    commits = read_commits(repo, since=since, until=until, max_count=max_commits)
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
        typer.echo(f"\nDry run — {len(commits)} commits, {len(clusters)} clusters. Skipping LLM narration.")
        raise typer.Exit(0)

    if len(clusters) > 50:
        typer.echo(
            f"\n  Warning: {len(clusters)} clusters will require {len(clusters)} API calls. "
            "Consider narrowing the date range or using --max-commits."
        )

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
