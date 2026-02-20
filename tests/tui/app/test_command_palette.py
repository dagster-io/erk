"""Tests for command palette from main list view and specific commands."""

from collections.abc import Callable
from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestCommandPaletteFromMain:
    """Tests for command palette from main list view.

    Ctrl+P opens the command palette directly from main list (no detail modal).
    The palette shows plan-specific commands for the selected row.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_copy_prepare(self) -> None:
        """Execute palette command copies prepare command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute command directly (simulates palette selection)
            app.execute_palette_command("copy_prepare")

            assert clipboard.last_copied == "erk prepare 123"

    @pytest.mark.asyncio
    async def test_execute_palette_command_open_pr(self) -> None:
        """Execute palette command opens PR in browser."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123, "Test Plan", pr_number=456, pr_url="https://github.com/test/pr/456"
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute open_pr command
            app.execute_palette_command("open_pr")

            assert provider.browser.last_launched == "https://github.com/test/pr/456"

    @pytest.mark.asyncio
    async def test_execute_palette_command_with_no_selection(self) -> None:
        """Execute palette command with no selection does nothing."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(plans=[], clipboard=clipboard)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute command with no rows selected
            app.execute_palette_command("copy_prepare")

            # Nothing should be copied
            assert clipboard.last_copied is None

    @pytest.mark.asyncio
    async def test_space_opens_detail_screen(self) -> None:
        """Space opens detail screen without palette."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press space (regular detail view)
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)
            # The flag should NOT be set (space = just detail, no palette)
            assert detail_screen._auto_open_palette is False


class TestExecutePaletteCommandLandPR:
    """Tests for execute_palette_command('land_pr').

    land_pr uses modal streaming via _push_streaming_detail.
    These tests verify guard conditions and that a PlanDetailScreen is pushed.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_land_pr_with_no_pr(self) -> None:
        """Execute palette command land_pr does nothing if no PR."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute land_pr command with no PR
            app.execute_palette_command("land_pr")
            await pilot.pause()

            # Should not have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_execute_palette_command_land_pr_pushes_streaming_detail(
        self, tmp_path: Path
    ) -> None:
        """Execute palette command land_pr pushes a PlanDetailScreen modal."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_head_branch="test-branch")],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)
            app.execute_palette_command("land_pr")
            await pilot.pause()

            # Should have pushed a PlanDetailScreen
            assert len(app.screen_stack) == initial_stack_len + 1
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_execute_palette_command_land_pr_with_no_branch(self) -> None:
        """Execute palette command land_pr does nothing if no pr_head_branch."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)]  # Has PR but no pr_head_branch
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute land_pr command - should do nothing since no pr_head_branch
            app.execute_palette_command("land_pr")
            await pilot.pause()

            # Should not have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len


class TestExecutePaletteCommandSubmitToQueue:
    """Tests for execute_palette_command('submit_to_queue').

    submit_to_queue uses modal streaming via _push_streaming_detail.
    These tests verify guard conditions and that a PlanDetailScreen is pushed.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_submit_to_queue_pushes_streaming_detail(
        self, tmp_path: Path
    ) -> None:
        """submit_to_queue pushes a PlanDetailScreen modal."""
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

            initial_stack_len = len(app.screen_stack)
            app.execute_palette_command("submit_to_queue")
            await pilot.pause()

            # Should have pushed a PlanDetailScreen
            assert len(app.screen_stack) == initial_stack_len + 1
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)


class TestExecutePaletteCommandFixConflictsRemote:
    """Tests for execute_palette_command('fix_conflicts_remote').

    Note: fix_conflicts_remote uses streaming output via subprocess. These tests verify
    the guard conditions. The guard condition test (no PR) doesn't invoke
    subprocess, so it can be tested without a real directory. Testing the
    positive case with actual subprocess execution is done via integration tests.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_fix_conflicts_remote_with_no_pr(self) -> None:
        """Execute palette command fix_conflicts_remote does nothing if no PR."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute fix_conflicts_remote command with no PR
            app.execute_palette_command("fix_conflicts_remote")
            await pilot.pause()

            # Should not have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_execute_palette_command_fix_conflicts_remote_pushes_screen_and_runs_command(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Execute palette command fix_conflicts_remote pushes screen and runs correct command."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
            repo_root=tmp_path,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        # Capture the command passed to run_streaming_command
        captured_command = None

        def mock_run_streaming_command(
            self: PlanDetailScreen,
            command: list[str],
            cwd: Path,
            title: str,
            *,
            timeout: float = 30.0,
            on_success: Callable[[], None] | None = None,
        ) -> None:
            nonlocal captured_command
            captured_command = command

        # Patch run_streaming_command to capture the command
        monkeypatch.setattr(
            PlanDetailScreen,
            "run_streaming_command",
            mock_run_streaming_command,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute fix_conflicts_remote command
            app.execute_palette_command("fix_conflicts_remote")
            await pilot.pause()

            # Should have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len + 1

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Verify correct command was prepared
            assert captured_command is not None
            assert captured_command == [
                "erk",
                "launch",
                "pr-fix-conflicts",
                "--pr",
                "456",
            ]


class TestExecutePaletteCommandCodespaceRunPlan:
    """Tests for execute_palette_command('codespace_run_plan').

    This command copies the codespace run objective plan command to clipboard.
    It is only available in the Objectives view.
    """

    @pytest.mark.asyncio
    async def test_codespace_run_plan_copies_command_to_clipboard(self) -> None:
        """Execute palette command codespace_run_plan copies correct command."""
        clipboard = FakeClipboard()
        objective_plans = [make_plan_row(7100, "Test Objective")]
        provider = FakePlanDataProvider(
            plans_by_labels={("erk-objective",): objective_plans},
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Switch to Objectives view
            await pilot.press("3")
            await pilot.pause()
            await pilot.pause()

            # Execute codespace_run_plan command
            app.execute_palette_command("codespace_run_plan")

            assert clipboard.last_copied == "erk codespace run objective plan 7100"
