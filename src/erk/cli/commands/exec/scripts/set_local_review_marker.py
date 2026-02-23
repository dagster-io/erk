"""Set local review marker on PR to skip CI reviews.

Appends an HTML comment to the PR body that signals CI to skip redundant
code reviews. The marker includes the HEAD SHA so it auto-invalidates
when new commits are pushed.

Marker format:
    <!-- erk:local-review-passed:<full-40-char-sha> -->

Usage:
    erk exec set-local-review-marker

Output:
    JSON with success status, PR number, and SHA.
    Exits 0 in all cases (including no-PR-found, which is not an error).
"""

import json
import re

import click

from erk_shared.context.helpers import require_git, require_github, require_repo_root
from erk_shared.gateway.github.types import PRNotFound

_MARKER_PATTERN = re.compile(r"<!-- erk:local-review-passed:[0-9a-f]{40} -->\n?")


def _build_marker(sha: str) -> str:
    return f"<!-- erk:local-review-passed:{sha} -->"


def _strip_existing_marker(body: str) -> str:
    """Remove any existing local-review-passed marker from body."""
    return _MARKER_PATTERN.sub("", body)


def _append_marker(body: str, sha: str) -> str:
    """Strip old marker if present, then append new marker."""
    cleaned = _strip_existing_marker(body)
    # Ensure body ends with newline before appending marker
    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned + _build_marker(sha) + "\n"


@click.command(name="set-local-review-marker")
@click.pass_context
def set_local_review_marker(ctx: click.Context) -> None:
    """Set local review marker on PR to skip CI reviews.

    Auto-detects current branch, gets HEAD SHA, finds the PR,
    and appends a marker to the PR body. The marker auto-invalidates
    when new commits are pushed (SHA mismatch).
    """
    git = require_git(ctx)
    github = require_github(ctx)
    repo_root = require_repo_root(ctx)

    # Get current branch
    current_branch = git.branch.get_current_branch(repo_root)
    if current_branch is None:
        click.echo(json.dumps({"success": False, "reason": "detached_head"}))
        return

    # Get HEAD SHA
    head_sha = git.branch.get_branch_head(repo_root, current_branch)
    if head_sha is None:
        click.echo(json.dumps({"success": False, "reason": "no_head_sha"}))
        return

    # Find PR for branch
    pr_result = github.get_pr_for_branch(repo_root, current_branch)
    if isinstance(pr_result, PRNotFound):
        click.echo(json.dumps({"success": False, "reason": "no_pr"}))
        return

    # Update PR body with marker
    new_body = _append_marker(pr_result.body, head_sha)
    github.update_pr_body(repo_root, pr_result.number, new_body)

    click.echo(
        json.dumps(
            {
                "success": True,
                "pr_number": pr_result.number,
                "sha": head_sha,
            }
        )
    )
