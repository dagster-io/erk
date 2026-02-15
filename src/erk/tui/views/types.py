"""View mode types for TUI dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ViewMode(Enum):
    """Available view modes for the dashboard."""

    PLANS = auto()
    LEARN = auto()
    OBJECTIVES = auto()


@dataclass(frozen=True)
class ViewConfig:
    """Configuration for a specific view mode.

    Attributes:
        mode: The view mode this config describes
        display_name: Human-readable name for the view
        labels: GitHub labels to use when fetching data
        key_hint: Key binding hint (e.g., "1", "2", "3")
    """

    mode: ViewMode
    display_name: str
    labels: tuple[str, ...]
    key_hint: str


PLANS_VIEW = ViewConfig(
    mode=ViewMode.PLANS,
    display_name="Plans",
    labels=("erk-plan",),
    key_hint="1",
)

LEARN_VIEW = ViewConfig(
    mode=ViewMode.LEARN,
    display_name="Learn",
    labels=("erk-plan",),
    key_hint="2",
)

OBJECTIVES_VIEW = ViewConfig(
    mode=ViewMode.OBJECTIVES,
    display_name="Objectives",
    labels=("erk-objective",),
    key_hint="3",
)

VIEW_CONFIGS: tuple[ViewConfig, ...] = (PLANS_VIEW, LEARN_VIEW, OBJECTIVES_VIEW)


def get_view_config(mode: ViewMode) -> ViewConfig:
    """Look up the ViewConfig for a given mode.

    Args:
        mode: The view mode to look up

    Returns:
        The corresponding ViewConfig
    """
    for config in VIEW_CONFIGS:
        if config.mode == mode:
            return config
    # This should never happen since ViewMode is an enum
    # and all modes have configs, but satisfy the type checker
    return PLANS_VIEW
