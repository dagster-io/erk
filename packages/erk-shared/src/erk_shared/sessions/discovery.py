"""Session discovery for plans.

This module provides functions to discover Claude Code sessions
associated with a plan issue.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.extraction.claude_installation.abc import ClaudeInstallation
from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.metadata.plan_header import (
    extract_plan_header_created_from_session,
    extract_plan_header_local_impl_session,
)
from erk_shared.learn.impl_events import (
    extract_implementation_sessions,
    extract_learn_sessions,
)
from erk_shared.non_ideal_state import SessionNotFound


@dataclass(frozen=True)
class SessionsForPlan:
    """Sessions associated with a plan issue.

    Attributes:
        planning_session_id: Session that created the plan (from created_from_session)
        implementation_session_ids: Sessions where plan was implemented
        learn_session_ids: Sessions where learn was previously invoked
    """

    planning_session_id: str | None
    implementation_session_ids: list[str]
    learn_session_ids: list[str]

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

    Extracts session IDs from:
    1. created_from_session in plan-header (planning session)
    2. last_local_impl_session in plan-header (most recent impl session)
    3. impl-started/impl-ended comments (all implementation sessions)
    4. learn-invoked comments (previous learn sessions)

    Args:
        github: GitHub issues interface
        repo_root: Repository root path
        issue_number: Plan issue number

    Returns:
        SessionsForPlan with all discovered session IDs
    """
    # Get issue body for metadata extraction
    issue_info = github.get_issue(repo_root, issue_number)
    planning_session_id = extract_plan_header_created_from_session(issue_info.body)
    metadata_impl_session = extract_plan_header_local_impl_session(issue_info.body)

    # Get comments to find implementation and learn sessions
    comments = github.get_issue_comments(repo_root, issue_number)

    comment_impl_sessions = extract_implementation_sessions(comments)
    learn_session_ids = extract_learn_sessions(comments)

    # Combine implementation sessions: metadata first (most recent), then from comments
    implementation_session_ids: list[str] = []
    seen: set[str] = set()

    if metadata_impl_session is not None:
        implementation_session_ids.append(metadata_impl_session)
        seen.add(metadata_impl_session)

    for session_id in comment_impl_sessions:
        if session_id not in seen:
            implementation_session_ids.append(session_id)
            seen.add(session_id)

    return SessionsForPlan(
        planning_session_id=planning_session_id,
        implementation_session_ids=implementation_session_ids,
        learn_session_ids=learn_session_ids,
    )


def get_readable_sessions(
    sessions_for_plan: SessionsForPlan,
    claude_installation: ClaudeInstallation,
    project_cwd: Path,
) -> list[str]:
    """Filter sessions to only those readable from the current project.

    Args:
        sessions_for_plan: Sessions discovered from the plan
        claude_installation: Claude installation for session existence checks
        project_cwd: Current working directory for project lookup

    Returns:
        List of session IDs that are readable (exist on disk)
    """
    readable: list[str] = []
    for session_id in sessions_for_plan.all_session_ids():
        session = claude_installation.get_session(project_cwd, session_id)
        # get_session returns SessionNotFound sentinel if not found
        if not isinstance(session, SessionNotFound):
            readable.append(session_id)
    return readable


def find_local_sessions_for_project(
    claude_installation: ClaudeInstallation,
    project_cwd: Path,
    *,
    limit: int,
) -> list[str]:
    """Find local sessions for a project (fallback when GitHub metadata unavailable).

    This is used when a plan issue doesn't have session tracking metadata.
    Returns session IDs for sessions that exist locally for this project,
    sorted by modification time (newest first).

    Args:
        claude_installation: Claude installation for session listing
        project_cwd: Current working directory for project lookup
        limit: Maximum number of sessions to return

    Returns:
        List of session IDs that exist locally for this project
    """
    sessions = claude_installation.find_sessions(
        project_cwd,
        current_session_id=None,
        min_size=1024,  # Skip tiny sessions (likely empty/aborted)
        limit=limit,
        include_agents=False,
    )
    return [s.session_id for s in sessions]
