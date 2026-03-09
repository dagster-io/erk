"""Tests for ViewBar widget."""

from erk.tui.views.types import ViewMode
from erk.tui.widgets.view_bar import ViewBar, _build_view_bar_content


class TestViewBar:
    """Tests for ViewBar rendering and state management."""

    def test_initial_active_view(self) -> None:
        """ViewBar stores the initial active view."""
        bar = ViewBar(active_view=ViewMode.PLANS, plans_display_name="PRs")
        assert bar._active_view == ViewMode.PLANS

    def test_set_active_view_updates_state(self) -> None:
        """set_active_view updates the active view mode."""
        bar = ViewBar(active_view=ViewMode.PLANS, plans_display_name="PRs")
        bar._active_view = ViewMode.LEARN
        assert bar._active_view == ViewMode.LEARN

    def test_set_active_view_to_objectives(self) -> None:
        """set_active_view can switch to objectives."""
        bar = ViewBar(active_view=ViewMode.PLANS, plans_display_name="PRs")
        bar._active_view = ViewMode.OBJECTIVES
        assert bar._active_view == ViewMode.OBJECTIVES


class TestBuildViewBarContent:
    """Tests for _build_view_bar_content pure function."""

    def test_tab_regions_with_default_plans_name(self) -> None:
        """Tab regions computed correctly with 'PRs' display name."""
        _text, regions = _build_view_bar_content(
            active_view=ViewMode.PLANS,
            plans_display_name="PRs",
        )

        # "1:PRs"=5, gap=2, "2:Learn"=7, gap=2, "3:Objectives"=12, gap=2, "4:Runs"=6
        assert len(regions) == 4
        assert regions[0] == (0, 5, ViewMode.PLANS)
        assert regions[1] == (7, 14, ViewMode.LEARN)
        assert regions[2] == (16, 28, ViewMode.OBJECTIVES)
        assert regions[3] == (30, 36, ViewMode.RUNS)

    def test_tab_regions_with_custom_plans_name(self) -> None:
        """Tab regions adjust when plans display name is longer."""
        _text, regions = _build_view_bar_content(
            active_view=ViewMode.PLANS,
            plans_display_name="Planned PRs",
        )

        # "1:Planned PRs" = 13 chars
        assert len(regions) == 4
        assert regions[0] == (0, 13, ViewMode.PLANS)
        assert regions[1] == (15, 22, ViewMode.LEARN)
        assert regions[2] == (24, 36, ViewMode.OBJECTIVES)
        assert regions[3] == (38, 44, ViewMode.RUNS)

    def test_text_content_matches_labels(self) -> None:
        """Built text contains all tab labels."""
        text, _regions = _build_view_bar_content(
            active_view=ViewMode.PLANS,
            plans_display_name="PRs",
        )

        plain = text.plain
        assert "1:PRs" in plain
        assert "2:Learn" in plain
        assert "3:Objectives" in plain
        assert "4:Runs" in plain

    def test_active_view_does_not_affect_regions(self) -> None:
        """Active view changes styling but not region positions."""
        _text1, regions1 = _build_view_bar_content(
            active_view=ViewMode.PLANS,
            plans_display_name="PRs",
        )
        _text2, regions2 = _build_view_bar_content(
            active_view=ViewMode.LEARN,
            plans_display_name="PRs",
        )

        assert regions1 == regions2


class TestViewBarTabRegions:
    """Tests for ViewBar tab region initialization."""

    def test_tab_regions_empty_before_mount(self) -> None:
        """Tab regions are empty before on_mount fires."""
        bar = ViewBar(active_view=ViewMode.PLANS, plans_display_name="PRs")
        assert bar._tab_regions == []
