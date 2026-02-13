"""Tests for build_claude_subprocess_env utility."""

import os
from unittest.mock import patch

from erk_shared.subprocess_utils import build_claude_subprocess_env


def test_build_claude_subprocess_env_strips_claudecode() -> None:
    """CLAUDECODE is removed from the returned environment."""
    with patch.dict(os.environ, {"CLAUDECODE": "1", "PATH": "/usr/bin"}):
        env = build_claude_subprocess_env()

    assert "CLAUDECODE" not in env
    assert env["PATH"] == "/usr/bin"


def test_build_claude_subprocess_env_works_without_claudecode() -> None:
    """Works when CLAUDECODE is not in environment."""
    with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True):
        env = build_claude_subprocess_env()

    assert "CLAUDECODE" not in env
    assert env["PATH"] == "/usr/bin"


def test_build_claude_subprocess_env_does_not_modify_os_environ() -> None:
    """Returns a copy, does not modify os.environ."""
    with patch.dict(os.environ, {"CLAUDECODE": "1"}):
        build_claude_subprocess_env()
        assert os.environ.get("CLAUDECODE") == "1"
