"""Tests for view comments and launch actions."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.screens.launch_screen import LaunchScreen
from erk.tui.screens.objective_nodes_screen import ObjectiveNodesScreen
from erk.tui.screens.unresolved_comments_screen import UnresolvedCommentsScreen
from erk.tui.widgets.status_bar import StatusBar
from tests.fakes.gateway.clipboard import FakeClipboard
from tests.fakes.gateway.plan_data_provider import FakePlanDataProvider, make_plan_row
from tests.fakes.gateway.pr_service import FakePrService


class TestActionViewComments:
    """Tests for action_view_comments (c key)."""

    @pytest.mark.asyncio
    async def test_no_selected_row_does_nothing(self) -> None:
        """No selected row → early return, no screen pushed."""
        provider = FakePlanDataProvider(plans=[])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            await pilot.press("c")
            await pilot.pause()

            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_no_pr_linked_shows_status_message(self) -> None:
        """Row with pr_number=None → status bar shows 'No PR linked to this plan'."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No PR linked to this plan"

    @pytest.mark.asyncio
    async def test_zero_unresolved_shows_status_message(self) -> None:
        """Row with 0 unresolved comments → status bar shows 'No unresolved comments'."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, comment_counts=(5, 5))]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No unresolved comments"

    @pytest.mark.asyncio
    async def test_unresolved_comments_pushes_screen(self) -> None:
        """Row with unresolved comments → pushes UnresolvedCommentsScreen."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, comment_counts=(3, 5))]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()
            await pilot.pause()

            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], UnresolvedCommentsScreen)


_V2_ROADMAP_BODY = """\
# Objective

### Phase 1: Foundation

<!-- erk:metadata-block:objective-roadmap -->
<details>
<summary><code>objective-roadmap</code></summary>

```yaml
schema_version: '2'
steps:
- id: '1.1'
  description: Setup infra
  status: done
  plan: null
  pr: null
```

</details>
<!-- /erk:metadata-block:objective-roadmap -->
"""


class TestActionViewNodes:
    """Tests for action_view_nodes (b key)."""

    @pytest.mark.asyncio
    async def test_no_selected_row_does_nothing(self) -> None:
        """No selected row → early return, no screen pushed."""
        provider = FakePlanDataProvider(plans=[])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            await pilot.press("b")
            await pilot.pause()

            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_not_objectives_view_does_nothing(self) -> None:
        """In Plans view, pressing 'b' does nothing."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            await pilot.press("b")
            await pilot.pause()

            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_empty_plan_body_shows_status_message(self) -> None:
        """Objective row with empty plan_body → status bar shows message."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Objective")])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("3")  # Switch to Objectives view
            await pilot.pause()
            await pilot.pause()

            await pilot.press("b")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No objective body available"

    @pytest.mark.asyncio
    async def test_plan_body_pushes_nodes_screen(self) -> None:
        """Objective row with plan_body → pushes ObjectiveNodesScreen."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Objective", plan_body=_V2_ROADMAP_BODY)]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("3")  # Switch to Objectives view
            await pilot.pause()
            await pilot.pause()

            await pilot.press("b")
            await pilot.pause()
            await pilot.pause()

            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], ObjectiveNodesScreen)


class TestActionLaunch:
    """Tests for action_launch and _on_launch_result."""

    @pytest.mark.asyncio
    async def test_launch_with_no_selected_row_does_nothing(self) -> None:
        """Pressing 'l' with no rows does not push a screen."""
        provider = FakePlanDataProvider(plans=[])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            await pilot.press("l")
            await pilot.pause()

            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_launch_pushes_launch_screen(self) -> None:
        """Pressing 'l' with a selected row pushes LaunchScreen."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    plan_url="https://github.com/test/repo/issues/123",
                    pr_number=456,
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

            await pilot.press("l")
            await pilot.pause()
            await pilot.pause()

            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], LaunchScreen)

    @pytest.mark.asyncio
    async def test_launch_result_none_does_not_execute_command(self) -> None:
        """_on_launch_result with None does not execute any command."""
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

            app._on_launch_result(None)

            assert clipboard.last_copied is None

    @pytest.mark.asyncio
    async def test_launch_result_executes_command(self) -> None:
        """_on_launch_result with a command_id executes that command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=123)],
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

            app._on_launch_result("copy_implement_local")

            expected = 'source "$(erk pr checkout 123 --script)" && erk implement --dangerous'
            assert clipboard.last_copied == expected

    @pytest.mark.asyncio
    async def test_launch_screen_dismisses_on_unmapped_key(self) -> None:
        """Pressing an unmapped key dismisses LaunchScreen with None result."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    plan_url="https://github.com/test/repo/issues/123",
                    pr_number=456,
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

            await pilot.press("l")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], LaunchScreen)

            # Press unmapped key — should dismiss
            await pilot.press("x")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], LaunchScreen)
