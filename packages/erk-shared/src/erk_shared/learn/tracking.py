"""Tracking of learn invocations on plan issues.

This module provides functions to record when learn is invoked
on a plan issue, creating a trail of extraction sessions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    render_erk_issue_event,
)

if TYPE_CHECKING:
    from erk_shared.plan_store.backend import PlanBackend


def track_learn_invocation(
    plan_backend: PlanBackend,
    repo_root: Path,
    plan_id: str,
    *,
    session_id: str | None,
    readable_count: int,
    total_count: int,
) -> None:
    """Record a learn invocation on a plan.

    Posts a comment with a learn-invoked metadata block
    to track when learn was run and from which session.

    Args:
        plan_backend: PlanBackend for posting the comment
        repo_root: Repository root path
        plan_id: Plan identifier (e.g., issue number as string)
        session_id: Session ID invoking learn (passed via --session-id CLI flag)
        readable_count: Number of readable sessions found
        total_count: Total sessions discovered for the plan
    """
    timestamp = datetime.now(UTC).isoformat()

    # Build metadata
    data: dict[str, object] = {
        "timestamp": timestamp,
        "readable_sessions": readable_count,
        "total_sessions": total_count,
    }
    if session_id is not None:
        data["session_id"] = session_id

    metadata_block = create_metadata_block(
        key="learn-invoked",
        data=data,
        schema=None,
    )

    # Build description
    if readable_count == 0:
        description = "No readable sessions found on this machine."
    else:
        description = f"Found {readable_count} readable sessions (of {total_count} total)."

    comment_body = render_erk_issue_event(
        title="📚 Learn invoked",
        metadata=metadata_block,
        description=description,
    )

    plan_backend.add_comment(repo_root, plan_id, comment_body)
