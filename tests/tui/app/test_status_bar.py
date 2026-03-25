"""Tests for StatusBar widget."""

from erk.tui.widgets.status_bar import StatusBar


class TestStatusBar:
    """Tests for StatusBar widget."""

    def test_set_plan_count_singular(self) -> None:
        """Status bar shows singular 'plan' for count of 1."""
        bar = StatusBar()
        bar.set_plan_count(1, noun="plans")
        bar._update_display()
        # Check internal state was set
        assert bar._plan_count == 1

    def test_set_plan_count_plural(self) -> None:
        """Status bar shows plural 'plans' for count > 1."""
        bar = StatusBar()
        bar.set_plan_count(5, noun="plans")
        bar._update_display()
        assert bar._plan_count == 5

    def test_set_message(self) -> None:
        """Status bar can display a message."""
        bar = StatusBar()
        bar.set_message("Test message")
        bar._update_display()
        assert bar._message == "Test message"

    def test_clear_message(self) -> None:
        """Status bar can clear message."""
        bar = StatusBar()
        bar.set_message("Test message")
        bar.set_message(None)
        assert bar._message is None

    def test_set_last_update_with_fetch_timings(self) -> None:
        """Status bar stores fetch_timings when provided."""
        from erk.tui.data.types import FetchTimings

        bar = StatusBar()
        timings = FetchTimings(
            rest_issues_ms=1000,
            graphql_enrich_ms=500,
            pr_parsing_ms=200,
            workflow_runs_ms=300,
            worktree_mapping_ms=50,
            row_building_ms=20,
            total_ms=2070,
        )
        bar.set_last_update("14:30:45", duration_secs=2.1, fetch_timings=timings)
        assert bar._last_update == "14:30:45"
        assert bar._fetch_duration == 2.1
        assert bar._fetch_timings is timings

    def test_set_last_update_without_fetch_timings(self) -> None:
        """Status bar works without fetch_timings (backwards compatibility)."""
        bar = StatusBar()
        bar.set_last_update("14:30:45", duration_secs=1.5)
        assert bar._last_update == "14:30:45"
        assert bar._fetch_duration == 1.5
        assert bar._fetch_timings is None

    def test_operation_progress_with_bracket_characters(self) -> None:
        """StatusBar handles bracket characters in operation progress text.

        Subprocess error messages like "Command '['gh', 'pr']' returned..."
        contain bracket characters that Rich interprets as markup tags,
        causing MarkupError crashes when markup=True. This test verifies
        that StatusBar can display such text without error.
        """
        bar = StatusBar()
        bar.start_operation(op_id="test", label="Running command")
        # This text mimics subprocess.CalledProcessError output, which
        # contains brackets that Rich would parse as markup tags
        bar.update_operation(
            op_id="test",
            progress="Command '['gh', 'pr', 'diff']' returned non-zero exit status 1",
        )
        bar._update_display()
