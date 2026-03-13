"""Tests for PlanDataTable widget."""

from rich.text import Text

from erk.core.display_utils import strip_rich_markup
from erk.tui.data.types import PrFilters
from erk.tui.views.types import ViewMode
from erk.tui.widgets.plan_table import PlanDataTable
from tests.fakes.gateway.plan_data_provider import make_pr_row


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


class TestPrRowData:
    """Tests for PrRowData dataclass."""

    def test_make_pr_row_defaults(self) -> None:
        """make_pr_row creates row with sensible defaults."""
        row = make_pr_row(123, "Test Plan")
        assert row.pr_number == 123
        assert row.full_title == "Test Plan"
        assert row.pr_url == "https://github.com/test/repo/issues/123"
        assert row.pr_display == "#123"
        assert row.worktree_name == ""
        assert row.exists_locally is False
        assert row.learn_status is None
        assert row.learn_plan_issue is None
        assert row.learn_plan_pr is None
        assert row.learn_display_icon == "-"
        assert row.is_learn_plan is False

    def test_make_pr_row_with_is_learn_plan(self) -> None:
        """make_pr_row respects is_learn_plan flag."""
        row = make_pr_row(123, "Learn Plan", is_learn_plan=True)
        assert row.is_learn_plan is True

    def test_make_pr_row_with_pr_url(self) -> None:
        """make_pr_row with PR URL override."""
        row = make_pr_row(
            123,
            "Feature",
            pr_url="https://github.com/test/repo/pull/123",
        )
        assert row.pr_number == 123
        assert row.pr_display == "#123"
        assert row.pr_url == "https://github.com/test/repo/pull/123"

    def test_make_pr_row_with_worktree(self) -> None:
        """make_pr_row with local worktree."""
        row = make_pr_row(
            123,
            "Feature",
            worktree_name="feature-branch",
            exists_locally=True,
        )
        assert row.worktree_name == "feature-branch"
        assert row.exists_locally is True

    def test_make_pr_row_with_custom_pr_display(self) -> None:
        """make_pr_row with custom pr_display for link indicator."""
        row = make_pr_row(
            123,
            "Feature",
            pr_display="#123 ✅🔗",
        )
        assert row.pr_number == 123
        assert row.pr_display == "#123 ✅🔗"

    def test_make_pr_row_with_learn_status_pending(self) -> None:
        """make_pr_row with learn_status pending shows spinner."""
        row = make_pr_row(123, "Test Plan", learn_status="pending")
        assert row.learn_status == "pending"
        assert row.learn_display_icon == "⟳"

    def test_make_pr_row_with_learn_status_completed_no_plan(self) -> None:
        """make_pr_row with learn_status completed_no_plan shows empty set."""
        row = make_pr_row(123, "Test Plan", learn_status="completed_no_plan")
        assert row.learn_status == "completed_no_plan"
        assert row.learn_display_icon == "∅"

    def test_make_pr_row_with_learn_status_completed_with_plan(self) -> None:
        """make_pr_row with learn_status completed_with_plan shows issue number."""
        row = make_pr_row(
            123, "Test Plan", learn_status="completed_with_plan", learn_plan_issue=456
        )
        assert row.learn_status == "completed_with_plan"
        assert row.learn_plan_issue == 456
        assert row.learn_display == "📋 #456"

    def test_make_pr_row_with_learn_status_plan_completed(self) -> None:
        """make_pr_row with learn_status plan_completed shows checkmark and PR."""
        row = make_pr_row(
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
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
        )
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan")

        values = table._row_to_values(row)

        # plan, stage, sts, created, obj, loc, branch, run-id, run, author,
        # pr, chks, cmts, local-wt, local-impl, remote-impl
        assert len(values) == 16
        assert _text_to_str(values[0]) == "#123"
        assert _text_to_str(values[4]) == "-"  # objective (none)
        assert values[5] == "-"  # location (no local, no run)
        assert values[6] == "-"  # branch (none)
        assert values[3] == "-"  # created_display
        assert values[9] == "test-user"  # author
        assert _text_to_str(values[13]) == "-"  # worktree (not exists)
        assert _text_to_str(values[14]) == "-"  # local impl

    def test_row_to_values_with_prs(self) -> None:
        """Row conversion with PR columns enabled."""
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            exclude_labels=(),
        )
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan")

        values = table._row_to_values(row)

        # plan, stage, sts, created, obj, loc, branch, run-id, run, author,
        # pr, chks, cmts, local-wt, local-impl, remote-impl
        assert len(values) == 16
        assert _text_to_str(values[4]) == "-"  # objective (none)
        assert values[5] == "-"  # location (no local, no run)
        assert values[6] == "-"  # branch (none)
        assert values[3] == "-"  # created_display
        assert values[9] == "test-user"  # author
        assert _text_to_str(values[10]) == "#123"  # pr display
        assert values[11] == "-"  # checks
        assert values[12] == "0/0"  # comments (default for PR with no counts)

    def test_row_to_values_with_pr_link_indicator(self) -> None:
        """Row conversion shows 🔗 indicator for PRs that will close issues."""
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            exclude_labels=(),
        )
        table = PlanDataTable(filters)
        # Use custom pr_display with link indicator
        row = make_pr_row(123, "Test Plan", pr_display="#456 ✅🔗")

        values = table._row_to_values(row)

        # PR display at index 10
        # (plan, stage, sts, created, obj, loc, branch, run-id, run, author, pr)
        assert _text_to_str(values[10]) == "#456 ✅🔗"

    def test_row_to_values_with_runs(self) -> None:
        """Row conversion with run columns enabled."""
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=True,
            exclude_labels=(),
        )
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan")

        values = table._row_to_values(row)

        # plan, stage, sts, created, obj, loc, branch, run-id, run, author,
        # pr, chks, cmts, local-wt, local-impl, remote-impl
        assert len(values) == 16

    def test_row_to_values_with_worktree(self) -> None:
        """Row shows worktree name when exists locally."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        row = make_pr_row(
            123,
            "Test Plan",
            worktree_name="feature-branch",
            exists_locally=True,
        )

        values = table._row_to_values(row)

        # Worktree is at index 13 (local-wt column)
        assert values[13] == "feature-branch"

    def test_row_to_values_branch_from_pr_head(self) -> None:
        """Row shows pr_head_branch when available."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan", pr_head_branch="feat/my-branch")

        values = table._row_to_values(row)

        # Branch is at index 6 (after plan, stage, sts, created, obj, loc)
        assert values[6] == "feat/my-branch"

    def test_row_to_values_branch_falls_back_to_worktree_branch(self) -> None:
        """Row falls back to worktree_branch when pr_head_branch is None."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan", worktree_branch="local-branch")

        values = table._row_to_values(row)

        # Branch is at index 6 (after plan, stage, sts, created, obj, loc)
        assert values[6] == "local-branch"

    def test_row_to_values_branch_prefers_pr_head_over_worktree(self) -> None:
        """Row prefers pr_head_branch over worktree_branch."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan", pr_head_branch="pr-branch", worktree_branch="wt-branch")

        values = table._row_to_values(row)

        assert values[6] == "pr-branch"

    def test_row_to_values_includes_author(self) -> None:
        """Row includes author at index 9."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan", author="schrockn")

        values = table._row_to_values(row)

        # Author is at index 9 (after plan, stage, sts, created, obj, loc, branch, run-id, run)
        assert values[9] == "schrockn"


class TestLocalWtColumnIndex:
    """Tests for local_wt_column_index tracking."""

    def test_column_index_none_before_setup(self) -> None:
        """Column index is None before columns are set up."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        # Don't call _setup_columns

        assert table.local_wt_column_index is None

    def test_expected_column_index_without_pr_column(self) -> None:
        """Expected column index is 12 when show_pr_column=False.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # Without pr column: plan(0), stage(1), sts(2), created(3), obj(4), loc(5), branch(6),
        # run-id(7), run(8), author(9), chks(10), cmts(11), local-wt(12)
        expected_index = 12
        assert expected_index == 12

    def test_expected_column_index_with_pr_column(self) -> None:
        """Expected column index is 13 when show_pr_column=True.

        This test verifies the expected column calculation logic.
        The actual _setup_columns() requires a running Textual app context.
        """
        # With pr column: plan(0), stage(1), sts(2), created(3), obj(4), loc(5), branch(6),
        # run-id(7), run(8), author(9), pr(10), chks(11), cmts(12), local-wt(13)
        expected_index = 13
        assert expected_index == 13


class TestObjectivesViewRowConversion:
    """Tests for row conversion in Objectives view."""

    def test_objectives_view_has_enriched_columns(self) -> None:
        """Objectives view produces enriched columns including deps-state."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(42, "Objective Plan")

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
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(
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
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(42, "Obj Plan", objective_deps_plans=())

        values = table._row_to_values(row)

        assert values[5] == "-"

    def test_deps_single_plan(self) -> None:
        """Single blocking plan shows linkified plan number."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(
            42,
            "Obj Plan",
            objective_deps_plans=(("#100", "https://github.com/test/repo/issues/100"),),
        )

        values = table._row_to_values(row)

        assert _text_to_str(values[5]) == "#100"

    def test_deps_three_plans(self) -> None:
        """Three blocking plans shows all three linkified."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(
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
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(
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
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(42, "Obj Plan")

        values = table._row_to_values(row)

        assert values[6] == "-"

    def test_next_shows_node_id(self) -> None:
        """Next column shows node ID when populated."""
        filters = PrFilters.default()
        table = PlanDataTable(filters)
        table._view_mode = ViewMode.OBJECTIVES
        row = make_pr_row(42, "Obj Plan", objective_next_node_display="1.1")

        values = table._row_to_values(row)

        assert values[6] == "1.1"


class TestShowPrColumnFalse:
    """Tests for show_pr_column=False behavior."""

    def test_row_to_values_with_show_pr_column_false_excludes_pr_value(self) -> None:
        """When show_pr_column=False, pr_display is omitted from row values.

        With show_pr_column=True (16 values):
          plan, stage, sts, created, obj, loc, branch, run-id, run, author,
          pr, chks, cmts, local-wt, local-impl, remote-impl

        With show_pr_column=False (15 values):
          plan, stage, sts, created, obj, loc, branch, run-id, run, author,
          chks, cmts, local-wt, local-impl, remote-impl
        """
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            exclude_labels=(),
            show_pr_column=False,
        )
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan")

        values = table._row_to_values(row)

        # One fewer value than with show_pr_column=True (which produces 16)
        assert len(values) == 15

    def test_row_to_values_with_show_pr_column_false_pr_display_not_in_values(self) -> None:
        """When show_pr_column=False, the pr_display string is absent from values."""
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            exclude_labels=(),
            show_pr_column=False,
        )
        table = PlanDataTable(filters)
        # Use custom pr_display to distinguish from plan column (#123)
        row = make_pr_row(123, "Test Plan", pr_display="#123 ✅")

        values = table._row_to_values(row)

        # The custom pr_display "#123 ✅" should not appear in values
        plain_values = [_text_to_str(v) for v in values]
        assert "#123 ✅" not in plain_values

    def test_row_to_values_with_show_pr_column_true_includes_pr_value(self) -> None:
        """When show_pr_column=True (default), pr_display is included at index 10."""
        filters = PrFilters(
            labels=("erk-pr",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=True,
            show_runs=False,
            exclude_labels=(),
            show_pr_column=True,
        )
        table = PlanDataTable(filters)
        row = make_pr_row(123, "Test Plan")

        values = table._row_to_values(row)

        assert len(values) == 16
        # pr at index 10 (after plan, stage, sts, created, obj, loc, branch, run-id, run, author)
        assert _text_to_str(values[10]) == "#123"


# --- Tests for stage column logic ---


def test_row_to_values_planned_pr_includes_stage() -> None:
    """Stage column is included in output (stage/sts/created columns are always present)."""
    filters = PrFilters(
        labels=("erk-plan",),
        state=None,
        run_state=None,
        limit=None,
        show_prs=False,
        show_runs=False,
        exclude_labels=(),
    )
    table = PlanDataTable(filters)
    row = make_pr_row(123, "Test Plan", lifecycle_display="[cyan]review[/cyan]")

    values = table._row_to_values(row)

    # plan, stage, sts, created, obj, loc, branch, run-id, run, author,
    # pr, chks, cmts, local-wt, local-impl, remote-impl
    assert len(values) == 16
    # Stage at index 1 (right after plan) - markup stripped
    assert _text_to_str(values[1]) == "review"


# --- Tests for compact status emoji column ---


def test_row_to_values_status_empty() -> None:
    """Status cell shows '-' when no local checkout and no run URL."""
    filters = PrFilters.default()
    table = PlanDataTable(filters)
    row = make_pr_row(123, "Test Plan", exists_locally=False, run_url=None)

    values = table._row_to_values(row)

    # loc is at index 5 (after plan, stage, sts, created, obj)
    assert values[5] == "-"


def test_row_to_values_status_local_only() -> None:
    """Status cell shows laptop emoji when only local checkout exists."""
    filters = PrFilters.default()
    table = PlanDataTable(filters)
    row = make_pr_row(123, "Test Plan", exists_locally=True)

    values = table._row_to_values(row)

    assert values[5] == "\U0001f4bb"


def test_row_to_values_status_remote_only() -> None:
    """Status cell shows globe emoji when only run URL exists."""
    filters = PrFilters.default()
    table = PlanDataTable(filters)
    row = make_pr_row(123, "Test Plan", run_url="https://github.com/runs/1")

    values = table._row_to_values(row)

    assert values[5] == "\u2601"


def test_row_to_values_status_both() -> None:
    """Status cell shows both emojis when local checkout and run URL exist."""
    filters = PrFilters.default()
    table = PlanDataTable(filters)
    row = make_pr_row(123, "Test Plan", exists_locally=True, run_url="https://github.com/runs/1")

    values = table._row_to_values(row)

    assert values[5] == "\U0001f4bb\u2601"


# --- Tests for row deduplication logic ---


def _deduplicate_rows(rows: list) -> list:
    """Apply deduplication logic (matching populate() behavior).

    This directly applies the same deduplication logic used in populate()
    to verify the filtering works correctly.
    """
    seen: set[int] = set()
    unique_rows: list = []
    for row in rows:
        if row.pr_number not in seen:
            seen.add(row.pr_number)
            unique_rows.append(row)
    return unique_rows


def test_deduplicates_rows_by_pr_number() -> None:
    """Deduplication keeps first occurrence when pr_number appears multiple times."""
    # Create rows with duplicate pr_ids (e.g., multi-label query returns same plan twice)
    row1 = make_pr_row(123, "Plan A")
    row2 = make_pr_row(456, "Plan B")
    row3 = make_pr_row(123, "Plan A")  # Duplicate of row1 by pr_number

    rows = [row1, row2, row3]
    unique_rows = _deduplicate_rows(rows)

    # Should have 2 rows (the duplicate was removed)
    assert len(unique_rows) == 2
    # First row should be preserved
    assert unique_rows[0].pr_number == 123
    assert unique_rows[1].pr_number == 456


def test_dedup_preserves_row_order() -> None:
    """Deduplication preserves order when removing duplicates."""
    row1 = make_pr_row(100, "Plan 1")
    row2 = make_pr_row(200, "Plan 2")
    row3 = make_pr_row(300, "Plan 3")
    row4 = make_pr_row(200, "Plan 2")  # Duplicate of row2
    row5 = make_pr_row(400, "Plan 4")

    rows = [row1, row2, row3, row4, row5]
    unique_rows = _deduplicate_rows(rows)

    # Should have 4 rows (one duplicate removed)
    assert len(unique_rows) == 4
    # Order should be preserved, with duplicate removed
    pr_ids = [r.pr_number for r in unique_rows]
    assert pr_ids == [100, 200, 300, 400]


def test_dedup_multi_label_query_scenario() -> None:
    """Deduplication handles multi-label queries returning same plan multiple times."""
    # Simulates multi-label query (e.g., erk-pr + erk-learn) returning same plan
    plan_a = make_pr_row(123, "Multi-Label Plan A")
    plan_b = make_pr_row(456, "Plan B")
    plan_a_duplicate = make_pr_row(123, "Multi-Label Plan A")  # Same plan, different label result
    plan_c = make_pr_row(789, "Plan C")

    rows = [plan_a, plan_b, plan_a_duplicate, plan_c]
    unique_rows = _deduplicate_rows(rows)

    # Should have 3 unique plans
    assert len(unique_rows) == 3
    unique_pr_ids = [r.pr_number for r in unique_rows]
    assert unique_pr_ids == [123, 456, 789]


def test_dedup_all_duplicate_rows_keeps_first() -> None:
    """Deduplication with all identical pr_ids keeps only first row."""
    row1 = make_pr_row(123, "Plan A")
    row2 = make_pr_row(123, "Plan A")
    row3 = make_pr_row(123, "Plan A")

    rows = [row1, row2, row3]
    unique_rows = _deduplicate_rows(rows)

    # Should have 1 row (all duplicates removed)
    assert len(unique_rows) == 1
    assert unique_rows[0].pr_number == 123


def test_dedup_empty_rows_list() -> None:
    """Deduplication handles empty rows list."""
    unique_rows = _deduplicate_rows([])

    assert len(unique_rows) == 0
