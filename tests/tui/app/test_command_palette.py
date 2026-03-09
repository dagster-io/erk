"""Tests for command palette functionality."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from erk_shared.fakes.clipboard import FakeClipboard
from erk_shared.fakes.plan_data_provider import FakePlanDataProvider, make_plan_row
from erk_shared.fakes.plan_service import FakePlanService


class TestClosePlanViaCommandPalette:
    """Tests for close plan functionality via command palette.

    Note: The top-level 'c' binding was removed. Close plan is now accessible
    via the command palette in the plan detail modal (Space → Ctrl+P → "Close Plan").
    The execute_command tests in tests/tui/commands/test_execute_command.py
    cover the close_plan command execution. These tests verify the integration.
    """

    @pytest.mark.asyncio
    async def test_close_plan_not_accessible_via_c_key(self) -> None:
        """Top-level 'c' key should no longer close plans."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Feature A"),
                make_plan_row(456, "Feature B"),
            ],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePlanService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()
            await pilot.pause()

            # Initially should have 2 plans
            assert len(provider._plans) == 2

            # Press 'c' - should NOT close plan (binding removed)
            await pilot.press("c")
            await pilot.pause()
            await pilot.pause()

            # Plans should remain unchanged
            assert len(provider._plans) == 2


class TestCommandPaletteFromMain:
    """Tests for command palette from main list view.

    Ctrl+P opens the command palette directly from main list (no detail modal).
    The palette shows plan-specific commands for the selected row.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_open_pr(self) -> None:
        """Execute palette command opens PR in browser."""
        from erk_shared.fakes.browser import FakeBrowserLauncher

        browser = FakeBrowserLauncher()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123, "Test Plan", pr_number=456, pr_url="https://github.com/test/pr/456"
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(browser=browser),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute open_pr command
            app.execute_palette_command("open_pr")

            assert browser.last_launched == "https://github.com/test/pr/456"

    @pytest.mark.asyncio
    async def test_execute_palette_command_with_no_selection(self) -> None:
        """Execute palette command with no selection does nothing."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(plans=[])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

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
        app = ErkDashApp(
            provider=provider, service=FakePlanService(), filters=filters, refresh_interval=0
        )

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


class TestCommandPaletteFromMainCopyVariants:
    """Tests for copy variant commands from main list view."""

    @pytest.mark.asyncio
    async def test_execute_palette_command_copy_close_plan(self) -> None:
        """Execute palette command copies close plan command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app.execute_palette_command("copy_close_plan")

            assert clipboard.last_copied == "erk pr close 123"

    @pytest.mark.asyncio
    async def test_execute_palette_command_copy_rebase_remote(self) -> None:
        """Execute palette command copies rebase remote command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app.execute_palette_command("copy_rebase_remote")

            assert clipboard.last_copied == "erk launch pr-rebase --pr 456"

    @pytest.mark.asyncio
    async def test_execute_palette_command_copy_address_remote(self) -> None:
        """Execute palette command copies address remote command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            app.execute_palette_command("copy_address_remote")

            assert clipboard.last_copied == "erk launch pr-address --pr 456"


class TestExecutePaletteCommandLandPR:
    """Tests for execute_palette_command('land_pr').

    land_pr uses toast + background worker pattern.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_land_pr_with_no_pr(self) -> None:
        """Execute palette command land_pr does nothing if no PR."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePlanService(), filters=filters, refresh_interval=0
        )

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
    async def test_execute_palette_command_land_pr_with_no_branch(self) -> None:
        """Execute palette command land_pr does nothing if no pr_head_branch."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)]  # Has PR but no pr_head_branch
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePlanService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute land_pr command - should do nothing since no pr_head_branch
            app.execute_palette_command("land_pr")
            await pilot.pause()

            # Should not have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len


class TestExecutePaletteCommandRebaseRemote:
    """Tests for execute_palette_command('rebase_remote').

    rebase_remote uses toast + background worker pattern.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_rebase_remote_with_no_pr(self) -> None:
        """Execute palette command rebase_remote does nothing if no PR."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePlanService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute rebase_remote command with no PR
            app.execute_palette_command("rebase_remote")
            await pilot.pause()

            # Should not have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_execute_palette_command_rebase_remote_uses_toast_pattern(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Execute palette command rebase_remote uses toast, not modal."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        # Capture calls to _rebase_remote_async
        captured_pr: int | None = None

        def mock_async(self_app: ErkDashApp, op_id: str, pr_number: int) -> None:
            nonlocal captured_pr
            captured_pr = pr_number

        monkeypatch.setattr(ErkDashApp, "_rebase_remote_async", mock_async)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            app.execute_palette_command("rebase_remote")
            await pilot.pause(0.3)

            # Should NOT have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len

            # Should have called _rebase_remote_async with the PR number
            assert captured_pr == 456


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
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePlanService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

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
