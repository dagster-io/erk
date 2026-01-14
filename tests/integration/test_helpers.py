"""Shared test helpers for integration tests."""

import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from pytest import MonkeyPatch


@contextmanager
def mock_subprocess_run(
    monkeypatch: MonkeyPatch,
    mock_fn: Callable[[list[str], Any], subprocess.CompletedProcess],
):
    """Context manager to mock subprocess.run with pytest monkeypatch.

    This helper provides a clean way to mock subprocess calls in integration tests,
    automatically handling cleanup via monkeypatch.

    Args:
        monkeypatch: The pytest monkeypatch fixture
        mock_fn: Function that receives (cmd: list[str], **kwargs) and returns
                 CompletedProcess. This function should assert on command structure
                 and return appropriate mock responses.

    Usage:
        def test_something(monkeypatch: MonkeyPatch) -> None:
            def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
                assert cmd == ["gh", "pr", "view", "123"]
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout="result", stderr=""
                )

            with mock_subprocess_run(monkeypatch, mock_run):
                # Test code that calls subprocess.run
                ops = RealGitHub.for_test()
                result = ops.some_method()
    """
    monkeypatch.setattr("subprocess.run", mock_fn)
    yield
