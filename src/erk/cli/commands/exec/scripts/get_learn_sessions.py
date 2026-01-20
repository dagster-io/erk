"""Get session information for a plan issue.

This exec script returns JSON with session data for use by the /erk:learn skill.
It replaces the `erk learn --json --no-track` workflow, separating data retrieval
from tracking.

Usage:
    erk exec get-learn-sessions <issue-number>
    erk exec get-learn-sessions <issue-url>

Output:
    JSON object with session information:
    {
        "success": true,
        "issue_number": 123,
        "planning_session_id": "abc-123" | null,
        "implementation_session_ids": [...],
        "learn_session_ids": [...],
        "readable_session_ids": [...],
        "session_paths": [...],
        "local_session_ids": [...],
        "last_remote_impl_at": "2024-01-01T..." | null,
        "last_remote_impl_run_id": "12345678" | null,
        "last_remote_impl_session_id": "abc-def-ghi" | null
    }

Exit Codes:
    0: Success
    1: Error (invalid issue, GitHub failure, etc.)
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_git,
    require_issues,
    require_repo_root,
)
from erk_shared.learn.extraction.session_source import (
    LocalSessionSource,
    SessionSourceDict,
)
from erk_shared.naming import extract_leading_issue_number
from erk_shared.sessions.discovery import (
    SessionsForPlan,
    find_local_sessions_for_project,
    find_sessions_for_plan,
    get_readable_sessions,
)


@dataclass(frozen=True)
class GetLearnSessionsResult:
    """Result of get-learn-sessions command."""

    success: bool
    issue_number: int
    planning_session_id: str | None
    implementation_session_ids: list[str]
    learn_session_ids: list[str]
    readable_session_ids: list[str]
    session_paths: list[str]
    local_session_ids: list[str]
    last_remote_impl_at: str | None
    last_remote_impl_run_id: str | None
    last_remote_impl_session_id: str | None
    session_sources: list[SessionSourceDict]


@dataclass(frozen=True)
class GetLearnSessionsError:
    """Error result when getting sessions fails."""

    success: bool
    error: str


def _extract_issue_number(identifier: str) -> int | None:
    """Extract issue number from identifier (number or URL).

    Args:
        identifier: Issue number or GitHub issue URL

    Returns:
        Issue number or None if invalid
    """
    # Try direct number (LBYL: check before converting)
    if identifier.isdigit():
        return int(identifier)

    # Try URL format: https://github.com/owner/repo/issues/123
    if "/issues/" in identifier:
        parts = identifier.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            return int(parts[-1])

    return None


def _build_result(
    *,
    issue_number: int,
    sessions_for_plan: SessionsForPlan,
    readable_session_ids: list[str],
    session_paths: list[str],
    local_session_ids: list[str],
    session_sources: list[LocalSessionSource],
) -> GetLearnSessionsResult:
    """Build the result dataclass from session data."""
    return GetLearnSessionsResult(
        success=True,
        issue_number=issue_number,
        planning_session_id=sessions_for_plan.planning_session_id,
        implementation_session_ids=sessions_for_plan.implementation_session_ids,
        learn_session_ids=sessions_for_plan.learn_session_ids,
        readable_session_ids=readable_session_ids,
        session_paths=session_paths,
        local_session_ids=local_session_ids,
        last_remote_impl_at=sessions_for_plan.last_remote_impl_at,
        last_remote_impl_run_id=sessions_for_plan.last_remote_impl_run_id,
        last_remote_impl_session_id=sessions_for_plan.last_remote_impl_session_id,
        session_sources=[source.to_dict() for source in session_sources],
    )


def _discover_sessions(
    *,
    github_issues,
    claude_installation,
    repo_root: Path,
    cwd: Path,
    issue_number: int,
) -> GetLearnSessionsResult:
    """Discover all sessions for a plan issue.

    Args:
        github_issues: GitHub issues interface
        claude_installation: Claude installation for session lookups
        repo_root: Repository root path
        cwd: Current working directory
        issue_number: Plan issue number

    Returns:
        GetLearnSessionsResult with all session data
    """
    # Find sessions for the plan from GitHub metadata
    sessions_for_plan = find_sessions_for_plan(
        github_issues,
        repo_root,
        issue_number,
    )

    # Get readable sessions (ones that exist on disk)
    readable_sessions = get_readable_sessions(
        sessions_for_plan,
        claude_installation,
    )
    readable_session_ids = [sid for sid, _ in readable_sessions]
    session_paths = [str(path) for _, path in readable_sessions]

    # Build session sources from readable sessions
    session_sources: list[LocalSessionSource] = [
        LocalSessionSource(session_id=sid, path=str(path)) for sid, path in readable_sessions
    ]

    # Local session fallback: when GitHub has no tracked sessions, scan local sessions
    local_session_ids: list[str] = []
    if not readable_session_ids:
        local_session_ids = find_local_sessions_for_project(
            claude_installation,
            cwd,
            limit=10,
        )
        # Get paths for local sessions and build session sources
        for sid in local_session_ids:
            path = claude_installation.get_session_path(cwd, sid)
            if path is not None:
                session_paths.append(str(path))
                session_sources.append(LocalSessionSource(session_id=sid, path=str(path)))

    return _build_result(
        issue_number=issue_number,
        sessions_for_plan=sessions_for_plan,
        readable_session_ids=readable_session_ids,
        session_paths=session_paths,
        local_session_ids=local_session_ids,
        session_sources=session_sources,
    )


@click.command(name="get-learn-sessions")
@click.argument("issue", type=str, required=False)
@click.pass_context
def get_learn_sessions(ctx: click.Context, issue: str | None) -> None:
    """Get session information for a plan issue.

    ISSUE can be a plan issue number (e.g., "123") or a full GitHub URL.
    If not provided, infers from current branch name (P{issue}-...).

    Returns JSON with session IDs and paths for use by /erk:learn skill.
    """
    # Get dependencies from context
    github_issues = require_issues(ctx)
    git = require_git(ctx)
    claude_installation = require_claude_installation(ctx)
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)

    # Resolve issue number: explicit argument or infer from branch
    issue_number: int | None = None
    if issue is not None:
        issue_number = _extract_issue_number(issue)
        if issue_number is None:
            error = GetLearnSessionsError(
                success=False,
                error=f"Invalid issue identifier: {issue}",
            )
            click.echo(json.dumps(asdict(error)))
            raise SystemExit(1)
    else:
        # Try to infer from current branch
        branch = git.get_current_branch(cwd)
        if branch is not None:
            issue_number = extract_leading_issue_number(branch)

    if issue_number is None:
        error = GetLearnSessionsError(
            success=False,
            error="No issue specified and could not infer from branch name",
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1)

    # Discover sessions
    result = _discover_sessions(
        github_issues=github_issues,
        claude_installation=claude_installation,
        repo_root=repo_root,
        cwd=cwd,
        issue_number=issue_number,
    )

    click.echo(json.dumps(asdict(result), indent=2))
