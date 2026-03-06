"""Tests for ErkBashPermissionsCapability.

Tests install, is_installed, and artifact declarations for bash permissions.
"""

import json
from pathlib import Path

from erk.capabilities.erk_bash_permissions import ErkBashPermissionsCapability
from erk.core.capabilities.registry import get_capability

# =============================================================================
# Tests for Permission Capabilities
# =============================================================================


def test_erk_bash_permissions_capability_properties() -> None:
    """Test ErkBashPermissionsCapability has correct properties."""
    cap = ErkBashPermissionsCapability()
    assert cap.name == "erk-bash-permissions"
    assert "Bash(erk:*)" in cap.description
    assert "settings.json" in cap.installation_check_description


def test_erk_bash_permissions_artifacts() -> None:
    """Test ErkBashPermissionsCapability lists correct artifacts."""
    cap = ErkBashPermissionsCapability()
    artifacts = cap.artifacts

    # settings.json is shared by multiple capabilities, so not listed
    assert len(artifacts) == 0


def test_erk_bash_permissions_is_installed_false_when_no_settings(tmp_path: Path) -> None:
    """Test is_installed returns False when settings.json doesn't exist."""
    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_erk_bash_permissions_is_installed_false_when_not_in_allow(tmp_path: Path) -> None:
    """Test is_installed returns False when permission not in allow list."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"permissions": {"allow": []}}), encoding="utf-8")

    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_erk_bash_permissions_is_installed_true_when_present(tmp_path: Path) -> None:
    """Test is_installed returns True when permission is in allow list."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(erk:*)"]}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_erk_bash_permissions_install_creates_settings(tmp_path: Path) -> None:
    """Test install creates settings.json if it doesn't exist."""
    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert ".claude/settings.json" in result.created_files

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "Bash(erk:*)" in settings["permissions"]["allow"]


def test_erk_bash_permissions_install_adds_to_existing(tmp_path: Path) -> None:
    """Test install adds permission to existing settings.json."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Read(/tmp/*)"]}, "hooks": {}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert "Added" in result.message

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "Bash(erk:*)" in settings["permissions"]["allow"]
    assert "Read(/tmp/*)" in settings["permissions"]["allow"]
    assert "hooks" in settings  # Preserves existing keys


def test_erk_bash_permissions_install_idempotent(tmp_path: Path) -> None:
    """Test install is idempotent when permission already exists."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(erk:*)"]}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert "already" in result.message

    # Verify it wasn't duplicated
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["permissions"]["allow"].count("Bash(erk:*)") == 1


def test_permission_capability_registered() -> None:
    """Test that permission capability is registered."""
    cap = get_capability("erk-bash-permissions")
    assert cap is not None
    assert cap.name == "erk-bash-permissions"
