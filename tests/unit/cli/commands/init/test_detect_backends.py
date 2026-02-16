"""Unit tests for detect_installed_backends."""

from erk.cli.commands.init.main import detect_installed_backends
from tests.fakes.shell import FakeShell


def test_detect_both_backends() -> None:
    """Both claude and codex installed returns both."""
    shell = FakeShell(installed_tools={"claude": "/usr/bin/claude", "codex": "/usr/bin/codex"})
    result = detect_installed_backends(shell)
    assert result == ["claude", "codex"]


def test_detect_only_claude() -> None:
    """Only claude installed returns just claude."""
    shell = FakeShell(installed_tools={"claude": "/usr/bin/claude"})
    result = detect_installed_backends(shell)
    assert result == ["claude"]


def test_detect_only_codex() -> None:
    """Only codex installed returns just codex."""
    shell = FakeShell(installed_tools={"codex": "/usr/bin/codex"})
    result = detect_installed_backends(shell)
    assert result == ["codex"]


def test_detect_no_backends() -> None:
    """No backends installed returns empty list."""
    shell = FakeShell(installed_tools={})
    result = detect_installed_backends(shell)
    assert result == []
