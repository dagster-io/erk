"""Tests for EntityLog — immutable append-only entries stored as comments."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from erk_shared.entity_store.log import (
    EntityLog,
    entity_log_append,
    entity_log_append_content,
)
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import (
    create_metadata_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.types import MetadataBlockSchema

REPO_ROOT = Path("/fake/repo")
NOW = datetime(2024, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class _NoopSchema(MetadataBlockSchema):
    """Test schema that accepts any data."""

    def validate(self, data: dict[str, Any]) -> None:
        pass

    def get_key(self) -> str:
        return "test"


NOOP_SCHEMA = _NoopSchema()


def _make_issue_info(
    *,
    number: int,
) -> IssueInfo:
    return IssueInfo(
        number=number,
        title="Test Issue",
        body="",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=[],
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="test-user",
    )


def _render_event_comment(key: str, data: dict) -> str:
    """Render a metadata block as it would appear in a GitHub comment."""
    block = create_metadata_block(key, data, schema=None)
    return render_erk_issue_event(
        title=f"Event: {key}",
        metadata=block,
        description="Test event",
    )


class TestEntityLogAppend:
    """Tests for entity_log_append() standalone function."""

    def test_append_creates_comment(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1)})
        comment_id = entity_log_append(
            github_issues=issues,
            repo_root=REPO_ROOT,
            number=1,
            key="workflow-started",
            data={"status": "started", "started_at": "2024-01-01T00:00:00Z"},
            title="Workflow Started",
            description="Starting workflow",
            schema=NOOP_SCHEMA,
        )
        assert isinstance(comment_id, int)
        assert len(issues.added_comments) == 1
        issue_num, body, cid = issues.added_comments[0]
        assert issue_num == 1
        assert "workflow-started" in body
        assert "started" in body

    def test_append_returns_unique_comment_ids(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1)})
        cid1 = entity_log_append(
            github_issues=issues,
            repo_root=REPO_ROOT,
            number=1,
            key="event-one",
            data={"key": "value1"},
            title="Event One",
            description="",
            schema=NOOP_SCHEMA,
        )
        cid2 = entity_log_append(
            github_issues=issues,
            repo_root=REPO_ROOT,
            number=1,
            key="event-two",
            data={"key": "value2"},
            title="Event Two",
            description="",
            schema=NOOP_SCHEMA,
        )
        # Each append should get a unique comment ID
        assert cid1 != cid2


class TestEntityLogAppendContent:
    """Tests for entity_log_append_content() standalone function."""

    def test_append_content_plan_body(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1)})
        comment_id = entity_log_append_content(
            github_issues=issues,
            repo_root=REPO_ROOT,
            number=1,
            key="plan-body",
            content="# My Plan\n\nThis is the plan content.",
            title="Implementation Plan",
        )
        assert isinstance(comment_id, int)
        assert len(issues.added_comments) == 1
        _, body, _ = issues.added_comments[0]
        assert "plan-body" in body
        assert "My Plan" in body

    def test_append_content_objective_body(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1)})
        comment_id = entity_log_append_content(
            github_issues=issues,
            repo_root=REPO_ROOT,
            number=1,
            key="objective-body",
            content="## Objective\n\nBuild a thing.",
            title="Objective",
        )
        assert isinstance(comment_id, int)
        _, body, _ = issues.added_comments[0]
        assert "objective-body" in body
        assert "Build a thing" in body

    def test_append_content_generic_key(self) -> None:
        issues = FakeGitHubIssues(issues={1: _make_issue_info(number=1)})
        comment_id = entity_log_append_content(
            github_issues=issues,
            repo_root=REPO_ROOT,
            number=1,
            key="custom-content",
            content="Some raw markdown content",
            title="Custom Content",
        )
        assert isinstance(comment_id, int)
        _, body, _ = issues.added_comments[0]
        assert "custom-content" in body
        assert "Some raw markdown content" in body


class TestEntityLogEntries:
    """Tests for EntityLog.entries(), latest(), all_entries."""

    def test_entries_returns_matching_key(self) -> None:
        comment1 = _render_event_comment(
            "workflow-started",
            {"started_at": "2024-01-01T00:00:00Z", "workflow_run_id": "111"},
        )
        comment2 = _render_event_comment(
            "submission-queued",
            {"queued_at": "2024-01-01T01:00:00Z"},
        )
        comment3 = _render_event_comment(
            "workflow-started",
            {"started_at": "2024-01-01T02:00:00Z", "workflow_run_id": "222"},
        )
        log = EntityLog(
            comment_bodies=[comment1, comment2, comment3],
        )
        entries = log.entries("workflow-started")
        assert len(entries) == 2
        assert entries[0].data["workflow_run_id"] == "111"
        assert entries[1].data["workflow_run_id"] == "222"

    def test_entries_returns_empty_for_unknown_key(self) -> None:
        log = EntityLog(comment_bodies=[])
        entries = log.entries("nonexistent-key")
        assert entries == []

    def test_latest_returns_most_recent(self) -> None:
        comment1 = _render_event_comment(
            "workflow-started",
            {"started_at": "2024-01-01T00:00:00Z", "workflow_run_id": "111"},
        )
        comment2 = _render_event_comment(
            "workflow-started",
            {"started_at": "2024-01-01T02:00:00Z", "workflow_run_id": "222"},
        )
        log = EntityLog(comment_bodies=[comment1, comment2])
        latest = log.latest("workflow-started")
        assert latest is not None
        assert latest.data["workflow_run_id"] == "222"

    def test_latest_returns_none_for_unknown_key(self) -> None:
        log = EntityLog(comment_bodies=[])
        assert log.latest("nonexistent") is None

    def test_all_entries_returns_all_keys(self) -> None:
        comment1 = _render_event_comment(
            "workflow-started",
            {"started_at": "2024-01-01T00:00:00Z"},
        )
        comment2 = _render_event_comment(
            "submission-queued",
            {"queued_at": "2024-01-01T01:00:00Z"},
        )
        log = EntityLog(comment_bodies=[comment1, comment2])
        all_entries = log.all_entries
        assert len(all_entries) == 2
        keys = {e.key for e in all_entries}
        assert keys == {"workflow-started", "submission-queued"}

    def test_all_entries_empty_when_no_comments(self) -> None:
        log = EntityLog(comment_bodies=[])
        assert log.all_entries == []

    def test_entries_preserves_chronological_order(self) -> None:
        """Log entries should be in chronological order (earliest first)."""
        comments = []
        for i in range(5):
            comments.append(
                _render_event_comment(
                    "impl-status",
                    {"step": i, "timestamp": f"2024-01-01T0{i}:00:00Z"},
                )
            )
        log = EntityLog(comment_bodies=comments)
        entries = log.entries("impl-status")
        assert len(entries) == 5
        for i, entry in enumerate(entries):
            assert entry.data["step"] == i
