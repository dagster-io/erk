"""Tests for RealCodespace with mocked subprocess execution.

These tests verify that RealCodespace correctly constructs CLI commands.
We use pytest monkeypatch to mock subprocess calls and capture the commands.
"""

import json
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


def test_get_repo_id_calls_gh_api(monkeypatch: MonkeyPatch) -> None:
    """get_repo_id() calls gh api repos/{owner_repo} with --jq .id."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="12345\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        repo_id = codespace.get_repo_id("owner/repo")

    assert repo_id == 12345
    assert len(called_with) == 1
    cmd = called_with[0]
    assert cmd == ["gh", "api", "repos/owner/repo", "--jq", ".id"]


def test_get_repo_id_propagates_failure(monkeypatch: MonkeyPatch) -> None:
    """get_repo_id() raises RuntimeError on subprocess failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=cmd,
            stderr="Not Found",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        with pytest.raises(RuntimeError):
            codespace.get_repo_id("owner/nonexistent")


def test_create_codespace_calls_gh_api(monkeypatch: MonkeyPatch) -> None:
    """create_codespace() POSTs to /user/codespaces with correct fields."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"name": "cs-new-abc123"}),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        name = codespace.create_codespace(
            repo_id=12345,
            machine="standardLinux32gb",
            display_name="my-codespace",
            branch=None,
        )

    assert name == "cs-new-abc123"
    assert len(called_with) == 1
    cmd = called_with[0]
    assert cmd == [
        "gh",
        "api",
        "--method",
        "POST",
        "/user/codespaces",
        "-F",
        "repository_id=12345",
        "-f",
        "machine=standardLinux32gb",
        "-f",
        "display_name=my-codespace",
        "-f",
        "devcontainer_path=.devcontainer/devcontainer.json",
    ]


def test_create_codespace_includes_branch_when_provided(monkeypatch: MonkeyPatch) -> None:
    """create_codespace() includes -f ref={branch} when branch is not None."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"name": "cs-branch-abc"}),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        name = codespace.create_codespace(
            repo_id=12345,
            machine="standardLinux32gb",
            display_name="my-codespace",
            branch="feature-branch",
        )

    assert name == "cs-branch-abc"
    assert len(called_with) == 1
    cmd = called_with[0]
    assert cmd == [
        "gh",
        "api",
        "--method",
        "POST",
        "/user/codespaces",
        "-F",
        "repository_id=12345",
        "-f",
        "machine=standardLinux32gb",
        "-f",
        "display_name=my-codespace",
        "-f",
        "devcontainer_path=.devcontainer/devcontainer.json",
        "-f",
        "ref=feature-branch",
    ]


def test_create_codespace_raises_on_missing_name(monkeypatch: MonkeyPatch) -> None:
    """create_codespace() raises RuntimeError when response lacks 'name' field."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"id": 999}),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        codespace = RealCodespace()
        with pytest.raises(RuntimeError, match="missing 'name' field"):
            codespace.create_codespace(
                repo_id=12345,
                machine="standardLinux32gb",
                display_name="my-codespace",
                branch=None,
            )
