"""Tests for multi-operation status bar tracking."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class _FakePopen:
    """Fake subprocess.Popen that yields configurable output lines."""

    def __init__(self, *, lines: tuple[str, ...] = (), return_code: int = 0) -> None:
        self._return_code = return_code
        self.stdout: list[str] = [line + "\n" for line in lines]

    def wait(self) -> int:
        return self._return_code


class TestOperationTracking:
    """Tests for multi-operation status bar tracking.

    Verifies that async operations register via start_operation, stream
    progress via update_operation, and clean up via finish_operation.
    """

    @pytest.mark.asyncio
    async def test_start_operation_sets_status_bar(self) -> None:
        """_start_operation registers operation and adds running class."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert not status_bar._operations
            assert not status_bar.has_class("running")

            app._start_operation(op_id="test-op", label="Working...")
            assert "test-op" in status_bar._operations
            assert status_bar._operations["test-op"].label == "Working..."
            assert status_bar.has_class("running")

    @pytest.mark.asyncio
    async def test_finish_operation_clears_status_bar(self) -> None:
        """_finish_operation removes operation and clears running class."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            app._start_operation(op_id="test-op", label="Working...")
            assert status_bar.has_class("running")

            app._finish_operation(op_id="test-op")
            assert "test-op" not in status_bar._operations
            assert not status_bar.has_class("running")

    @pytest.mark.asyncio
    async def test_close_plan_starts_then_finishes_operation(self, tmp_path: Path) -> None:
        """_close_plan_async finishes operation on success."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Test Plan", plan_url="https://github.com/test/repo/issues/123")
            ],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)

            op_id = "close-plan-123"
            app._start_operation(op_id=op_id, label="Closing plan #123...")
            assert op_id in status_bar._operations

            app._close_plan_async(op_id, 123, "https://github.com/test/repo/issues/123")
            await pilot.pause(0.3)

            assert op_id not in status_bar._operations

    @pytest.mark.asyncio
    async def test_address_remote_finishes_operation_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_address_remote_async finishes operation on success."""
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

            status_bar = app.query_one(StatusBar)
            op_id = "address-pr-456"
            app._start_operation(op_id=op_id, label="Dispatching address for PR #456...")
            assert op_id in status_bar._operations

            app._address_remote_async(op_id, 456)
            await pilot.pause(0.3)

            assert op_id not in status_bar._operations

    @pytest.mark.asyncio
    async def test_address_remote_finishes_operation_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_address_remote_async finishes operation on failure."""
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

            status_bar = app.query_one(StatusBar)
            op_id = "address-pr-456"
            app._start_operation(op_id=op_id, label="Dispatching address for PR #456...")

            app._address_remote_async(op_id, 456)
            await pilot.pause(0.3)

            assert op_id not in status_bar._operations

    @pytest.mark.asyncio
    async def test_land_pr_finishes_operation_on_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async finishes operation on success."""
        import subprocess

        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        def fake_popen(*args: object, **kwargs: object) -> _FakePopen:
            return _FakePopen(lines=("Merging branch",), return_code=0)

        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            op_id = "land-pr-456"
            app._start_operation(op_id=op_id, label="Landing PR #456...")

            app._land_pr_async(
                op_id,
                456,
                "test-branch",
                None,
            )
            await pilot.pause(0.3)

            assert op_id not in status_bar._operations

    @pytest.mark.asyncio
    async def test_land_pr_finishes_operation_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_land_pr_async finishes operation on failure."""
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

            status_bar = app.query_one(StatusBar)
            op_id = "land-pr-456"
            app._start_operation(op_id=op_id, label="Landing PR #456...")

            app._land_pr_async(
                op_id,
                456,
                "test-branch",
                None,
            )
            await pilot.pause(0.3)

            assert op_id not in status_bar._operations

    @pytest.mark.asyncio
    async def test_multi_operation_keeps_running_until_all_finish(self) -> None:
        """Starting two operations, finishing one keeps running class."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            app._start_operation(op_id="op-1", label="Landing PR #1...")
            app._start_operation(op_id="op-2", label="Dispatching plan #2...")
            assert len(status_bar._operations) == 2
            assert status_bar.has_class("running")

            # Finish one - should still be running
            app._finish_operation(op_id="op-1")
            assert len(status_bar._operations) == 1
            assert status_bar.has_class("running")
            assert "op-2" in status_bar._operations

            # Finish second - should clear running
            app._finish_operation(op_id="op-2")
            assert not status_bar._operations
            assert not status_bar.has_class("running")

    @pytest.mark.asyncio
    async def test_update_operation_updates_progress(self) -> None:
        """update_operation updates the progress text for an operation."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            app._start_operation(op_id="test-op", label="Landing PR #456...")
            assert status_bar._operations["test-op"].progress == ""

            app._update_operation(op_id="test-op", progress="Merging branch")
            assert status_bar._operations["test-op"].progress == "Merging branch"
            assert status_bar._last_updated_op_id == "test-op"

    @pytest.mark.asyncio
    async def test_update_operation_skips_unknown_op_id(self) -> None:
        """update_operation is a no-op if op_id is not registered."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            # Should not crash
            app._update_operation(op_id="nonexistent", progress="line")
            assert not status_bar._operations
