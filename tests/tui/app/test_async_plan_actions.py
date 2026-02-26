"""Tests for ErkDashApp - async plan actions."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestDispatchToQueueAsync:
    """Tests for _dispatch_to_queue_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_dispatch_to_queue_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_dispatch_to_queue_async should run correct subprocess command."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_args: list[str] = []

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_args.extend(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._dispatch_to_queue_async(123)
            await pilot.pause(0.3)

            assert captured_args == ["erk", "pr", "dispatch", "123"]

    @pytest.mark.asyncio
    async def test_dispatch_to_queue_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_dispatch_to_queue_async should trigger refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._dispatch_to_queue_async(123)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_dispatch_to_queue_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_dispatch_to_queue_async should NOT refresh on failure."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, args, stderr="submit failed")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._dispatch_to_queue_async(123)
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before


class TestCloseObjectiveAsync:
    """Tests for _close_objective_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_close_objective_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_close_objective_async should run correct subprocess command."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_args: list[str] = []

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_args.extend(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._close_objective_async(123)
            await pilot.pause(0.3)

            assert captured_args == ["erk", "objective", "close", "123", "--force"]

    @pytest.mark.asyncio
    async def test_close_objective_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_close_objective_async should trigger refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._close_objective_async(123)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before


class TestCheckObjectiveAsync:
    """Tests for _check_objective_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_check_objective_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_check_objective_async should run correct subprocess command."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_args: list[str] = []

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_args.extend(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._check_objective_async(123)
            await pilot.pause(0.3)

            assert captured_args == ["erk", "objective", "check", "123"]

    @pytest.mark.asyncio
    async def test_check_objective_no_refresh(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_check_objective_async should NOT trigger refresh (read-only)."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._check_objective_async(123)
            await pilot.pause(0.3)

            # check_objective is read-only, no refresh
            assert provider.fetch_count == count_before


class TestOneShotPlanAsync:
    """Tests for _one_shot_plan_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_one_shot_plan_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_one_shot_plan_async should run correct subprocess command."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_args: list[str] = []

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_args.extend(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._one_shot_plan_async(123)
            await pilot.pause(0.3)

            assert captured_args == ["erk", "objective", "plan", "123", "--one-shot"]

    @pytest.mark.asyncio
    async def test_one_shot_plan_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_one_shot_plan_async should trigger refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._one_shot_plan_async(123)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before
