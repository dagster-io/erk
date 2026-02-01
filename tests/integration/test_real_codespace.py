"""Tests for RealCodespace with mocked subprocess execution.

These tests verify that RealCodespace correctly constructs CLI commands.
We use pytest monkeypatch to mock subprocess calls and capture the commands.
"""

import subprocess

import pytest
from pytest import MonkeyPatch

from erk_shared.gateway.codespace.real import RealCodespace
from tests.integration.test_helpers import mock_subprocess_run


def test_start_codespace_uses_rest_api(monkeypatch: MonkeyPatch) -> None:
    """start_codespace() uses GitHub REST API, not gh codespace start."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        codespace.start_codespace("my-codespace-abc123")

    assert len(called_with) == 1
    cmd = called_with[0]
    assert cmd == [
        "gh",
        "api",
        "--method",
        "POST",
        "/user/codespaces/my-codespace-abc123/start",
    ]


def test_start_codespace_propagates_failure(monkeypatch: MonkeyPatch) -> None:
    """start_codespace() raises RuntimeError on subprocess failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="codespace not found",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        with pytest.raises(RuntimeError):
            codespace.start_codespace("nonexistent")


def test_run_ssh_command_uses_codespace_ssh(monkeypatch: MonkeyPatch) -> None:
    """run_ssh_command() uses gh codespace ssh with correct flags."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        exit_code = codespace.run_ssh_command("my-cs", "echo hello")

    assert exit_code == 0
    assert len(called_with) == 1
    cmd = called_with[0]
    assert cmd == [
        "gh",
        "codespace",
        "ssh",
        "-c",
        "my-cs",
        "--",
        "echo hello",
    ]
