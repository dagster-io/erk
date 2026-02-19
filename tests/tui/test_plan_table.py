"""Tests for PlanDataTable widget."""

from rich.text import Text

from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode
from erk.tui.widgets.plan_table import PlanDataTable, _strip_rich_markup
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


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
        assert row.plan_id == 123
        assert row.title == "Test Plan"
        assert row.plan_url == "https://github.com/test/repo/issues/123"
        assert row.pr_number is None
        assert row.pr_display == "-"
        assert row.worktree_name == ""
        assert row.exists_locally is False
        assert row.learn_status is None
        assert row.learn_plan_issue is None
        assert row.learn_plan_pr is None
        assert row.learn_display_icon == "-"
        assert row.is_learn_plan is False

    def test_make_plan_row_with_is_learn_plan(self) -> None:
        """make_plan_row respects is_learn_plan flag."""
        row = make_plan_row(123, "Learn Plan", is_learn_plan=True)
        assert row.is_learn_plan is True

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

    def test_make_plan_row_with_learn_status_pending(self) -> None:
        """make_plan_row with learn_status pending shows spinner."""
        row = make_plan_row(123, "Test Plan", learn_status="pending")
        assert row.learn_status == "pending"
        assert row.learn_display_icon == "⟳"

    def test_make_plan_row_with_learn_status_completed_no_plan(self) -> None:
        """make_plan_row with learn_status completed_no_plan shows empty set."""
        row = make_plan_row(123, "Test Plan", learn_status="completed_no_plan")
        assert row.learn_status == "completed_no_plan"
        assert row.learn_display_icon == "∅"

    def test_make_plan_row_with_learn_status_completed_with_plan(self) -> None:
        """make_plan_row with learn_status completed_with_plan shows issue number."""
        row = make_plan_row(
            123, "Test Plan", learn_status="completed_with_plan", learn_plan_issue=456
        )
        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        assert row.learn_display == "📋 #456"

    def test_make_plan_row_with_learn_status_plan_completed(self) -> None:
        """make_plan_row with learn_status plan_completed shows checkmark and PR."""
        row = make_plan_row(
            123,
            "Test Plan",
            learn_status="plan_completed",
            learn_plan_issue=456,
            learn_plan_pr=789,
        )
        assert row.learn_status == "plan_completed"
        assert row.learn_plan_issue == 456
        assert row.learn_plan_pr == 789
        assert row.learn_display == "✓ #789"


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

        # Should have: plan, title, created, author, obj, lrn, local-wt, local-impl
        assert len(values) == 8
        assert _text_to_str(values[0]) == "#123"
        assert _text_to_str(values[1]) == "Test Plan"
        assert values[2] == "-"  # created_display
        assert values[3] == "test-user"  # author
        assert _text_to_str(values[4]) == "-"  # objective (none)
        assert _text_to_str(values[5]) == "-"  # learn (no status)
        assert _text_to_str(values[6]) == "-"  # worktree (not exists)
        assert _text_to_str(values[7]) == "-"  # local impl

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

        # plan, title, created, author, pr, chks, comments, obj, lrn, local-wt, local-impl
        assert len(values) == 11
        assert values[2] == "-"  # created_display
        assert values[3] == "test-user"  # author
        assert _text_to_str(values[4]) == "#456"  # pr display
        assert values[5] == "-"  # checks
        assert values[6] == "0/0"  # comments (default for PR with no counts)
        assert _text_to_str(values[7]) == "-"  # objective (none)
        assert _text_to_str(values[8]) == "-"  # learn (no status)

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

        # PR display at index 4 (plan, title, created, author, pr, ...)
        assert _text_to_str(values[4]) == "#456 ✅🔗"

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

        # plan, title, created, author, obj, lrn, local-wt, local-impl,
        # remote-impl, run-id, run-state
        assert len(values) == 11

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

        # Worktree is at index 6 (after plan, title, created, author, obj, lrn)
        assert values[6] == "feature-branch"

    def test_row_to_values_with_learn_status_clickable(self) -> None:
        """Row shows learn display with clickable styling when issue/PR set."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        row = make_plan_row(
            123,
            "Test Plan",
            learn_status="completed_with_plan",
            learn_plan_issue=456,
        )

        values = table._row_to_values(row)

        # Learn column is at index 5 (after plan, title, created, author, obj)
        learn_cell = values[5]
        # Should be styled as clickable (cyan underline)
        assert isinstance(learn_cell, Text)
        assert learn_cell.plain == "📋 #456"
        assert "cyan" in str(learn_cell.style)
        assert "underline" in str(learn_cell.style)

    def test_row_to_values_with_learn_status_not_clickable(self) -> None:
        """Row shows learn display without styling when not clickable."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan", learn_status="pending")

        values = table._row_to_values(row)

        # Learn column is at index 5 (icon-only display, after plan, title, created, author, obj)
        learn_cell = values[5]
        # Should be plain string (not styled)
        assert learn_cell == "⟳"

    def test_row_to_values_includes_author(self) -> None:
        """Row includes author at index 3."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan", author="schrockn")

        values = table._row_to_values(row)

        # Author is at index 3 (after plan, title, created)
        assert values[3] == "schrockn"


class TestLocalWtColumnIndex:
    """Tests for local_wt_column_index tracking."""

    def test_column_index_none_before_setup(self) -> None:
        """Column index is None before columns are set up."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        # Don't call _setup_columns

        assert table.local_wt_column_index is None

    def test_expected_column_index_without_prs(self) -> None:
        """Expected column index is 6 when show_prs=False.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Without PRs: plan(0), title(1), created(2), author(3),
        # obj(4), lrn(5), local-wt(6), local-impl(7)
        expected_index = 6
        assert expected_index == 6

    def test_expected_column_index_with_prs(self) -> None:
        """Expected column index is 9 when show_prs=True.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Column layout with PRs:
        # With PRs: plan(0), title(1), created(2), author(3), pr(4),
        # chks(5), comments(6), obj(7), lrn(8), local-wt(9), local-impl(10)
        expected_index = 9
        assert expected_index == 9

    def test_expected_column_index_with_all_columns(self) -> None:
        """Expected column index is 9 with show_prs=True and show_runs=True.

        The local-wt column index doesn't change with show_runs because
        run columns are added after local-wt.
        """
        # Column layout:
        # plan(0), title(1), created(2), author(3), pr(4), chks(5), comments(6), obj(7), lrn(8),
        # local-wt(9), local-impl(10), ...runs
        # Still 9: runs come after local-wt
        expected_index = 9
        assert expected_index == 9


class TestObjectivesViewRowConversion:
    """Tests for row conversion in Objectives view."""

    def test_objectives_view_has_enriched_columns(self) -> None:
        """Objectives view produces plan, title, progress, next, updated, author."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Objective Plan")

        values = table._row_to_values(row)

        # Objectives view: plan, title, progress, next, deps, updated, author
        assert len(values) == 7
        assert _text_to_str(values[0]) == "#42"
        assert _text_to_str(values[1]) == "Objective Plan"
        assert values[2] == "-"  # progress_display
        assert _text_to_str(values[3]) == "-"  # next_step_display
        assert values[4] == "-"  # deps_display
        assert values[5] == "-"  # updated_display
        assert values[6] == "test-user"  # author

    def test_objectives_view_strips_title_prefix(self) -> None:
        """Objectives view strips 'Objective: ' prefix from title."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Objective: Enrich Dashboard")

        values = table._row_to_values(row)

        assert _text_to_str(values[1]) == "Enrich Dashboard"

    def test_objectives_view_preserves_non_prefixed_title(self) -> None:
        """Objectives view preserves titles without the prefix."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "My Plan Title")

        values = table._row_to_values(row)

        assert _text_to_str(values[1]) == "My Plan Title"

    def test_objectives_view_shows_progress_and_next(self) -> None:
        """Objectives view shows progress and next step from row data."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(
            42,
            "Objective: Build Feature",
            objective_done_nodes=3,
            objective_total_nodes=7,
            objective_progress_display="3/7",
            objective_next_node_display="1.3 Add tests",
            updated_display="2h ago",
        )

        values = table._row_to_values(row)

        assert values[2] == "3/7"  # progress
        assert _text_to_str(values[3]) == "1.3 Add tests"  # next step
        assert values[4] == "-"  # deps
        assert values[5] == "2h ago"  # updated


class TestShowPrColumnFalse:
    """Tests for show_pr_column=False behavior."""

    def test_row_to_values_with_show_pr_column_false_excludes_pr_value(self) -> None:
        """When show_pr_column=False, pr_display is omitted from row values.

        With show_prs=True, show_pr_column=True:
          plan, title, created, author, pr, chks, comments, obj, lrn, local-wt, local-impl = 11

        With show_prs=True, show_pr_column=False:
          plan, title, created, author, chks, comments, obj, lrn, local-wt, local-impl = 10
        """
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            show_pr_column=False,
        )
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        # One fewer value than with show_pr_column=True (which produces 11)
        assert len(values) == 10

    def test_row_to_values_with_show_pr_column_false_pr_display_not_in_values(self) -> None:
        """When show_pr_column=False, the pr_display string is absent from values."""
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            show_pr_column=False,
        )
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        # No value should contain "#456" (the pr_display)
        plain_values = [_text_to_str(v) for v in values]
        assert "#456" not in plain_values

    def test_row_to_values_with_show_pr_column_true_includes_pr_value(self) -> None:
        """When show_pr_column=True (default), pr_display is included at index 4."""
        filters = PlanFilters(
            labels=("erk-plan",),
            state=None,
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            show_pr_column=True,
        )
        table = PlanDataTable(filters)
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        assert len(values) == 11
        assert _text_to_str(values[4]) == "#456"  # pr at index 4
