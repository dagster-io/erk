"""Tests for plan_store.conversion module."""

from datetime import UTC, datetime

from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.schemas import (
    LAST_LOCAL_IMPL_AT,
    LEARN_PLAN_ISSUE,
    OBJECTIVE_ISSUE,
    WORKTREE_NAME,
)
from erk_shared.gateway.github.types import PRDetails
from erk_shared.plan_store.conversion import (
    header_datetime,
    header_int,
    header_str,
    issue_info_to_plan,
    pr_details_to_plan,
)
from erk_shared.plan_store.types import PlanState
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_issue(
    *,
    number: int = 42,
    title: str = "Test plan",
    body: str = "",
    state: str = "OPEN",
) -> IssueInfo:
    """Create an IssueInfo for testing."""
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 12, 0, tzinfo=UTC),
        author="test-user",
    )


class TestIssueInfoToPlan:
    """Tests for issue_info_to_plan conversion."""

    def test_basic_fields_mapped(self) -> None:
        """Plan fields are populated from IssueInfo."""
        issue = _make_issue(number=42, title="My plan", state="OPEN")
        plan = issue_info_to_plan(issue)

        assert plan.plan_identifier == "42"
        assert plan.title == "My plan"
        assert plan.state == PlanState.OPEN
        assert plan.url == "https://github.com/test/repo/issues/42"
        assert plan.labels == ["erk-plan"]
        assert plan.metadata["number"] == 42
        assert plan.metadata["author"] == "test-user"

    def test_closed_state(self) -> None:
        """CLOSED state maps correctly."""
        issue = _make_issue(state="CLOSED")
        plan = issue_info_to_plan(issue)
        assert plan.state == PlanState.CLOSED

    def test_header_fields_populated_from_plan_header(self) -> None:
        """header_fields are populated from plan-header metadata block."""
        body = format_plan_header_body_for_test(
            worktree_name="my-worktree",
            objective_issue=100,
        )
        issue = _make_issue(body=body)
        plan = issue_info_to_plan(issue)

        assert plan.header_fields.get(WORKTREE_NAME) == "my-worktree"
        assert plan.header_fields.get(OBJECTIVE_ISSUE) == 100

    def test_objective_id_extracted_from_header_fields(self) -> None:
        """objective_id is extracted from header_fields during conversion."""
        body = format_plan_header_body_for_test(objective_issue=200)
        issue = _make_issue(body=body)
        plan = issue_info_to_plan(issue)

        assert plan.objective_id == 200

    def test_empty_body_produces_empty_header_fields(self) -> None:
        """Empty body produces empty header_fields dict."""
        issue = _make_issue(body="")
        plan = issue_info_to_plan(issue)

        assert plan.header_fields == {}
        assert plan.objective_id is None

    def test_body_without_plan_header_produces_empty_header_fields(self) -> None:
        """Body without plan-header block produces empty header_fields."""
        issue = _make_issue(body="Just a regular issue body")
        plan = issue_info_to_plan(issue)

        assert plan.header_fields == {}
        assert plan.objective_id is None


class TestHeaderStr:
    """Tests for header_str typed accessor."""

    def test_string_value_returned_directly(self) -> None:
        """String values are returned as-is."""
        fields: dict[str, object] = {WORKTREE_NAME: "my-wt"}
        assert header_str(fields, WORKTREE_NAME) == "my-wt"

    def test_datetime_value_converted_to_iso(self) -> None:
        """datetime values are converted to ISO string."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        fields: dict[str, object] = {LAST_LOCAL_IMPL_AT: dt}
        result = header_str(fields, LAST_LOCAL_IMPL_AT)
        assert result is not None
        assert "2024-01-15" in result

    def test_missing_key_returns_none(self) -> None:
        """Missing key returns None."""
        fields: dict[str, object] = {}
        assert header_str(fields, WORKTREE_NAME) is None

    def test_none_value_returns_none(self) -> None:
        """None value returns None."""
        fields: dict[str, object] = {WORKTREE_NAME: None}
        assert header_str(fields, WORKTREE_NAME) is None


class TestHeaderInt:
    """Tests for header_int typed accessor."""

    def test_int_value_returned_directly(self) -> None:
        """Integer values are returned as-is."""
        fields: dict[str, object] = {OBJECTIVE_ISSUE: 42}
        assert header_int(fields, OBJECTIVE_ISSUE) == 42

    def test_missing_key_returns_none(self) -> None:
        """Missing key returns None."""
        fields: dict[str, object] = {}
        assert header_int(fields, OBJECTIVE_ISSUE) is None

    def test_none_value_returns_none(self) -> None:
        """None value returns None."""
        fields: dict[str, object] = {LEARN_PLAN_ISSUE: None}
        assert header_int(fields, LEARN_PLAN_ISSUE) is None

    def test_non_int_value_returns_none(self) -> None:
        """Non-integer values return None."""
        fields: dict[str, object] = {OBJECTIVE_ISSUE: "not-an-int"}
        assert header_int(fields, OBJECTIVE_ISSUE) is None


class TestHeaderDatetime:
    """Tests for header_datetime typed accessor."""

    def test_datetime_value_returned_directly(self) -> None:
        """datetime values are returned as-is."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        fields: dict[str, object] = {LAST_LOCAL_IMPL_AT: dt}
        assert header_datetime(fields, LAST_LOCAL_IMPL_AT) == dt

    def test_iso_string_parsed_to_datetime(self) -> None:
        """ISO string values are parsed to datetime."""
        fields: dict[str, object] = {LAST_LOCAL_IMPL_AT: "2024-01-15T10:30:00Z"}
        result = header_datetime(fields, LAST_LOCAL_IMPL_AT)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_missing_key_returns_none(self) -> None:
        """Missing key returns None."""
        fields: dict[str, object] = {}
        assert header_datetime(fields, LAST_LOCAL_IMPL_AT) is None

    def test_none_value_returns_none(self) -> None:
        """None value returns None."""
        fields: dict[str, object] = {LAST_LOCAL_IMPL_AT: None}
        assert header_datetime(fields, LAST_LOCAL_IMPL_AT) is None

    def test_non_datetime_non_string_returns_none(self) -> None:
        """Non-datetime, non-string values return None."""
        fields: dict[str, object] = {LAST_LOCAL_IMPL_AT: 12345}
        assert header_datetime(fields, LAST_LOCAL_IMPL_AT) is None


def _make_pr_details(
    *,
    number: int = 42,
    title: str = "Test plan",
    body: str = "",
    state: str = "OPEN",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    author: str = "test-user",
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/test/repo/pull/{number}",
        title=title,
        body=body,
        state=state,
        is_draft=True,
        base_ref_name="master",
        head_ref_name="plan-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test",
        repo="repo",
        labels=("erk-plan",),
        created_at=created_at or datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=updated_at or datetime(2024, 1, 16, 12, 0, tzinfo=UTC),
        author=author,
    )


class TestPrDetailsToPlan:
    """Tests for pr_details_to_plan conversion."""

    def test_pr_timestamps_mapped_to_plan(self) -> None:
        """Real PR timestamps are preserved, not replaced with epoch sentinel."""
        created = datetime(2025, 6, 10, 9, 0, tzinfo=UTC)
        updated = datetime(2025, 6, 11, 14, 30, tzinfo=UTC)
        pr = _make_pr_details(created_at=created, updated_at=updated)

        plan = pr_details_to_plan(pr, plan_body=None)

        assert plan.created_at == created
        assert plan.updated_at == updated

    def test_pr_author_mapped_to_metadata(self) -> None:
        """Author from PRDetails is stored in plan metadata."""
        pr = _make_pr_details(author="schrockn")

        plan = pr_details_to_plan(pr, plan_body=None)

        assert plan.metadata["author"] == "schrockn"

    def test_plan_body_overrides_pr_body_when_provided(self) -> None:
        """Extracted plan_body is used as the plan body, not the raw PR body."""
        pr = _make_pr_details(body="<!-- metadata -->\n\n---\n\n# Plan content")

        plan = pr_details_to_plan(pr, plan_body="# Plan content")

        assert plan.body == "# Plan content"

    def test_pr_body_used_when_plan_body_is_none(self) -> None:
        """PR body is used directly when plan_body is None."""
        pr = _make_pr_details(body="raw pr body")

        plan = pr_details_to_plan(pr, plan_body=None)

        assert plan.body == "raw pr body"
