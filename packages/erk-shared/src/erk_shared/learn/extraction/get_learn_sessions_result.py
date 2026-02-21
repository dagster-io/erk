"""TypedDict definitions for get-learn-sessions JSON output.

These types are the single source of truth for the JSON schema produced by
get-learn-sessions and consumed by trigger-async-learn (and other callers).
Using TypedDict gives static type safety via ty check without runtime overhead,
and maps directly to the dict access patterns used by JSON consumers.
"""

from typing import TypedDict

from erk_shared.learn.extraction.session_source import SessionSourceDict


class GetLearnSessionsResultDict(TypedDict):
    """Successful result from get-learn-sessions command."""

    success: bool
    plan_id: str
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
    last_session_branch: str | None
    last_session_id: str | None
    last_session_source: str | None


class GetLearnSessionsErrorDict(TypedDict):
    """Error result from get-learn-sessions command."""

    success: bool
    error: str
