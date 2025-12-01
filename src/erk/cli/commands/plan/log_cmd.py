"""Command to display chronological event log for a plan.

Uses the provider-agnostic PlanEventStore to fetch events,
abstracting away the underlying storage format (e.g., GitHub comments).
"""

import json
from datetime import datetime
from typing import TypedDict

import click
from erk_shared.output.output import user_output
from erk_shared.plan_store.event_store import PlanEvent, PlanEventType

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


# Output format types for JSON serialization
class OutputEvent(TypedDict):
    """Structured event for output (JSON and timeline)."""

    timestamp: str
    event_type: str
    metadata: dict[str, object]


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

        # Resolve plan identifier
        plan = ctx.plan_store.get_plan(repo_root, identifier)
        plan_identifier = plan.plan_identifier

        # Fetch events from event store (already sorted chronologically)
        plan_events = ctx.plan_event_store.get_events(repo_root, plan_identifier)

        # Convert to output format
        output_events = [_plan_event_to_output(e) for e in plan_events]

        # Output events
        if output_json:
            _output_json(output_events)
        else:
            _output_timeline(output_events, plan_identifier)

    except (RuntimeError, ValueError) as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e


def _plan_event_to_output(event: PlanEvent) -> OutputEvent:
    """Convert PlanEvent to output format.

    Args:
        event: PlanEvent from event store

    Returns:
        OutputEvent ready for JSON or timeline display
    """
    # Map PlanEventType to display string
    event_type_map = {
        PlanEventType.CREATED: "plan_created",
        PlanEventType.QUEUED: "submission_queued",
        PlanEventType.WORKFLOW_STARTED: "workflow_started",
        PlanEventType.PROGRESS: "implementation_status",
        PlanEventType.COMPLETED: "implementation_status",
        PlanEventType.FAILED: "implementation_status",
        PlanEventType.RETRY: "plan_retry",
        PlanEventType.WORKTREE_CREATED: "worktree_created",
    }

    return OutputEvent(
        timestamp=event.timestamp.isoformat(),
        event_type=event_type_map.get(event.event_type, event.event_type.value),
        metadata=event.data,
    )


def _output_json(events: list[OutputEvent]) -> None:
    """Output events as JSON array."""
    user_output(json.dumps(events, indent=2))


def _output_timeline(events: list[OutputEvent], plan_identifier: str) -> None:
    """Output events as human-readable timeline.

    Args:
        events: List of OutputEvent objects sorted chronologically
        plan_identifier: Plan identifier for display
    """
    if not events:
        user_output(f"No events found for plan #{plan_identifier}")
        return

    user_output(f"Plan #{plan_identifier} Event Timeline\n")

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


def _format_event_description(event: OutputEvent) -> str:
    """Format event as human-readable description.

    Args:
        event: OutputEvent object with event_type and metadata

    Returns:
        Formatted description string
    """
    event_type = event["event_type"]
    metadata = event["metadata"]

    if event_type == "plan_created":
        worktree = metadata.get("worktree_name", "unknown")
        return f"Plan created: worktree '{worktree}' assigned"

    if event_type == "submission_queued":
        submitted_by = metadata.get("submitted_by", "unknown")
        return f"Queued for execution by {submitted_by}"

    if event_type == "workflow_started":
        workflow_url = metadata.get("workflow_run_url", "")
        return f"GitHub Actions workflow started: {workflow_url}"

    if event_type == "implementation_status":
        status = metadata.get("status", "unknown")

        if status == "starting":
            worktree = metadata.get("worktree", "unknown")
            return f"Implementation starting in worktree '{worktree}'"

        if status == "in_progress":
            completed = metadata.get("completed_steps", 0)
            total = metadata.get("total_steps", 0)
            step_desc = metadata.get("step_description")
            if step_desc:
                return f"Progress: {completed}/{total} steps - {step_desc}"
            return f"Progress: {completed}/{total} steps"

        if status == "complete":
            return "Implementation complete"

        if status == "failed":
            return "Implementation failed"

        return f"Status: {status}"

    if event_type == "plan_retry":
        retry_count = metadata.get("retry_count", "unknown")
        triggered_by = metadata.get("triggered_by", "unknown")
        return f"Retry #{retry_count} triggered by {triggered_by}"

    if event_type == "worktree_created":
        worktree = metadata.get("worktree_name", "unknown")
        branch = metadata.get("branch_name", "unknown")
        return f"Worktree created: '{worktree}' (branch: {branch})"

    # Fallback for unknown event types
    return f"Event: {event_type}"
