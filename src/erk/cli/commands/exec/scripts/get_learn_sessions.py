"""Get session information for a plan.

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
        "plan_id": "123",
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
import subprocess
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.learn.extraction.get_learn_sessions_result import (
    GetLearnSessionsErrorDict,
    GetLearnSessionsResultDict,
)
from erk_shared.learn.extraction.session_source import (
    LocalSessionSource,
    RemoteSessionSource,
    SessionSource,
)
from erk_shared.sessions.discovery import (
    SessionsForPlan,
    find_local_sessions_for_project,
    get_readable_sessions,
)


def _extract_plan_number(identifier: str) -> int | None:
    """Extract plan number from identifier (number or URL).

    Args:
        identifier: Issue number or GitHub issue URL

    Returns:
        Plan number or None if invalid
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


def _fetch_preprocessed_manifest(
    *,
    repo_root: Path,
    plan_id: str,
    git,
) -> dict | None:
    """Check for preprocessed session manifest on planned-pr-context branch.

    Args:
        repo_root: Repository root path.
        plan_id: Plan identifier.
        git: Git gateway for branch operations.

    Returns:
        Parsed manifest dict if found, None otherwise.
    """
    session_branch = f"planned-pr-context/{plan_id}"
    if not git.branch.branch_exists_on_remote(repo_root, "origin", session_branch):
        return None

    git.remote.fetch_branch(repo_root, "origin", session_branch)

    result = subprocess.run(
        [
            "git",
            "show",
            f"origin/{session_branch}:.erk/sessions/manifest.json",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    content = result.stdout.strip()
    if not content:
        return None
    return json.loads(content)


def _build_result(
    *,
    plan_id: str,
    sessions_for_plan: SessionsForPlan,
    readable_session_ids: list[str],
    session_paths: list[str],
    local_session_ids: list[str],
    session_sources: list[SessionSource],
    preprocessed_manifest: dict | None,
) -> GetLearnSessionsResultDict:
    """Build the result dict from session data."""
    return GetLearnSessionsResultDict(
        success=True,
        plan_id=plan_id,
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
        last_session_branch=sessions_for_plan.last_session_branch,
        last_session_id=sessions_for_plan.last_session_id,
        last_session_source=sessions_for_plan.last_session_source,
        preprocessed_manifest=preprocessed_manifest,
    )


def _discover_sessions(
    *,
    plan_backend,
    claude_installation,
    git,
    repo_root: Path,
    cwd: Path,
    plan_id: str,
    branch_name: str | None,
) -> GetLearnSessionsResultDict:
    """Discover all sessions for a plan.

    Args:
        plan_backend: PlanBackend for session discovery
        claude_installation: Claude installation for session lookups
        git: Git gateway for branch operations
        repo_root: Repository root path
        cwd: Current working directory
        plan_id: Plan identifier
        branch_name: Current branch name for local session filtering

    Returns:
        GetLearnSessionsResultDict with all session data
    """
    # Check for preprocessed manifest on planned-pr-context branch
    preprocessed_manifest = _fetch_preprocessed_manifest(
        repo_root=repo_root,
        plan_id=plan_id,
        git=git,
    )

    # Find sessions for the plan via PlanBackend
    sessions_for_plan = plan_backend.find_sessions_for_plan(
        repo_root,
        plan_id,
    )

    # Get readable sessions (ones that exist on disk)
    readable_sessions = get_readable_sessions(
        sessions_for_plan,
        claude_installation,
    )
    readable_session_ids = [sid for sid, _ in readable_sessions]
    session_paths = [str(path) for _, path in readable_sessions]

    # Build session sources from readable sessions
    session_sources: list[SessionSource] = [
        LocalSessionSource(session_id=sid, path=str(path)) for sid, path in readable_sessions
    ]

    # Local session fallback: when GitHub has no tracked sessions, scan local sessions
    local_session_ids: list[str] = []
    if not readable_session_ids:
        local_session_ids = find_local_sessions_for_project(
            claude_installation,
            cwd,
            limit=10,
            branch_name=branch_name,
        )
        # Get paths for local sessions and build session sources
        for sid in local_session_ids:
            path = claude_installation.get_session_path(cwd, sid)
            if path is not None:
                session_paths.append(str(path))
                session_sources.append(LocalSessionSource(session_id=sid, path=str(path)))

    # Add remote session source from branch-based or legacy artifact session
    # Prefer branch-based fields (last_session_*) over legacy fields (last_remote_impl_*)
    if (
        sessions_for_plan.last_session_branch is not None
        and sessions_for_plan.last_session_id is not None
    ):
        # Use branch-based session (preferred)
        remote_source = RemoteSessionSource(
            session_id=sessions_for_plan.last_session_id,
            run_id=None,  # Branch-based sessions don't use run IDs
            session_branch=sessions_for_plan.last_session_branch,
            path=None,  # Path is None until downloaded
        )
        session_sources.append(remote_source)
    elif (
        sessions_for_plan.last_remote_impl_session_id is not None
        and sessions_for_plan.last_remote_impl_run_id is not None
    ):
        # Fall back to legacy artifact-based session
        remote_source = RemoteSessionSource(
            session_id=sessions_for_plan.last_remote_impl_session_id,
            run_id=sessions_for_plan.last_remote_impl_run_id,
            path=None,  # Path is None until downloaded
            session_branch=None,
        )
        session_sources.append(remote_source)

    return _build_result(
        plan_id=plan_id,
        sessions_for_plan=sessions_for_plan,
        readable_session_ids=readable_session_ids,
        session_paths=session_paths,
        local_session_ids=local_session_ids,
        session_sources=session_sources,
        preprocessed_manifest=preprocessed_manifest,
    )


@click.command(name="get-learn-sessions")
@click.argument("issue", type=str, required=False)
@click.pass_context
def get_learn_sessions(ctx: click.Context, issue: str | None) -> None:
    """Get session information for a plan.

    ISSUE can be a plan number (e.g., "123") or a full GitHub URL.
    If not provided, infers from .erk/impl-context/plan-ref.json on the current branch.

    Returns JSON with session IDs and paths for use by /erk:learn skill.
    """
    # Get dependencies from context
    git = require_git(ctx)
    claude_installation = require_claude_installation(ctx)
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    plan_backend = require_plan_backend(ctx)

    # Get current branch for local session filtering
    branch_name = git.branch.get_current_branch(cwd)

    # Resolve plan_id: explicit argument or infer from branch
    plan_id: str | None = None
    if issue is not None:
        plan_number = _extract_plan_number(issue)
        if plan_number is None:
            error = GetLearnSessionsErrorDict(
                success=False,
                error=f"Invalid issue identifier: {issue}",
            )
            click.echo(json.dumps(error))
            raise SystemExit(1)
        plan_id = str(plan_number)
    elif branch_name is not None:
        plan_id = plan_backend.resolve_plan_id_for_branch(repo_root, branch_name)

    if plan_id is None:
        error = GetLearnSessionsErrorDict(
            success=False,
            error="No issue specified and could not infer from branch name",
        )
        click.echo(json.dumps(error))
        raise SystemExit(1)

    # Discover sessions
    result = _discover_sessions(
        plan_backend=plan_backend,
        claude_installation=claude_installation,
        git=git,
        repo_root=repo_root,
        cwd=cwd,
        plan_id=plan_id,
        branch_name=branch_name,
    )

    click.echo(json.dumps(result, indent=2))
