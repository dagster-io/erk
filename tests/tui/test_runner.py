"""Tests for TuiRunner implementations."""

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.runner import FakeTuiRunner
from tests.fakes.plan_data_provider import FakePlanDataProvider


def test_apps_run_starts_empty() -> None:
    """FakeTuiRunner starts with empty app list."""
    runner = FakeTuiRunner()
    assert runner.apps_run == []


def test_run_captures_app() -> None:
    """run() captures app in apps_run list."""
    runner = FakeTuiRunner()
    provider = FakePlanDataProvider()
    filters = PlanFilters.default()
    app = ErkDashApp(provider, filters, refresh_interval=0)

    runner.run(app)

    assert len(runner.apps_run) == 1
    assert runner.apps_run[0] is app


def test_run_captures_multiple_apps() -> None:
    """run() captures multiple apps in order."""
    runner = FakeTuiRunner()
    provider = FakePlanDataProvider()
    filters = PlanFilters.default()
    app1 = ErkDashApp(provider, filters, refresh_interval=0)
    app2 = ErkDashApp(provider, filters, refresh_interval=0)

    runner.run(app1)
    runner.run(app2)

    assert len(runner.apps_run) == 2
    assert runner.apps_run[0] is app1
    assert runner.apps_run[1] is app2


def test_run_does_not_start_event_loop() -> None:
    """run() does not start the Textual event loop.

    This test verifies that FakeTuiRunner.run() returns immediately
    without blocking (which would happen if it called app.run()).
    If the app's run() were called, this test would hang.
    """
    runner = FakeTuiRunner()
    provider = FakePlanDataProvider()
    filters = PlanFilters.default()
    app = ErkDashApp(provider, filters, refresh_interval=0)

    # This should return immediately - if it hangs, the test fails
    runner.run(app)

    # Verify app was captured but not actually run
    assert len(runner.apps_run) == 1
