"""Unit tests for status history building utilities.

Layer 3 (Pure Unit Tests): Tests for pure status history construction logic.
Zero dependencies on external systems.
"""

from erk_shared.entity_store.types import LogEntry
from erk_shared.gateway.github.status_history import build_status_history, extract_workflow_run_id


def _log_entry(key: str, data: dict, *, comment_id: int = 0) -> LogEntry:
    return LogEntry(key=key, data=data, comment_id=comment_id)


class TestExtractWorkflowRunId:
    """Test extract_workflow_run_id function."""

    def test_empty_entries(self) -> None:
        """No entries returns None."""
        run_id = extract_workflow_run_id([])
        assert run_id is None

    def test_extracts_workflow_run_id(self) -> None:
        """Extracts workflow run ID from workflow-started entry."""
        entries = [
            _log_entry(
                "workflow-started",
                {
                    "status": "started",
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_id": "123456789",
                    "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
                    "issue_number": 123,
                },
            ),
        ]
        run_id = extract_workflow_run_id(entries)
        assert run_id == "123456789"

    def test_returns_most_recent_workflow_run(self) -> None:
        """Returns most recent workflow run when multiple exist."""
        entries = [
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T10:00:00Z",
                    "workflow_run_id": "111111111",
                },
            ),
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T12:00:00Z",
                    "workflow_run_id": "222222222",
                },
            ),
        ]
        run_id = extract_workflow_run_id(entries)
        assert run_id == "222222222"

    def test_ignores_other_entry_keys(self) -> None:
        """Ignores non-workflow-started entries."""
        entries = [
            _log_entry(
                "submission-queued",
                {
                    "queued_at": "2024-01-15T10:00:00Z",
                    "submitted_by": "john.doe",
                },
            ),
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_id": "123456789",
                },
            ),
        ]
        run_id = extract_workflow_run_id(entries)
        assert run_id == "123456789"

    def test_missing_workflow_run_id_field(self) -> None:
        """Returns None if workflow_run_id field is missing."""
        entries = [
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_url": "https://github.com/org/repo/actions/runs/123456789",
                },
            ),
        ]
        run_id = extract_workflow_run_id(entries)
        assert run_id is None

    def test_missing_started_at_field(self) -> None:
        """Returns None if started_at field is missing."""
        entries = [
            _log_entry(
                "workflow-started",
                {
                    "workflow_run_id": "123456789",
                },
            ),
        ]
        run_id = extract_workflow_run_id(entries)
        assert run_id is None

    def test_no_matching_entries(self) -> None:
        """Returns None when no workflow-started entries exist."""
        entries = [
            _log_entry("submission-queued", {"queued_at": "2024-01-15T10:00:00Z"}),
        ]
        run_id = extract_workflow_run_id(entries)
        assert run_id is None


class TestBuildStatusHistory:
    """Test build_status_history function."""

    def test_empty_entries(self) -> None:
        """No entries results in just completion event."""
        history = build_status_history([], "2024-01-15T12:00:00Z")

        assert len(history) == 1
        assert history[0]["status"] == "completed"
        assert history[0]["timestamp"] == "2024-01-15T12:00:00Z"
        assert history[0]["reason"] == "Implementation finished"

    def test_submission_queued_event(self) -> None:
        """Extracts submission-queued event."""
        entries = [
            _log_entry(
                "submission-queued",
                {
                    "status": "queued",
                    "queued_at": "2024-01-15T10:00:00Z",
                    "submitted_by": "john.doe",
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        assert len(history) == 2
        assert history[0]["status"] == "queued"
        assert history[0]["timestamp"] == "2024-01-15T10:00:00Z"
        assert history[0]["reason"] == "erk pr dispatch executed"
        assert history[1]["status"] == "completed"

    def test_workflow_started_event(self) -> None:
        """Extracts workflow-started event."""
        entries = [
            _log_entry(
                "workflow-started",
                {
                    "status": "started",
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_id": "123456789",
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        assert len(history) == 2
        assert history[0]["status"] == "started"
        assert history[0]["timestamp"] == "2024-01-15T11:00:00Z"
        assert history[0]["reason"] == "GitHub Actions workflow triggered"
        assert history[1]["status"] == "completed"

    def test_full_lifecycle(self) -> None:
        """Extracts all events from full lifecycle."""
        entries = [
            _log_entry(
                "submission-queued",
                {
                    "queued_at": "2024-01-15T10:00:00Z",
                    "submitted_by": "john.doe",
                },
            ),
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_id": "123456789",
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        assert len(history) == 3
        assert history[0]["status"] == "queued"
        assert history[0]["timestamp"] == "2024-01-15T10:00:00Z"
        assert history[1]["status"] == "started"
        assert history[1]["timestamp"] == "2024-01-15T11:00:00Z"
        assert history[2]["status"] == "completed"
        assert history[2]["timestamp"] == "2024-01-15T12:00:00Z"

    def test_multiple_entries(self) -> None:
        """Handles multiple entries including different keys."""
        entries = [
            _log_entry(
                "submission-queued",
                {
                    "queued_at": "2024-01-15T10:00:00Z",
                },
            ),
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_id": "123456789",
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        assert len(history) == 3
        assert history[0]["status"] == "queued"
        assert history[1]["status"] == "started"
        assert history[2]["status"] == "completed"

    def test_ignores_other_entry_keys(self) -> None:
        """Ignores entries that aren't status events."""
        entries = [
            _log_entry(
                "erk-pr",
                {
                    "issue_number": 123,
                    "worktree_name": "feature-123",
                    "timestamp": "2024-01-15T09:00:00Z",
                },
            ),
            _log_entry(
                "submission-queued",
                {
                    "queued_at": "2024-01-15T10:00:00Z",
                    "submitted_by": "john.doe",
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        assert len(history) == 2  # queued + completed, not erk-pr
        assert history[0]["status"] == "queued"
        assert history[1]["status"] == "completed"

    def test_missing_timestamp_field(self) -> None:
        """Skips events with missing timestamp fields."""
        entries = [
            _log_entry(
                "submission-queued",
                {
                    "status": "queued",
                    "submitted_by": "john.doe",
                    # No queued_at field
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        # Should only have completion event since queued_at is missing
        assert len(history) == 1
        assert history[0]["status"] == "completed"

    def test_preserves_entry_order(self) -> None:
        """Events appear in the order entries are provided."""
        entries = [
            _log_entry(
                "workflow-started",
                {
                    "started_at": "2024-01-15T11:00:00Z",
                    "workflow_run_id": "123456789",
                },
            ),
            _log_entry(
                "submission-queued",
                {
                    "queued_at": "2024-01-15T10:00:00Z",
                    "submitted_by": "john.doe",
                },
            ),
        ]
        history = build_status_history(entries, "2024-01-15T12:00:00Z")

        # Order should match input: started, queued, then completed
        assert len(history) == 3
        assert history[0]["status"] == "started"
        assert history[1]["status"] == "queued"
        assert history[2]["status"] == "completed"
