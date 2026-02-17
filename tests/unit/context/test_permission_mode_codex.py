"""Tests for permission_mode_to_codex mapping."""

from __future__ import annotations

import pytest

from erk_shared.context.types import permission_mode_to_codex


class TestPermissionModeToCodexExec:
    """Tests for exec mode permission mapping."""

    def test_safe_returns_sandbox_read_only(self) -> None:
        result = permission_mode_to_codex("safe", mode="exec")
        assert result == ["--sandbox", "read-only"]

    def test_edits_returns_full_auto(self) -> None:
        result = permission_mode_to_codex("edits", mode="exec")
        assert result == ["--full-auto"]

    def test_plan_returns_sandbox_read_only(self) -> None:
        result = permission_mode_to_codex("plan", mode="exec")
        assert result == ["--sandbox", "read-only"]

    def test_dangerous_returns_yolo(self) -> None:
        result = permission_mode_to_codex("dangerous", mode="exec")
        assert result == ["--yolo"]


class TestPermissionModeToCodexTui:
    """Tests for TUI mode permission mapping."""

    def test_safe_returns_sandbox_read_only_with_untrusted(self) -> None:
        result = permission_mode_to_codex("safe", mode="tui")
        assert result == ["--sandbox", "read-only", "-a", "untrusted"]

    def test_edits_returns_workspace_write_with_on_request(self) -> None:
        result = permission_mode_to_codex("edits", mode="tui")
        assert result == ["--sandbox", "workspace-write", "-a", "on-request"]

    def test_plan_returns_sandbox_read_only_with_never(self) -> None:
        result = permission_mode_to_codex("plan", mode="tui")
        assert result == ["--sandbox", "read-only", "-a", "never"]

    def test_dangerous_returns_yolo(self) -> None:
        result = permission_mode_to_codex("dangerous", mode="tui")
        assert result == ["--yolo"]


def test_invalid_mode_raises_value_error() -> None:
    """Unknown permission_mode raises ValueError."""
    with pytest.raises(ValueError, match="Unknown permission_mode"):
        permission_mode_to_codex("nonexistent", mode="exec")  # type: ignore[arg-type]
