"""Tests for view mode types."""

from erk.tui.views.types import (
    LEARN_VIEW,
    OBJECTIVES_VIEW,
    PLANS_VIEW,
    VIEW_CONFIGS,
    ViewConfig,
    ViewMode,
    get_view_config,
)


class TestViewMode:
    """Tests for ViewMode enum."""

    def test_has_three_modes(self) -> None:
        """ViewMode has exactly three modes."""
        assert len(ViewMode) == 3
        assert ViewMode.PLANS is not None
        assert ViewMode.LEARN is not None
        assert ViewMode.OBJECTIVES is not None


class TestViewConfig:
    """Tests for ViewConfig dataclass."""

    def test_plans_view_config(self) -> None:
        """PLANS_VIEW has correct configuration."""
        assert PLANS_VIEW.mode == ViewMode.PLANS
        assert PLANS_VIEW.display_name == "Plans"
        assert PLANS_VIEW.labels == ("erk-plan",)
        assert PLANS_VIEW.key_hint == "1"

    def test_learn_view_config(self) -> None:
        """LEARN_VIEW has correct configuration."""
        assert LEARN_VIEW.mode == ViewMode.LEARN
        assert LEARN_VIEW.display_name == "Learn"
        assert LEARN_VIEW.labels == ("erk-plan",)
        assert LEARN_VIEW.key_hint == "2"

    def test_objectives_view_config(self) -> None:
        """OBJECTIVES_VIEW has correct configuration."""
        assert OBJECTIVES_VIEW.mode == ViewMode.OBJECTIVES
        assert OBJECTIVES_VIEW.display_name == "Objectives"
        assert OBJECTIVES_VIEW.labels == ("erk-objective",)
        assert OBJECTIVES_VIEW.key_hint == "3"

    def test_view_configs_tuple_has_all_views(self) -> None:
        """VIEW_CONFIGS contains all three view configs."""
        assert len(VIEW_CONFIGS) == 3
        modes = {c.mode for c in VIEW_CONFIGS}
        assert modes == {ViewMode.PLANS, ViewMode.LEARN, ViewMode.OBJECTIVES}

    def test_view_config_is_frozen(self) -> None:
        """ViewConfig is a frozen dataclass."""
        config = ViewConfig(
            mode=ViewMode.PLANS,
            display_name="Test",
            labels=("test",),
            key_hint="x",
        )
        try:
            config.display_name = "Changed"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


class TestGetViewConfig:
    """Tests for get_view_config function."""

    def test_returns_plans_config(self) -> None:
        """get_view_config returns PLANS_VIEW for ViewMode.PLANS."""
        config = get_view_config(ViewMode.PLANS)
        assert config.mode == ViewMode.PLANS
        assert config.display_name == "Plans"

    def test_returns_learn_config(self) -> None:
        """get_view_config returns LEARN_VIEW for ViewMode.LEARN."""
        config = get_view_config(ViewMode.LEARN)
        assert config.mode == ViewMode.LEARN
        assert config.display_name == "Learn"

    def test_returns_objectives_config(self) -> None:
        """get_view_config returns OBJECTIVES_VIEW for ViewMode.OBJECTIVES."""
        config = get_view_config(ViewMode.OBJECTIVES)
        assert config.mode == ViewMode.OBJECTIVES
        assert config.display_name == "Objectives"
