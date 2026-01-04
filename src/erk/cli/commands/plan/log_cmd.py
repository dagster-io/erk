"""Command to display chronological event log for a plan."""

import json
from collections.abc import Callable
from datetime import datetime
from typing import Literal, TypedDict

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.metadata import parse_metadata_blocks
from erk_shared.output.output import user_output

# Event type literals
type EventType = Literal[
    "plan-created",
    "submission-queued",
    "workflow-started",
    "implementation-status",
    "plan-retry",
    "worktree-created",
]


# Event metadata types
class PlanCreatedMetadata(TypedDict, total=False):
    """Metadata for plan_created event."""

    worktree_name: str
    issue_number: int


class SubmissionQueuedMetadata(TypedDict, total=False):
    """Metadata for submission_queued event."""

    status: str
    submitted_by: str
    expected_workflow: str


class WorkflowStartedMetadata(TypedDict, total=False):
    """Metadata for workflow_started event."""

    status: str
    workflow_run_id: str
    workflow_run_url: str


class ImplementationStatusMetadata(TypedDict, total=False):
    """Metadata for implementation_status event."""

    status: str
    completed_steps: int
    total_steps: int
    step_description: str
    worktree: str
    branch: str


class PlanRetryMetadata(TypedDict, total=False):
    """Metadata for plan_retry event."""

    retry_count: int
    triggered_by: str


class WorktreeCreatedMetadata(TypedDict, total=False):
    """Metadata for worktree_created event."""

    worktree_name: str
    branch_name: str


# Union type for all metadata types
type EventMetadata = (
    PlanCreatedMetadata
    | SubmissionQueuedMetadata
    | WorkflowStartedMetadata
    | ImplementationStatusMetadata
    | PlanRetryMetadata
    | WorktreeCreatedMetadata
)


class Event(TypedDict):
    """Structured event with timestamp, type, and metadata."""

    timestamp: str
    event_type: EventType
    metadata: EventMetadata


# Type alias for event extractor functions
type EventExtractor = Callable[[dict], Event | None]


@click.command("log")
@click.argument("identifier", type=str)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output events as JSON instead of human-readable timeline",
)
@click.pass_obj
def plan_log(ctx: ErkContext, identifier: str, output_json: bool) -> None:
    """Display chronological event log for a plan.

    Shows all events from plan creation through submission, workflow execution,
    implementation progress, and completion. Events are displayed in chronological
    order (oldest first).

    IDENTIFIER can be an issue number (e.g., "42") or a worktree name.

    Examples:

        \b
        # View timeline for plan 42
        $ erk plan log 42

        # View events as JSON for scripting
        $ erk plan log 42 --json

        # View by worktree name
        $ erk plan log erk-add-feature
    """
    try:
        repo = discover_repo_context(ctx, ctx.cwd)
        ensure_erk_metadata_dir(repo)
        repo_root = repo.root

        # Resolve plan identifier to issue number
        plan = ctx.plan_store.get_plan(repo_root, identifier)

        # Convert plan identifier to issue number (GitHub: issue number as string)
        if not plan.plan_identifier.isdigit():
            user_output(
                click.style("Error: ", fg="red")
                + f"Invalid plan identifier '{plan.plan_identifier}': not a valid issue number"
            )
            raise SystemExit(1)

        issue_number = int(plan.plan_identifier)

        # Fetch all comments for the plan issue
        comment_bodies = ctx.issues.get_issue_comments(repo_root, issue_number)

        # Extract events from all comments
        events = _extract_events_from_comments(comment_bodies)

        # Sort events chronologically (oldest first)
        events.sort(key=lambda e: e["timestamp"])

        # Output events
        if output_json:
            _output_json(events)
        else:
            _output_timeline(events, issue_number)

    except (RuntimeError, ValueError) as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e


def _extract_events_from_comments(comment_bodies: list[str]) -> list[Event]:
    """Extract all events from comment metadata blocks.

    Args:
        comment_bodies: List of GitHub issue comment bodies

    Returns:
        List of Event objects with timestamp, event_type, and metadata fields
    """
    events: list[Event] = []

    for comment_body in comment_bodies:
        blocks = parse_metadata_blocks(comment_body)

        for block in blocks:
            event = _block_to_event(block.key, block.data)
            if event is not None:
                events.append(event)

    return events


def _block_to_event(key: str, data: dict) -> Event | None:
    """Convert a metadata block to an Event.

    Args:
        key: Metadata block key (e.g., "erk-plan", "submission-queued")
        data: Metadata block data

    Returns:
        Event object or None if block type is not recognized
    """
    # Map block types to event extractors
    extractors: dict[str, EventExtractor] = {
        "erk-plan": _extract_plan_created_event,
        "submission-queued": _extract_submission_queued_event,
        "workflow-started": _extract_workflow_started_event,
        "erk-implementation-status": _extract_implementation_status_event,
        "plan-retry": _extract_plan_retry_event,
        "erk-worktree-creation": _extract_worktree_creation_event,
    }

    extractor = extractors.get(key)
    if extractor is None:
        return None

    return extractor(data)


def _extract_plan_created_event(data: dict) -> Event | None:
    """Extract plan creation event from erk-plan block."""
    timestamp = data.get("timestamp")
    if not timestamp:
        return None

    metadata: PlanCreatedMetadata = {}
    if "worktree_name" in data:
        metadata["worktree_name"] = data["worktree_name"]
    if "issue_number" in data:
        metadata["issue_number"] = data["issue_number"]

    return Event(
        timestamp=timestamp,
        event_type="plan-created",
        metadata=metadata,
    )


def _extract_submission_queued_event(data: dict) -> Event | None:
    """Extract submission queued event from submission-queued block."""
    timestamp = data.get("queued_at")
    if not timestamp:
        return None

    metadata: SubmissionQueuedMetadata = {"status": "queued"}
    if "submitted_by" in data:
        metadata["submitted_by"] = data["submitted_by"]
    if "expected_workflow" in data:
        metadata["expected_workflow"] = data["expected_workflow"]

    return Event(
        timestamp=timestamp,
        event_type="submission-queued",
        metadata=metadata,
    )


def _extract_workflow_started_event(data: dict) -> Event | None:
    """Extract workflow started event from workflow-started block."""
    timestamp = data.get("started_at")
    if not timestamp:
        return None

    metadata: WorkflowStartedMetadata = {"status": "started"}
    if "workflow_run_id" in data:
        metadata["workflow_run_id"] = data["workflow_run_id"]
    if "workflow_run_url" in data:
        metadata["workflow_run_url"] = data["workflow_run_url"]

    return Event(
        timestamp=timestamp,
        event_type="workflow-started",
        metadata=metadata,
    )


def _extract_implementation_status_event(data: dict) -> Event | None:
    """Extract implementation status event from erk-implementation-status block."""
    timestamp = data.get("timestamp")
    if not timestamp:
        return None

    status = data.get("status")
    if not status:
        return None

    metadata: ImplementationStatusMetadata = {"status": status}

    if "completed_steps" in data:
        metadata["completed_steps"] = data["completed_steps"]
    if "total_steps" in data:
        metadata["total_steps"] = data["total_steps"]
    if "step_description" in data:
        metadata["step_description"] = data["step_description"]
    if "worktree" in data:
        metadata["worktree"] = data["worktree"]
    if "branch" in data:
        metadata["branch"] = data["branch"]

    return Event(
        timestamp=timestamp,
        event_type="implementation-status",
        metadata=metadata,
    )


def _extract_plan_retry_event(data: dict) -> Event | None:
    """Extract plan retry event from plan-retry block."""
    timestamp = data.get("retry_timestamp")
    if not timestamp:
        return None

    metadata: PlanRetryMetadata = {}
    if "retry_count" in data:
        metadata["retry_count"] = data["retry_count"]
    if "triggered_by" in data:
        metadata["triggered_by"] = data["triggered_by"]

    return Event(
        timestamp=timestamp,
        event_type="plan-retry",
        metadata=metadata,
    )


def _extract_worktree_creation_event(data: dict) -> Event | None:
    """Extract worktree creation event from erk-worktree-creation block."""
    timestamp = data.get("timestamp")
    if not timestamp:
        return None

    metadata: WorktreeCreatedMetadata = {}
    if "worktree_name" in data:
        metadata["worktree_name"] = data["worktree_name"]
    if "branch_name" in data:
        metadata["branch_name"] = data["branch_name"]

    return Event(
        timestamp=timestamp,
        event_type="worktree-created",
        metadata=metadata,
    )


def _output_json(events: list[Event]) -> None:
    """Output events as JSON array."""
    user_output(json.dumps(events, indent=2))


def _output_timeline(events: list[Event], issue_number: int) -> None:
    """Output events as human-readable timeline.

    Args:
        events: List of Event objects sorted chronologically
        issue_number: GitHub issue number for the plan
    """
    if not events:
        user_output(f"No events found for plan #{issue_number}")
        return

    user_output(f"Plan #{issue_number} Event Timeline\n")

    for event in events:
        # Format timestamp as human-readable
        timestamp_str = _format_timestamp(event["timestamp"])

        # Format event description
        description = _format_event_description(event)

        # Output timeline entry
        user_output(f"[{timestamp_str}] {description}")


def _format_timestamp(iso_timestamp: str) -> str:
    """Format ISO 8601 timestamp as human-readable string.

    Args:
        iso_timestamp: ISO 8601 timestamp string

    Returns:
        Formatted timestamp like "2024-01-15 12:30:45 UTC"
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, AttributeError):
        # Fallback: return original if parsing fails
        return iso_timestamp


def _format_event_description(event: Event) -> str:
    """Format event as human-readable description.

    Args:
        event: Event object with event_type and metadata

    Returns:
        Formatted description string
    """
    event_type = event["event_type"]
    metadata = event["metadata"]

    if event_type == "plan-created":
        worktree = metadata.get("worktree_name", "unknown")
        return f"Plan created: worktree '{worktree}' assigned"

    if event_type == "submission-queued":
        submitted_by = metadata.get("submitted_by", "unknown")
        return f"Queued for execution by {submitted_by}"

    if event_type == "workflow-started":
        workflow_url = metadata.get("workflow_run_url", "")
        return f"GitHub Actions workflow started: {workflow_url}"

    if event_type == "implementation-status":
        status = metadata.get("status", "unknown")

        if status == "starting":
            worktree = metadata.get("worktree", "unknown")
            return f"Implementation starting in worktree '{worktree}'"

        if status == "in_progress":
            return "Implementation in progress"

        if status == "complete":
            return "Implementation complete"

        if status == "failed":
            return "Implementation failed"

        return f"Status: {status}"

    if event_type == "plan-retry":
        retry_count = metadata.get("retry_count", "unknown")
        triggered_by = metadata.get("triggered_by", "unknown")
        return f"Retry #{retry_count} triggered by {triggered_by}"

    if event_type == "worktree-created":
        worktree = metadata.get("worktree_name", "unknown")
        branch = metadata.get("branch_name", "unknown")
        return f"Worktree created: '{worktree}' (branch: {branch})"

    # Fallback for unknown event types
    return f"Event: {event_type}"
