"""Tests for FilterState type and progressive escape behavior."""

from erk.tui.filtering.types import FilterMode, FilterState


def test_initial_state_is_inactive() -> None:
    """Initial state is inactive with empty query."""
    state = FilterState.initial()
    assert state.mode == FilterMode.INACTIVE
    assert state.query == ""


def test_activate_transitions_to_active() -> None:
    """Activate transitions from inactive to active."""
    state = FilterState.initial()
    active = state.activate()
    assert active.mode == FilterMode.ACTIVE
    assert active.query == ""


def test_with_query_updates_query() -> None:
    """with_query updates the query text."""
    state = FilterState.initial().activate()
    updated = state.with_query("test")
    assert updated.query == "test"
    assert updated.mode == FilterMode.ACTIVE


def test_progressive_escape_clears_text_first() -> None:
    """Progressive escape clears text first, staying in active mode."""
    state = FilterState(mode=FilterMode.ACTIVE, query="test")
    escaped = state.handle_escape()
    assert escaped.mode == FilterMode.ACTIVE
    assert escaped.query == ""


def test_progressive_escape_deactivates_when_empty() -> None:
    """Progressive escape deactivates when query is empty."""
    state = FilterState(mode=FilterMode.ACTIVE, query="")
    escaped = state.handle_escape()
    assert escaped.mode == FilterMode.INACTIVE
    assert escaped.query == ""


def test_double_escape_fully_exits_filter_mode() -> None:
    """Two escapes fully exit filter mode: clear text, then deactivate."""
    state = FilterState(mode=FilterMode.ACTIVE, query="test")
    first = state.handle_escape()
    assert first.mode == FilterMode.ACTIVE
    assert first.query == ""

    second = first.handle_escape()
    assert second.mode == FilterMode.INACTIVE
    assert second.query == ""
