"""Unit tests for dash-data exec command."""

import json
from datetime import UTC, datetime

from erk.cli.commands.exec.scripts.dash_data import _serialize_plan_row
from erk.tui.data.types import PlanRowData
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_serialize_plan_row_basic() -> None:
    """Test basic serialization of PlanRowData to dict."""
    row = make_plan_row(123, "Test Plan")
    result = _serialize_plan_row(row)

    assert result["plan_id"] == 123
    assert result["title"] == "Test Plan"
    assert result["plan_url"] == "https://github.com/test/repo/issues/123"
    assert result["pr_number"] is None
    assert result["exists_locally"] is False
    assert result["last_local_impl_at"] is None
    assert result["last_remote_impl_at"] is None


def test_serialize_plan_row_datetime_fields() -> None:
    """Test that datetime fields are converted to ISO 8601 strings."""
    now = datetime(2025, 6, 15, 12, 30, 0, tzinfo=UTC)
    row = PlanRowData(
        plan_id=456,
        plan_url="https://github.com/test/repo/issues/456",
        title="Datetime Test",
        pr_number=None,
        pr_url=None,
        pr_display="-",
        checks_display="-",
        worktree_name="",
        exists_locally=False,
        local_impl_display="-",
        remote_impl_display="-",
        run_id_display="-",
        run_state_display="-",
        run_url=None,
        full_title="Datetime Test",
        plan_body="",
        pr_title=None,
        pr_state=None,
        pr_head_branch=None,
        worktree_branch=None,
        last_local_impl_at=now,
        last_remote_impl_at=now,
        run_id=None,
        run_status=None,
        run_conclusion=None,
        log_entries=(),
        resolved_comment_count=0,
        total_comment_count=0,
        comments_display="-",
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_issue_closed=None,
        learn_plan_pr=None,
        learn_run_url=None,
        learn_display="- not started",
        learn_display_icon="-",
        objective_issue=None,
        objective_display="-",
        objective_done_nodes=0,
        objective_total_nodes=0,
        objective_progress_display="-",
        objective_next_node_display="-",
        updated_at=now,
        updated_display="-",
        created_at=now,
        created_display="-",
        author="test-user",
        is_learn_plan=False,
    )

    result = _serialize_plan_row(row)

    assert result["last_local_impl_at"] == "2025-06-15T12:30:00+00:00"
    assert result["last_remote_impl_at"] == "2025-06-15T12:30:00+00:00"


def test_serialize_plan_row_tuple_to_list() -> None:
    """Test that tuple fields (log_entries) are converted to lists."""
    row = PlanRowData(
        plan_id=789,
        plan_url="https://github.com/test/repo/issues/789",
        title="Tuple Test",
        pr_number=None,
        pr_url=None,
        pr_display="-",
        checks_display="-",
        worktree_name="",
        exists_locally=False,
        local_impl_display="-",
        remote_impl_display="-",
        run_id_display="-",
        run_state_display="-",
        run_url=None,
        full_title="Tuple Test",
        plan_body="",
        pr_title=None,
        pr_state=None,
        pr_head_branch=None,
        worktree_branch=None,
        last_local_impl_at=None,
        last_remote_impl_at=None,
        run_id=None,
        run_status=None,
        run_conclusion=None,
        log_entries=(("started", "2025-01-01T00:00:00Z", "https://example.com"),),
        resolved_comment_count=0,
        total_comment_count=0,
        comments_display="-",
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_issue_closed=None,
        learn_plan_pr=None,
        learn_run_url=None,
        learn_display="- not started",
        learn_display_icon="-",
        objective_issue=None,
        objective_display="-",
        objective_done_nodes=0,
        objective_total_nodes=0,
        objective_progress_display="-",
        objective_next_node_display="-",
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_display="-",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        created_display="-",
        author="test-user",
        is_learn_plan=False,
    )

    result = _serialize_plan_row(row)

    assert isinstance(result["log_entries"], list)
    assert len(result["log_entries"]) == 1
    assert result["log_entries"][0] == ["started", "2025-01-01T00:00:00Z", "https://example.com"]


def test_serialize_plan_row_with_pr_data() -> None:
    """Test serialization includes PR data when present."""
    row = make_plan_row(
        100,
        "PR Plan",
        pr_number=200,
        pr_url="https://github.com/test/repo/pull/200",
        pr_title="Fix something",
        pr_state="OPEN",
    )
    result = _serialize_plan_row(row)

    assert result["pr_number"] == 200
    assert result["pr_url"] == "https://github.com/test/repo/pull/200"
    assert result["pr_title"] == "Fix something"
    assert result["pr_state"] == "OPEN"


def test_serialize_plan_row_all_fields_present() -> None:
    """Test that all PlanRowData fields appear in serialized output."""
    row = make_plan_row(1, "All Fields")
    result = _serialize_plan_row(row)

    expected_fields = {
        "plan_id",
        "plan_url",
        "title",
        "pr_number",
        "pr_url",
        "pr_display",
        "checks_display",
        "worktree_name",
        "exists_locally",
        "local_impl_display",
        "remote_impl_display",
        "run_id_display",
        "run_state_display",
        "run_url",
        "full_title",
        "plan_body",
        "pr_title",
        "pr_state",
        "pr_head_branch",
        "worktree_branch",
        "last_local_impl_at",
        "last_remote_impl_at",
        "run_id",
        "run_status",
        "run_conclusion",
        "log_entries",
        "resolved_comment_count",
        "total_comment_count",
        "comments_display",
        "learn_status",
        "learn_plan_issue",
        "learn_plan_issue_closed",
        "learn_plan_pr",
        "learn_run_url",
        "learn_display",
        "learn_display_icon",
        "objective_issue",
        "objective_display",
        "objective_done_nodes",
        "objective_total_nodes",
        "objective_progress_display",
        "objective_next_node_display",
        "updated_at",
        "updated_display",
        "created_at",
        "created_display",
        "author",
        "is_learn_plan",
    }
    assert set(result.keys()) == expected_fields


def test_serialize_plan_row_json_roundtrip() -> None:
    """Test that serialized output is valid JSON."""
    now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    row = PlanRowData(
        plan_id=42,
        plan_url="https://github.com/test/repo/issues/42",
        title="JSON Test",
        pr_number=99,
        pr_url="https://github.com/test/repo/pull/99",
        pr_display="#99 ✅",
        checks_display="✓",
        worktree_name="erk-slot-1",
        exists_locally=True,
        local_impl_display="2h ago",
        remote_impl_display="-",
        run_id_display="-",
        run_state_display="-",
        run_url=None,
        full_title="JSON Test Full Title",
        plan_body="Some body",
        pr_title="Fix it",
        pr_state="MERGED",
        pr_head_branch="feature-branch",
        worktree_branch="feature-branch",
        last_local_impl_at=now,
        last_remote_impl_at=None,
        run_id=None,
        run_status=None,
        run_conclusion=None,
        log_entries=(("started", "2025-01-01T00:00:00Z", "https://example.com"),),
        resolved_comment_count=3,
        total_comment_count=5,
        comments_display="3/5",
        learn_status="pending",
        learn_plan_issue=None,
        learn_plan_issue_closed=None,
        learn_plan_pr=None,
        learn_run_url=None,
        learn_display="⟳ in progress",
        learn_display_icon="⟳",
        objective_issue=100,
        objective_display="#100",
        objective_done_nodes=0,
        objective_total_nodes=0,
        objective_progress_display="-",
        objective_next_node_display="-",
        updated_at=now,
        updated_display="-",
        created_at=now,
        created_display="-",
        author="test-user",
        is_learn_plan=False,
    )

    result = _serialize_plan_row(row)
    json_str = json.dumps(result)
    parsed = json.loads(json_str)

    assert parsed["plan_id"] == 42
    assert parsed["last_local_impl_at"] == "2025-01-15T10:00:00+00:00"
    assert parsed["last_remote_impl_at"] is None
    assert parsed["log_entries"] == [["started", "2025-01-01T00:00:00Z", "https://example.com"]]
    assert parsed["objective_issue"] == 100
