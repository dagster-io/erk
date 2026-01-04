"""Mark one or more steps as completed or incomplete in progress.md.

This exec command updates the YAML frontmatter in .impl/progress.md to mark
steps as completed or incomplete, then regenerates the checkboxes.

Also updates the GitHub issue metadata (current_step field in plan-header block)
and posts a progress comment when an issue.json reference exists.

Supports marking multiple steps in a single invocation to avoid race conditions
when Claude runs parallel commands.

Usage:
    erk exec mark-step STEP_NUM [STEP_NUM ...]
    erk exec mark-step STEP_NUM --incomplete
    erk exec mark-step STEP_NUM --notes "Implementation details"
    erk exec mark-step STEP_NUM --json

Output:
    JSON format: {"success": true, "step_nums": [N, ...], "completed": true,
                  "total_completed": X, "total_steps": Y, "github_updated": true}
    Human format: ✓ Step N: <description>\n              Progress: X/Y

Exit Codes:
    0: Success
    1: Error (missing file, invalid step number, malformed YAML)

Examples:
    $ erk exec mark-step 5
    ✓ Step 5: Implement feature X
    Progress: 5/10

    $ erk exec mark-step 1 2 3
    ✓ Step 1: First step
    ✓ Step 2: Second step
    ✓ Step 3: Third step
    Progress: 3/10

    $ erk exec mark-step 5 --notes "Added auth middleware"
    ✓ Step 5: Implement feature X
    Progress: 5/10

    $ erk exec mark-step 5 --json
    {"success": true, "step_nums": [5], "completed": true, ...}

    $ erk exec mark-step 5 --incomplete
    ○ Step 5: Implement feature X
    Progress: 4/10
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

import click
import frontmatter

from erk_shared.context.helpers import require_cwd, require_repo_root
from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.github.issues.real import RealGitHubIssues
from erk_shared.github.metadata import (
    extract_step_progress,
    format_progress_update_comment,
    update_step_progress,
)
from erk_shared.impl_folder import read_issue_reference, validate_progress_schema


def _error(msg: str) -> NoReturn:
    """Output error message and exit with code 1."""
    click.echo(f"❌ Error: {msg}", err=True)
    raise SystemExit(1)


def _validate_progress_file(cwd: Path) -> Path:
    """Validate .impl/progress.md exists.

    Args:
        cwd: Current working directory

    Returns:
        Path to progress.md

    Raises:
        SystemExit: If validation fails
    """
    progress_file = cwd / ".impl" / "progress.md"

    if not progress_file.exists():
        _error("No progress.md found in .impl/ folder")

    return progress_file


def _parse_progress_file(progress_file: Path) -> tuple[dict[str, Any], str]:
    """Parse progress.md file and extract metadata and body.

    Args:
        progress_file: Path to progress.md

    Returns:
        Tuple of (metadata dict, body content)

    Raises:
        SystemExit: If YAML is malformed or missing required fields
    """
    content = progress_file.read_text(encoding="utf-8")

    # Gracefully handle YAML parsing errors (third-party API exception handling)
    try:
        post = frontmatter.loads(content)
    except Exception as e:
        _error(f"Failed to parse YAML frontmatter: {e}")

    metadata = post.metadata

    # Validate required fields
    if "steps" not in metadata:
        _error("Progress file missing 'steps' array in frontmatter")

    if "total_steps" not in metadata:
        _error("Progress file missing 'total_steps' in frontmatter")

    if not isinstance(metadata["steps"], list):
        _error("'steps' field must be an array")

    return metadata, post.content


def _validate_step_nums(
    step_nums: tuple[int, ...],
    total_steps: int,
) -> None:
    """Validate all step numbers are in range.

    Args:
        step_nums: Tuple of step numbers (1-indexed)
        total_steps: Total number of steps in the plan

    Raises:
        SystemExit: If any step_num is out of range
    """
    if len(step_nums) == 0:
        _error("At least one step number is required")

    for step_num in step_nums:
        if step_num < 1 or step_num > total_steps:
            _error(f"Step number {step_num} out of range (1-{total_steps})")


def _update_step_status(
    metadata: dict[str, Any],
    step_num: int,
    completed: bool,
) -> None:
    """Update step status in metadata.

    Args:
        metadata: Progress metadata dict (modified in place)
        step_num: Step number (1-indexed), must be pre-validated
        completed: True to mark complete, False for incomplete

    Note:
        Does NOT validate step_num - caller must validate first.
        Does NOT recalculate completed_steps - caller must do this after all updates.
    """
    steps = metadata["steps"]

    # Update step status (convert to 0-indexed)
    steps[step_num - 1]["completed"] = completed


def _recalculate_completed_steps(metadata: dict[str, Any]) -> None:
    """Recalculate completed_steps count from steps array.

    Args:
        metadata: Progress metadata dict (modified in place)
    """
    steps = metadata["steps"]
    completed_count = sum(1 for step in steps if step["completed"])
    metadata["completed_steps"] = completed_count


def _regenerate_checkboxes(steps: list[dict[str, Any]]) -> str:
    """Regenerate checkbox markdown from steps array.

    Args:
        steps: List of step dicts with 'title' and 'completed' fields

    Returns:
        Markdown body with checkboxes
    """
    lines = ["# Progress Tracking\n"]

    for step in steps:
        checkbox = "[x]" if step["completed"] else "[ ]"
        lines.append(f"- {checkbox} {step['title']}")

    lines.append("")  # Trailing newline
    return "\n".join(lines)


def _write_progress_file(
    progress_file: Path,
    metadata: dict[str, Any],
    current_step: int,
) -> None:
    """Write updated progress.md file with new metadata and regenerated checkboxes.

    Args:
        progress_file: Path to progress.md
        metadata: Updated metadata dict
        current_step: Highest completed step number (0 = not started)
    """
    # Update current_step in metadata
    metadata["current_step"] = current_step

    # Regenerate body from steps array
    body = _regenerate_checkboxes(metadata["steps"])

    # Create frontmatter post and write atomically
    post = frontmatter.Post(body, **metadata)
    content = frontmatter.dumps(post)
    progress_file.write_text(content, encoding="utf-8")


def _calculate_current_step(metadata: dict[str, Any]) -> int:
    """Calculate current step as highest completed step number.

    Args:
        metadata: Progress metadata dict

    Returns:
        Highest completed step number (1-indexed), or 0 if none completed
    """
    current_step = 0
    for i, step in enumerate(metadata["steps"]):
        if step["completed"]:
            current_step = max(current_step, i + 1)
    return current_step


def _get_session_id() -> str | None:
    """Get Claude Code session ID from environment variable."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID")


def _get_user() -> str | None:
    """Get current user from GitHub auth or git config."""
    github_issues = RealGitHubIssues(target_repo=None)
    return github_issues.get_current_username()


def _update_github_issue(
    cwd: Path,
    issue_number: int,
    previous_step: int,
    current_step: int,
    total_steps: int,
    steps_completed: list[int],
    step_titles: list[str],
    notes: str | None,
) -> bool:
    """Update GitHub issue metadata and post progress comment.

    Args:
        cwd: Current working directory (repo root)
        issue_number: Issue number to update
        previous_step: Step number before this update
        current_step: Current step number after this update
        total_steps: Total number of steps
        steps_completed: List of step numbers marked complete in this update
        step_titles: List of step titles (parallel to steps_completed)
        notes: Optional implementation notes

    Returns:
        True if update succeeded, False if failed (silently)
    """
    try:
        github_issues = RealGitHubIssues(target_repo=None)

        # Update plan-header metadata with current_step
        issue_info = github_issues.get_issue(cwd, issue_number)
        updated_body = update_step_progress(issue_info.body, current_step)
        github_issues.update_issue_body(cwd, issue_number, updated_body)

        # Post progress comment
        timestamp = datetime.now(UTC).isoformat()
        session_id = _get_session_id()
        user = _get_user()

        comment_body = format_progress_update_comment(
            timestamp=timestamp,
            steps_completed=steps_completed,
            step_titles=step_titles,
            previous_step=previous_step,
            current_step=current_step,
            total_steps=total_steps,
            session_id=session_id,
            user=user,
            notes=notes,
        )
        github_issues.add_comment(cwd, issue_number, comment_body)

        return True
    except Exception as e:
        # Best-effort: GitHub update is optional, local update is authoritative
        # Log to stderr so failures are diagnosable without blocking the operation
        print(f"Warning: GitHub update failed: {e}", file=sys.stderr)
        return False


def _mark_step_github_only(
    ctx: click.Context,
    issue_number: int,
    step_nums: tuple[int, ...],
    completed: bool,
    notes: str | None,
    output_json: bool,
) -> None:
    """Mark steps via GitHub API only, without local .impl/ folder.

    This mode is used for local execution without the .impl/ file overhead.
    Step progress is read from and written to the GitHub issue directly.
    """
    repo_root = require_repo_root(ctx)
    github_issues = require_github_issues(ctx)

    # Validate step_nums is not empty
    if len(step_nums) == 0:
        _error("At least one step number is required")

    # Fetch issue and extract step progress
    issue_info = github_issues.get_issue(repo_root, issue_number)
    progress = extract_step_progress(issue_info.body)

    if progress is None:
        _error(
            f"Issue #{issue_number} does not have step progress metadata. "
            "Ensure the issue was created with step tracking enabled."
        )

    # Type narrowing: progress is guaranteed not None after _error() (NoReturn)
    assert progress is not None  # for pyright

    # Validate step numbers against total_steps
    for step_num in step_nums:
        if step_num < 1 or step_num > progress.total_steps:
            _error(f"Step number {step_num} out of range (1-{progress.total_steps})")

    # Calculate previous_step (from GitHub's current state)
    previous_step = progress.current_step

    # Calculate new current_step as highest completed step
    # For "completed" mode: max of existing current_step and newly completed steps
    # For "incomplete" mode: recalculate from scratch
    if completed:
        new_current_step = max(previous_step, *step_nums)
    else:
        # When marking incomplete, current_step becomes highest step BELOW the unmarked ones
        # that was previously completed
        remaining_completed = previous_step
        for step_num in step_nums:
            if step_num == remaining_completed:
                remaining_completed = step_num - 1
        new_current_step = max(0, remaining_completed)

    # Update GitHub issue body with new current_step
    updated_body = update_step_progress(issue_info.body, new_current_step)
    github_issues.update_issue_body(repo_root, issue_number, updated_body)

    # Collect step titles for progress comment
    step_titles = []
    for step_num in step_nums:
        # Find the step title from the progress.steps list
        matching_step = next((s for s in progress.steps if s.number == step_num), None)
        if matching_step is not None:
            step_titles.append(matching_step.title)
        else:
            step_titles.append(f"Step {step_num}")

    # Post progress comment (only for completed, not incomplete)
    github_updated = True
    if completed:
        timestamp = datetime.now(UTC).isoformat()
        session_id = _get_session_id()
        user = _get_user()

        comment_body = format_progress_update_comment(
            timestamp=timestamp,
            steps_completed=list(step_nums),
            step_titles=step_titles,
            previous_step=previous_step,
            current_step=new_current_step,
            total_steps=progress.total_steps,
            session_id=session_id,
            user=user,
            notes=notes,
        )
        github_issues.add_comment(repo_root, issue_number, comment_body)

    # Calculate total_completed for output
    # In GitHub-only mode, we track via current_step (highest completed)
    total_completed = new_current_step

    # Output result
    if output_json:
        result = {
            "success": True,
            "step_nums": list(step_nums),
            "completed": completed,
            "total_completed": total_completed,
            "total_steps": progress.total_steps,
            "github_updated": github_updated,
            "mode": "github-only",
        }
        click.echo(json.dumps(result))
    else:
        status_icon = "✓" if completed else "○"
        for step_num, title in zip(step_nums, step_titles, strict=True):
            click.echo(f"{status_icon} Step {step_num}: {title}")
        click.echo(f"Progress: {new_current_step}/{progress.total_steps}")


@click.command(name="mark-step")
@click.argument("step_nums", type=int, nargs=-1)
@click.option(
    "--completed/--incomplete",
    default=True,
    help="Mark as completed (default) or incomplete",
)
@click.option("--notes", type=str, help="Implementation notes to include in progress comment")
@click.option("--json", "output_json", is_flag=True, help="Output JSON format")
@click.option(
    "--issue",
    type=int,
    help="GitHub issue number (GitHub-only mode, no local .impl/ required)",
)
@click.pass_context
def mark_step(
    ctx: click.Context,
    step_nums: tuple[int, ...],
    completed: bool,
    notes: str | None,
    output_json: bool,
    issue: int | None,
) -> None:
    """Mark one or more steps as completed or incomplete.

    When --issue is provided, operates in GitHub-only mode (no local .impl/ required).
    Otherwise, updates the YAML frontmatter in .impl/progress.md.

    Also updates GitHub issue metadata and posts a progress comment.

    Supports multiple step numbers to avoid race conditions from parallel execution.

    STEP_NUMS: One or more step numbers to mark (1-indexed)
    """
    # GitHub-only mode: operate entirely via GitHub API
    if issue is not None:
        _mark_step_github_only(
            ctx=ctx,
            issue_number=issue,
            step_nums=step_nums,
            completed=completed,
            notes=notes,
            output_json=output_json,
        )
        return

    # Local mode: use .impl/progress.md as source of truth
    cwd = require_cwd(ctx)
    progress_file = _validate_progress_file(cwd)
    metadata, _ = _parse_progress_file(progress_file)

    # Validate all steps first (fail fast before any modifications)
    _validate_step_nums(step_nums, metadata["total_steps"])

    # Calculate previous_step before making any changes
    previous_step = _calculate_current_step(metadata)

    # Update all steps in a single read-modify-write cycle
    for step_num in step_nums:
        _update_step_status(metadata, step_num, completed)

    # Recalculate completed count once after all updates
    _recalculate_completed_steps(metadata)

    # Calculate new current_step after updates
    current_step = _calculate_current_step(metadata)

    _write_progress_file(progress_file, metadata, current_step)

    # Verify file integrity after write - fail hard on validation error
    errors = validate_progress_schema(progress_file)
    if errors:
        _error(f"Post-write validation failed: {'; '.join(errors)}")

    # Collect step titles for the completed steps
    step_titles = [metadata["steps"][s - 1]["title"] for s in step_nums]

    # Update GitHub issue metadata and post comment (best-effort)
    github_updated = False
    impl_dir = cwd / ".impl"
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is not None and completed:
        # Only post progress comment when marking steps complete (not incomplete)
        github_updated = _update_github_issue(
            cwd=cwd,
            issue_number=issue_ref.issue_number,
            previous_step=previous_step,
            current_step=current_step,
            total_steps=metadata["total_steps"],
            steps_completed=list(step_nums),
            step_titles=step_titles,
            notes=notes,
        )

    # Output result
    if output_json:
        result = {
            "success": True,
            "step_nums": list(step_nums),
            "completed": completed,
            "total_completed": metadata["completed_steps"],
            "total_steps": metadata["total_steps"],
            "github_updated": github_updated,
        }
        click.echo(json.dumps(result))
    else:
        # Output each marked step
        status_icon = "✓" if completed else "○"
        for step_num in step_nums:
            step_title = metadata["steps"][step_num - 1]["title"]
            click.echo(f"{status_icon} Step {step_num}: {step_title}")
        click.echo(f"Progress: {metadata['completed_steps']}/{metadata['total_steps']}")
