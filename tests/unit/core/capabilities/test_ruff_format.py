"""Tests for RuffFormatCapability.

Tests install, is_installed, and artifact declarations for ruff format hook.
"""

import json
from pathlib import Path

from erk.capabilities.ruff_format import RuffFormatCapability
from erk.core.capabilities.registry import get_capability

# =============================================================================
# Tests for RuffFormatCapability
# =============================================================================


def test_ruff_format_capability_properties() -> None:
    """Test RuffFormatCapability has correct properties."""
    cap = RuffFormatCapability()
    assert cap.name == "ruff-format"
    assert cap.scope == "project"
    assert "ruff" in cap.description.lower() or "format" in cap.description.lower()
    assert "PostToolUse" in cap.installation_check_description


def test_ruff_format_capability_artifacts() -> None:
    """Test RuffFormatCapability lists correct artifacts."""
    cap = RuffFormatCapability()
    artifacts = cap.artifacts

    # settings.json is shared by multiple capabilities, so not listed
    assert len(artifacts) == 0


def test_ruff_format_is_installed_false_when_no_settings(tmp_path: Path) -> None:
    """Test is_installed returns False when settings.json doesn't exist."""
    cap = RuffFormatCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_ruff_format_is_installed_false_when_no_hook(tmp_path: Path) -> None:
    """Test is_installed returns False when hook not configured."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({}), encoding="utf-8")

    cap = RuffFormatCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_ruff_format_is_installed_true_when_hook_present(tmp_path: Path) -> None:
    """Test is_installed returns True when ruff format hook is configured."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                '[[ "${file_path}" == *.py ]] && '
                                'uv run ruff format "${file_path}" || true'
                            ),
                        }
                    ],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    cap = RuffFormatCapability()
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_ruff_format_install_creates_settings(tmp_path: Path) -> None:
    """Test install creates settings.json if it doesn't exist."""
    cap = RuffFormatCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert ".claude/settings.json" in result.created_files

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "PostToolUse" in settings["hooks"]


def test_ruff_format_install_adds_to_existing(tmp_path: Path) -> None:
    """Test install adds hook to existing settings.json."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Read(/tmp/*)"]}}),
        encoding="utf-8",
    )

    cap = RuffFormatCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert "Added" in result.message

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "PostToolUse" in settings["hooks"]
    # Preserves existing keys
    assert "permissions" in settings
    assert "Read(/tmp/*)" in settings["permissions"]["allow"]


def test_ruff_format_install_preserves_existing_hooks(tmp_path: Path) -> None:
    """Test install preserves existing hooks when adding ruff format hook."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {"matcher": "*", "hooks": [{"type": "command", "command": "echo test"}]}
            ]
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    cap = RuffFormatCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True

    final_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    # UserPromptSubmit should be preserved
    assert "UserPromptSubmit" in final_settings["hooks"]
    # PostToolUse should be added
    assert "PostToolUse" in final_settings["hooks"]


def test_ruff_format_install_idempotent(tmp_path: Path) -> None:
    """Test install is idempotent when hook already exists."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                '[[ "${file_path}" == *.py ]] && '
                                'uv run ruff format "${file_path}" || true'
                            ),
                        }
                    ],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    cap = RuffFormatCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert "already" in result.message


def test_ruff_format_install_handles_invalid_json(tmp_path: Path) -> None:
    """Test install fails gracefully with invalid JSON."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("invalid json {{{", encoding="utf-8")

    cap = RuffFormatCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is False
    assert "Invalid JSON" in result.message


def test_ruff_format_capability_registered() -> None:
    """Test that ruff-format capability is registered."""
    cap = get_capability("ruff-format")
    assert cap is not None
    assert cap.name == "ruff-format"


def test_ruff_format_is_installed_returns_false_with_none_repo_root() -> None:
    """Test is_installed returns False when repo_root is None."""
    cap = RuffFormatCapability()
    assert cap.is_installed(None, backend="claude") is False


def test_ruff_format_install_fails_with_none_repo_root() -> None:
    """Test install fails when repo_root is None."""
    cap = RuffFormatCapability()
    result = cap.install(None, backend="claude")

    assert result.success is False
    assert "requires repo_root" in result.message


def test_ruff_format_is_not_required() -> None:
    """Test that RuffFormatCapability is not required."""
    cap = RuffFormatCapability()
    assert cap.required is False
