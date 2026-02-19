"""Session discovery for plans.

This module provides functions to discover Claude Code sessions
associated with a plan issue.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.claude_installation.abc import (
    ClaudeInstallation,
    FoundSession,
)
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.learn.extraction.session_schema import extract_git_branch


@dataclass(frozen=True)
class SessionsForPlan:
    """Sessions associated with a plan issue.

    Attributes:
        planning_session_id: Session that created the plan (from created_from_session)
        implementation_session_ids: Sessions where plan was implemented
        learn_session_ids: Sessions where learn was previously invoked
        last_remote_impl_at: Timestamp of remote implementation (if implemented via GitHub Actions)
        last_remote_impl_run_id: GitHub Actions run ID for remote implementation
        last_remote_impl_session_id: Claude Code session ID for remote implementation
        last_session_gist_url: URL of gist containing latest session JSONL
        last_session_id: Session ID of latest uploaded session
        last_session_source: "local" or "remote" indicating session origin
    """

    planning_session_id: str | None
    implementation_session_ids: list[str]
    learn_session_ids: list[str]
    last_remote_impl_at: str | None
    last_remote_impl_run_id: str | None
    last_remote_impl_session_id: str | None
    # New gist-based session fields
    last_session_gist_url: str | None
    last_session_id: str | None
    last_session_source: str | None  # "local" or "remote"

    def all_session_ids(self) -> list[str]:
        """Return all session IDs in logical order.

        Order: planning session first, then implementation sessions, then learn sessions.
        Deduplicates across categories.
        """
        seen: set[str] = set()
        result: list[str] = []

        # Planning session first
        if self.planning_session_id is not None:
            result.append(self.planning_session_id)
            seen.add(self.planning_session_id)

        # Implementation sessions
        for session_id in self.implementation_session_ids:
            if session_id not in seen:
                result.append(session_id)
                seen.add(session_id)

        # Learn sessions
        for session_id in self.learn_session_ids:
            if session_id not in seen:
                result.append(session_id)
                seen.add(session_id)

        return result


def find_sessions_for_plan(
    github: GitHubIssues,
    repo_root: Path,
    issue_number: int,
) -> SessionsForPlan:
    """Find all Claude Code sessions associated with a plan issue.

    DEPRECATED: Use ``PlanBackend.find_sessions_for_plan()`` instead.
    This wrapper constructs a temporary GitHubPlanStore to delegate.

    Args:
        github: GitHub issues interface
        repo_root: Repository root path
        issue_number: Plan issue number

    Returns:
        SessionsForPlan with all discovered session IDs
    """
    from erk_shared.plan_store.github import GitHubPlanStore

    backend = GitHubPlanStore(github)
    return backend.find_sessions_for_plan(repo_root, str(issue_number))


def get_readable_sessions(
    sessions_for_plan: SessionsForPlan,
    claude_installation: ClaudeInstallation,
) -> list[tuple[str, Path]]:
    """Filter sessions to only those readable locally.

    Uses global session lookup - no project_cwd needed since sessions
    are identified by globally unique UUIDs.

    Args:
        sessions_for_plan: Sessions discovered from the plan
        claude_installation: Claude installation for session existence checks

    Returns:
        List of (session_id, path) tuples for sessions that exist on disk
    """
    readable: list[tuple[str, Path]] = []
    for session_id in sessions_for_plan.all_session_ids():
        result = claude_installation.find_session_globally(session_id)
        if isinstance(result, FoundSession):
            readable.append((session_id, result.path))
    return readable


def find_local_sessions_for_project(
    claude_installation: ClaudeInstallation,
    project_cwd: Path,
    *,
    limit: int,
    branch_name: str | None,
) -> list[str]:
    """Find local sessions for a project (fallback when GitHub metadata unavailable).

    This is used when a plan issue doesn't have session tracking metadata.
    Returns session IDs for sessions that exist locally for this project,
    sorted by modification time (newest first).

    When branch_name is provided, filters to only sessions whose gitBranch
    matches the given branch. This prevents unrelated sessions from other
    branches being included in learn analysis.

    Args:
        claude_installation: Claude installation for session listing
        project_cwd: Current working directory for project lookup
        limit: Maximum number of sessions to return
        branch_name: When set, only include sessions from this branch

    Returns:
        List of session IDs that exist locally for this project
    """
    # Request more sessions when filtering to account for non-matching branches
    fetch_limit = limit if branch_name is None else limit * 5
    sessions = claude_installation.find_sessions(
        project_cwd,
        current_session_id=None,
        min_size=1024,
        limit=fetch_limit,
        include_agents=False,
    )

    if branch_name is None:
        return [s.session_id for s in sessions]

    matching: list[str] = []
    for session in sessions:
        content = claude_installation.read_session(
            project_cwd, session.session_id, include_agents=False
        )
        if content is None:
            continue
        branch = extract_git_branch(content.main_content)
        if branch == branch_name:
            matching.append(session.session_id)
            if len(matching) >= limit:
                break
        else:
            print(
                f"Skipping session {session.session_id}: "
                f"branch '{branch}' does not match '{branch_name}'",
                file=sys.stderr,
            )

    return matching
