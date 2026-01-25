"""Unit tests for FakeBeadsGateway.

Tests verify that the FakeBeadsGateway correctly filters and returns
issues based on provided criteria.
"""

from erk_shared.gateway.beads.fake import FakeBeadsGateway
from erk_shared.gateway.beads.types import BeadsIssue


def _make_issue(
    *,
    id: str,
    title: str,
    status: str,
    labels: tuple[str, ...],
) -> BeadsIssue:
    """Create a BeadsIssue with minimal required fields for testing."""
    return BeadsIssue(
        id=id,
        title=title,
        description="",
        status=status,
        labels=labels,
        assignee=None,
        notes="",
        created_at="2024-01-15T10:30:00Z",
        updated_at="2024-01-15T10:30:00Z",
    )


class TestFakeBeadsGatewayListIssues:
    """Tests for FakeBeadsGateway.list_issues()."""

    def test_list_issues_empty(self) -> None:
        """Returns empty list when no issues configured."""
        gateway = FakeBeadsGateway(issues=None)

        result = gateway.list_issues(labels=None, status=None, limit=None)

        assert result == []

    def test_list_issues_with_data(self) -> None:
        """Returns all configured issues when no filters applied."""
        issues = [
            _make_issue(id="bd-001", title="First", status="open", labels=()),
            _make_issue(id="bd-002", title="Second", status="closed", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=None, status=None, limit=None)

        assert len(result) == 2
        assert result[0].id == "bd-001"
        assert result[1].id == "bd-002"

    def test_list_issues_filter_by_single_label(self) -> None:
        """Filters issues by a single label."""
        issues = [
            _make_issue(id="bd-001", title="Has label", status="open", labels=("erk-plan",)),
            _make_issue(id="bd-002", title="No label", status="open", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=["erk-plan"], status=None, limit=None)

        assert len(result) == 1
        assert result[0].id == "bd-001"

    def test_list_issues_filter_by_multiple_labels_and_logic(self) -> None:
        """Filters issues requiring ALL specified labels (AND logic)."""
        issues = [
            _make_issue(
                id="bd-001",
                title="Has both",
                status="open",
                labels=("erk-plan", "priority"),
            ),
            _make_issue(
                id="bd-002",
                title="Has one",
                status="open",
                labels=("erk-plan",),
            ),
            _make_issue(id="bd-003", title="Has none", status="open", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=["erk-plan", "priority"], status=None, limit=None)

        assert len(result) == 1
        assert result[0].id == "bd-001"

    def test_list_issues_filter_by_status(self) -> None:
        """Filters issues by status."""
        issues = [
            _make_issue(id="bd-001", title="Open", status="open", labels=()),
            _make_issue(id="bd-002", title="Closed", status="closed", labels=()),
            _make_issue(id="bd-003", title="In Progress", status="in_progress", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=None, status="open", limit=None)

        assert len(result) == 1
        assert result[0].id == "bd-001"

    def test_list_issues_with_limit(self) -> None:
        """Respects limit parameter."""
        issues = [
            _make_issue(id="bd-001", title="First", status="open", labels=()),
            _make_issue(id="bd-002", title="Second", status="open", labels=()),
            _make_issue(id="bd-003", title="Third", status="open", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=None, status=None, limit=2)

        assert len(result) == 2
        assert result[0].id == "bd-001"
        assert result[1].id == "bd-002"

    def test_list_issues_combined_filters(self) -> None:
        """Applies label and status filters together."""
        issues = [
            _make_issue(id="bd-001", title="Open with label", status="open", labels=("erk-plan",)),
            _make_issue(
                id="bd-002",
                title="Closed with label",
                status="closed",
                labels=("erk-plan",),
            ),
            _make_issue(id="bd-003", title="Open no label", status="open", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=["erk-plan"], status="open", limit=None)

        assert len(result) == 1
        assert result[0].id == "bd-001"


class TestFakeBeadsGatewayWithEmptyIssues:
    """Test edge cases with empty issues list."""

    def test_empty_list_explicit(self) -> None:
        """Empty list passed explicitly works correctly."""
        gateway = FakeBeadsGateway(issues=[])

        result = gateway.list_issues(labels=None, status=None, limit=None)

        assert result == []

    def test_limit_greater_than_available(self) -> None:
        """Limit greater than available issues returns all."""
        issues = [
            _make_issue(id="bd-001", title="Only one", status="open", labels=()),
        ]
        gateway = FakeBeadsGateway(issues=issues)

        result = gateway.list_issues(labels=None, status=None, limit=100)

        assert len(result) == 1
