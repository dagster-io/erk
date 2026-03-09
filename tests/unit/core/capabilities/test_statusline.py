"""Tests for StatuslineCapability.

Tests install, is_installed, and artifact declarations for statusline.
"""

from erk.capabilities.statusline import StatuslineCapability
from erk.core.capabilities.registry import get_capability
from erk_shared.fakes.claude_installation import FakeClaudeInstallation

# =============================================================================
# Tests for StatuslineCapability
# =============================================================================


def test_statusline_capability_properties() -> None:
    """Test StatuslineCapability has correct properties."""
    cap = StatuslineCapability(claude_installation=None)
    assert cap.name == "statusline"
    assert cap.scope == "user"
    assert "status line" in cap.description.lower()
    assert "statusLine" in cap.installation_check_description


def test_statusline_capability_artifacts() -> None:
    """Test StatuslineCapability lists correct artifacts."""
    cap = StatuslineCapability(claude_installation=None)
    artifacts = cap.artifacts

    # settings.json is shared by multiple capabilities, so not listed
    assert len(artifacts) == 0


def test_statusline_is_installed_false_when_not_configured() -> None:
    """Test is_installed returns False when statusline not configured."""
    fake_claude = FakeClaudeInstallation.for_test(settings={})
    cap = StatuslineCapability(claude_installation=fake_claude)

    # User-level capability ignores repo_root
    assert cap.is_installed(None, backend="claude") is False


def test_statusline_is_installed_true_when_configured() -> None:
    """Test is_installed returns True when erk-statusline is configured."""
    fake_claude = FakeClaudeInstallation.for_test(
        settings={
            "statusLine": {
                "type": "command",
                "command": "uvx erk-statusline",
            }
        }
    )
    cap = StatuslineCapability(claude_installation=fake_claude)

    # User-level capability ignores repo_root
    assert cap.is_installed(None, backend="claude") is True


def test_statusline_install_configures_statusline() -> None:
    """Test install configures erk-statusline in settings."""
    fake_claude = FakeClaudeInstallation.for_test(settings={})
    cap = StatuslineCapability(claude_installation=fake_claude)

    result = cap.install(None, backend="claude")

    assert result.success is True
    assert "Configured" in result.message

    # Verify settings were written
    assert len(fake_claude.settings_writes) == 1
    written_settings = fake_claude.settings_writes[0]
    assert "statusLine" in written_settings
    assert "erk-statusline" in written_settings["statusLine"]["command"]


def test_statusline_install_idempotent() -> None:
    """Test install is idempotent when already configured."""
    fake_claude = FakeClaudeInstallation.for_test(
        settings={
            "statusLine": {
                "type": "command",
                "command": "uvx erk-statusline",
            }
        }
    )
    cap = StatuslineCapability(claude_installation=fake_claude)

    result = cap.install(None, backend="claude")

    assert result.success is True
    assert "already configured" in result.message

    # Verify no writes were made
    assert len(fake_claude.settings_writes) == 0


def test_statusline_capability_registered() -> None:
    """Test that statusline capability is registered."""
    cap = get_capability("statusline")
    assert cap is not None
    assert cap.name == "statusline"
    assert cap.scope == "user"
