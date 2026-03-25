"""Tests for FakeCmux implementation."""

import pytest

from tests.fakes.gateway.cmux import FakeCmux


def test_create_workspace_returns_configured_ref() -> None:
    """create_workspace returns the workspace_ref passed to constructor."""
    cmux = FakeCmux(workspace_ref="workspace-12345")

    result = cmux.create_workspace(command="echo hello")

    assert result == "workspace-12345"


def test_create_workspace_tracks_calls() -> None:
    """create_workspace calls are tracked in create_calls property."""
    cmux = FakeCmux(workspace_ref="ws-1")
    cmux.create_workspace(command="cmd1")
    cmux.create_workspace(command="cmd2")

    assert len(cmux.create_calls) == 2
    assert cmux.create_calls[0].command == "cmd1"
    assert cmux.create_calls[1].command == "cmd2"


def test_create_workspace_error_injection() -> None:
    """create_error causes create_workspace to raise RuntimeError."""
    cmux = FakeCmux(workspace_ref="unused", create_error="workspace already exists")

    with pytest.raises(RuntimeError, match="workspace already exists"):
        cmux.create_workspace(command="cmd")


def test_create_workspace_error_still_tracks_call() -> None:
    """create_workspace tracks the call even when raising an error."""
    cmux = FakeCmux(workspace_ref="unused", create_error="fail")

    with pytest.raises(RuntimeError):
        cmux.create_workspace(command="my-cmd")

    assert len(cmux.create_calls) == 1
    assert cmux.create_calls[0].command == "my-cmd"


def test_rename_workspace_tracks_calls() -> None:
    """rename_workspace calls are tracked in rename_calls property."""
    cmux = FakeCmux(workspace_ref="ws-1")
    cmux.rename_workspace(workspace_ref="ws-1", new_name="my-branch")

    assert len(cmux.rename_calls) == 1
    assert cmux.rename_calls[0].workspace_ref == "ws-1"
    assert cmux.rename_calls[0].new_name == "my-branch"


def test_create_calls_returns_defensive_copy() -> None:
    """create_calls returns a copy to prevent external mutation."""
    cmux = FakeCmux(workspace_ref="ws-1")
    cmux.create_workspace(command="cmd")

    returned = cmux.create_calls
    returned.clear()

    assert len(cmux.create_calls) == 1


def test_rename_calls_returns_defensive_copy() -> None:
    """rename_calls returns a copy to prevent external mutation."""
    cmux = FakeCmux(workspace_ref="ws-1")
    cmux.rename_workspace(workspace_ref="ws-1", new_name="name")

    returned = cmux.rename_calls
    returned.clear()

    assert len(cmux.rename_calls) == 1


def test_empty_initially() -> None:
    """create_calls and rename_calls are empty initially."""
    cmux = FakeCmux(workspace_ref="ws-1")

    assert cmux.create_calls == []
    assert cmux.rename_calls == []
