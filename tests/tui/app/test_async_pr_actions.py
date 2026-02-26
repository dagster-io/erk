"""Tests for ErkDashApp - async pr actions."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._address_remote_async(456)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, args, stderr="dispatch failed")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._address_remote_async(456)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_args.extend(args)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._fix_conflicts_remote_async(456)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._fix_conflicts_remote_async(456)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, args, stderr="dispatch failed")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._fix_conflicts_remote_async(456)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(456, "test-branch", None)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._land_pr_async(456, "test-branch", None)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, args, stderr="land failed")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            count_before = provider.fetch_count

            app._land_pr_async(456, "test-branch", None)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(456, "test-branch", 789)
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

        def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app._land_pr_async(456, "test-branch", None)
            await pilot.pause(0.3)

            # Only the land command, no objective update
            assert len(captured_calls) == 1
