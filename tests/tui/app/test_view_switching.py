"""Tests for view switching (1/2/3 keys)."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode, get_view_config
from erk.tui.widgets.view_bar import ViewBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestViewSwitching:
    """Tests for view switching (1/2/3 keys)."""

    @pytest.mark.asyncio
    async def test_app_has_view_bar(self) -> None:
        """App composes a ViewBar widget."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test():
            view_bar = app.query_one(ViewBar)
            assert view_bar is not None

    @pytest.mark.asyncio
    async def test_default_view_is_plans(self) -> None:
        """App starts in Plans view mode."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

    @pytest.mark.asyncio
    async def test_pressing_2_switches_to_learn_view(self) -> None:
        """Pressing '2' switches to Learn view."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Regular Plan"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS
            # Plans view excludes learn plans
            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 1

            # Switch to Learn view
            await pilot.press("2")
            await pilot.pause()

            assert app._view_mode == ViewMode.LEARN
            # Learn view filters to only learn plans
            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 2

    @pytest.mark.asyncio
    async def test_plans_view_excludes_learn_plans(self) -> None:
        """Plans view filters out learn plans."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Regular Plan A"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
                make_plan_row(3, "Regular Plan B"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS
            # Plans view should exclude the learn plan
            assert len(app._rows) == 2
            issue_numbers = {r.plan_id for r in app._rows}
            assert issue_numbers == {1, 3}

    @pytest.mark.asyncio
    async def test_pressing_3_switches_to_objectives_view(self) -> None:
        """Pressing '3' switches to Objectives view."""
        objective_plans = [
            make_plan_row(10, "Objective A"),
            make_plan_row(20, "Objective B"),
        ]
        provider = FakePlanDataProvider(
            plans=[make_plan_row(1, "Regular Plan")],
            plans_by_labels={
                ("erk-objective",): objective_plans,
            },
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

            # Switch to Objectives view
            await pilot.press("3")
            await pilot.pause()
            await pilot.pause()

            assert app._view_mode == ViewMode.OBJECTIVES
            assert len(app._rows) == 2

    @pytest.mark.asyncio
    async def test_pressing_1_returns_to_plans_view(self) -> None:
        """Pressing '1' returns to Plans view from another view."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS
            # Plans view excludes learn plans
            assert len(app._rows) == 1

            # Switch to Learn
            await pilot.press("2")
            await pilot.pause()
            assert app._view_mode == ViewMode.LEARN
            assert len(app._rows) == 1

            # Switch back to Plans
            await pilot.press("1")
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS
            assert len(app._rows) == 1

    @pytest.mark.asyncio
    async def test_same_view_key_is_noop(self) -> None:
        """Pressing '1' while already in Plans view does nothing."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            initial_fetch_count = provider.fetch_count

            # Press '1' - already in Plans, should be noop
            await pilot.press("1")
            await pilot.pause()

            assert app._view_mode == ViewMode.PLANS
            # Should not have triggered another fetch
            assert provider.fetch_count == initial_fetch_count

    @pytest.mark.asyncio
    async def test_view_bar_updates_on_switch(self) -> None:
        """ViewBar shows the active view after switching."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            view_bar = app.query_one(ViewBar)
            assert view_bar._active_view == ViewMode.PLANS

            await pilot.press("2")
            await pilot.pause()

            assert view_bar._active_view == ViewMode.LEARN

    @pytest.mark.asyncio
    async def test_right_arrow_wraps_from_last_to_first(self) -> None:
        """Right arrow wraps from Objectives back to Plans."""
        objective_plans = [make_plan_row(10, "Objective A")]
        provider = FakePlanDataProvider(
            plans=[make_plan_row(1, "Plan A")],
            plans_by_labels={
                ("erk-objective",): objective_plans,
            },
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

            # Plans -> Learn -> Objectives
            await pilot.press("right")
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            await pilot.pause()

            assert app._view_mode == ViewMode.OBJECTIVES

            # Objectives -> Plans (wrap)
            await pilot.press("right")
            await pilot.pause()

            assert app._view_mode == ViewMode.PLANS

    @pytest.mark.asyncio
    async def test_left_arrow_wraps_from_first_to_last(self) -> None:
        """Left arrow from Learn goes to Plans."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Go to Learn first
            await pilot.press("2")
            await pilot.pause()
            assert app._view_mode == ViewMode.LEARN

            # Left arrow goes to Plans
            await pilot.press("left")
            await pilot.pause()

            assert app._view_mode == ViewMode.PLANS

    @pytest.mark.asyncio
    async def test_data_cache_avoids_refetch(self) -> None:
        """Switching back to a cached view does not refetch."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            count_after_initial = provider.fetch_count

            # Switch to Learn (uses cache since same labels)
            await pilot.press("2")
            await pilot.pause()

            # Switch back to Plans (should use cache)
            await pilot.press("1")
            await pilot.pause()

            # The Plans view uses the same erk-plan labels as Learn view,
            # so cache is shared. No additional fetch needed.
            assert provider.fetch_count == count_after_initial

    @pytest.mark.asyncio
    async def test_stale_fetch_does_not_update_display(self) -> None:
        """Late-arriving fetch from previous tab caches data but does not update display.

        Simulates the race condition: _update_table receives data fetched for
        Plans view while the user has already switched to Objectives view.
        The data should be cached under Plans labels but the Objectives display
        should remain unchanged.
        """
        objective_plans = [
            make_plan_row(10, "Objective A"),
            make_plan_row(20, "Objective B"),
        ]
        provider = FakePlanDataProvider(
            plans=[make_plan_row(1, "Plan A")],
            plans_by_labels={
                ("erk-objective",): objective_plans,
            },
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Initial state: Plans view with 1 row
            assert app._view_mode == ViewMode.PLANS
            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 1

            # Switch to Objectives view
            await pilot.press("3")
            await pilot.pause()
            await pilot.pause()

            assert app._view_mode == ViewMode.OBJECTIVES
            assert len(app._rows) == 2
            displayed_issues = {r.plan_id for r in app._rows}
            assert displayed_issues == {10, 20}

            # Simulate a stale fetch arriving: data fetched for Plans view
            # but user already switched to Objectives
            stale_plans = [make_plan_row(99, "Stale Plan")]
            app._update_table(
                stale_plans,
                "12:00:00",
                0.5,
                fetched_mode=ViewMode.PLANS,
            )

            # Display should NOT have changed - still showing Objectives
            assert app._view_mode == ViewMode.OBJECTIVES
            assert len(app._rows) == 2
            assert {r.plan_id for r in app._rows} == {10, 20}

            # But the stale data should be cached under Plans labels
            plans_labels = get_view_config(ViewMode.PLANS).labels
            assert plans_labels in app._data_cache
            assert len(app._data_cache[plans_labels]) == 1
            assert app._data_cache[plans_labels][0].plan_id == 99

    @pytest.mark.asyncio
    async def test_right_arrow_cycles_to_next_view(self) -> None:
        """Right arrow cycles through views: PLANS -> LEARN -> OBJECTIVES -> PLANS."""
        objective_plans = [
            make_plan_row(10, "Objective A"),
        ]
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Regular Plan"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
            ],
            plans_by_labels={
                ("erk-objective",): objective_plans,
            },
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

            # Right arrow: PLANS -> LEARN
            await pilot.press("right")
            await pilot.pause()
            assert app._view_mode == ViewMode.LEARN

            # Right arrow: LEARN -> OBJECTIVES
            await pilot.press("right")
            await pilot.pause()
            await pilot.pause()
            assert app._view_mode == ViewMode.OBJECTIVES

            # Right arrow: OBJECTIVES -> PLANS (wrap-around)
            await pilot.press("right")
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

    @pytest.mark.asyncio
    async def test_left_arrow_cycles_to_previous_view(self) -> None:
        """Left arrow cycles through views: PLANS -> OBJECTIVES -> LEARN -> PLANS."""
        objective_plans = [
            make_plan_row(10, "Objective A"),
        ]
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Regular Plan"),
                make_plan_row(2, "Learn Plan", is_learn_plan=True),
            ],
            plans_by_labels={
                ("erk-objective",): objective_plans,
            },
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS

            # Left arrow: PLANS -> OBJECTIVES (wrap-around)
            await pilot.press("left")
            await pilot.pause()
            await pilot.pause()
            assert app._view_mode == ViewMode.OBJECTIVES

            # Left arrow: OBJECTIVES -> LEARN
            await pilot.press("left")
            await pilot.pause()
            assert app._view_mode == ViewMode.LEARN

            # Left arrow: LEARN -> PLANS
            await pilot.press("left")
            await pilot.pause()
            assert app._view_mode == ViewMode.PLANS
