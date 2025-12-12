"""Signal implementation events (started/ended) to GitHub.

This kit CLI command wraps the start/end signaling operations:
- "started": Combines post-start-comment and mark-impl-started
- "ended": Runs mark-impl-ended

Provides a single entry point for /erk:plan-implement to signal events
with graceful failure (always exits 0 for || true pattern).

Usage:
    erk kit exec erk impl-signal started
    erk kit exec erk impl-signal ended

Output:
    JSON with success status or error information
    Always exits with code 0 (graceful degradation for || true pattern)

Exit Codes:
    0: Always (even on error, to support || true pattern)

Examples:
    $ erk kit exec erk impl-signal started
    {"success": true, "event": "started", "issue_number": 123}

    $ erk kit exec erk impl-signal ended
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

from erk.kits.context_helpers import require_github_issues
from erk_shared.context.helpers import require_repo_root
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


def _signal_started(ctx: click.Context) -> None:
    """Handle 'started' event - post comment and update metadata."""
    event = "started"

    # Find impl directory (.impl/ or .worker-impl/) - check BEFORE context access
    impl_dir = Path.cwd() / ".impl"
    if not impl_dir.exists():
        impl_dir = Path.cwd() / ".worker-impl"

    # Read issue reference FIRST (doesn't require context)
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        _output_error(event, "no_issue_reference", "No issue reference found in issue.json")
        return

    # Now get context dependencies (after confirming we need them)
    try:
        repo_root = require_repo_root(ctx)
    except SystemExit:
        _output_error(event, "context_not_initialized", "Context not initialized")
        return

    # Get worktree and branch names
    worktree_name = _get_worktree_name()
    if worktree_name is None:
        _output_error(event, "worktree_detection_failed", "Could not determine worktree name")
        return

    branch_name = _get_branch_name()
    if branch_name is None:
        _output_error(event, "branch_detection_failed", "Could not determine branch name")
        return

    # Read total steps from progress.md
    progress_file = impl_dir / "progress.md"
    if not progress_file.exists():
        _output_error(event, "no_progress_file", f"Progress file not found: {progress_file}")
        return

    content = progress_file.read_text(encoding="utf-8")
    frontmatter = parse_progress_frontmatter(content)
    if frontmatter is None:
        _output_error(event, "invalid_progress_format", "Invalid YAML frontmatter in progress.md")
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
        _output_error(event, "local_state_write_failed", f"Failed to write local state: {e}")
        return

    # Get GitHub Issues from context
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        _output_error(event, "context_not_initialized", "Context not initialized")
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
        _output_error(event, "github_comment_failed", f"Failed to post comment: {e}")
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
        _output_error(event, "no_issue_reference", "No issue reference found in issue.json")
        return

    # Now get context dependencies (after confirming we need them)
    try:
        repo_root = require_repo_root(ctx)
    except SystemExit:
        _output_error(event, "context_not_initialized", "Context not initialized")
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
        _output_error(event, "local_state_write_failed", f"Failed to write local state: {e}")
        return

    # Get GitHub Issues from context
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        _output_error(event, "context_not_initialized", "Context not initialized")
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
        _output_error(event, "github_api_failed", f"Failed to update issue: {e}")
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
@click.pass_context
def impl_signal(ctx: click.Context, event: str) -> None:
    """Signal implementation events to GitHub.

    EVENT can be 'started' or 'ended'.

    'started' posts a start comment and updates issue metadata.
    'ended' updates issue metadata with ended event.

    Always exits with code 0 for graceful degradation (|| true pattern).
    """
    if event == "started":
        _signal_started(ctx)
    else:
        _signal_ended(ctx)
