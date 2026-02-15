"""Tests for ViewBar widget."""

from erk.tui.views.types import ViewMode
from erk.tui.widgets.view_bar import ViewBar


class TestViewBar:
    """Tests for ViewBar rendering and state management."""

    def test_initial_active_view(self) -> None:
        """ViewBar stores the initial active view."""
        bar = ViewBar(active_view=ViewMode.PLANS)
        assert bar._active_view == ViewMode.PLANS

    def test_set_active_view_updates_state(self) -> None:
        """set_active_view updates the active view mode."""
        bar = ViewBar(active_view=ViewMode.PLANS)
        bar._active_view = ViewMode.LEARN
        assert bar._active_view == ViewMode.LEARN

    def test_set_active_view_to_objectives(self) -> None:
        """set_active_view can switch to objectives."""
        bar = ViewBar(active_view=ViewMode.PLANS)
        bar._active_view = ViewMode.OBJECTIVES
        assert bar._active_view == ViewMode.OBJECTIVES
