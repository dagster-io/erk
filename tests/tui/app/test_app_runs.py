"""Integration tests for Runs tab in ErkDashApp.

Tests _load_run_data(), on_run_clicked(), and on_run_pr_clicked() event handlers.
"""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PrFilters
from erk.tui.views.types import ViewMode
from erk.tui.widgets.run_table import RunDataTable
from tests.fakes.gateway.browser import FakeBrowserLauncher
from tests.fakes.gateway.pr_service import FakePrService
from tests.fakes.tests.tui_plan_data_provider import FakePrDataProvider, make_pr_row, make_run_row


class TestLoadRunData:
    """Tests for _load_run_data() triggered by switching to Runs view."""

    @pytest.mark.asyncio
    async def test_switching_to_runs_loads_run_data(self) -> None:
        """Pressing '4' switches to Runs view and populates run table."""
        run_rows = [
            make_run_row("1001", workflow_name="plan-implement"),
            make_run_row("1002", workflow_name="pr-address"),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            assert app._view_mode == ViewMode.RUNS
            assert len(app._run_rows) == 2
            assert app._run_rows[0].run_id == "1001"
            assert app._run_rows[1].run_id == "1002"

    @pytest.mark.asyncio
    async def test_runs_tab_shows_run_table_hides_plan_table(self) -> None:
        """Runs view shows RunDataTable and hides PlanDataTable."""
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs([make_run_row("1001")])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            assert run_table.display is True
            assert app._table is not None
            assert app._table.display is False

    @pytest.mark.asyncio
    async def test_runs_empty_shows_empty_table(self) -> None:
        """Runs view with no data shows empty run table."""
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            assert app._view_mode == ViewMode.RUNS
            assert len(app._run_rows) == 0

    @pytest.mark.asyncio
    async def test_run_data_cached_on_tab_switch(self) -> None:
        """Switching away from Runs and back uses cached data."""
        run_rows = [make_run_row("1001")]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to Runs
            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()
            assert len(app._run_rows) == 1

            # Switch back to Plans
            await pilot.press("1")
            await pilot.pause()

            # Switch to Runs again - should use cache
            initial_fetch_count = provider.fetch_count
            await pilot.press("4")
            await pilot.pause()

            # Cache was used so no new fetch needed
            assert len(app._run_rows) == 1
            assert provider.fetch_count == initial_fetch_count

    @pytest.mark.asyncio
    async def test_status_bar_shows_run_count(self) -> None:
        """Status bar shows run count when in Runs view."""
        run_rows = [make_run_row("1001"), make_run_row("1002"), make_run_row("1003")]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            assert app._status_bar is not None
            # Status bar should have been updated with run count
            assert app._status_bar._plan_count == 3


class TestOnRunClicked:
    """Tests for on_run_clicked() event handler."""

    @pytest.mark.asyncio
    async def test_run_click_opens_run_url(self) -> None:
        """Clicking a run-id cell opens the run URL in browser."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [
            make_run_row(
                "1001",
                run_url="https://github.com/test/repo/actions/runs/1001",
            ),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to Runs view
            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            # Simulate RunClicked message
            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.RunClicked(0))
            await pilot.pause()

            assert len(browser.launch_calls) == 1
            assert browser.launch_calls[0] == "https://github.com/test/repo/actions/runs/1001"

    @pytest.mark.asyncio
    async def test_run_click_out_of_range_is_noop(self) -> None:
        """Clicking out-of-range row index does nothing."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [make_run_row("1001")]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            # Post message with out-of-range index
            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.RunClicked(99))
            await pilot.pause()

            assert len(browser.launch_calls) == 0

    @pytest.mark.asyncio
    async def test_run_click_no_url_is_noop(self) -> None:
        """Clicking a run without a URL does nothing."""
        from erk.tui.data.types import RunRowData

        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_no_url = RunRowData(
            run_id="1001",
            run_url=None,
            status="completed",
            conclusion="success",
            status_display="Success",
            workflow_name="plan-implement",
            pr_number=None,
            pr_url=None,
            pr_display="-",
            pr_title=None,
            pr_state=None,
            title_display="-",
            branch_display="main",
            submitted_display="03-09 14:30",
            created_at=None,
            checks_display="-",
            run_id_display="1001",
            branch="-",
        )
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs([run_no_url])
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.RunClicked(0))
            await pilot.pause()

            assert len(browser.launch_calls) == 0


class TestOnRunPrClicked:
    """Tests for on_run_pr_clicked() event handler."""

    @pytest.mark.asyncio
    async def test_pr_click_opens_pr_url(self) -> None:
        """Clicking a PR cell in runs table opens PR URL in browser."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [
            make_run_row(
                "1001",
                pr_number=42,
                pr_url="https://github.com/test/repo/pull/42",
                pr_display="#42",
            ),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.PrClicked(0))
            await pilot.pause()

            assert len(browser.launch_calls) == 1
            assert browser.launch_calls[0] == "https://github.com/test/repo/pull/42"

    @pytest.mark.asyncio
    async def test_pr_click_out_of_range_is_noop(self) -> None:
        """Clicking PR cell with out-of-range index does nothing."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [make_run_row("1001", pr_number=42, pr_url="https://example.com")]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.PrClicked(99))
            await pilot.pause()

            assert len(browser.launch_calls) == 0

    @pytest.mark.asyncio
    async def test_pr_click_no_url_is_noop(self) -> None:
        """Clicking PR cell when run has no PR URL does nothing."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [make_run_row("1001")]  # No PR
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.PrClicked(0))
            await pilot.pause()

            assert len(browser.launch_calls) == 0

    @pytest.mark.asyncio
    async def test_status_bar_message_on_run_click(self) -> None:
        """Status bar shows message after clicking a run."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [
            make_run_row(
                "1001",
                run_url="https://github.com/test/repo/actions/runs/1001",
            ),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.RunClicked(0))
            await pilot.pause()

            assert app._status_bar is not None
            # Status bar message should mention the run ID
            assert "1001" in (app._status_bar._message or "")

    @pytest.mark.asyncio
    async def test_status_bar_message_on_pr_click(self) -> None:
        """Status bar shows message after clicking a PR in runs table."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [
            make_run_row(
                "1001",
                pr_number=42,
                pr_url="https://github.com/test/repo/pull/42",
            ),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            run_table.post_message(RunDataTable.PrClicked(0))
            await pilot.pause()

            assert app._status_bar is not None
            assert "42" in (app._status_bar._message or "")


class TestRunPrFilter:
    """Tests for 'f' key PR state filter on Runs tab."""

    @pytest.mark.asyncio
    async def test_f_key_toggles_pr_filter(self) -> None:
        """Pressing 'f' toggles the run PR filter state."""
        run_rows = [make_run_row("1001")]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()
            assert app._run_pr_filter_active is False

            await pilot.press("f")
            await pilot.pause()
            assert app._run_pr_filter_active is True

            await pilot.press("f")
            await pilot.pause()
            assert app._run_pr_filter_active is False

    @pytest.mark.asyncio
    async def test_filter_excludes_merged_and_closed_runs(self) -> None:
        """PR filter hides runs linked to MERGED and CLOSED PRs."""
        run_rows = [
            make_run_row("1001", pr_number=10, pr_state="OPEN"),
            make_run_row("1002", pr_number=20, pr_state="MERGED"),
            make_run_row("1003", pr_number=30, pr_state="CLOSED"),
            make_run_row("1004"),  # No PR (pr_state=None)
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()
            assert len(app._run_rows) == 4

            await pilot.press("f")
            await pilot.pause()
            assert len(app._run_rows) == 2
            run_ids = {r.run_id for r in app._run_rows}
            assert run_ids == {"1001", "1004"}

    @pytest.mark.asyncio
    async def test_filter_keeps_open_and_no_pr_runs(self) -> None:
        """PR filter keeps runs with OPEN PRs and runs without any PR."""
        run_rows = [
            make_run_row("1001", pr_number=10, pr_state="OPEN"),
            make_run_row("1002"),  # No PR
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("f")
            await pilot.pause()
            assert len(app._run_rows) == 2

    @pytest.mark.asyncio
    async def test_escape_clears_pr_filter(self) -> None:
        """Pressing escape when PR filter is active clears the filter."""
        run_rows = [
            make_run_row("1001", pr_number=10, pr_state="OPEN"),
            make_run_row("1002", pr_number=20, pr_state="MERGED"),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("f")
            await pilot.pause()
            assert app._run_pr_filter_active is True
            assert len(app._run_rows) == 1

            await pilot.press("escape")
            await pilot.pause()
            assert app._run_pr_filter_active is False
            assert len(app._run_rows) == 2

    @pytest.mark.asyncio
    async def test_f_key_noop_on_non_runs_tab(self) -> None:
        """Pressing 'f' on non-Runs tabs does nothing."""
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

            await pilot.press("f")
            await pilot.pause()
            assert app._run_pr_filter_active is False


class TestRunsNavigation:
    """Tests for j/k navigation and disabled actions on Runs tab."""

    @pytest.mark.asyncio
    async def test_j_k_navigate_run_table(self) -> None:
        """j/k keys move cursor in run table when on Runs tab."""
        run_rows = [
            make_run_row("1001"),
            make_run_row("1002"),
            make_run_row("1003"),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            run_table = app.query_one(RunDataTable)
            assert run_table.cursor_row == 0

            await pilot.press("j")
            await pilot.pause()
            assert run_table.cursor_row == 1

            await pilot.press("k")
            await pilot.pause()
            assert run_table.cursor_row == 0

    @pytest.mark.asyncio
    async def test_launch_disabled_on_runs_tab(self) -> None:
        """Pressing 'l' on Runs tab does not open launch screen."""
        run_rows = [make_run_row("1001")]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("l")
            await pilot.pause()

            # Should still be on main screen, no LaunchScreen pushed
            assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_p_opens_pr_on_runs_tab(self) -> None:
        """Pressing 'p' on Runs tab opens the selected run's PR."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [
            make_run_row(
                "1001",
                pr_number=42,
                pr_url="https://github.com/test/repo/pull/42",
                pr_display="#42",
            ),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("p")
            await pilot.pause()

            assert len(browser.launch_calls) == 1
            assert browser.launch_calls[0] == "https://github.com/test/repo/pull/42"

    @pytest.mark.asyncio
    async def test_p_no_pr_on_runs_tab_is_noop(self) -> None:
        """Pressing 'p' on Runs tab with no PR shows status message."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [make_run_row("1001")]  # No PR
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("p")
            await pilot.pause()

            assert len(browser.launch_calls) == 0

    @pytest.mark.asyncio
    async def test_n_opens_run_on_runs_tab(self) -> None:
        """Pressing 'n' on Runs tab opens the selected run URL."""
        browser = FakeBrowserLauncher()
        service = FakePrService(browser=browser)
        run_rows = [
            make_run_row(
                "1001",
                run_url="https://github.com/test/repo/actions/runs/1001",
            ),
        ]
        provider = FakePrDataProvider(plans=[make_pr_row(1, "Plan A")])
        provider.set_runs(run_rows)
        filters = PrFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("n")
            await pilot.pause()

            assert len(browser.launch_calls) == 1
            assert browser.launch_calls[0] == "https://github.com/test/repo/actions/runs/1001"
