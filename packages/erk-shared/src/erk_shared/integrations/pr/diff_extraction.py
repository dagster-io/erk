"""Diff extraction for AI commit message generation.

This module extracts PR diff content from GitHub and prepares it for AI analysis.
It is part of the two-layer PR submission architecture, called after core_submit
to get the diff for AI-powered commit message generation.
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.prompts import truncate_diff
from erk_shared.scratch.scratch import write_scratch_file


def execute_diff_extraction(
    ctx: ErkContext,
    cwd: Path,
    pr_number: int,
    session_id: str,
) -> Generator[ProgressEvent | CompletionEvent[Path | None]]:
    """Extract PR diff from GitHub API and write to scratch file.

    This operation fetches the diff for an existing PR and writes it to a
    session-scoped scratch file for AI analysis.

    Args:
        ctx: ErkContext providing git and github operations
        cwd: Working directory (must be in a git repository)
        pr_number: PR number to get diff for
        session_id: Session ID for scratch file isolation

    Yields:
        ProgressEvent for status updates
        CompletionEvent with Path to diff file on success, None on failure
    """
    repo_root = ctx.git.get_repository_root(cwd)

    # Get PR diff from GitHub API
    yield ProgressEvent(f"Getting PR diff from GitHub... (gh pr diff {pr_number})")
    pr_diff = ctx.github.get_pr_diff(repo_root, pr_number)
    diff_lines = len(pr_diff.splitlines())
    yield ProgressEvent(f"PR diff retrieved ({diff_lines} lines)", style="success")

    # Truncate diff if needed
    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated:
        yield ProgressEvent("Diff truncated for size", style="warning")

    # Write diff to scratch file
    diff_file = write_scratch_file(
        diff_content,
        session_id=session_id,
        suffix=".diff",
        prefix="pr-diff-",
        repo_root=Path(repo_root),
    )
    yield ProgressEvent(f"Diff written to {diff_file}", style="success")

    yield CompletionEvent(diff_file)
