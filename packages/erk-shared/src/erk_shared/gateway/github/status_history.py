"""Status history building utilities for GitHub issue metadata.

Functions for constructing status history from entity log entries.

These functions accept LogEntry objects (from EntityLog.all_entries() or
EntityLog.entries()) and transform them into status history records.
"""

from erk_shared.entity_store.types import LogEntry
from erk_shared.gateway.github.metadata.types import BlockKeys


def extract_workflow_run_id(entries: list[LogEntry]) -> str | None:
    """Extract workflow run ID from workflow-started log entries.

    Searches through log entries for workflow-started events and
    extracts the most recent workflow_run_id.

    Args:
        entries: List of LogEntry objects (from EntityLog.all_entries())

    Returns:
        Workflow run ID string if found, None otherwise
    """
    workflow_run_id: str | None = None
    latest_timestamp: str | None = None

    for entry in entries:
        if entry.key == BlockKeys.WORKFLOW_STARTED:
            run_id = entry.data.get("workflow_run_id")
            started_at = entry.data.get("started_at")

            if run_id and started_at:
                if latest_timestamp is None or started_at > latest_timestamp:
                    workflow_run_id = run_id
                    latest_timestamp = started_at

    return workflow_run_id


def build_status_history(
    entries: list[LogEntry],
    completion_timestamp: str,
) -> list[dict[str, str]]:
    """Build status history from entity log entries.

    Extracts status events from log entries and constructs a chronological
    history of status transitions.

    Args:
        entries: List of LogEntry objects (from EntityLog.all_entries())
        completion_timestamp: ISO 8601 timestamp for completion event

    Returns:
        List of status events with status, timestamp, and reason fields.
        Events are in order of appearance, then completed appended.
    """
    status_history: list[dict[str, str]] = []

    for entry in entries:
        if entry.key == BlockKeys.SUBMISSION_QUEUED:
            queued_at = entry.data.get("queued_at")
            if queued_at:
                status_history.append(
                    {
                        "status": "queued",
                        "timestamp": queued_at,
                        "reason": "erk pr dispatch executed",
                    }
                )

        if entry.key == BlockKeys.WORKFLOW_STARTED:
            started_at = entry.data.get("started_at")
            if started_at:
                status_history.append(
                    {
                        "status": "started",
                        "timestamp": started_at,
                        "reason": "GitHub Actions workflow triggered",
                    }
                )

    status_history.append(
        {
            "status": "completed",
            "timestamp": completion_timestamp,
            "reason": "Implementation finished",
        }
    )

    return status_history
