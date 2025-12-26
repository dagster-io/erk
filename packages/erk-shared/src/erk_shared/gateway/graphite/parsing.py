"""Parsing utilities for Graphite cache and PR information."""

import json
import warnings
from pathlib import Path
from typing import Any

from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.github.parsing import _parse_github_pr_url
from erk_shared.github.types import PullRequestInfo


def read_graphite_json_file(file_path: Path, description: str) -> dict[str, Any]:
    """Read and parse a Graphite JSON file.

    Args:
        file_path: Path to the JSON file (must exist)
        description: Human-readable description for error messages
            (e.g., "Graphite cache", "Graphite PR info")

    Returns:
        Parsed JSON dict

    Raises:
        FileNotFoundError: If file doesn't exist
        OSError: If file cannot be read
        json.JSONDecodeError: If JSON is invalid (warning emitted before raising)

    Note:
        Callers must check file_path.exists() before calling if they want
        to handle missing files gracefully.

        When JSON parsing fails, a UserWarning is emitted before the
        JSONDecodeError is re-raised to provide context about the failure.
    """
    json_str = file_path.read_text(encoding="utf-8")
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        warnings.warn(f"Cannot parse {description} at {file_path}: Invalid JSON", stacklevel=2)
        raise


def parse_graphite_pr_info(json_str: str) -> dict[str, PullRequestInfo]:
    """Parse Graphite's .graphite_pr_info JSON into PullRequestInfo objects.

    Args:
        json_str: JSON string from .graphite_pr_info file

    Returns:
        Mapping of branch name to PullRequestInfo
    """
    data = json.loads(json_str)
    prs = {}

    for pr in data.get("prInfos", []):
        branch = pr["headRefName"]

        graphite_url = pr["url"]
        github_url = _graphite_url_to_github_url(graphite_url)
        parsed = _parse_github_pr_url(github_url)
        if parsed is None:
            continue
        owner, repo = parsed

        prs[branch] = PullRequestInfo(
            number=pr["prNumber"],
            state=pr["state"],
            url=github_url,
            is_draft=pr["isDraft"],
            title=pr.get("title"),  # Title not available from Graphite cache
            checks_passing=None,  # CI status not available from Graphite cache
            owner=owner,
            repo=repo,
        )

    return prs


def parse_graphite_cache(
    json_str: str, git_branch_heads: dict[str, str]
) -> dict[str, BranchMetadata]:
    """Parse Graphite's .graphite_cache_persist JSON into BranchMetadata objects.

    Args:
        json_str: JSON string from .graphite_cache_persist file
        git_branch_heads: Mapping of branch name to commit SHA from git

    Returns:
        Mapping of branch name to BranchMetadata
    """
    cache_data = json.loads(json_str)
    branches_data: list[tuple[str, dict[str, object]]] = cache_data.get("branches", [])

    result = {}
    for branch_name, info in branches_data:
        if not isinstance(info, dict):
            continue

        # Get commit SHA from git (not stored in cache)
        commit_sha = git_branch_heads.get(branch_name, "")

        parent = info.get("parentBranchName")
        if not isinstance(parent, str | None):
            parent = None

        children_raw = info.get("children", [])
        if not isinstance(children_raw, list):
            children_raw = []
        children = [c for c in children_raw if isinstance(c, str)]

        # A branch is trunk if it has explicit TRUNK marker OR has no parent
        is_trunk = info.get("validationResult") == "TRUNK" or parent is None

        result[branch_name] = BranchMetadata(
            name=branch_name,
            parent=parent,
            children=children,
            is_trunk=is_trunk,
            commit_sha=commit_sha,
        )

    return result


def _graphite_url_to_github_url(graphite_url: str) -> str:
    """Convert Graphite URL to GitHub URL.

    Input: https://app.graphite.com/github/pr/dagster-io/erk/42
    Output: https://github.com/dagster-io/erk/pull/42
    """
    parts = graphite_url.split("/")
    if len(parts) >= 8 and parts[2] == "app.graphite.com":
        owner = parts[5]
        repo = parts[6]
        pr_number = parts[7]
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    return graphite_url
