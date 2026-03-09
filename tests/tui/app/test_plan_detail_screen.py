"""Tests for PlanDetailScreen modal."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
from erk_shared.gateway.pr_service.fake import FakePrService


class TestPlanDetailScreen:
    """Tests for PlanDetailScreen modal."""

    @pytest.mark.asyncio
    async def test_space_opens_detail_screen(self) -> None:
        """Pressing space opens the plan detail modal."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, pr_title="Test PR")]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press space to show detail
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            # Detail screen should be in the screen stack
            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_dismisses_on_escape(self) -> None:
        """Detail modal closes when pressing escape."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail modal
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            # Should be showing detail
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

            # Press escape to close
            await pilot.press("escape")
            await pilot.pause()

            # Should be back to main screen
            assert not isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_dismisses_on_q(self) -> None:
        """Detail modal closes when pressing q."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

            await pilot.press("q")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_dismisses_on_space(self) -> None:
        """Detail modal closes when pressing space again."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

            await pilot.press("space")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_displays_full_title(self) -> None:
        """Detail modal shows full untruncated title."""
        long_title = (
            "This is a very long plan title that would normally be truncated "
            "in the table view but should be fully visible in the detail modal"
        )
        provider = FakePlanDataProvider(plans=[make_plan_row(123, long_title)])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)
            # The modal stores the full row data which contains full_title
            assert detail_screen._row.full_title == long_title

    @pytest.mark.asyncio
    async def test_detail_modal_shows_pr_info_when_linked(self) -> None:
        """Detail modal shows PR information when PR is linked."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    pr_number=456,
                    pr_title="Test PR Title",
                    pr_state="OPEN",
                    pr_url="https://github.com/test/repo/pull/456",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)
            assert detail_screen._row.pr_number == 456
            assert detail_screen._row.pr_title == "Test PR Title"
            assert detail_screen._row.pr_state == "OPEN"


class TestPlanDetailScreenCopyActions:
    """Tests for PlanDetailScreen copy keyboard shortcuts."""

    @pytest.mark.asyncio
    async def test_copy_prepare_shortcut_1(self) -> None:
        """Pressing '1' in detail screen copies prepare command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            # Press '1' to copy prepare command
            await pilot.press("1")
            await pilot.pause()

            assert clipboard.last_copied == "erk br co --for-plan 123"

    @pytest.mark.asyncio
    async def test_copy_dispatch_shortcut_3(self) -> None:
        """Pressing '3' in detail screen copies dispatch command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("3")
            await pilot.pause()

            assert clipboard.last_copied == "erk pr dispatch 123"

    @pytest.mark.asyncio
    async def test_copy_checkout_shortcut_c_with_local_worktree(self) -> None:
        """Pressing 'c' in detail screen copies checkout command for local worktree."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    worktree_name="feature-123",
                    worktree_branch="feature-123",
                    exists_locally=True,
                )
            ],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            assert clipboard.last_copied == "erk br co feature-123"

    @pytest.mark.asyncio
    async def test_copy_pr_checkout_script_shortcut_e(self) -> None:
        """Pressing 'e' in detail screen copies PR checkout (cd) command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    pr_number=456,
                    exists_locally=False,
                )
            ],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("e")
            await pilot.pause()

            assert clipboard.last_copied == 'source "$(erk pr checkout 456 --script)"'


class TestPlanDetailScreenRebaseKeybinding:
    """Tests for action_rebase_remote() triggered via keybinding '5'.

    The keybinding action dismisses the detail screen and delegates to
    the app's toast + async worker pattern.
    """

    @pytest.mark.asyncio
    async def test_rebase_keybinding_uses_toast_pattern(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Pressing '5' in detail screen triggers toast + async rebase."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        captured_pr: int | None = None

        def mock_async(self_app: ErkDashApp, op_id: str, pr_number: int) -> None:
            nonlocal captured_pr
            captured_pr = pr_number

        monkeypatch.setattr(ErkDashApp, "_rebase_remote_async", mock_async)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Press '5' to trigger rebase_remote keybinding
            await pilot.press("5")
            await pilot.pause()

            # Detail screen should have been dismissed (stack shrunk)
            assert len(app.screen_stack) < initial_stack_len

            # Should have called _rebase_remote_async with the PR number
            assert captured_pr == 456

    @pytest.mark.asyncio
    async def test_rebase_keybinding_does_nothing_without_pr(self) -> None:
        """Pressing '5' in detail screen does nothing if no PR number."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Press '5' with no PR - should do nothing
            await pilot.press("5")
            await pilot.pause()

            # Detail screen should still be open (not dismissed)
            assert len(app.screen_stack) == initial_stack_len


class TestPlanDetailScreenRewriteCommand:
    """Tests for rewrite_remote and copy_rewrite_remote via execute_command.

    The rewrite action is available through the command palette (execute_command),
    not a direct keybinding.
    """

    @pytest.mark.asyncio
    async def test_rewrite_remote_dismisses_and_dispatches(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """execute_command('rewrite_remote') dismisses screen and dispatches rewrite."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        captured_pr: int | None = None

        def mock_rewrite(self_app: ErkDashApp, op_id: str, pr_number: int) -> None:
            nonlocal captured_pr
            captured_pr = pr_number

        monkeypatch.setattr(ErkDashApp, "_rewrite_remote_async", mock_rewrite)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)
            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Trigger rewrite via execute_command
            detail_screen.execute_command("rewrite_remote")
            await pilot.pause()

            # Detail screen should have been dismissed
            assert len(app.screen_stack) < initial_stack_len

            # Should have called _rewrite_remote_async with the PR number
            assert captured_pr == 456

    @pytest.mark.asyncio
    async def test_copy_rewrite_remote_copies_command(self) -> None:
        """execute_command('copy_rewrite_remote') copies the rewrite command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456)],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(clipboard=clipboard),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Trigger copy via execute_command
            detail_screen.execute_command("copy_rewrite_remote")
            await pilot.pause()

            assert clipboard.last_copied == "erk launch pr-rewrite --pr 456"
