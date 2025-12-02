"""Prepare branch for PR submission (squash + diff extraction, no submit).

This script handles the mechanical preparation of a branch for PR submission,
without actually submitting to GitHub. It checks for conflicts, squashes commits,
and extracts the diff for AI commit message generation.

Usage:
    dot-agent run gt pr-prep --session-id <id>

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (validation failed or operation failed)

Error Types:
    - gt_not_authenticated: Graphite CLI is not authenticated
    - gh_not_authenticated: GitHub CLI is not authenticated
    - no_branch: Could not determine current branch
    - no_parent: Could not determine parent branch
    - no_commits: No commits found in branch
    - restack_conflict: Restack conflicts detected (user must resolve)
    - squash_conflict: Conflicts detected during squash
    - squash_failed: Failed to squash commits

Examples:
    $ dot-agent run gt pr-prep --session-id abc123
    {"success": true, "diff_file": "/path/to/diff", ...}
"""

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.real import RealGtKit

PrepErrorType = Literal[
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_parent",
    "no_commits",
    "restack_conflict",
    "squash_conflict",
    "squash_failed",
]


@dataclass
class PrepResult:
    """Success result from prep phase."""

    success: bool
    diff_file: str
    repo_root: str
    current_branch: str
    parent_branch: str
    commit_count: int
    squashed: bool
    message: str


@dataclass
class PrepError:
    """Error result from prep phase."""

    success: bool
    error_type: PrepErrorType
    message: str
    details: dict[str, str | bool]


def execute_prep(session_id: str, ops: GtKit | None = None) -> PrepResult | PrepError:
    """Execute prep phase: check auth, check conflicts, squash, extract diff.

    Args:
        session_id: Claude session ID for scratch file isolation. Writes diff
            to .tmp/<session_id>/ in repo root (readable by subagents without
            permission prompts).
        ops: Optional GtKit for dependency injection.

    Returns:
        PrepResult on success, or PrepError on failure
    """
    if ops is None:
        ops = RealGtKit()

    # Step 0a: Check Graphite authentication FIRST
    click.echo("  ↳ Checking Graphite authentication... (gt auth whoami)", err=True)
    gt_authenticated, gt_username, _ = ops.main_graphite().check_auth_status()
    if not gt_authenticated:
        return PrepError(
            success=False,
            error_type="gt_not_authenticated",
            message="Graphite CLI (gt) is not authenticated",
            details={
                "fix": "Run 'gt auth' to authenticate with Graphite",
                "authenticated": False,
            },
        )
    click.echo(f"  ✓ Authenticated as {gt_username}", err=True)

    # Step 0b: Check GitHub authentication
    click.echo("  ↳ Checking GitHub authentication... (gh auth status)", err=True)
    gh_authenticated, gh_username, _ = ops.github().check_auth_status()
    if not gh_authenticated:
        return PrepError(
            success=False,
            error_type="gh_not_authenticated",
            message="GitHub CLI (gh) is not authenticated",
            details={
                "fix": "Run 'gh auth login' to authenticate with GitHub",
                "authenticated": False,
            },
        )
    click.echo(f"  ✓ Authenticated as {gh_username}", err=True)

    cwd = Path.cwd()

    # Step 1: Get current branch
    branch_name = ops.git().get_current_branch(cwd)
    if branch_name is None:
        return PrepError(
            success=False,
            error_type="no_branch",
            message="Could not determine current branch",
            details={"branch_name": "unknown"},
        )

    # Step 2: Get parent branch
    repo_root = ops.git().get_repository_root(cwd)
    parent_branch = ops.main_graphite().get_parent_branch(ops.git(), repo_root, branch_name)
    if parent_branch is None:
        return PrepError(
            success=False,
            error_type="no_parent",
            message=f"Could not determine parent branch for: {branch_name}",
            details={"branch_name": branch_name},
        )

    # Step 3: Check for restack conflicts (CRITICAL - abort if any)
    click.echo("  ↳ Checking for restack conflicts... (gt restack --dry-run)", err=True)
    try:
        # Run restack dry-run to check for conflicts
        ops.main_graphite().restack(repo_root, no_interactive=True, quiet=True)
        click.echo("  ✓ No restack conflicts detected", err=True)
    except subprocess.CalledProcessError as e:
        # Check if failure was due to conflicts
        stderr = e.stderr if hasattr(e, "stderr") else ""
        combined_output = (e.stdout if hasattr(e, "stdout") else "") + stderr
        if "conflict" in combined_output.lower() or "merge conflict" in combined_output.lower():
            return PrepError(
                success=False,
                error_type="restack_conflict",
                message="Restack conflicts detected. Run 'gt restack' to resolve conflicts first.",
                details={
                    "branch_name": branch_name,
                    "parent_branch": parent_branch,
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": stderr,
                },
            )
        # Generic restack check failure - proceed anyway
        click.echo("  ⚠️  Could not verify restack status, proceeding", err=True)

    # Step 4: Count commits in branch
    commit_count = ops.git().count_commits_ahead(cwd, parent_branch)
    if commit_count == 0:
        return PrepError(
            success=False,
            error_type="no_commits",
            message=f"No commits found in branch: {branch_name}",
            details={"branch_name": branch_name, "parent_branch": parent_branch},
        )

    # Step 5: Squash commits only if 2+ commits
    squashed = False
    if commit_count >= 2:
        click.echo(f"  ↳ Squashing {commit_count} commits... (gt squash --no-edit)", err=True)
        try:
            ops.main_graphite().squash_branch(repo_root, quiet=False)
            squashed = True
            click.echo(f"  ✓ Squashed {commit_count} commits into 1", err=True)
        except subprocess.CalledProcessError as e:
            # Check if failure was due to merge conflict
            stderr = e.stderr if hasattr(e, "stderr") else ""
            combined_output = (e.stdout if hasattr(e, "stdout") else "") + stderr
            if "conflict" in combined_output.lower() or "merge conflict" in combined_output.lower():
                return PrepError(
                    success=False,
                    error_type="squash_conflict",
                    message="Merge conflicts detected while squashing commits",
                    details={
                        "branch_name": branch_name,
                        "commit_count": str(commit_count),
                        "stdout": e.stdout if hasattr(e, "stdout") else "",
                        "stderr": stderr,
                    },
                )

            # Generic squash failure
            return PrepError(
                success=False,
                error_type="squash_failed",
                message="Failed to squash commits",
                details={
                    "branch_name": branch_name,
                    "commit_count": str(commit_count),
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": stderr,
                },
            )

    # Step 6: Get local diff (not PR diff - we haven't submitted yet)
    click.echo(f"  ↳ Getting diff from {parent_branch}...HEAD", err=True)
    diff_content = ops.git().get_diff_to_branch(repo_root, parent_branch)
    diff_lines = len(diff_content.splitlines())
    click.echo(f"  ✓ Diff retrieved ({diff_lines} lines)", err=True)

    # Step 7: Write diff to scratch file
    from erk_shared.scratch.scratch import write_scratch_file

    diff_file = str(
        write_scratch_file(
            diff_content,
            session_id=session_id,
            suffix=".diff",
            prefix="pr-prep-diff-",
            repo_root=Path(repo_root),
        )
    )
    click.echo(f"  ✓ Diff written to {diff_file}", err=True)

    # Build success message
    message_parts = [f"Branch prepared for PR: {branch_name}"]
    if squashed:
        message_parts.append(f"Squashed {commit_count} commits into 1")
    else:
        message_parts.append("Single commit, no squash needed")
    message = "\n".join(message_parts)

    return PrepResult(
        success=True,
        diff_file=diff_file,
        repo_root=str(repo_root),
        current_branch=branch_name,
        parent_branch=parent_branch,
        commit_count=commit_count,
        squashed=squashed,
        message=message,
    )


@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID for scratch file isolation. "
    "Writes diff to .tmp/<session-id>/ in repo root.",
)
def pr_prep(session_id: str) -> None:
    """Prepare branch for PR submission (squash + diff extraction, no submit).

    Returns JSON with diff file path for AI commit message generation.
    """
    try:
        result = execute_prep(session_id=session_id)
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, PrepError):
            raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None
