"""Tests for permission_mode_to_codex_exec and permission_mode_to_codex_tui mapping."""

from __future__ import annotations

import pytest

from erk_shared.context.types import permission_mode_to_codex_exec, permission_mode_to_codex_tui


class TestPermissionModeToCodexExec:
    """Tests for exec mode permission mapping."""

    def test_safe_returns_sandbox_read_only(self) -> None:
        result = permission_mode_to_codex_exec("safe")
        assert result == ["--sandbox", "read-only"]

    def test_edits_returns_full_auto(self) -> None:
        result = permission_mode_to_codex_exec("edits")
        assert result == ["--full-auto"]

    def test_plan_returns_sandbox_read_only(self) -> None:
        result = permission_mode_to_codex_exec("plan")
        assert result == ["--sandbox", "read-only"]

    def test_dangerous_returns_yolo(self) -> None:
        result = permission_mode_to_codex_exec("dangerous")
        assert result == ["--yolo"]


class TestPermissionModeToCodexTui:
    """Tests for TUI mode permission mapping."""

    def test_safe_returns_sandbox_read_only_with_untrusted(self) -> None:
        result = permission_mode_to_codex_tui("safe")
        assert result == ["--sandbox", "read-only", "-a", "untrusted"]

    def test_edits_returns_workspace_write_with_on_request(self) -> None:
        result = permission_mode_to_codex_tui("edits")
        assert result == ["--sandbox", "workspace-write", "-a", "on-request"]

    def test_plan_returns_sandbox_read_only_with_never(self) -> None:
        result = permission_mode_to_codex_tui("plan")
        assert result == ["--sandbox", "read-only", "-a", "never"]

    def test_dangerous_returns_yolo(self) -> None:
        result = permission_mode_to_codex_tui("dangerous")
        assert result == ["--yolo"]


def test_invalid_mode_raises_value_error() -> None:
    """Unknown permission_mode raises ValueError."""
    with pytest.raises(ValueError, match="Unknown permission_mode"):
        permission_mode_to_codex_exec("nonexistent")  # type: ignore[arg-type]
