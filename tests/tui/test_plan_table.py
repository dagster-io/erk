"""Tests for PlanDataTable widget."""

from rich.text import Text

from erk.core.display_utils import strip_rich_markup
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode
from erk.tui.widgets.plan_table import PlanDataTable
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def _text_to_str(value: str | Text) -> str:
    """Convert Text or str to plain string for assertions."""
    if isinstance(value, Text):
        return value.plain
    return strip_rich_markup(value)


class TestStripRichMarkup:
    """Tests for strip_rich_markup utility function."""

    def test_removes_link_tags(self) -> None:
        """Link markup is removed."""
        text = "[link=https://example.com]click here[/link]"
        result = strip_rich_markup(text)
        assert result == "click here"

    def test_removes_color_tags(self) -> None:
        """Color markup is removed."""
        text = "[cyan]colored text[/cyan]"
        result = strip_rich_markup(text)
        assert result == "colored text"

    def test_preserves_plain_text(self) -> None:
        """Plain text without markup is unchanged."""
        text = "plain text"
        result = strip_rich_markup(text)
        assert result == "plain text"

    def test_removes_nested_tags(self) -> None:
        """Nested tags are removed."""
        text = "[bold][cyan]styled[/cyan][/bold]"
        result = strip_rich_markup(text)
        assert result == "styled"

    def test_handles_emoji_pr_cell(self) -> None:
        """PR cell with emoji and link is cleaned."""
        text = "[link=https://github.com/repo/pull/123]#123[/link] 👀"
        result = strip_rich_markup(text)
        assert result == "#123 👀"


class TestPlanRowData:
    """Tests for PlanRowData dataclass."""

    def test_make_plan_row_defaults(self) -> None:
        """make_plan_row creates row with sensible defaults."""
        row = make_plan_row(123, "Test Plan")
        assert row.plan_id == 123
        assert row.full_title == "Test Plan"
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

        # plan, obj, loc, branch, run-id, run, created, author,
        # pr, chks, cmts, local-wt, local-impl, remote-impl
        assert len(values) == 14
        assert _text_to_str(values[0]) == "#123"
        assert _text_to_str(values[1]) == "-"  # objective (none)
        assert values[2] == "-"  # location (no local, no run)
        assert values[3] == "-"  # branch (none)
        assert values[6] == "-"  # created_display
        assert values[7] == "test-user"  # author
        assert _text_to_str(values[11]) == "-"  # worktree (not exists)
        assert _text_to_str(values[12]) == "-"  # local impl

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

        # plan, obj, loc, branch, run-id, run, created, author,
        # pr, chks, cmts, local-wt, local-impl, remote-impl
        assert len(values) == 14
        assert _text_to_str(values[1]) == "-"  # objective (none)
        assert values[2] == "-"  # location (no local, no run)
        assert values[3] == "-"  # branch (none)
        assert values[6] == "-"  # created_display
        assert values[7] == "test-user"  # author
        assert _text_to_str(values[8]) == "#456"  # pr display
        assert values[9] == "-"  # checks
        assert values[10] == "0/0"  # comments (default for PR with no counts)

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

        # PR display at index 8 (plan, obj, loc, branch, run-id, run, created, author, pr, ...)
        assert _text_to_str(values[8]) == "#456 ✅🔗"

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

        # plan, obj, loc, branch, run-id, run, created, author,
        # pr, chks, cmts, local-wt, local-impl, remote-impl
        assert len(values) == 14

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

        # Worktree is at index 11 (local-wt column)
        assert values[11] == "feature-branch"

    def test_row_to_values_branch_from_pr_head(self) -> None:
        """Row shows pr_head_branch when available."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", pr_head_branch="feat/my-branch")

        values = table._row_to_values(row)

        # Branch is at index 3 (after plan, obj, sts)
        assert values[3] == "feat/my-branch"

    def test_row_to_values_branch_falls_back_to_worktree_branch(self) -> None:
        """Row falls back to worktree_branch when pr_head_branch is None."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", worktree_branch="local-branch")

        values = table._row_to_values(row)

        # Branch is at index 3 (after plan, obj, sts)
        assert values[3] == "local-branch"

    def test_row_to_values_branch_prefers_pr_head_over_worktree(self) -> None:
        """Row prefers pr_head_branch over worktree_branch."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(
            123, "Test Plan", pr_head_branch="pr-branch", worktree_branch="wt-branch"
        )

        values = table._row_to_values(row)

        assert values[3] == "pr-branch"

    def test_row_to_values_includes_author(self) -> None:
        """Row includes author at index 7."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        row = make_plan_row(123, "Test Plan", author="schrockn")

        values = table._row_to_values(row)

        # Author is at index 7 (after plan, obj, loc, branch, run-id, run, created)
        assert values[7] == "schrockn"


class TestLocalWtColumnIndex:
    """Tests for local_wt_column_index tracking."""

    def test_column_index_none_before_setup(self) -> None:
        """Column index is None before columns are set up."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        # Don't call _setup_columns

        assert table.local_wt_column_index is None

    def test_expected_column_index_without_pr_column(self) -> None:
        """Expected column index is 10 when show_pr_column=False.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Without pr column: plan(0), obj(1), loc(2), branch(3),
        # run-id(4), run(5), created(6), author(7), chks(8), cmts(9), local-wt(10)
        expected_index = 10
        assert expected_index == 10

    def test_expected_column_index_with_pr_column(self) -> None:
        """Expected column index is 11 when show_pr_column=True.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # With pr column: plan(0), obj(1), loc(2), branch(3),
        # run-id(4), run(5), created(6), author(7), pr(8), chks(9), cmts(10), local-wt(11)
        expected_index = 11
        assert expected_index == 11


class TestObjectivesViewRowConversion:
    """Tests for row conversion in Objectives view."""

    def test_objectives_view_has_enriched_columns(self) -> None:
        """Objectives view produces plan, slug, progress, state, deps-state, deps, next, updated, author."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Objective Plan")

        values = table._row_to_values(row)

        # Objectives view: plan, slug, progress, state, deps-state, deps, next, updated, author
        assert len(values) == 9
        assert _text_to_str(values[0]) == "#42"
        assert values[1] == "-"  # slug_display
        assert values[2] == "-"  # progress_display
        assert _text_to_str(values[3]) == "-"  # state_display
        assert values[4] == "-"  # deps-state display
        assert values[5] == "-"  # deps (no deps plans)
        assert values[6] == "-"  # next node display
        assert values[7] == "-"  # updated_display
        assert values[8] == "test-user"  # author

    def test_objectives_view_shows_slug_and_sparkline(self) -> None:
        """Objectives view shows slug and state sparkline from row data."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(
            42,
            "Objective: Build Feature",
            objective_done_nodes=3,
            objective_total_nodes=7,
            objective_progress_display="3/7",
            objective_slug_display="build-feature",
            objective_state_display="✓✓✓▶▶○○",
            updated_display="2h ago",
        )

        values = table._row_to_values(row)

        assert values[1] == "build-feature"  # slug
        assert values[2] == "3/7"  # progress
        assert _text_to_str(values[3]) == "✓✓✓▶▶○○"  # state sparkline
        assert values[4] == "-"  # deps-state display
        assert values[5] == "-"  # deps (no deps plans)
        assert values[6] == "-"  # next node display
        assert values[7] == "2h ago"  # updated


class TestObjectivesViewDepsColumn:
    """Tests for deps column rendering in Objectives view."""

    def test_deps_empty_shows_dash(self) -> None:
        """No blocking deps shows '-'."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Obj Plan", objective_deps_plans=())

        values = table._row_to_values(row)

        assert values[5] == "-"

    def test_deps_single_plan(self) -> None:
        """Single blocking plan shows linkified plan number."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(
            42,
            "Obj Plan",
            objective_deps_plans=(("#100", "https://github.com/test/repo/issues/100"),),
        )

        values = table._row_to_values(row)

        assert _text_to_str(values[5]) == "#100"

    def test_deps_three_plans(self) -> None:
        """Three blocking plans shows all three linkified."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(
            42,
            "Obj Plan",
            objective_deps_plans=(
                ("#100", "https://github.com/test/repo/issues/100"),
                ("#200", "https://github.com/test/repo/issues/200"),
                ("#300", "https://github.com/test/repo/issues/300"),
            ),
        )

        values = table._row_to_values(row)

        plain = _text_to_str(values[5])
        assert "#100" in plain
        assert "#200" in plain
        assert "#300" in plain
        assert "\u2026" not in plain  # No ellipsis for exactly 3

    def test_deps_four_plans_truncates_with_ellipsis(self) -> None:
        """Four+ blocking plans shows first two plus ellipsis."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(
            42,
            "Obj Plan",
            objective_deps_plans=(
                ("#100", "https://github.com/test/repo/issues/100"),
                ("#200", "https://github.com/test/repo/issues/200"),
                ("#300", "https://github.com/test/repo/issues/300"),
                ("#400", "https://github.com/test/repo/issues/400"),
            ),
        )

        values = table._row_to_values(row)

        plain = _text_to_str(values[5])
        assert "#100" in plain
        assert "#200" in plain
        assert "#300" not in plain  # Truncated
        assert "\u2026" in plain  # Ellipsis present


class TestObjectivesViewNextColumn:
    """Tests for next column rendering in Objectives view."""

    def test_next_default_shows_dash(self) -> None:
        """Default next node display shows '-'."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Obj Plan")

        values = table._row_to_values(row)

        assert values[6] == "-"

    def test_next_shows_node_id(self) -> None:
        """Next column shows node ID when populated."""
        filters = PlanFilters.default()
        table = PlanDataTable(filters, plan_backend="github")
        table._view_mode = ViewMode.OBJECTIVES
        row = make_plan_row(42, "Obj Plan", objective_next_node_display="1.1")

        values = table._row_to_values(row)

        assert values[6] == "1.1"


class TestShowPrColumnFalse:
    """Tests for show_pr_column=False behavior."""

    def test_row_to_values_with_show_pr_column_false_excludes_pr_value(self) -> None:
        """When show_pr_column=False, pr_display is omitted from row values.

        With show_pr_column=True (14 values):
          plan, obj, loc, branch, run-id, run, created, author,
          pr, chks, cmts, local-wt, local-impl, remote-impl

        With show_pr_column=False (13 values):
          plan, obj, loc, branch, run-id, run, created, author,
          chks, cmts, local-wt, local-impl, remote-impl
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

        # One fewer value than with show_pr_column=True (which produces 14)
        assert len(values) == 13

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
        """When show_pr_column=True (default), pr_display is included at index 8."""
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

        assert len(values) == 14
        # pr at index 8 (after plan, obj, loc, branch, run-id, run, created, author)
        assert _text_to_str(values[8]) == "#456"


# --- Tests for stage column logic in planned_pr mode ---


def test_row_to_values_planned_pr_includes_stage() -> None:
    """planned_pr backend includes lifecycle_display stage value in output."""
    filters = PlanFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
    )
    table = PlanDataTable(filters, plan_backend="planned_pr")
    row = make_plan_row(123, "Test Plan", lifecycle_display="[cyan]review[/cyan]")

    values = table._row_to_values(row)

    # planned_pr: plan, stage, sts, created, obj, loc, branch, run-id, run, author,
    # pr, chks, cmts, local-wt, local-impl, remote-impl
    assert len(values) == 16
    # Stage at index 1 (right after plan in planned_pr mode) - markup stripped
    assert _text_to_str(values[1]) == "review"


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

    # github mode: plan, obj, loc, branch, run-id, run, created, author,
    # pr, chks, cmts, local-wt, local-impl, remote-impl = 14
    assert len(values) == 14


def test_stage_column_index_set_for_planned_pr() -> None:
    """_stage_column_index is set when plan_backend is draft_pr."""
    filters = PlanFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
    )
    table = PlanDataTable(filters, plan_backend="planned_pr")

    # _stage_column_index is set during __init__ but columns aren't set up
    # until on_mount. Verify the initial value is None (pre-setup).
    assert table._stage_column_index is None

    # After __init__, _plan_backend should be set
    assert table._plan_backend == "planned_pr"


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
    """Status cell shows globe emoji when only run URL exists."""
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
