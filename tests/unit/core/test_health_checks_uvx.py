"""Tests for uvx invocation health check."""

from unittest.mock import patch

from erk.core.health_checks import check_uvx_invocation


def test_check_passes_when_not_uvx() -> None:
    """Check passes without warning when not running via uvx."""
    with patch("erk.cli.uvx_detection.is_running_via_uvx", return_value=False):
        result = check_uvx_invocation()

    assert result.passed is True
    assert result.warning is False
    assert result.name == "uvx-invocation"
    assert "Not running via uvx" in result.message


def test_check_warns_when_via_uvx() -> None:
    """Check passes but warns when running via uvx."""
    with patch("erk.cli.uvx_detection.is_running_via_uvx", return_value=True):
        result = check_uvx_invocation()

    assert result.passed is True
    assert result.warning is True
    assert result.name == "uvx-invocation"
    assert "uvx" in result.message.lower()
    assert "shell integration unavailable" in result.message.lower()


def test_check_provides_remediation_details() -> None:
    """Check provides instructions for fixing when running via uvx."""
    with patch("erk.cli.uvx_detection.is_running_via_uvx", return_value=True):
        result = check_uvx_invocation()

    assert result.details is not None
    assert "uv tool install" in result.details
    assert "erk init --shell" in result.details
