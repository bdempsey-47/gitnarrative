"""Post-clustering classification: partition clusters into major and minor."""

from __future__ import annotations

from fnmatch import fnmatch

from gitnarrative.clusterer import Cluster

# File patterns that indicate docs-only changes
_DOCS_PATTERNS = ("*.md", "docs/*", "LICENSE*", "LICENSE", "*.txt", "*.rst")

# File patterns that indicate CI/config-only changes
_CI_CONFIG_PATTERNS = (
    ".github/*",
    "*.yml",
    "*.yaml",
    ".gitignore",
    "*.toml",
    "Dockerfile",
    ".dockerignore",
    "*.cfg",
)

# Commit prefixes that indicate minor work
_MINOR_PREFIXES = ("chore:", "docs:", "ci:", "style:", "build:")


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    """Check if a file path matches any of the given glob patterns."""
    basename = path.split("/")[-1]
    return any(fnmatch(basename, p) or fnmatch(path, p) for p in patterns)


def classify_cluster(cluster: Cluster) -> str:
    """Classify a cluster as 'major' or 'minor'.

    A cluster is minor if it's a single commit AND meets any of:
    - Merge commit (message starts with "Merge ")
    - All files are docs
    - All files are CI/config
    - Message prefix is chore:/docs:/ci:/style:/build:
    - Zero files (empty merge)
    """
    if len(cluster.commits) > 1:
        return "major"

    commit = cluster.commits[0]
    msg = commit.message.strip()

    # Empty merge
    if not commit.files:
        return "minor"

    # Merge commit
    if msg.startswith("Merge "):
        return "minor"

    # Minor prefix
    msg_lower = msg.lower()
    if any(msg_lower.startswith(p) for p in _MINOR_PREFIXES):
        return "minor"

    # All files are docs
    if all(_matches_any(f.path, _DOCS_PATTERNS) for f in commit.files):
        return "minor"

    # All files are CI/config
    if all(_matches_any(f.path, _CI_CONFIG_PATTERNS) for f in commit.files):
        return "minor"

    return "major"


def partition_clusters(
    clusters: list[Cluster],
) -> tuple[list[Cluster], list[Cluster]]:
    """Split clusters into (major, minor) preserving order."""
    major: list[Cluster] = []
    minor: list[Cluster] = []
    for cluster in clusters:
        if classify_cluster(cluster) == "major":
            major.append(cluster)
        else:
            minor.append(cluster)
    return major, minor
