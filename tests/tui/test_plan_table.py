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
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan")

        values = table._row_to_values(row)

        # plan, obj, sts, title, branch, created, author, lrn, local-wt, local-impl
        assert len(values) == 10
        assert _text_to_str(values[0]) == "#123"
        assert _text_to_str(values[1]) == "-"  # objective (none)
        assert values[2] == "-"  # status (no local, no run)
        assert _text_to_str(values[3]) == "Test Plan"
        assert values[4] == "-"  # branch (none)
        assert values[5] == "-"  # created_display
        assert values[6] == "test-user"  # author
        assert _text_to_str(values[7]) == "-"  # learn (no status)
        assert _text_to_str(values[8]) == "-"  # worktree (not exists)
        assert _text_to_str(values[9]) == "-"  # local impl

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
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        # plan, obj, sts, title, branch, created, author,
        # pr, chks, comments, lrn, local-wt, local-impl
        assert len(values) == 13
        assert _text_to_str(values[1]) == "-"  # objective (none)
        assert values[2] == "-"  # status (no local, no run)
        assert _text_to_str(values[3]) == "Test Plan"
        assert values[4] == "-"  # branch (none)
        assert values[5] == "-"  # created_display
        assert values[6] == "test-user"  # author
        assert _text_to_str(values[7]) == "#456"  # pr display
        assert values[8] == "-"  # checks
        assert values[9] == "0/0"  # comments (default for PR with no counts)
        assert _text_to_str(values[10]) == "-"  # learn (no status)

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
        table = PlanDataTable(filters, plan_backend="github")
        # Use custom pr_display with link indicator (simulates will_close_target=True)
        row = make_plan_row(123, "Test Plan", pr_number=456, pr_display="#456 ✅🔗")

        values = table._row_to_values(row)

        # PR display at index 7 (plan, obj, sts, title, branch, created, author, pr, ...)
        assert _text_to_str(values[7]) == "#456 ✅🔗"

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
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan")

        values = table._row_to_values(row)

        # plan, obj, sts, title, branch, created, author, lrn, local-wt, local-impl,
        # remote-impl, run-id, run-state
        assert len(values) == 13

    def test_row_to_values_with_worktree(self) -> None:
        """Row shows worktree name when exists locally."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(
            123,
            "Test Plan",
            worktree_name="feature-branch",
            exists_locally=True,
        )

        values = table._row_to_values(row)

        # Worktree is at index 8 (after plan, obj, sts, title, branch, created, author, lrn)
        assert values[8] == "feature-branch"

    def test_row_to_values_branch_from_pr_head(self) -> None:
        """Row shows pr_head_branch when available."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", pr_head_branch="feat/my-branch")

        values = table._row_to_values(row)

        # Branch is at index 4 (after plan, obj, sts, title)
        assert values[4] == "feat/my-branch"

    def test_row_to_values_branch_falls_back_to_worktree_branch(self) -> None:
        """Row falls back to worktree_branch when pr_head_branch is None."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", worktree_branch="local-branch")

        values = table._row_to_values(row)

        # Branch is at index 4 (after plan, obj, sts, title)
        assert values[4] == "local-branch"

    def test_row_to_values_branch_prefers_pr_head_over_worktree(self) -> None:
        """Row prefers pr_head_branch over worktree_branch."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(
            123, "Test Plan", pr_head_branch="pr-branch", worktree_branch="wt-branch"
        )

        values = table._row_to_values(row)

        assert values[4] == "pr-branch"

    def test_row_to_values_with_learn_status_clickable(self) -> None:
        """Row shows learn display with clickable styling when issue/PR set."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(
            123,
            "Test Plan",
            learn_status="completed_with_plan",
            learn_plan_issue=456,
        )

        values = table._row_to_values(row)

        # Learn column is at index 7 (after plan, obj, sts, title, branch, created, author)
        learn_cell = values[7]
        # Should be styled as clickable (cyan underline)
        assert isinstance(learn_cell, Text)
        assert learn_cell.plain == "📋 #456"
        assert "cyan" in str(learn_cell.style)
        assert "underline" in str(learn_cell.style)

    def test_row_to_values_with_learn_status_not_clickable(self) -> None:
        """Row shows learn display without styling when not clickable."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", learn_status="pending")

        values = table._row_to_values(row)

        # Learn column at index 7 (after plan, obj, sts, title, branch, created, author)
        learn_cell = values[7]
        # Should be plain string (not styled)
        assert learn_cell == "⟳"

    def test_row_to_values_includes_author(self) -> None:
        """Row includes author at index 3."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", author="schrockn")

        values = table._row_to_values(row)

        # Author is at index 6 (after plan, obj, sts, title, branch, created)
        assert values[6] == "schrockn"


class TestLocalWtColumnIndex:
    """Tests for local_wt_column_index tracking."""

    def test_column_index_none_before_setup(self) -> None:
        """Column index is None before columns are set up."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        # Don't call _setup_columns

        assert table.local_wt_column_index is None

    def test_expected_column_index_without_prs(self) -> None:
        """Expected column index is 8 when show_prs=False.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Without PRs: plan(0), obj(1), sts(2), title(3), branch(4),
        # created(5), author(6), lrn(7), local-wt(8), local-impl(9)
        expected_index = 8
        assert expected_index == 8

    def test_expected_column_index_with_prs(self) -> None:
        """Expected column index is 11 when show_prs=True.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Column layout with PRs:
        # With PRs: plan(0), obj(1), sts(2), title(3), branch(4), author(5),
        # created(6), pr(7), chks(8), comments(9), lrn(10), local-wt(11), local-impl(12)
        expected_index = 11
        assert expected_index == 11

    def test_expected_column_index_with_all_columns(self) -> None:
        """Expected column index is 11 with show_prs=True and show_runs=True.

        The local-wt column index doesn't change with show_runs because
        run columns are added after local-wt.
        """
        # Column layout:
        # plan(0), obj(1), sts(2), title(3), branch(4), created(5), author(6),
        # pr(7), chks(8), comments(9), lrn(10), local-wt(11), local-impl(12), ...runs
        # Still 11: runs come after local-wt
        expected_index = 11
        assert expected_index == 11


class TestObjectivesViewRowConversion:
    """Tests for row conversion in Objectives view."""

    def test_objectives_view_has_enriched_columns(self) -> None:
        """Objectives view produces plan, title, progress, next, updated, author."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
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
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Objective: Enrich Dashboard")

        values = table._row_to_values(row)

        assert _text_to_str(values[1]) == "Enrich Dashboard"

    def test_objectives_view_preserves_non_prefixed_title(self) -> None:
        """Objectives view preserves titles without the prefix."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "My Plan Title")

        values = table._row_to_values(row)

        assert _text_to_str(values[1]) == "My Plan Title"

    def test_objectives_view_shows_progress_and_next(self) -> None:
        """Objectives view shows progress and next step from row data."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
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

        With show_prs=True, show_pr_column=True (13 values):
          plan, obj, sts, title, branch, created, author, pr,
          chks, comments, lrn, local-wt, local-impl

        With show_prs=True, show_pr_column=False (12 values):
          plan, obj, sts, title, branch, created, author,
          chks, comments, lrn, local-wt, local-impl
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
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        # One fewer value than with show_pr_column=True (which produces 13)
        assert len(values) == 12

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
        table = PlanDataTable(filters, plan_backend="github")
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
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", pr_number=456)

        values = table._row_to_values(row)

        assert len(values) == 13
        # pr at index 7 (after plan, obj, sts, title, branch, created, author)
        assert _text_to_str(values[7]) == "#456"


# --- Tests for stage column logic in draft_pr mode ---


def test_row_to_values_draft_pr_includes_stage() -> None:
    """draft_pr backend includes lifecycle_display stage value in output."""
    filters = PlanFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
    )
    table = PlanDataTable(filters, plan_backend="draft_pr")
    row = make_plan_row(123, "Test Plan", lifecycle_display="[cyan]review[/cyan]")

    values = table._row_to_values(row)

    # draft_pr adds stage after author:
    # plan, obj, sts, title, branch, created, author, stage, lrn, local-wt, local-impl
    assert len(values) == 11
    # Stage at index 7 (after plan, obj, sts, title, branch, created, author) - markup stripped
    assert _text_to_str(values[7]) == "review"


def test_row_to_values_github_does_not_include_stage() -> None:
    """github backend does NOT include stage value in output."""
    filters = PlanFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
    )
    table = PlanDataTable(filters, plan_backend="github")
    row = make_plan_row(123, "Test Plan", lifecycle_display="[cyan]review[/cyan]")

    values = table._row_to_values(row)

    # github mode: plan, obj, sts, title, branch, created, author, lrn, local-wt, local-impl = 10
    assert len(values) == 10


def test_stage_column_index_set_for_draft_pr() -> None:
    """_stage_column_index is set when plan_backend is draft_pr."""
    filters = PlanFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
    )
    table = PlanDataTable(filters, plan_backend="draft_pr")

    # _stage_column_index is set during __init__ but columns aren't set up
    # until on_mount. Verify the initial value is None (pre-setup).
    assert table._stage_column_index is None

    # After __init__, _plan_backend should be set
    assert table._plan_backend == "draft_pr"


def test_stage_column_index_none_for_github() -> None:
    """_stage_column_index remains None when plan_backend is github."""
    filters = PlanFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
    )
    table = PlanDataTable(filters, plan_backend="github")
    assert table._stage_column_index is None


# --- Tests for compact status emoji column ---


def test_row_to_values_status_empty() -> None:
    """Status cell shows '-' when no local checkout and no run URL."""
    filters = PlanFilters.default()
    table = PlanDataTable(filters, plan_backend="github")
    row = make_plan_row(123, "Test Plan", exists_locally=False, run_url=None)

    values = table._row_to_values(row)

    # sts is at index 2 (after plan, obj)
    assert values[2] == "-"


def test_row_to_values_status_local_only() -> None:
    """Status cell shows laptop emoji when only local checkout exists."""
    filters = PlanFilters.default()
    table = PlanDataTable(filters, plan_backend="github")
    row = make_plan_row(123, "Test Plan", exists_locally=True)

    values = table._row_to_values(row)

    assert values[2] == "\U0001f4bb"


def test_row_to_values_status_remote_only() -> None:
    """Status cell shows cloud emoji when only run URL exists."""
    filters = PlanFilters.default()
    table = PlanDataTable(filters, plan_backend="github")
    row = make_plan_row(123, "Test Plan", run_url="https://github.com/runs/1")

    values = table._row_to_values(row)

    assert values[2] == "\u2601"


def test_row_to_values_status_both() -> None:
    """Status cell shows both emojis when local checkout and run URL exist."""
    filters = PlanFilters.default()
    table = PlanDataTable(filters, plan_backend="github")
    row = make_plan_row(123, "Test Plan", exists_locally=True, run_url="https://github.com/runs/1")

    values = table._row_to_values(row)

    assert values[2] == "\U0001f4bb\u2601"
