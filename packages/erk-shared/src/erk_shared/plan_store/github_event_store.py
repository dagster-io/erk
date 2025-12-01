"""GitHub implementation of plan event storage.

Events are stored as GitHub issue comments with metadata blocks.
Each event type maps to a specific metadata block format.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.issues import GitHubIssues
from erk_shared.github.metadata import (
    MetadataBlock,
    parse_metadata_blocks,
    render_metadata_block,
)
from erk_shared.plan_store.event_store import PlanEvent, PlanEventStore, PlanEventType


class GitHubPlanEventStore(PlanEventStore):
    """GitHub implementation storing events as issue comments.

    Each event is stored as a comment with a metadata block.
    Events are parsed from comments when retrieved.
    """

    def __init__(self, github_issues: GitHubIssues) -> None:
        """Initialize GitHubPlanEventStore with GitHub issues interface.

        Args:
            github_issues: GitHubIssues implementation for comment operations
        """
        self._github_issues = github_issues

    def append_event(
        self,
        repo_root: Path,
        plan_identifier: str,
        event: PlanEvent,
    ) -> None:
        """Convert PlanEvent to metadata block and post as comment.

        Args:
            repo_root: Repository root directory
            plan_identifier: Issue number as string
            event: Event to append

        Raises:
            RuntimeError: If gh CLI fails
        """
        issue_number = int(plan_identifier)

        # Convert event to metadata block
        metadata_block = self._event_to_metadata_block(event)
        comment_body = render_metadata_block(metadata_block)

        self._github_issues.add_comment(repo_root, issue_number, comment_body)

    def get_events(
        self,
        repo_root: Path,
        plan_identifier: str,
        event_types: list[PlanEventType] | None = None,
    ) -> list[PlanEvent]:
        """Parse events from issue comments.

        Args:
            repo_root: Repository root directory
            plan_identifier: Issue number as string
            event_types: Optional filter (None = all events)

        Returns:
            List of events sorted chronologically (oldest first)

        Raises:
            RuntimeError: If gh CLI fails
        """
        issue_number = int(plan_identifier)
        comments = self._github_issues.get_issue_comments(repo_root, issue_number)

        events: list[PlanEvent] = []
        for comment in comments:
            blocks = parse_metadata_blocks(comment)
            for block in blocks:
                event = self._metadata_block_to_event(block)
                if event is not None:
                    if event_types is None or event.event_type in event_types:
                        events.append(event)

        # Sort chronologically (oldest first)
        events.sort(key=lambda e: e.timestamp)
        return events

    def get_latest_event(
        self,
        repo_root: Path,
        plan_identifier: str,
        event_type: PlanEventType | None = None,
    ) -> PlanEvent | None:
        """Get most recent event.

        Args:
            repo_root: Repository root directory
            plan_identifier: Issue number as string
            event_type: Optional filter (None = any event type)

        Returns:
            Most recent event matching criteria, or None if no events

        Raises:
            RuntimeError: If gh CLI fails
        """
        filter_types = [event_type] if event_type else None
        events = self.get_events(repo_root, plan_identifier, filter_types)
        return events[-1] if events else None

    def _event_to_metadata_block(self, event: PlanEvent) -> MetadataBlock:
        """Convert domain event to GitHub metadata block format.

        Maps PlanEventType to the appropriate metadata block key and
        converts event data to the expected format.

        Args:
            event: PlanEvent to convert

        Returns:
            MetadataBlock ready to render as comment
        """
        # Map event type to metadata block key
        key_map = {
            PlanEventType.CREATED: "erk-plan",
            PlanEventType.QUEUED: "submission-queued",
            PlanEventType.WORKFLOW_STARTED: "workflow-started",
            PlanEventType.PROGRESS: "erk-implementation-status",
            PlanEventType.COMPLETED: "erk-implementation-status",
            PlanEventType.FAILED: "erk-implementation-status",
            PlanEventType.RETRY: "plan-retry",
            PlanEventType.WORKTREE_CREATED: "erk-worktree-creation",
        }

        key = key_map.get(event.event_type, "erk-event")

        # Build data dict based on event type
        data: dict[str, object] = {}

        if event.event_type == PlanEventType.CREATED:
            data["timestamp"] = event.timestamp.isoformat()
            data.update(event.data)

        elif event.event_type == PlanEventType.QUEUED:
            data["queued_at"] = event.timestamp.isoformat()
            if "submitted_by" in event.data:
                data["submitted_by"] = event.data["submitted_by"]
            if "expected_workflow" in event.data:
                data["expected_workflow"] = event.data["expected_workflow"]

        elif event.event_type == PlanEventType.WORKFLOW_STARTED:
            data["started_at"] = event.timestamp.isoformat()
            if "workflow_run_id" in event.data:
                data["workflow_run_id"] = event.data["workflow_run_id"]
            if "workflow_run_url" in event.data:
                data["workflow_run_url"] = event.data["workflow_run_url"]

        elif event.event_type in (
            PlanEventType.PROGRESS,
            PlanEventType.COMPLETED,
            PlanEventType.FAILED,
        ):
            data["timestamp"] = event.timestamp.isoformat()
            if event.event_type == PlanEventType.COMPLETED:
                data["status"] = "complete"
            elif event.event_type == PlanEventType.FAILED:
                data["status"] = "failed"
            else:
                data["status"] = event.data.get("status", "in_progress")
            # Copy other fields
            progress_fields = (
                "completed_steps",
                "total_steps",
                "step_description",
                "worktree",
                "branch",
            )
            for field in progress_fields:
                if field in event.data:
                    data[field] = event.data[field]

        elif event.event_type == PlanEventType.RETRY:
            data["retry_timestamp"] = event.timestamp.isoformat()
            if "retry_count" in event.data:
                data["retry_count"] = event.data["retry_count"]
            if "triggered_by" in event.data:
                data["triggered_by"] = event.data["triggered_by"]

        elif event.event_type == PlanEventType.WORKTREE_CREATED:
            data["timestamp"] = event.timestamp.isoformat()
            if "worktree_name" in event.data:
                data["worktree_name"] = event.data["worktree_name"]
            if "branch_name" in event.data:
                data["branch_name"] = event.data["branch_name"]

        return MetadataBlock(key=key, data=data)

    def _metadata_block_to_event(self, block: MetadataBlock) -> PlanEvent | None:
        """Convert GitHub metadata block to domain event.

        Parses metadata block and maps to the appropriate PlanEventType.

        Args:
            block: MetadataBlock parsed from comment

        Returns:
            PlanEvent or None if block type is not recognized
        """
        key = block.key
        data = block.data

        # Map metadata block key to event type and extract timestamp
        if key == "erk-plan":
            timestamp_str = data.get("timestamp")
            if not timestamp_str:
                return None
            timestamp = self._parse_timestamp(timestamp_str)
            event_data: dict[str, object] = {}
            if "worktree_name" in data:
                event_data["worktree_name"] = data["worktree_name"]
            if "issue_number" in data:
                event_data["issue_number"] = data["issue_number"]
            return PlanEvent(
                event_type=PlanEventType.CREATED,
                timestamp=timestamp,
                data=event_data,
            )

        if key == "submission-queued":
            timestamp_str = data.get("queued_at")
            if not timestamp_str:
                return None
            timestamp = self._parse_timestamp(timestamp_str)
            event_data = {"status": "queued"}
            if "submitted_by" in data:
                event_data["submitted_by"] = data["submitted_by"]
            if "expected_workflow" in data:
                event_data["expected_workflow"] = data["expected_workflow"]
            return PlanEvent(
                event_type=PlanEventType.QUEUED,
                timestamp=timestamp,
                data=event_data,
            )

        if key == "workflow-started":
            timestamp_str = data.get("started_at")
            if not timestamp_str:
                return None
            timestamp = self._parse_timestamp(timestamp_str)
            event_data = {"status": "started"}
            if "workflow_run_id" in data:
                event_data["workflow_run_id"] = data["workflow_run_id"]
            if "workflow_run_url" in data:
                event_data["workflow_run_url"] = data["workflow_run_url"]
            return PlanEvent(
                event_type=PlanEventType.WORKFLOW_STARTED,
                timestamp=timestamp,
                data=event_data,
            )

        if key == "erk-implementation-status":
            timestamp_str = data.get("timestamp")
            if not timestamp_str:
                return None
            timestamp = self._parse_timestamp(timestamp_str)
            status = data.get("status")
            if not status:
                return None

            # Map status to event type
            if status == "complete":
                event_type = PlanEventType.COMPLETED
            elif status == "failed":
                event_type = PlanEventType.FAILED
            else:
                event_type = PlanEventType.PROGRESS

            event_data = {"status": status}
            progress_fields = (
                "completed_steps",
                "total_steps",
                "step_description",
                "worktree",
                "branch",
            )
            for field in progress_fields:
                if field in data:
                    event_data[field] = data[field]

            return PlanEvent(
                event_type=event_type,
                timestamp=timestamp,
                data=event_data,
            )

        if key == "plan-retry":
            timestamp_str = data.get("retry_timestamp")
            if not timestamp_str:
                return None
            timestamp = self._parse_timestamp(timestamp_str)
            event_data = {}
            if "retry_count" in data:
                event_data["retry_count"] = data["retry_count"]
            if "triggered_by" in data:
                event_data["triggered_by"] = data["triggered_by"]
            return PlanEvent(
                event_type=PlanEventType.RETRY,
                timestamp=timestamp,
                data=event_data,
            )

        if key == "erk-worktree-creation":
            timestamp_str = data.get("timestamp")
            if not timestamp_str:
                return None
            timestamp = self._parse_timestamp(timestamp_str)
            event_data = {}
            if "worktree_name" in data:
                event_data["worktree_name"] = data["worktree_name"]
            if "branch_name" in data:
                event_data["branch_name"] = data["branch_name"]
            return PlanEvent(
                event_type=PlanEventType.WORKTREE_CREATED,
                timestamp=timestamp,
                data=event_data,
            )

        # Unrecognized block type
        return None

    def _parse_timestamp(self, timestamp_str: object) -> datetime:
        """Parse ISO 8601 timestamp string to datetime.

        Args:
            timestamp_str: ISO 8601 timestamp string

        Returns:
            datetime object (UTC if no timezone specified)
        """
        if not isinstance(timestamp_str, str):
            return datetime.now(UTC)
        # Handle Z suffix for UTC
        ts = timestamp_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        # Ensure UTC if no timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
