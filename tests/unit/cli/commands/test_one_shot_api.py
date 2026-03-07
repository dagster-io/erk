"""Tests for API-only one-shot operations."""

import base64
import json
from unittest.mock import patch

from erk.cli.commands.one_shot_api import (
    api_commit_file,
    api_create_branch,
    api_get_branch_sha,
    api_get_default_branch,
    gh_env_for_nwo,
)


def test_gh_env_for_nwo_sets_gh_repo() -> None:
    """Test that gh_env_for_nwo sets GH_REPO in environment."""
    env = gh_env_for_nwo("owner/repo")
    assert env["GH_REPO"] == "owner/repo"


def test_api_get_default_branch() -> None:
    """Test correct gh api command construction for getting default branch."""
    with patch("erk.cli.commands.one_shot_api.run_subprocess_with_context") as mock_run:
        mock_run.return_value.stdout = "main\n"
        result = api_get_default_branch("owner/repo")

    assert result == "main"
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["cmd"] == [
        "gh",
        "api",
        "repos/owner/repo",
        "--jq",
        ".default_branch",
    ]
    assert call_kwargs["operation_context"] == "get default branch for owner/repo"


def test_api_get_branch_sha() -> None:
    """Test correct gh api command construction for getting branch SHA."""
    expected_sha = "abc123def456"
    with patch("erk.cli.commands.one_shot_api.run_subprocess_with_context") as mock_run:
        mock_run.return_value.stdout = f"{expected_sha}\n"
        result = api_get_branch_sha("owner/repo", "main")

    assert result == expected_sha
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["cmd"] == [
        "gh",
        "api",
        "repos/owner/repo/git/ref/heads/main",
        "--jq",
        ".object.sha",
    ]


def test_api_create_branch() -> None:
    """Test correct gh api command construction for creating a branch."""
    with patch("erk.cli.commands.one_shot_api.run_subprocess_with_context") as mock_run:
        api_create_branch("owner/repo", "plnd/my-branch", "abc123")

    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["cmd"] == [
        "gh",
        "api",
        "repos/owner/repo/git/refs",
        "-X",
        "POST",
        "--input",
        "-",
    ]
    payload = json.loads(call_kwargs["input"])
    assert payload["ref"] == "refs/heads/plnd/my-branch"
    assert payload["sha"] == "abc123"


def test_api_commit_file() -> None:
    """Test correct gh api command construction for committing a file."""
    content = "fix the import in config.py\n"
    with patch("erk.cli.commands.one_shot_api.run_subprocess_with_context") as mock_run:
        api_commit_file(
            "owner/repo",
            branch="plnd/my-branch",
            path=".erk/impl-context/prompt.md",
            content=content,
            message="One-shot: fix the import in config.py",
        )

    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs["cmd"] == [
        "gh",
        "api",
        "repos/owner/repo/contents/.erk/impl-context/prompt.md",
        "-X",
        "PUT",
        "--input",
        "-",
    ]
    payload = json.loads(call_kwargs["input"])
    assert payload["message"] == "One-shot: fix the import in config.py"
    assert payload["branch"] == "plnd/my-branch"
    # Verify base64 encoding roundtrip
    decoded = base64.b64decode(payload["content"]).decode("utf-8")
    assert decoded == content
