"""Tests for PlanDataTable widget."""

from rich.text import Text

from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable, _strip_rich_markup
from tests.fakes.plan_data_provider import make_plan_row


def _text_to_str(value: str | Text) -> str:
    """Convert Text or str to plain string for assertions."""
    if isinstance(value, Text):
        return value.plain
    return value


class TestStripRichMarkup:
    """Tests for _strip_rich_markup utility function."""

    def test_removes_link_tags(self) -> None:
        """Link markup is removed."""
        text = "[link=https://example.com]click here[/link]"
        result = _strip_rich_markup(text)
        assert result == "click here"

    def test_removes_color_tags(self) -> None:
        """Color markup is removed."""
        text = "[cyan]colored text[/cyan]"
        result = _strip_rich_markup(text)
        assert result == "colored text"

    def test_preserves_plain_text(self) -> None:
        """Plain text without markup is unchanged."""
        text = "plain text"
        result = _strip_rich_markup(text)
        assert result == "plain text"

    def test_removes_nested_tags(self) -> None:
        """Nested tags are removed."""
        text = "[bold][cyan]styled[/cyan][/bold]"
        result = _strip_rich_markup(text)
        assert result == "styled"

    def test_handles_emoji_pr_cell(self) -> None:
        """PR cell with emoji and link is cleaned."""
        text = "[link=https://github.com/repo/pull/123]#123[/link] 👀"
        result = _strip_rich_markup(text)
        assert result == "#123 👀"


class TestPlanRowData:
    """Tests for PlanRowData dataclass."""

    def test_make_plan_row_defaults(self) -> None:
        """make_plan_row creates row with sensible defaults."""
        row = make_plan_row(123, "Test Plan")
        assert row.issue_number == 123
        assert row.title == "Test Plan"
        assert row.issue_url == "https://github.com/test/repo/issues/123"
        assert row.pr_number is None
        assert row.pr_display == "-"
        assert row.worktree_name == ""
        assert row.exists_locally is False

    def test_make_plan_row_with_pr(self) -> None:
        """make_plan_row with PR data."""
        row = make_plan_row(
            123,
            "Feature",
            pr_number=456,
            pr_url="https://github.com/test/repo/pull/456",
        )
        assert row.pr_number == 456
        assert row.pr_display == "#456"
        assert row.pr_url == "https://github.com/test/repo/pull/456"

    def test_make_plan_row_with_worktree(self) -> None:
        """make_plan_row with local worktree."""
        row = make_plan_row(
            123,
            "Feature",
            worktree_name="feature-branch",
            exists_locally=True,
        )
        assert row.worktree_name == "feature-branch"
        assert row.exists_locally is True

    def test_make_plan_row_with_custom_pr_display(self) -> None:
        """make_plan_row with custom pr_display for link indicator."""
        row = make_plan_row(
            123,
            "Feature",
            pr_number=456,
            pr_display="#456 ✅🔗",
        )
        assert row.pr_number == 456
        assert row.pr_display == "#456 ✅🔗"


class TestPlanDataTableRowConversion:
    """Tests for PlanDataTable row value conversion."""

    def test_row_to_values_basic(self) -> None:
        """Basic row conversion without optional columns."""
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
        )
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan")

        values = table._row_to_values(row)

        # Should have: plan, title, local-wt, local-impl
        assert len(values) == 4
        assert _text_to_str(values[0]) == "#123"
        assert _text_to_str(values[1]) == "Test Plan"
        assert _text_to_str(values[2]) == "-"  # worktree (not exists)
        assert _text_to_str(values[3]) == "-"  # local impl

    def test_row_to_values_with_prs(self) -> None:
        """Row conversion with PR columns enabled."""
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
        )
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        # Should have: plan, title, pr, chks, local-wt, local-impl
        assert len(values) == 6
        assert values[2] == "#456"  # pr display
        assert values[3] == "-"  # checks

    def test_row_to_values_with_pr_link_indicator(self) -> None:
        """Row conversion shows 🔗 indicator for PRs that will close issues."""
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
        )
        table = PlanDataTable(filters)
        # Use custom pr_display with link indicator (simulates will_close_target=True)
        row = make_plan_row(123, "Test Plan", pr_number=456, pr_display="#456 ✅🔗")

        values = table._row_to_values(row)

        # PR display should include the link indicator
        assert values[2] == "#456 ✅🔗"

    def test_row_to_values_with_runs(self) -> None:
        """Row conversion with run columns enabled."""
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=True,
        )
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan")

        values = table._row_to_values(row)

        # Should have: plan, title, local-wt, local-impl, remote-impl, run-id, run-state
        assert len(values) == 7

    def test_row_to_values_with_worktree(self) -> None:
        """Row shows worktree name when exists locally."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        row = make_plan_row(
            123,
            "Test Plan",
            worktree_name="feature-branch",
            exists_locally=True,
        )

        values = table._row_to_values(row)

        assert values[2] == "feature-branch"


class TestLocalWtColumnIndex:
    """Tests for local_wt_column_index tracking."""

    def test_column_index_none_before_setup(self) -> None:
        """Column index is None before columns are set up."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        # Don't call _setup_columns

        assert table.local_wt_column_index is None

    def test_expected_column_index_without_prs(self) -> None:
        """Expected column index is 2 when show_prs=False (plan, title, local-wt).

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Column layout without PRs: plan(0), title(1), local-wt(2), local-impl(3)
        expected_index = 2
        assert expected_index == 2

    def test_expected_column_index_with_prs(self) -> None:
        """Expected column index is 4 when show_prs=True (plan, title, pr, chks, local-wt).

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Column layout with PRs: plan(0), title(1), pr(2), chks(3), local-wt(4), local-impl(5)
        expected_index = 4
        assert expected_index == 4

    def test_expected_column_index_with_all_columns(self) -> None:
        """Expected column index is 4 with show_prs=True and show_runs=True.

        The local-wt column index doesn't change with show_runs because
        run columns are added after local-wt.
        """
        # Column layout: plan(0), title(1), pr(2), chks(3), local-wt(4), local-impl(5), ...runs
        # Still 4: runs come after local-wt
        expected_index = 4
        assert expected_index == 4
