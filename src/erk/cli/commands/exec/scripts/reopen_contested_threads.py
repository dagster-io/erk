"""Detect and reopen contested resolved PR review threads.

A "contested" thread is one that was resolved by erk:pr-address (identified by
the PR_ADDRESS_MARKER in a comment) but has received additional reviewer comments
after the last marker comment.

This exec command fetches all resolved threads, detects contested ones, and
unresolves them so they will be picked up by subsequent pr-address runs.

Usage:
    erk exec reopen-contested-threads
    erk exec reopen-contested-threads --pr 123

Output:
    JSON with result summary

Exit Codes:
    0: Always (even on error, to support non-blocking use)

Examples:
    $ erk exec reopen-contested-threads
    {
      "success": true,
      "pr_number": 123,
      "contested_threads": [...],
      "total_resolved_checked": 5,
      "total_contested": 1,
      "total_reopened": 1
    }
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk.cli.script_output import handle_non_ideal_exit
from erk_shared.context.helpers import get_current_branch, require_github, require_repo_root
from erk_shared.gateway.github.checks import GitHubChecks
from erk_shared.gateway.github.types import PRReviewThread
from erk_shared.non_ideal_state import BranchDetectionFailed

if TYPE_CHECKING:
    from erk_shared.gateway.github.abc import LocalGitHub

# Marker placed in resolution comments by erk:pr-address
PR_ADDRESS_MARKER = "<!-- erk:pr-address-resolved -->"


# --- Pure helper functions (testable without gateway) ---


def _has_marker(body: str) -> bool:
    """Return True if the comment body contains the pr-address resolution marker."""
    return PR_ADDRESS_MARKER in body


def _find_contested_threads(threads: list[PRReviewThread]) -> list[PRReviewThread]:
    """Find resolved threads that have reviewer comments after the last marker comment.

    A thread is contested if:
    1. It is resolved
    2. At least one comment contains the PR_ADDRESS_MARKER
    3. There are comments after the last marker comment

    Args:
        threads: All review threads (resolved and unresolved)

    Returns:
        List of contested threads (resolved, had marker, have post-marker comments)
    """
    contested: list[PRReviewThread] = []
    for thread in threads:
        if not thread.is_resolved:
            continue

        comments = list(thread.comments)

        # Find the index of the last marker comment
        last_marker_index: int | None = None
        for i, comment in enumerate(comments):
            if _has_marker(comment.body):
                last_marker_index = i

        if last_marker_index is None:
            # No marker — this was manually resolved, not by pr-address
            continue

        # Check if any comments exist after the last marker
        if last_marker_index < len(comments) - 1:
            contested.append(thread)

    return contested


# --- Output dataclasses ---


@dataclass(frozen=True)
class ContestedThreadResult:
    """Result for a single contested thread unresolve attempt."""

    thread_id: str
    path: str
    line: int | None
    unresolve_success: bool


@dataclass(frozen=True)
class ReopenContestResult:
    """Success result for reopen-contested-threads command."""

    success: bool
    pr_number: int
    contested_threads: list[ContestedThreadResult]
    total_resolved_checked: int
    total_contested: int
    total_reopened: int


@dataclass(frozen=True)
class ReopenContestError:
    """Error result for reopen-contested-threads command."""

    success: bool
    error_type: str
    message: str


# --- Command ---


@click.command(name="reopen-contested-threads")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.pass_context
@handle_non_ideal_exit
def reopen_contested_threads(ctx: click.Context, pr: int | None) -> None:
    """Detect and reopen contested resolved PR review threads.

    A contested thread is one resolved by erk:pr-address that has received
    additional reviewer comments after resolution. Reopening these threads
    ensures subsequent pr-address runs will see and address the pushback.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    # Resolve PR number
    if pr is None:
        branch = GitHubChecks.branch(get_current_branch(ctx))
        if isinstance(branch, BranchDetectionFailed):
            branch.ensure()
        assert not isinstance(branch, BranchDetectionFailed)
        pr_details = GitHubChecks.pr_for_branch(github, repo_root, branch).ensure()
    else:
        pr_details = GitHubChecks.pr_by_number(github, repo_root, pr).ensure()

    pr_number = pr_details.number

    # Fetch all threads including resolved
    all_threads = github.get_pr_review_threads(repo_root, pr_number, include_resolved=True)
    resolved_threads = [t for t in all_threads if t.is_resolved]

    # Detect contested threads
    contested = _find_contested_threads(resolved_threads)

    # Unresolve each contested thread
    thread_results: list[ContestedThreadResult] = []
    for thread in contested:
        success = _unresolve_thread(github, repo_root, thread)
        thread_results.append(
            ContestedThreadResult(
                thread_id=thread.id,
                path=thread.path,
                line=thread.line,
                unresolve_success=success,
            )
        )

    total_reopened = sum(1 for r in thread_results if r.unresolve_success)

    result = ReopenContestResult(
        success=True,
        pr_number=pr_number,
        contested_threads=thread_results,
        total_resolved_checked=len(resolved_threads),
        total_contested=len(contested),
        total_reopened=total_reopened,
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


def _unresolve_thread(github: LocalGitHub, repo_root: Path, thread: PRReviewThread) -> bool:
    """Attempt to unresolve a single thread, returning success status."""
    try:
        return github.unresolve_review_thread(repo_root, thread.id)
    except RuntimeError:
        return False
