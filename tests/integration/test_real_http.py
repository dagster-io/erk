"""Tests for HTTP client auth with mocked subprocess execution.

These tests verify that fetch_github_token correctly calls gh CLI and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import subprocess

import pytest
from pytest import MonkeyPatch

from erk_shared.gateway.http.auth import fetch_github_token
from tests.integration.test_helpers import mock_subprocess_run


def test_fetch_github_token_success(monkeypatch: MonkeyPatch) -> None:
    """Test fetching GitHub token successfully."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == ["gh", "auth", "token", "--hostname", "github.com"]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="ghp_test_token_123\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        token = fetch_github_token()
        assert token == "ghp_test_token_123"


def test_fetch_github_token_custom_hostname(monkeypatch: MonkeyPatch) -> None:
    """Test fetching token for custom hostname."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        assert cmd == ["gh", "auth", "token", "--hostname", "github.example.com"]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="ghe_enterprise_token\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        token = fetch_github_token(hostname="github.example.com")
        assert token == "ghe_enterprise_token"


def test_fetch_github_token_empty_raises(monkeypatch: MonkeyPatch) -> None:
    """Test that empty token raises ValueError."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="\n",  # Empty after strip
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        with pytest.raises(ValueError, match="Empty token"):
            fetch_github_token()


def test_fetch_github_token_strips_whitespace(monkeypatch: MonkeyPatch) -> None:
    """Test that token whitespace is stripped."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="  ghp_token_with_spaces  \n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        token = fetch_github_token()
        assert token == "ghp_token_with_spaces"
