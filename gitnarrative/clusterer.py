"""Stage 2: Cluster commits into feature groups using heuristics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from gitnarrative.git_reader import Commit

# Files that appear in many commits but don't signal a shared feature
TRIVIAL_FILES = {
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pyproject.toml",
    "poetry.lock",
    "requirements.txt",
    ".gitignore",
    "CHANGELOG.md",
    "README.md",
}

MAX_GAP_DAYS = 7


@dataclass
class Cluster:
    commits: list[Commit] = field(default_factory=list)
    name: str = ""
    files: set[str] = field(default_factory=set)

    @property
    def start(self):
        return min(c.date for c in self.commits)

    @property
    def end(self):
        return max(c.date for c in self.commits)


def _non_trivial_files(commit: Commit) -> set[str]:
    """Return file paths that are meaningful for clustering."""
    return {
        f.path
        for f in commit.files
        if f.path.split("/")[-1] not in TRIVIAL_FILES
    }


def _build_adjacency(commits: list[Commit]) -> dict[int, set[int]]:
    """Build an adjacency map: two commits are linked if they share 2+ non-trivial files."""
    file_to_commits: dict[str, list[int]] = defaultdict(list)
    for i, commit in enumerate(commits):
        for f in _non_trivial_files(commit):
            file_to_commits[f].append(i)

    adj: dict[int, set[int]] = defaultdict(set)
    for indices in file_to_commits.values():
        for a in indices:
            for b in indices:
                if a != b:
                    # Count shared files between a and b
                    shared = _non_trivial_files(commits[a]) & _non_trivial_files(commits[b])
                    if len(shared) >= 2:
                        adj[a].add(b)
                        adj[b].add(a)
    return adj


def _connected_components(n: int, adj: dict[int, set[int]]) -> list[list[int]]:
    """Find connected components via BFS."""
    visited = set()
    components: list[list[int]] = []
    for i in range(n):
        if i in visited:
            continue
        component = []
        queue = [i]
        while queue:
            node = queue.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        component.sort()
        components.append(component)
    return components


def _split_by_time_gap(commits: list[Commit], indices: list[int]) -> list[list[int]]:
    """Split a component if there's a gap larger than MAX_GAP_DAYS between consecutive commits."""
    if len(indices) <= 1:
        return [indices]

    sorted_indices = sorted(indices, key=lambda i: commits[i].date)
    groups: list[list[int]] = [[sorted_indices[0]]]

    for prev_idx, curr_idx in zip(sorted_indices, sorted_indices[1:]):
        gap = commits[curr_idx].date - commits[prev_idx].date
        if gap > timedelta(days=MAX_GAP_DAYS):
            groups.append([curr_idx])
        else:
            groups[-1].append(curr_idx)

    return groups


def _extract_name(commits: list[Commit], indices: list[int]) -> str:
    """Extract a candidate feature name from commit messages."""
    # Look for common prefixes like "feat:", "fix:", "refactor:" etc.
    prefix_counts: dict[str, int] = defaultdict(int)
    for i in indices:
        msg = commits[i].message.lower()
        # Match "prefix: rest" or "prefix(scope): rest"
        match = msg.split(":", 1)
        if len(match) == 2 and len(match[0]) < 30:
            prefix_counts[match[0].strip()] += 1

    if prefix_counts:
        # Use the most common prefix
        best = max(prefix_counts, key=prefix_counts.get)
        return best.title()

    # Fallback: use the first commit's message truncated
    return commits[indices[0]].message[:60]


def cluster_commits(commits: list[Commit]) -> list[Cluster]:
    """Cluster commits into feature groups."""
    if not commits:
        return []

    adj = _build_adjacency(commits)
    components = _connected_components(len(commits), adj)

    clusters: list[Cluster] = []
    for component in components:
        # Split components with large time gaps
        sub_groups = _split_by_time_gap(commits, component)
        for group in sub_groups:
            cluster = Cluster(
                commits=[commits[i] for i in group],
                name=_extract_name(commits, group),
            )
            for i in group:
                cluster.files.update(f.path for f in commits[i].files)
            clusters.append(cluster)

    # Sort clusters by start date
    clusters.sort(key=lambda c: c.start)
    return clusters
