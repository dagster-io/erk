"""Tests for async operations (address remote, fix conflicts, land PR, dispatch, etc.)."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class _FakePopen:
    """Fake subprocess.Popen that yields configurable output lines."""

    def __init__(self, *, lines: tuple[str, ...] = (), return_code: int = 0) -> None:
        self._return_code = return_code
        self.stdout: list[str] = [line + "\n" for line in lines]

    def wait(self) -> int:
        return self._return_code


class TestAddressRemoteAsync:
    """Tests for _address_remote_async subprocess behavior.

    Verifies that address_remote triggers a data refresh on success.
    """

    @pytest.mark.asyncio
    async def test_address_remote_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_address_remote_async should trigger action_refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("Updated dispatch metadata",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._address_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_address_remote_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_address_remote_async should NOT refresh on subprocess failure."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("dispatch failed",), return_code=1)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._address_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before


class TestFixConflictsRemoteAsync:
    """Tests for _fix_conflicts_remote_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_fix_conflicts_remote_passes_correct_args(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_fix_conflicts_remote_async should pass correct args to subprocess."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_args: list[str] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            if args:
                captured_args.extend(args[0])  # type: ignore[arg-type]
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._fix_conflicts_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert captured_args == [
                "erk",
                "launch",
                "pr-fix-conflicts",
                "--pr",
                "456",
            ]

    @pytest.mark.asyncio
    async def test_fix_conflicts_remote_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_fix_conflicts_remote_async should trigger refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("Updated dispatch metadata",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._fix_conflicts_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_fix_conflicts_remote_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_fix_conflicts_remote_async should NOT refresh on failure."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("dispatch failed",), return_code=1)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._fix_conflicts_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before


class TestLandPrAsync:
    """Tests for _land_pr_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_land_pr_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should run land-execute with correct args."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            if args:
                captured_calls.append(list(args[0]))  # type: ignore[arg-type]
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(
                "test-op",
                456,
                "test-branch",
                None,
            )
            await pilot.pause(0.3)

            assert len(captured_calls) == 1
            assert captured_calls[0] == [
                "erk",
                "exec",
                "land-execute",
                "--pr-number=456",
                "--branch=test-branch",
                "-f",
            ]

    @pytest.mark.asyncio
    async def test_land_pr_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should trigger refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._land_pr_async(
                "test-op",
                456,
                "test-branch",
                None,
            )
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_land_pr_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should NOT refresh on failure."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("land failed",), return_code=1)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._land_pr_async(
                "test-op",
                456,
                "test-branch",
                None,
            )
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before

    @pytest.mark.asyncio
    async def test_land_pr_chains_objective_update(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should chain objective update when objective_issue is set."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    pr_number=456,
                    pr_head_branch="test-branch",
                    objective_issue=789,
                )
            ],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            if args:
                captured_calls.append(list(args[0]))  # type: ignore[arg-type]
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(
                "test-op",
                456,
                "test-branch",
                789,
            )
            await pilot.pause(0.3)

            assert len(captured_calls) == 2
            assert captured_calls[1] == [
                "erk",
                "exec",
                "objective-update-after-land",
                "--objective=789",
                "--pr=456",
                "--branch=test-branch",
            ]

    @pytest.mark.asyncio
    async def test_land_pr_skips_objective_update_without_objective(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should NOT chain objective update without objective."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            if args:
                captured_calls.append(list(args[0]))  # type: ignore[arg-type]
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(
                "test-op",
                456,
                "test-branch",
                None,
            )
            await pilot.pause(0.3)

            # Only the land command, no objective update
            assert len(captured_calls) == 1


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

        captured_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            captured_calls.append(list(args[0]))
            return _FakePopen(lines=("Dispatched",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._dispatch_to_queue_async("test-op", 123)
            await pilot.pause(0.3)

            assert captured_calls == [["erk", "pr", "dispatch", "123"]]

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

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("Dispatched",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._dispatch_to_queue_async("test-op", 123)
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

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("submit failed",), return_code=1)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._dispatch_to_queue_async("test-op", 123)
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

        captured_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            captured_calls.append(list(args[0]))
            return _FakePopen(lines=("Closed",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._close_objective_async("test-op", 123)
            await pilot.pause(0.3)

            assert captured_calls == [["erk", "objective", "close", "123", "--force"]]

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

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("Closed",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._close_objective_async("test-op", 123)
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

        captured_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            captured_calls.append(list(args[0]))
            return _FakePopen(lines=("Checked",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._check_objective_async("test-op", 123)
            await pilot.pause(0.3)

            assert captured_calls == [["erk", "objective", "check", "123"]]

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

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("Checked",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._check_objective_async("test-op", 123)
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

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            if args:
                captured_args.extend(args[0])  # type: ignore[arg-type]
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._one_shot_plan_async("test-op", 123)
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

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._one_shot_plan_async("test-op", 123)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before
