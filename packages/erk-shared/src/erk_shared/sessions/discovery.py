"""Session discovery for plans.

This module provides functions to discover Claude Code sessions
associated with a plan issue.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_created_from_session,
    extract_plan_header_last_learn_session,
    extract_plan_header_last_session_id,
    extract_plan_header_last_session_source,
    extract_plan_header_local_impl_session,
    extract_plan_header_remote_impl_at,
    extract_plan_header_remote_impl_run_id,
    extract_plan_header_remote_impl_session_id,
    extract_plan_header_session_gist_url,
)
from erk_shared.learn.extraction.claude_installation.abc import (
    ClaudeInstallation,
    FoundSession,
)
from erk_shared.learn.impl_events import (
    extract_implementation_sessions,
    extract_learn_sessions,
)


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

    Extracts session IDs from:
    1. created_from_session in plan-header (planning session)
    2. last_local_impl_session in plan-header (most recent impl session)
    3. impl-started/impl-ended comments (all implementation sessions)
    4. last_learn_session in plan-header (most recent learn session)
    5. learn-invoked comments (previous learn sessions)

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
    metadata_learn_session = extract_plan_header_last_learn_session(issue_info.body)
    last_remote_impl_at = extract_plan_header_remote_impl_at(issue_info.body)
    last_remote_impl_run_id = extract_plan_header_remote_impl_run_id(issue_info.body)
    last_remote_impl_session_id = extract_plan_header_remote_impl_session_id(issue_info.body)
    # Extract new gist-based session fields
    last_session_gist_url = extract_plan_header_session_gist_url(issue_info.body)
    last_session_id = extract_plan_header_last_session_id(issue_info.body)
    last_session_source = extract_plan_header_last_session_source(issue_info.body)

    # Get comments to find implementation and learn sessions
    comments = github.get_issue_comments(repo_root, issue_number)

    comment_impl_sessions = extract_implementation_sessions(comments)
    comment_learn_sessions = extract_learn_sessions(comments)

    # Combine implementation sessions: metadata first (most recent), then from comments
    implementation_session_ids: list[str] = []
    impl_seen: set[str] = set()

    if metadata_impl_session is not None:
        implementation_session_ids.append(metadata_impl_session)
        impl_seen.add(metadata_impl_session)

    for session_id in comment_impl_sessions:
        if session_id not in impl_seen:
            implementation_session_ids.append(session_id)
            impl_seen.add(session_id)

    # Combine learn sessions: metadata first (most recent), then from comments
    learn_session_ids: list[str] = []
    learn_seen: set[str] = set()

    if metadata_learn_session is not None:
        learn_session_ids.append(metadata_learn_session)
        learn_seen.add(metadata_learn_session)

    for session_id in comment_learn_sessions:
        if session_id not in learn_seen:
            learn_session_ids.append(session_id)
            learn_seen.add(session_id)

    return SessionsForPlan(
        planning_session_id=planning_session_id,
        implementation_session_ids=implementation_session_ids,
        learn_session_ids=learn_session_ids,
        last_remote_impl_at=last_remote_impl_at,
        last_remote_impl_run_id=last_remote_impl_run_id,
        last_remote_impl_session_id=last_remote_impl_session_id,
        last_session_gist_url=last_session_gist_url,
        last_session_id=last_session_id,
        last_session_source=last_session_source,
    )


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
