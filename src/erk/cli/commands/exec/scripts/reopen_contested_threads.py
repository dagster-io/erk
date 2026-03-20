"""Reopen contested resolved PR review threads.

Detects resolved threads that were resolved by pr-address (evidenced by
the HTML marker comment) but have new reviewer comments after the last
attribution comment. These "contested" threads are unresolved so they get
picked up by normal pr-address classification.

Usage:
    erk exec reopen-contested-threads
    erk exec reopen-contested-threads --pr 123

Output:
    JSON with contested thread info and unresolve results

Exit Codes:
    0: Always (even on error, to support || true pattern)
    1: Context not initialized

Examples:
    $ erk exec reopen-contested-threads
    {"success": true, "pr_number": 123, "contested_threads": [], ...}

    $ erk exec reopen-contested-threads --pr 456
    {"success": true, "pr_number": 456, "contested_threads": [{"thread_id": "PRRT_abc", ...}], ...}
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

import click

from erk.cli.commands.exec.scripts.resolve_review_thread import PR_ADDRESS_MARKER
from erk.cli.script_output import exit_with_error
from erk_shared.context.helpers import (
    get_current_branch,
    require_github,
    require_repo_root,
)
from erk_shared.gateway.github.checks import GitHubChecks
from erk_shared.gateway.github.types import PRReviewThread
from erk_shared.non_ideal_state import BranchDetectionFailed

if TYPE_CHECKING:
    from pathlib import Path

    from erk_shared.gateway.github.abc import LocalGitHub


@dataclass(frozen=True)
class ContestedThreadResult:
    """Result for a single contested thread unresolve attempt."""

    thread_id: str
    path: str
    line: int | None
    unresolve_success: bool


def _has_marker(body: str) -> bool:
    """Check if a comment body contains the pr-address resolution marker.

    Args:
        body: Comment body text

    Returns:
        True if the comment was made by pr-address (contains the marker)
    """
    return PR_ADDRESS_MARKER in body


def _find_contested_threads(threads: list[PRReviewThread]) -> list[PRReviewThread]:
    """Find resolved threads that have reviewer pushback after pr-address attribution.

    A thread is "contested" if:
    1. It is resolved
    2. At least one comment contains the pr-address marker (was resolved by pr-address)
    3. There are comments after the last pr-address marker comment

    Manually resolved threads (no marker comment) are left alone.

    Args:
        threads: All PR review threads (including resolved ones)

    Returns:
        List of resolved threads with unaddressed pushback
    """
    contested: list[PRReviewThread] = []
    for thread in threads:
        if not thread.is_resolved:
            continue

        # Find the index of the last comment with the pr-address marker
        last_marker_idx = -1
        for idx, comment in enumerate(thread.comments):
            if _has_marker(comment.body):
                last_marker_idx = idx

        # No marker means this was manually resolved - skip it
        if last_marker_idx == -1:
            continue

        # If there are comments after the last marker comment, it's contested
        if last_marker_idx < len(thread.comments) - 1:
            contested.append(thread)

    return contested


@click.command(name="reopen-contested-threads")
@click.option(
    "--pr", default=None, type=int, help="PR number (default: detect from current branch)"
)
@click.pass_context
def reopen_contested_threads(ctx: click.Context, pr: int | None) -> None:
    """Reopen resolved PR review threads that have unaddressed reviewer pushback.

    Checks resolved threads for those previously addressed by pr-address
    (identified by HTML marker comment) but with new comments after the
    attribution. These contested threads are unresolved so they appear
    in normal pr-address classification.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Resolve PR number from flag or current branch
    if pr is None:
        branch = GitHubChecks.branch(get_current_branch(ctx))
        if isinstance(branch, BranchDetectionFailed):
            branch.ensure()
        assert not isinstance(branch, BranchDetectionFailed)  # type narrowing after NoReturn
        pr_details = GitHubChecks.pr_for_branch(github, repo_root, branch).ensure()
    else:
        pr_details = GitHubChecks.pr_by_number(github, repo_root, pr).ensure()

    # Fetch all threads including resolved ones
    try:
        all_threads = github.get_pr_review_threads(
            repo_root, pr_details.number, include_resolved=True
        )
    except RuntimeError as e:
        exit_with_error("github-api-failed", str(e))

    resolved_threads = [t for t in all_threads if t.is_resolved]
    contested = _find_contested_threads(resolved_threads)

    # Unresolve each contested thread
    contested_results: list[ContestedThreadResult] = []
    total_reopened = 0
    for thread in contested:
        success = _unresolve_thread(github, repo_root, thread.id)
        if success:
            total_reopened += 1
        contested_results.append(
            ContestedThreadResult(
                thread_id=thread.id,
                path=thread.path,
                line=thread.line,
                unresolve_success=success,
            )
        )

    result = {
        "success": True,
        "pr_number": pr_details.number,
        "contested_threads": [asdict(r) for r in contested_results],
        "total_resolved_checked": len(resolved_threads),
        "total_contested": len(contested),
        "total_reopened": total_reopened,
    }
    click.echo(json.dumps(result, indent=2))
    raise SystemExit(0)


def _unresolve_thread(github: LocalGitHub, repo_root: Path, thread_id: str) -> bool:
    """Attempt to unresolve a thread, returning success status without raising.

    Args:
        github: GitHub gateway instance
        repo_root: Repository root path
        thread_id: GraphQL node ID of the thread

    Returns:
        True if unresolved successfully, False on failure
    """
    try:
        return github.unresolve_review_thread(repo_root, thread_id)
    except RuntimeError:
        return False
