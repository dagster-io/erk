"""Tests for view mode types."""

from erk.tui.views.types import (
    LEARN_VIEW,
    OBJECTIVES_VIEW,
    PLANS_VIEW,
    RUNS_VIEW,
    VIEW_CONFIGS,
    ViewConfig,
    ViewMode,
    get_next_view_mode,
    get_previous_view_mode,
    get_view_config,
)


class TestViewMode:
    """Tests for ViewMode enum."""

    def test_has_four_modes(self) -> None:
        """ViewMode has exactly four modes."""
        assert len(ViewMode) == 4
        assert ViewMode.PLANS is not None
        assert ViewMode.LEARN is not None
        assert ViewMode.OBJECTIVES is not None
        assert ViewMode.RUNS is not None


class TestViewConfig:
    """Tests for ViewConfig dataclass."""

    def test_plans_view_config(self) -> None:
        """PLANS_VIEW has correct configuration."""
        assert PLANS_VIEW.mode == ViewMode.PLANS
        assert PLANS_VIEW.display_name == "PRs"
        assert PLANS_VIEW.labels == ("erk-core",)
        assert PLANS_VIEW.key_hint == "1"

    def test_learn_view_config(self) -> None:
        """LEARN_VIEW has correct configuration."""
        assert LEARN_VIEW.mode == ViewMode.LEARN
        assert LEARN_VIEW.display_name == "Learn"
        assert LEARN_VIEW.labels == ("erk-learn",)
        assert LEARN_VIEW.key_hint == "2"

    def test_objectives_view_config(self) -> None:
        """OBJECTIVES_VIEW has correct configuration."""
        assert OBJECTIVES_VIEW.mode == ViewMode.OBJECTIVES
        assert OBJECTIVES_VIEW.display_name == "Objectives"
        assert OBJECTIVES_VIEW.labels == ("erk-objective",)
        assert OBJECTIVES_VIEW.key_hint == "3"

    def test_runs_view_config(self) -> None:
        """RUNS_VIEW has correct configuration."""
        assert RUNS_VIEW.mode == ViewMode.RUNS
        assert RUNS_VIEW.display_name == "Runs"
        assert RUNS_VIEW.labels == ()
        assert RUNS_VIEW.key_hint == "4"

    def test_view_configs_tuple_has_all_views(self) -> None:
        """VIEW_CONFIGS contains all four view configs."""
        assert len(VIEW_CONFIGS) == 4
        modes = {c.mode for c in VIEW_CONFIGS}
        assert modes == {ViewMode.PLANS, ViewMode.LEARN, ViewMode.OBJECTIVES, ViewMode.RUNS}

    def test_view_config_is_frozen(self) -> None:
        """ViewConfig is a frozen dataclass."""
        config = ViewConfig(
            mode=ViewMode.PLANS,
            display_name="Test",
            labels=("test",),
            key_hint="x",
            exclude_labels=(),
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
        assert config.display_name == "PRs"

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

    def test_returns_runs_config(self) -> None:
        """get_view_config returns RUNS_VIEW for ViewMode.RUNS."""
        config = get_view_config(ViewMode.RUNS)
        assert config.mode == ViewMode.RUNS
        assert config.display_name == "Runs"


class TestGetNextViewMode:
    """Tests for get_next_view_mode function."""

    def test_plans_to_learn(self) -> None:
        """Next after PLANS is LEARN."""
        assert get_next_view_mode(ViewMode.PLANS) == ViewMode.LEARN

    def test_learn_to_objectives(self) -> None:
        """Next after LEARN is OBJECTIVES."""
        assert get_next_view_mode(ViewMode.LEARN) == ViewMode.OBJECTIVES

    def test_objectives_to_runs(self) -> None:
        """Next after OBJECTIVES is RUNS."""
        assert get_next_view_mode(ViewMode.OBJECTIVES) == ViewMode.RUNS

    def test_runs_wraps_to_plans(self) -> None:
        """Next after RUNS wraps to PLANS."""
        assert get_next_view_mode(ViewMode.RUNS) == ViewMode.PLANS


class TestGetPreviousViewMode:
    """Tests for get_previous_view_mode function."""

    def test_plans_wraps_to_runs(self) -> None:
        """Previous before PLANS wraps to RUNS."""
        assert get_previous_view_mode(ViewMode.PLANS) == ViewMode.RUNS

    def test_learn_to_plans(self) -> None:
        """Previous before LEARN is PLANS."""
        assert get_previous_view_mode(ViewMode.LEARN) == ViewMode.PLANS

    def test_objectives_to_learn(self) -> None:
        """Previous before OBJECTIVES is LEARN."""
        assert get_previous_view_mode(ViewMode.OBJECTIVES) == ViewMode.LEARN

    def test_runs_to_objectives(self) -> None:
        """Previous before RUNS is OBJECTIVES."""
        assert get_previous_view_mode(ViewMode.RUNS) == ViewMode.OBJECTIVES
