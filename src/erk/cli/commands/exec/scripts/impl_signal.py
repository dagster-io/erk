"""Signal implementation events (started/ended) to GitHub.

This exec command wraps the start/end signaling operations:
- "started": Combines post-start-comment and mark-impl-started
- "ended": Runs mark-impl-ended

Provides a single entry point for /erk:plan-implement to signal events
with graceful failure (always exits 0 for || true pattern).

Usage:
    erk exec impl-signal started
    erk exec impl-signal ended

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk exec impl-signal started
    {"success": true, "event": "started", "issue_number": 123}

    $ erk exec impl-signal ended
    {"success": true, "event": "ended", "issue_number": 123}
"""

import getpass
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_claude_installation,
    require_repo_root,
)
from erk_shared.context.helpers import (
    require_issues as require_github_issues,
)
from erk_shared.env import in_github_actions
from erk_shared.github.metadata import (
    create_start_status_block,
    render_erk_issue_event,
    update_plan_header_local_impl_event,
    update_plan_header_remote_impl,
)
from erk_shared.impl_folder import (
    parse_progress_frontmatter,
    read_issue_reference,
    write_local_run_state,
)


@dataclass(frozen=True)
class SignalSuccess:
    """Success response for signal command."""

    success: bool
    event: str
    issue_number: int


@dataclass(frozen=True)
class SignalError:
    """Error response for signal command."""

    success: bool
    event: str
    error_type: str
    message: str


def _output_error(event: str, error_type: str, message: str) -> None:
    """Output error JSON and exit gracefully."""
    result = SignalError(
        success=False,
        event=event,
        error_type=error_type,
        message=message,
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


def _delete_claude_plan_file(ctx: click.Context, session_id: str, cwd: Path) -> bool:
    """Delete the Claude plan file for the given session.

    This is called when implementation starts to clean up the plan file.
    The plan content has already been saved to GitHub and snapshotted.

    Args:
        ctx: Click context for dependency injection.
        session_id: The session ID to look up the plan slug.
        cwd: Current working directory for hint.

    Returns:
        True if file was deleted, False if not found or error.
    """
    try:
        installation = require_claude_installation(ctx)
    except SystemExit:
        return False

    slugs = installation.extract_slugs_from_session(cwd, session_id)
    if not slugs:
        return False

    plan_file = installation.get_plans_dir_path() / f"{slugs[-1]}.md"
    if plan_file.exists():
        plan_file.unlink()
        return True
    return False


def _get_worktree_name() -> str | None:
    """Get current worktree name from git worktree list."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        current_dir = Path.cwd().resolve()
        lines = result.stdout.strip().split("\n")

        for line in lines:
            if line.startswith("worktree "):
                worktree_path = Path(line[len("worktree ") :])
                if current_dir == worktree_path or current_dir.is_relative_to(worktree_path):
                    return worktree_path.name

        return None
    except subprocess.CalledProcessError:
        return None


def _get_branch_name() -> str | None:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        if branch:
            return branch
        return None
    except subprocess.CalledProcessError:
        return None


def _signal_started(ctx: click.Context, session_id: str | None) -> None:
    """Handle 'started' event - post comment and update metadata."""
    event = "started"

    # Find impl directory (.impl/ or .worker-impl/) - check BEFORE context access
    impl_dir = Path.cwd() / ".impl"
    if not impl_dir.exists():
        impl_dir = Path.cwd() / ".worker-impl"

    # Read issue reference FIRST (doesn't require context)
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        _output_error(event, "no-issue-reference", "No issue reference found in issue.json")
        return

    # Delete Claude plan file if session_id provided
    # The plan has been saved to GitHub and snapshotted, so it's safe to delete
    if session_id is not None:
        _delete_claude_plan_file(ctx, session_id, Path.cwd())

    # Now get context dependencies (after confirming we need them)
    try:
        repo_root = require_repo_root(ctx)
    except SystemExit:
        _output_error(event, "context-not-initialized", "Context not initialized")
        return

    # Get worktree and branch names
    worktree_name = _get_worktree_name()
    if worktree_name is None:
        _output_error(event, "worktree-detection-failed", "Could not determine worktree name")
        return

    branch_name = _get_branch_name()
    if branch_name is None:
        _output_error(event, "branch-detection-failed", "Could not determine branch name")
        return

    # Read total steps from progress.md
    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        _output_error(event, "no-progress-file", f"Progress file not found: {progress_file}")
        return

    content = progress_file.read_text(encoding="utf-8")
    frontmatter = parse_progress_frontmatter(content)
    if frontmatter is None:
        _output_error(event, "invalid-progress-format", "Invalid YAML frontmatter in progress.md")
        return

    total_steps = frontmatter["total_steps"]

    # Capture metadata
    timestamp = datetime.now(UTC).isoformat()
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
    user = getpass.getuser()

    # Write local state file first (fast, no network)
    try:
        write_local_run_state(
            impl_dir=impl_dir,
            last_event="started",
            timestamp=timestamp,
            user=user,
            session_id=session_id,
        )
    except (FileNotFoundError, ValueError) as e:
        _output_error(event, "local-state-write-failed", f"Failed to write local state: {e}")
        return

    # Get GitHub Issues from context
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        _output_error(event, "context-not-initialized", "Context not initialized")
        return

    # Post start comment
    try:
        block = create_start_status_block(
            total_steps=total_steps,
            worktree=worktree_name,
            branch=branch_name,
        )

        description = f"""**Worktree:** `{worktree_name}`
**Branch:** `{branch_name}`"""

        comment_body = render_erk_issue_event(
            title="🚀 Starting implementation",
            metadata=block,
            description=description,
        )

        github.add_comment(repo_root, issue_ref.issue_number, comment_body)
    except RuntimeError as e:
        _output_error(event, "github-comment-failed", f"Failed to post comment: {e}")
        return

    # Update issue metadata
    try:
        issue = github.get_issue(repo_root, issue_ref.issue_number)

        if in_github_actions():
            updated_body = update_plan_header_remote_impl(
                issue_body=issue.body,
                remote_impl_at=timestamp,
            )
        else:
            updated_body = update_plan_header_local_impl_event(
                issue_body=issue.body,
                local_impl_at=timestamp,
                event="started",
                session_id=session_id,
                user=user,
            )

        github.update_issue_body(repo_root, issue_ref.issue_number, updated_body)
    except (RuntimeError, ValueError):
        # Non-fatal - comment was posted, metadata update failed
        # Continue successfully
        pass

    result = SignalSuccess(
        success=True,
        event=event,
        issue_number=issue_ref.issue_number,
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


def _signal_ended(ctx: click.Context) -> None:
    """Handle 'ended' event - update metadata."""
    event = "ended"

    # Find impl directory - check BEFORE context access
    impl_dir = Path.cwd() / ".impl"
    if not impl_dir.exists():
        impl_dir = Path.cwd() / ".worker-impl"

    # Read issue reference FIRST (doesn't require context)
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        _output_error(event, "no-issue-reference", "No issue reference found in issue.json")
        return

    # Now get context dependencies (after confirming we need them)
    try:
        repo_root = require_repo_root(ctx)
    except SystemExit:
        _output_error(event, "context-not-initialized", "Context not initialized")
        return

    # Capture metadata
    timestamp = datetime.now(UTC).isoformat()
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
    user = getpass.getuser()

    # Write local state file first
    try:
        write_local_run_state(
            impl_dir=impl_dir,
            last_event="ended",
            timestamp=timestamp,
            user=user,
            session_id=session_id,
        )
    except (FileNotFoundError, ValueError) as e:
        _output_error(event, "local-state-write-failed", f"Failed to write local state: {e}")
        return

    # Get GitHub Issues from context
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        _output_error(event, "context-not-initialized", "Context not initialized")
        return

    # Update issue metadata
    try:
        issue = github.get_issue(repo_root, issue_ref.issue_number)

        if in_github_actions():
            updated_body = update_plan_header_remote_impl(
                issue_body=issue.body,
                remote_impl_at=timestamp,
            )
        else:
            updated_body = update_plan_header_local_impl_event(
                issue_body=issue.body,
                local_impl_at=timestamp,
                event="ended",
                session_id=session_id,
                user=user,
            )

        github.update_issue_body(repo_root, issue_ref.issue_number, updated_body)
    except (RuntimeError, ValueError) as e:
        _output_error(event, "github-api-failed", f"Failed to update issue: {e}")
        return

    result = SignalSuccess(
        success=True,
        event=event,
        issue_number=issue_ref.issue_number,
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)


@click.command(name="impl-signal")
@click.argument("event", type=click.Choice(["started", "ended"]))
@click.option(
    "--session-id",
    default=None,
    help="Session ID for plan file deletion on 'started' event",
)
@click.pass_context
def impl_signal(ctx: click.Context, event: str, session_id: str | None) -> None:
    """Signal implementation events to GitHub.

    EVENT can be 'started' or 'ended'.

    'started' posts a start comment and updates issue metadata.
    'ended' updates issue metadata with ended event.

    When --session-id is provided on 'started', also deletes the Claude plan file
    (the content has been saved to GitHub and snapshotted).

    Always exits with code 0 for graceful degradation (|| true pattern).
    """
    if event == "started":
        _signal_started(ctx, session_id)
    else:
        _signal_ended(ctx)
