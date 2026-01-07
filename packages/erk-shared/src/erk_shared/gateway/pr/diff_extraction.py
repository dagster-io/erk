"""Diff extraction for AI commit message generation.

This module extracts PR diff content from GitHub and prepares it for AI analysis.
It is part of the two-layer PR submission architecture, called after core_submit
to get the diff for AI-powered commit message generation.
"""

import re
from collections.abc import Generator
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.prompts import truncate_diff
from erk_shared.scratch.scratch import write_scratch_file

# Lock files that are auto-generated and add no value to PR descriptions.
# These are filtered out before sending diffs to AI for analysis.
EXCLUDED_LOCK_FILES = frozenset(
    {
        "uv.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.lock",
        "poetry.lock",
        "Pipfile.lock",
        "composer.lock",
        "Gemfile.lock",
    }
)

# Pattern to extract file path from diff header: "diff --git a/path/to/file b/path/to/file"
_DIFF_FILE_PATH_PATTERN = re.compile(r"^diff --git a/(.+?) b/")


def filter_diff_excluded_files(diff: str) -> str:
    """Filter out lock files and other auto-generated files from a diff.

    Splits the diff by 'diff --git' markers and removes sections where
    the filename (basename) is in EXCLUDED_LOCK_FILES.

    Args:
        diff: The full diff string from git/GitHub

    Returns:
        Filtered diff with excluded file sections removed
    """
    if not diff:
        return diff

    # Split by "diff --git" while preserving the delimiter
    # The first element will be empty or contain any content before the first diff
    sections = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)

    filtered_sections: list[str] = []
    for section in sections:
        # Skip empty sections
        if not section.strip():
            continue

        # Check if this section starts with a diff header
        if not section.startswith("diff --git "):
            # This is content before the first diff (usually empty), keep it
            filtered_sections.append(section)
            continue

        # Extract the file path from the diff header
        match = _DIFF_FILE_PATH_PATTERN.match(section)
        if match:
            file_path = match.group(1)
            filename = Path(file_path).name

            # Skip this section if the filename is in the excluded set
            if filename in EXCLUDED_LOCK_FILES:
                continue

        filtered_sections.append(section)

    return "".join(filtered_sections)


def execute_diff_extraction(
    ctx: ErkContext,
    cwd: Path,
    pr_number: int,
    session_id: str,
) -> Generator[ProgressEvent | CompletionEvent[Path | None]]:
    """Extract PR diff using local git and write to scratch file.

    This operation computes the diff between HEAD and the PR's base branch,
    then writes it to a session-scoped scratch file for AI analysis.

    Uses local git diff instead of GitHub API to avoid size limits (GitHub
    returns HTTP 406 for diffs exceeding ~20k lines).

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

    # Get base branch for the PR, fall back to trunk if not available
    yield ProgressEvent(f"Getting diff for PR #{pr_number}...")
    base_branch = ctx.github.get_pr_base_branch(repo_root, pr_number)
    if base_branch is None:
        base_branch = ctx.git.detect_trunk_branch(repo_root)

    # Use local git diff - no size limits unlike GitHub API
    pr_diff = ctx.git.get_diff_to_branch(cwd, base_branch)
    diff_lines = len(pr_diff.splitlines())
    yield ProgressEvent(f"Diff retrieved ({diff_lines} lines)", style="success")

    # Filter out lock files before truncation
    pr_diff = filter_diff_excluded_files(pr_diff)

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
