"""Tests for check_statusline_configured health check.

These tests verify the health check correctly reports statusline configuration
status from global Claude settings via FakeClaudeInstallation.
"""

import pytest

from erk.core.claude_settings import get_erk_statusline_command
from erk.core.health_checks import check_statusline_configured
from erk_shared.extraction.claude_installation import FakeClaudeInstallation


def test_returns_info_when_no_settings_file() -> None:
    """Test returns info-level result when no global settings file exists."""
    installation = FakeClaudeInstallation(
        projects=None,
        plans=None,
        settings=None,
        local_settings=None,
        session_slugs=None,
        session_planning_agents=None,
        plans_dir_path=None,
    )

    result = check_statusline_configured(installation)

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is True
    assert "not configured" in result.message.lower()
    assert result.details is not None
    assert "erk init --statusline" in result.details


def test_returns_configured_when_erk_statusline_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test returns configured status when erk-statusline is set."""
    monkeypatch.delenv("ERK_STATUSLINE_COMMAND", raising=False)

    installation = FakeClaudeInstallation(
        projects=None,
        plans=None,
        settings={
            "statusLine": {
                "type": "command",
                "command": get_erk_statusline_command(),
            }
        },
        local_settings=None,
        session_slugs=None,
        session_planning_agents=None,
        plans_dir_path=None,
    )

    result = check_statusline_configured(installation)

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is False  # Not info - it's a success
    assert "erk-statusline configured" in result.message
    assert result.details is None


def test_returns_info_when_different_statusline() -> None:
    """Test returns info-level result when different statusline is configured."""
    installation = FakeClaudeInstallation(
        projects=None,
        plans=None,
        settings={
            "statusLine": {
                "type": "command",
                "command": "uvx other-statusline",
            }
        },
        local_settings=None,
        session_slugs=None,
        session_planning_agents=None,
        plans_dir_path=None,
    )

    result = check_statusline_configured(installation)

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is True
    # Shows existing statusline command
    assert "uvx other-statusline" in result.message
    assert "Different statusline configured" in result.message
    assert result.details is not None
    assert "erk init --statusline" in result.details


def test_returns_info_when_no_statusline_in_settings() -> None:
    """Test returns info-level result when settings exist but no statusLine."""
    installation = FakeClaudeInstallation(
        projects=None,
        plans=None,
        settings={"permissions": {"allow": []}},
        local_settings=None,
        session_slugs=None,
        session_planning_agents=None,
        plans_dir_path=None,
    )

    result = check_statusline_configured(installation)

    assert result.passed is True
    assert result.name == "statusline"
    assert result.info is True
    assert "not configured" in result.message.lower()
    assert result.details is not None
    assert "erk init --statusline" in result.details
