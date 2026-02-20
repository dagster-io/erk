"""Tests for PlanBodyScreen modal (view plan text with async loading)."""

import pytest
from textual.widgets import Markdown

from erk.tui.app import ErkDashApp, PlanBodyScreen
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestPlanBodyScreen:
    """Tests for PlanBodyScreen modal (view plan text with async loading)."""

    @pytest.mark.asyncio
    async def test_v_key_opens_issue_body_screen(self) -> None:
        """Pressing 'v' opens the issue body modal."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        provider.set_plan_content(123, "# Test Plan\n\nThis is the plan content.")
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press 'v' to view plan content
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()

            # PlanBodyScreen should be in the screen stack
            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], PlanBodyScreen)

    @pytest.mark.asyncio
    async def test_issue_body_screen_fetches_and_shows_content(self) -> None:
        """PlanBodyScreen fetches and displays the plan content."""
        plan_content = "# Implementation Plan\n\n1. Step one\n2. Step two"
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        provider.set_plan_content(123, plan_content)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("v")
            await pilot.pause()
            # Wait for async fetch to complete
            await pilot.pause(0.3)

            body_screen = app.screen_stack[-1]
            assert isinstance(body_screen, PlanBodyScreen)
            # Content should have been fetched
            assert body_screen._content == plan_content
            assert body_screen._loading is False

    @pytest.mark.asyncio
    async def test_issue_body_screen_dismisses_on_escape(self) -> None:
        """PlanBodyScreen closes when pressing escape."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        provider.set_plan_content(123, "Plan content")
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open body screen
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanBodyScreen)

            # Press escape to close
            await pilot.press("escape")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanBodyScreen)

    @pytest.mark.asyncio
    async def test_issue_body_screen_dismisses_on_q(self) -> None:
        """PlanBodyScreen closes when pressing q."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        provider.set_plan_content(123, "Plan content")
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanBodyScreen)

            await pilot.press("q")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanBodyScreen)

    @pytest.mark.asyncio
    async def test_issue_body_screen_dismisses_on_space(self) -> None:
        """PlanBodyScreen closes when pressing space."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        provider.set_plan_content(123, "Plan content")
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanBodyScreen)

            await pilot.press("space")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanBodyScreen)

    @pytest.mark.asyncio
    async def test_issue_body_screen_shows_empty_message_when_no_content(self) -> None:
        """PlanBodyScreen shows empty message when no plan content found."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        # Don't set plan content - fetch will return None
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("v")
            await pilot.pause()
            # Wait for async fetch to complete
            await pilot.pause(0.3)

            body_screen = app.screen_stack[-1]
            assert isinstance(body_screen, PlanBodyScreen)
            # Content should be None (not found)
            assert body_screen._content is None
            assert body_screen._loading is False

    @pytest.mark.asyncio
    async def test_issue_body_screen_shows_plan_number_and_title(self) -> None:
        """PlanBodyScreen shows plan number and full title in header."""
        full_title = "This is a very long plan title that should be shown in full"
        provider = FakePlanDataProvider(
            plans=[make_plan_row(456, full_title, plan_body="metadata body")]
        )
        provider.set_plan_content(456, "Plan content")
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("v")
            await pilot.pause()
            await pilot.pause()

            body_screen = app.screen_stack[-1]
            assert isinstance(body_screen, PlanBodyScreen)
            assert body_screen._plan_id == 456
            assert body_screen._full_title == full_title

    @pytest.mark.asyncio
    async def test_issue_body_screen_renders_content_as_markdown(self) -> None:
        """PlanBodyScreen renders plan content using Markdown widget."""
        plan_content = "# Header\n\n- List item 1\n- List item 2"
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", plan_body="metadata body")]
        )
        provider.set_plan_content(123, plan_content)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("v")
            await pilot.pause()
            # Wait for async fetch to complete
            await pilot.pause(0.3)

            body_screen = app.screen_stack[-1]
            assert isinstance(body_screen, PlanBodyScreen)

            # Verify content is rendered as Markdown widget
            content_widget = body_screen.query_one("#body-content", Markdown)
            assert content_widget is not None

    @pytest.mark.asyncio
    async def test_objective_view_shows_objective_header_and_fetches_content(self) -> None:
        """In Objectives view, PlanBodyScreen fetches objective content."""
        objective_content = "# Roadmap\n\n- Step 1\n- Step 2"
        objective_plans = [
            make_plan_row(100, "My Objective", plan_body="objective metadata"),
        ]
        provider = FakePlanDataProvider(
            plans_by_labels={("erk-objective",): objective_plans},
        )
        provider.set_objective_content(100, objective_content)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Switch to Objectives view
            await pilot.press("3")
            await pilot.pause()
            await pilot.pause()

            assert app._view_mode == ViewMode.OBJECTIVES

            # Press 'v' to view content
            await pilot.press("v")
            await pilot.pause()
            await pilot.pause(0.3)

            body_screen = app.screen_stack[-1]
            assert isinstance(body_screen, PlanBodyScreen)
            # Should use "Objective" content type
            assert body_screen._content_type == "Objective"
            assert body_screen._content == objective_content
            assert body_screen._loading is False
