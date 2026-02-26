"""Tests for ErkDashApp - status bar."""

from erk.tui.app import (
    ErkDashApp,
    _build_github_url,
)
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode, get_view_config
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider


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
            plan_parsing_ms=200,
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


class TestBuildGithubUrl:
    """Tests for _build_github_url helper function."""

    def test_build_github_url_for_pull_request(self) -> None:
        """_build_github_url constructs PR URL from issue URL."""
        issue_url = "https://github.com/owner/repo/issues/123"
        result = _build_github_url(issue_url, "pull", 456)
        assert result == "https://github.com/owner/repo/pull/456"

    def test_build_github_url_for_issue(self) -> None:
        """_build_github_url constructs issue URL from issue URL."""
        issue_url = "https://github.com/owner/repo/issues/123"
        result = _build_github_url(issue_url, "issues", 789)
        assert result == "https://github.com/owner/repo/issues/789"


def test_display_name_plans_view() -> None:
    """PLANS view returns 'Planned PRs'."""
    provider = FakePlanDataProvider()
    filters = PlanFilters.default()
    app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)
    assert app._display_name_for_view(ViewMode.PLANS) == "Planned PRs"


def test_display_name_non_plans_view() -> None:
    """Non-PLANS mode returns default display name."""
    provider = FakePlanDataProvider()
    filters = PlanFilters.default()
    app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)
    expected_learn = get_view_config(ViewMode.LEARN).display_name
    assert app._display_name_for_view(ViewMode.LEARN) == expected_learn
    expected_obj = get_view_config(ViewMode.OBJECTIVES).display_name
    assert app._display_name_for_view(ViewMode.OBJECTIVES) == expected_obj
