"""Stage 1: Extract commits and file stats from a git repository."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from git import Repo


@dataclass
class FileStat:
    path: str
    insertions: int
    deletions: int


@dataclass
class Commit:
    sha: str
    date: datetime
    author: str
    message: str
    files: list[FileStat] = field(default_factory=list)


def read_commits(
    repo_path: Path,
    since: str | None = None,
    until: str | None = None,
) -> list[Commit]:
    """Read commits from a git repo, returning them in chronological order."""
    repo = Repo(repo_path)

    log_args: dict = {"no-walk": False}
    if since:
        log_args["since"] = since
    if until:
        log_args["until"] = until

    commits: list[Commit] = []
    for git_commit in repo.iter_commits("HEAD", **log_args):
        file_stats: list[FileStat] = []
        try:
            stats = git_commit.stats.files
            for filepath, stat in stats.items():
                file_stats.append(
                    FileStat(
                        path=filepath,
                        insertions=stat.get("insertions", 0),
                        deletions=stat.get("deletions", 0),
                    )
                )
        except Exception:
            pass  # merge commits or empty commits may not have stats

        commits.append(
            Commit(
                sha=git_commit.hexsha[:8],
                date=datetime.fromtimestamp(git_commit.committed_date),
                author=git_commit.author.name or "Unknown",
                message=git_commit.message.strip().split("\n")[0],
                files=file_stats,
            )
        )

    # Return chronological order (oldest first)
    commits.reverse()
    return commits
