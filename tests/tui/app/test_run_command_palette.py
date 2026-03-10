"""Tests for run command palette functionality."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from tests.fakes.gateway.browser import FakeBrowserLauncher
from tests.fakes.gateway.clipboard import FakeClipboard
from tests.fakes.gateway.plan_data_provider import FakePlanDataProvider
from tests.fakes.gateway.pr_service import FakePrService
from tests.fakes.tests.tui_plan_data_provider import make_run_row


class TestRunPaletteCopyCommands:
    """Tests for copy commands in the run command palette."""

    @pytest.mark.asyncio
    async def test_copy_cancel_cmd(self) -> None:
        """Copy cancel command includes 'erk workflow run cancel'."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider()
        provider.set_runs([make_run_row("12345", status="in_progress", conclusion=None)])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Switch to Runs tab
            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("copy_cancel_cmd")

            assert clipboard.last_copied == "erk workflow run cancel 12345"

    @pytest.mark.asyncio
    async def test_copy_retry_cmd(self) -> None:
        """Copy retry command includes 'erk workflow run retry'."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider()
        provider.set_runs([make_run_row("67890", status="completed", conclusion="failure")])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("copy_retry_cmd")

            assert clipboard.last_copied == "erk workflow run retry 67890"


class TestRunPaletteOpenCommands:
    """Tests for open commands in the run command palette."""

    @pytest.mark.asyncio
    async def test_open_run_url(self) -> None:
        """Open run URL launches browser with run URL."""
        browser = FakeBrowserLauncher()
        provider = FakePlanDataProvider()
        provider.set_runs([
            make_run_row(
                "12345",
                run_url="https://github.com/test/repo/actions/runs/12345",
            )
        ])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(browser=browser),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("open_run_url")

            assert browser.last_launched == "https://github.com/test/repo/actions/runs/12345"

    @pytest.mark.asyncio
    async def test_open_run_pr(self) -> None:
        """Open run PR launches browser with PR URL."""
        browser = FakeBrowserLauncher()
        provider = FakePlanDataProvider()
        provider.set_runs([
            make_run_row(
                "12345",
                pr_url="https://github.com/test/repo/pull/456",
            )
        ])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(browser=browser),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("open_run_pr")

            assert browser.last_launched == "https://github.com/test/repo/pull/456"


class TestRunPaletteActionCommands:
    """Tests for action commands (cancel/retry) in the run command palette."""

    @pytest.mark.asyncio
    async def test_cancel_run_dispatches_to_worker(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Cancel run dispatches to _cancel_run_async with correct args."""
        provider = FakePlanDataProvider()
        provider.set_runs([make_run_row("12345", status="in_progress", conclusion=None)])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        captured: tuple[str, str] | None = None

        def mock_cancel(self_app: ErkDashApp, op_id: str, run_id: str) -> None:
            nonlocal captured
            captured = (op_id, run_id)

        monkeypatch.setattr(ErkDashApp, "_cancel_run_async", mock_cancel)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("cancel_run")
            await pilot.pause()

            assert captured is not None
            assert captured[0] == "cancel-run-12345"
            assert captured[1] == "12345"

    @pytest.mark.asyncio
    async def test_retry_run_dispatches_to_worker(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Retry run dispatches to _retry_run_async with failed_only=False."""
        provider = FakePlanDataProvider()
        provider.set_runs([make_run_row("12345", status="completed", conclusion="failure")])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        captured: tuple[str, str, bool] | None = None

        def mock_retry(
            self_app: ErkDashApp, op_id: str, run_id: str, *, failed_only: bool
        ) -> None:
            nonlocal captured
            captured = (op_id, run_id, failed_only)

        monkeypatch.setattr(ErkDashApp, "_retry_run_async", mock_retry)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("retry_run")
            await pilot.pause()

            assert captured is not None
            assert captured[0] == "retry-run-12345"
            assert captured[1] == "12345"
            assert captured[2] is False

    @pytest.mark.asyncio
    async def test_retry_failed_run_dispatches_to_worker(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Retry failed run dispatches to _retry_run_async with failed_only=True."""
        provider = FakePlanDataProvider()
        provider.set_runs([make_run_row("12345", status="completed", conclusion="failure")])
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        captured: tuple[str, str, bool] | None = None

        def mock_retry(
            self_app: ErkDashApp, op_id: str, run_id: str, *, failed_only: bool
        ) -> None:
            nonlocal captured
            captured = (op_id, run_id, failed_only)

        monkeypatch.setattr(ErkDashApp, "_retry_run_async", mock_retry)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("retry_failed_run")
            await pilot.pause()

            assert captured is not None
            assert captured[0] == "retry-failed-run-12345"
            assert captured[1] == "12345"
            assert captured[2] is True


class TestRunPaletteNoSelection:
    """Tests for run palette commands with no row selected."""

    @pytest.mark.asyncio
    async def test_no_selection_does_nothing(self) -> None:
        """Run palette command with no runs does nothing."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider()
        # No runs set — empty list
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=PlanFilters.default(),
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("4")
            await pilot.pause()
            await pilot.pause()

            app.execute_run_palette_command("copy_cancel_cmd")

            assert clipboard.last_copied is None
