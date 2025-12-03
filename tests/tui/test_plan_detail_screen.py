"""Unit tests for PlanDetailScreen badge logic functions."""

from erk.tui.app import PlanDetailScreen
from tests.fakes.plan_data_provider import make_plan_row


class TestGetPrStateBadge:
    """Tests for _get_pr_state_badge() pure function logic."""

    def test_pr_state_merged_returns_merged_badge(self) -> None:
        """MERGED state returns MERGED text with badge-merged class."""
        row = make_plan_row(123, "Test", pr_state="MERGED")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_pr_state_badge()
        assert text == "MERGED"
        assert css_class == "badge-merged"

    def test_pr_state_closed_returns_closed_badge(self) -> None:
        """CLOSED state returns CLOSED text with badge-closed class."""
        row = make_plan_row(123, "Test", pr_state="CLOSED")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_pr_state_badge()
        assert text == "CLOSED"
        assert css_class == "badge-closed"

    def test_pr_state_open_returns_open_badge(self) -> None:
        """OPEN state returns OPEN text with badge-open class."""
        row = make_plan_row(123, "Test", pr_state="OPEN")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_pr_state_badge()
        assert text == "OPEN"
        assert css_class == "badge-open"

    def test_pr_state_none_returns_pr_badge(self) -> None:
        """None state returns PR text with badge-pr class."""
        row = make_plan_row(123, "Test", pr_state=None)
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_pr_state_badge()
        assert text == "PR"
        assert css_class == "badge-pr"

    def test_pr_state_unknown_returns_pr_badge(self) -> None:
        """Unknown state returns PR text with badge-pr class."""
        row = make_plan_row(123, "Test", pr_state="UNKNOWN_STATE")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_pr_state_badge()
        assert text == "PR"
        assert css_class == "badge-pr"


class TestGetRunBadge:
    """Tests for _get_run_badge() pure function logic."""

    def test_no_run_status_returns_no_runs(self) -> None:
        """No run_status returns 'No runs' with badge-dim class."""
        row = make_plan_row(123, "Test", run_status=None)
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "No runs"
        assert css_class == "badge-dim"

    def test_conclusion_success_returns_passed_badge(self) -> None:
        """Success conclusion returns passed badge."""
        row = make_plan_row(123, "Test", run_status="completed", run_conclusion="success")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "✓ Passed"
        assert css_class == "badge-success"

    def test_conclusion_failure_returns_failed_badge(self) -> None:
        """Failure conclusion returns failed badge."""
        row = make_plan_row(123, "Test", run_status="completed", run_conclusion="failure")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "✗ Failed"
        assert css_class == "badge-failure"

    def test_conclusion_cancelled_returns_dim_badge(self) -> None:
        """Cancelled conclusion returns dim badge."""
        row = make_plan_row(123, "Test", run_status="completed", run_conclusion="cancelled")
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "Cancelled"
        assert css_class == "badge-dim"

    def test_status_in_progress_returns_running_badge(self) -> None:
        """In progress status returns running badge."""
        row = make_plan_row(123, "Test", run_status="in_progress", run_conclusion=None)
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "Running..."
        assert css_class == "badge-pending"

    def test_status_queued_returns_queued_badge(self) -> None:
        """Queued status returns queued badge."""
        row = make_plan_row(123, "Test", run_status="queued", run_conclusion=None)
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "Queued"
        assert css_class == "badge-pending"

    def test_unknown_status_returns_status_with_dim_badge(self) -> None:
        """Unknown status returns the status text with badge-dim class."""
        row = make_plan_row(123, "Test", run_status="some_other_status", run_conclusion=None)
        screen = PlanDetailScreen(row)
        text, css_class = screen._get_run_badge()
        assert text == "some_other_status"
        assert css_class == "badge-dim"
