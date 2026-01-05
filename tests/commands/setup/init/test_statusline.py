"""Tests for statusline setup during init.

Mock Usage Policy:
------------------
This file uses minimal mocking for external boundaries:

1. user_confirm mocking:
   - LEGITIMATE: Testing CLI's response to user confirmation
   - The prompt logic is a boundary (TTY interaction)
   - Here we test that statusline setup handles yes/no responses appropriately

2. perform_statusline_setup mocking in CLI test:
   - LEGITIMATE: Testing that CLI flag correctly invokes the function
   - The function is tested directly in other tests

NOTE: These tests use perform_statusline_setup() directly with path injection
to avoid mocking HOME environment variable.
"""

import json
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.init import perform_statusline_setup
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_statusline_setup_configures_empty_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup configures statusline in empty settings.json."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # Create settings.json
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")

    # Mock user_confirm to return True (confirm write)
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=True):
        perform_statusline_setup(settings_path=settings_path)

    # Verify settings were written
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "statusLine" in updated_settings
    assert updated_settings["statusLine"]["type"] == "command"
    assert "erk-statusline" in updated_settings["statusLine"]["command"]


def test_statusline_setup_creates_settings_if_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup creates settings.json if it doesn't exist."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # No settings.json file
    settings_path = tmp_path / ".claude" / "settings.json"

    # Mock user_confirm to return True (confirm write)
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=True):
        perform_statusline_setup(settings_path=settings_path)

    # Verify file was created
    assert settings_path.exists()
    created_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "erk-statusline" in created_settings["statusLine"]["command"]


def test_statusline_setup_skips_when_already_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup skips when erk-statusline is already configured."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # Create settings.json with erk-statusline already configured
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    existing_settings = {
        "statusLine": {
            "type": "command",
            "command": "uvx erk-statusline",
        }
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    # Run setup with injected path (no confirm needed - skips without prompting)
    perform_statusline_setup(settings_path=settings_path)

    # File should not have been modified - content should be same
    unchanged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert unchanged_settings == existing_settings


def test_statusline_setup_prompts_for_different_command(tmp_path: Path) -> None:
    """Test perform_statusline_setup prompts when different statusline is configured."""
    # Create settings.json with different statusline
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    existing_settings = {
        "statusLine": {
            "type": "command",
            "command": "other-statusline",
        }
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    # Mock user_confirm to return False (decline replacement)
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=False):
        perform_statusline_setup(settings_path=settings_path)

    # Verify settings were NOT changed
    unchanged_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert unchanged_settings["statusLine"]["command"] == "other-statusline"


def test_statusline_setup_replaces_when_confirmed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test perform_statusline_setup replaces existing statusline when user confirms."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)
    # Create settings.json with different statusline
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)
    settings_path = claude_dir / "settings.json"
    existing_settings = {
        "statusLine": {
            "type": "command",
            "command": "other-statusline",
        }
    }
    settings_path.write_text(json.dumps(existing_settings), encoding="utf-8")

    # Mock user_confirm to return True for both prompts
    with mock.patch("erk.cli.commands.init.user_confirm", return_value=True):
        perform_statusline_setup(settings_path=settings_path)

    # Verify settings were updated
    updated_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "erk-statusline" in updated_settings["statusLine"]["command"]


def test_init_statusline_flag_recognized() -> None:
    """Test that --statusline flag is recognized and invokes statusline setup.

    This is a minimal CLI integration test - detailed behavior is tested
    via perform_statusline_setup() unit tests above.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        erk_root = env.cwd / "erks"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=True)
        erk_installation = FakeErkInstallation(config=global_config)

        test_ctx = env.build_context(
            git=git_ops,
            erk_installation=erk_installation,
            global_config=global_config,
        )

        # Mock the function to avoid HOME dependency in CLI test
        with mock.patch("erk.cli.commands.init.perform_statusline_setup") as mock_setup:
            result = runner.invoke(cli, ["init", "--statusline"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify the function was called with settings_path=None (uses default)
        mock_setup.assert_called_once_with(settings_path=None)

        # Verify no config.toml was created (other init steps skipped)
        config_path = env.cwd / ".erk" / "config.toml"
        assert not config_path.exists()
