"""Tests for FetchTimings dataclass."""

import pytest

from erk.tui.data.types import FetchTimings


class TestFetchTimings:
    """Tests for FetchTimings dataclass."""

    def test_frozen(self) -> None:
        """FetchTimings instances are immutable."""
        timings = FetchTimings(
            rest_issues_ms=100,
            graphql_enrich_ms=200,
            plan_parsing_ms=50,
            workflow_runs_ms=300,
            worktree_mapping_ms=10,
            row_building_ms=5,
            total_ms=665,
        )
        with pytest.raises(AttributeError):
            timings.total_ms = 0  # type: ignore[misc]

    def test_summary_all_phases_above_threshold(self) -> None:
        """Summary includes all phases when above their thresholds."""
        timings = FetchTimings(
            rest_issues_ms=1200,
            graphql_enrich_ms=2300,
            plan_parsing_ms=160,
            workflow_runs_ms=800,
            worktree_mapping_ms=200,
            row_building_ms=300,
            total_ms=4960,
        )
        result = timings.summary()
        assert result == "rest:1.2 gql:2.3 parse:0.2 wf:0.8 wt:0.2 rows:0.3 = 5.0s"

    def test_summary_omits_zero_values(self) -> None:
        """Summary omits phases with zero milliseconds (threshold > 0)."""
        timings = FetchTimings(
            rest_issues_ms=1000,
            graphql_enrich_ms=0,
            plan_parsing_ms=0,
            workflow_runs_ms=0,
            worktree_mapping_ms=0,
            row_building_ms=0,
            total_ms=1000,
        )
        result = timings.summary()
        assert result == "rest:1.0 = 1.0s"

    def test_summary_omits_below_threshold(self) -> None:
        """Summary omits parse/wt/rows when below 100ms threshold."""
        timings = FetchTimings(
            rest_issues_ms=500,
            graphql_enrich_ms=300,
            plan_parsing_ms=50,
            workflow_runs_ms=100,
            worktree_mapping_ms=99,
            row_building_ms=10,
            total_ms=1059,
        )
        result = timings.summary()
        assert "parse:" not in result
        assert "wt:" not in result
        assert "rows:" not in result
        assert "rest:0.5" in result
        assert "gql:0.3" in result
        assert "wf:0.1" in result

    def test_summary_total_always_shown(self) -> None:
        """Total time is always included in summary."""
        timings = FetchTimings(
            rest_issues_ms=0,
            graphql_enrich_ms=0,
            plan_parsing_ms=0,
            workflow_runs_ms=0,
            worktree_mapping_ms=0,
            row_building_ms=0,
            total_ms=500,
        )
        result = timings.summary()
        assert result == " = 0.5s"
