"""Status history building utilities for GitHub issue metadata.

Pure functions for constructing status history from metadata blocks.
"""

from erk_shared.github.metadata.core import parse_metadata_blocks


def extract_workflow_run_id(comment_bodies: list[str]) -> str | None:
    """Extract workflow run ID from workflow-started metadata blocks.

    Searches through comment bodies for workflow-started metadata blocks and
    extracts the most recent workflow_run_id.

    Args:
        comment_bodies: List of comment body strings from GitHub issue

    Returns:
        Workflow run ID string if found, None otherwise

    Example:
        >>> comment_bodies = [
        ...     "<!-- erk:metadata-block:workflow-started -->...",
        ... ]
        >>> run_id = extract_workflow_run_id(comment_bodies)
        >>> run_id
        '123456789'
    """
    workflow_run_id: str | None = None
    latest_timestamp: str | None = None

    # Parse all metadata blocks from all comments
    for comment_body in comment_bodies:
        blocks = parse_metadata_blocks(comment_body)

        for block in blocks:
            # Extract workflow-started event
            if block.key == "workflow-started":
                run_id = block.data.get("workflow_run_id")
                started_at = block.data.get("started_at")

                # Keep track of most recent workflow run
                if run_id and started_at:
                    if latest_timestamp is None or started_at > latest_timestamp:
                        workflow_run_id = run_id
                        latest_timestamp = started_at

    return workflow_run_id


def build_status_history(
    comment_bodies: list[str],
    completion_timestamp: str,
) -> list[dict[str, str]]:
    """Build status history from comment metadata blocks.

    Extracts status events from metadata blocks in GitHub issue comments
    and constructs a chronological history of status transitions.

    Args:
        comment_bodies: List of comment body strings from GitHub issue
        completion_timestamp: ISO 8601 timestamp for completion event

    Returns:
        List of status events with status, timestamp, and reason fields.
        Events are in chronological order (queued → started → completed).

    Example:
        >>> comment_bodies = [
        ...     "<!-- erk:metadata-block:submission-queued -->...",
        ...     "<!-- erk:metadata-block:workflow-started -->...",
        ... ]
        >>> history = build_status_history(comment_bodies, "2024-01-15T12:00:00Z")
        >>> len(history)
        3
        >>> history[0]["status"]
        'queued'
        >>> history[-1]["status"]
        'completed'
    """
    status_history: list[dict[str, str]] = []

    # Parse all metadata blocks from all comments
    for comment_body in comment_bodies:
        blocks = parse_metadata_blocks(comment_body)

        for block in blocks:
            # Extract queued event
            if block.key == "submission-queued":
                queued_at = block.data.get("queued_at")
                if queued_at:
                    status_history.append(
                        {
                            "status": "queued",
                            "timestamp": queued_at,
                            "reason": "erk plan submit executed",
                        }
                    )

            # Extract started event
            if block.key == "workflow-started":
                started_at = block.data.get("started_at")
                if started_at:
                    status_history.append(
                        {
                            "status": "started",
                            "timestamp": started_at,
                            "reason": "GitHub Actions workflow triggered",
                        }
                    )

    # Add current completion event
    status_history.append(
        {
            "status": "completed",
            "timestamp": completion_timestamp,
            "reason": "Implementation finished",
        }
    )

    return status_history
