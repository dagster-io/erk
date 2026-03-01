"""Tests for async operations (address remote, fix conflicts, land PR, dispatch, etc.)."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp, _extract_learn_plan_number, _OperationResult
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


class TestRebaseRemoteAsync:
    """Tests for _rebase_remote_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_rebase_remote_passes_correct_args(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_rebase_remote_async should pass correct args to subprocess."""
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

            app._rebase_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert captured_args == [
                "erk",
                "launch",
                "pr-fix-conflicts",
                "--pr",
                "456",
            ]

    @pytest.mark.asyncio
    async def test_rebase_remote_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_rebase_remote_async should trigger refresh after success."""
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

            app._rebase_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_rebase_remote_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_rebase_remote_async should NOT refresh on failure."""
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

            app._rebase_remote_async("test-op", 456)
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
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=None,
                plan_id=None,
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
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=None,
                plan_id=None,
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
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=None,
                plan_id=None,
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
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=789,
                plan_id=None,
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
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=None,
                plan_id=None,
            )
            await pilot.pause(0.3)

            # Only the land command, no objective update
            assert len(captured_calls) == 1

    @pytest.mark.asyncio
    async def test_land_pr_includes_plan_number_flag(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should include --plan-number when plan_id is set."""
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
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=None,
                plan_id=42,
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
                "--plan-number=42",
            ]

    @pytest.mark.asyncio
    async def test_land_pr_shows_learn_plan_toast(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async should show toast when learn plan is created."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(
                lines=("Landing PR...", "Created learn plan #999", "Done"),
                return_code=0,
            )

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        notifications: list[str] = []
        original_notify = app.notify

        def tracking_notify(message: str, **kwargs: object) -> None:
            notifications.append(str(message))
            original_notify(message, **kwargs)  # type: ignore[arg-type]

        app.notify = tracking_notify  # type: ignore[assignment]

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(
                op_id="test-op",
                pr_number=456,
                branch="test-branch",
                objective_issue=None,
                plan_id=None,
            )
            await pilot.pause(0.3)

            assert any("learn plan #999" in n.lower() for n in notifications)


class TestExtractLearnPlanNumber:
    """Tests for _extract_learn_plan_number helper."""

    def test_extracts_number_from_output(self) -> None:
        """Should extract learn plan number when present in output."""
        result = _OperationResult(
            success=True,
            output_lines=("Some output", "Created learn plan #1234", "Done"),
            return_code=0,
        )
        assert _extract_learn_plan_number(result) == 1234

    def test_returns_none_when_not_present(self) -> None:
        """Should return None when no learn plan line in output."""
        result = _OperationResult(
            success=True,
            output_lines=("Some output", "Done"),
            return_code=0,
        )
        assert _extract_learn_plan_number(result) is None

    def test_extracts_from_middle_of_line(self) -> None:
        """Should extract number even when text surrounds the pattern."""
        result = _OperationResult(
            success=True,
            output_lines=("Info: Created learn plan #5678 successfully",),
            return_code=0,
        )
        assert _extract_learn_plan_number(result) == 5678


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


class TestOneShotDispatchAsync:
    """Tests for _one_shot_dispatch_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_one_shot_dispatch_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_one_shot_dispatch_async should run correct subprocess command."""
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

            app._one_shot_dispatch_async("test-op", "my prompt")
            await pilot.pause(0.3)

            assert captured_args == ["erk", "one-shot", "my prompt"]

    @pytest.mark.asyncio
    async def test_one_shot_dispatch_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_one_shot_dispatch_async should trigger refresh after success."""
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

            app._one_shot_dispatch_async("test-op", "my prompt")
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_one_shot_dispatch_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_one_shot_dispatch_async should NOT refresh on failure."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
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

            app._one_shot_dispatch_async("test-op", "my prompt")
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before


class TestRewriteRemoteAsync:
    """Tests for _rewrite_remote_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_rewrite_remote_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_rewrite_remote_async should trigger action_refresh after success."""
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

            app._rewrite_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_rewrite_remote_no_refresh_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_rewrite_remote_async should NOT refresh on subprocess failure."""
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

            app._rewrite_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before

    @pytest.mark.asyncio
    async def test_rewrite_remote_calls_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_rewrite_remote_async should pass correct args to subprocess."""
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

            app._rewrite_remote_async("test-op", 456)
            await pilot.pause(0.3)

            assert captured_args == [
                "erk",
                "launch",
                "pr-rewrite",
                "--pr",
                "456",
            ]


class TestCmuxSyncAsync:
    """Tests for _cmux_sync_async subprocess behavior."""

    @pytest.mark.asyncio
    async def test_cmux_sync_runs_correct_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_cmux_sync_async should run cmux-sync-workspace with correct args."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_popen_calls: list[list[str]] = []

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            if args:
                captured_popen_calls.append(list(args[0]))  # type: ignore[arg-type]
            return _FakePopen(return_code=0)

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "Popen", fake_popen)
        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._cmux_sync_async("test-op", 456, "test-branch")
            await pilot.pause(0.3)

            assert len(captured_popen_calls) == 1
            assert captured_popen_calls[0] == [
                "erk",
                "exec",
                "cmux-sync-workspace",
                "--pr",
                "456",
                "--branch",
                "test-branch",
            ]

    @pytest.mark.asyncio
    async def test_cmux_sync_triggers_refresh_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_cmux_sync_async should trigger refresh after success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(return_code=0)

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "Popen", fake_popen)
        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._cmux_sync_async("test-op", 456, "test-branch")
            await pilot.pause(0.3)

            assert provider.fetch_count > count_before

    @pytest.mark.asyncio
    async def test_cmux_sync_shows_error_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_cmux_sync_async should NOT refresh on failure."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("sync failed",), return_code=1)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._cmux_sync_async("test-op", 456, "test-branch")
            await pilot.pause(0.3)

            assert provider.fetch_count == count_before


class TestCmuxFocusWorkspace:
    """Tests for _cmux_focus_workspace synchronous method."""

    @pytest.mark.asyncio
    async def test_focus_selects_matching_workspace(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Should call select-workspace when a matching workspace is found."""
        import json
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_run_calls: list[list[str]] = []

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = list(args[0]) if args else []  # type: ignore[arg-type]
            captured_run_calls.append(cmd)
            if "list-workspaces" in cmd:
                data = json.dumps({"workspaces": [{"title": "test-branch", "ref": "ws-42"}]})
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=data, stderr="")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._cmux_focus_workspace("test-branch")

            assert len(captured_run_calls) == 2
            assert captured_run_calls[0] == ["cmux", "--json", "list-workspaces"]
            assert captured_run_calls[1] == [
                "cmux",
                "select-workspace",
                "--workspace",
                "ws-42",
            ]

    @pytest.mark.asyncio
    async def test_focus_no_match_skips_select(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Should only call list-workspaces when no workspace title matches."""
        import json
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        captured_run_calls: list[list[str]] = []

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = list(args[0]) if args else []  # type: ignore[arg-type]
            captured_run_calls.append(cmd)
            data = json.dumps({"workspaces": [{"title": "other-branch", "ref": "ws-99"}]})
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=data, stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._cmux_focus_workspace("test-branch")

            assert len(captured_run_calls) == 1
            assert captured_run_calls[0] == ["cmux", "--json", "list-workspaces"]

    @pytest.mark.asyncio
    async def test_focus_silently_handles_subprocess_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """CalledProcessError should not propagate."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, "cmux")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Should not raise
            app._cmux_focus_workspace("test-branch")

    @pytest.mark.asyncio
    async def test_focus_silently_handles_json_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Invalid JSON stdout should not propagate."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="not valid json", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Should not raise
            app._cmux_focus_workspace("test-branch")
