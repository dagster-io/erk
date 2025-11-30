"""Unit tests for Codespace service module.

Tests for:
- Finding existing codespaces
- Creating new codespaces
- Waiting for codespaces to become available
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erk.core.codespace import (
    CodespaceError,
    create_codespace,
    find_existing_codespace,
    get_current_branch,
    get_or_create_codespace,
    get_repo_name,
    wait_for_codespace,
)


class TestGetRepoName:
    """Tests for get_repo_name function."""

    def test_returns_owner_repo_format(self, tmp_path: Path) -> None:
        """get_repo_name returns the repo in owner/repo format."""
        with patch("erk.core.codespace.run_subprocess_with_context") as mock_run:
            mock_run.return_value = MagicMock(stdout="anthropics/erk\n")

            result = get_repo_name(tmp_path)

            assert result == "anthropics/erk"
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "gh",
                "repo",
                "view",
                "--json",
                "nameWithOwner",
                "-q",
                ".nameWithOwner",
            ]

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """get_repo_name strips leading/trailing whitespace."""
        with patch("erk.core.codespace.run_subprocess_with_context") as mock_run:
            mock_run.return_value = MagicMock(stdout="  owner/repo  \n")

            result = get_repo_name(tmp_path)

            assert result == "owner/repo"


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_returns_branch_name(self, tmp_path: Path) -> None:
        """get_current_branch returns the current git branch."""
        with patch("erk.core.codespace.run_subprocess_with_context") as mock_run:
            mock_run.return_value = MagicMock(stdout="feature/my-branch\n")

            result = get_current_branch(tmp_path)

            assert result == "feature/my-branch"
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "rev-parse", "--abbrev-ref", "HEAD"]


class TestFindExistingCodespace:
    """Tests for find_existing_codespace function."""

    def test_returns_matching_codespace_name(self) -> None:
        """find_existing_codespace returns name when matching codespace exists."""
        codespaces = [
            {"name": "cs-abc123", "gitStatus": {"ref": "main"}, "state": "Available"},
            {"name": "cs-def456", "gitStatus": {"ref": "feature"}, "state": "Available"},
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(codespaces))

            result = find_existing_codespace("owner/repo", "feature")

            assert result == "cs-def456"

    def test_returns_none_when_no_matching_branch(self) -> None:
        """find_existing_codespace returns None when no codespace on branch."""
        codespaces = [
            {"name": "cs-abc123", "gitStatus": {"ref": "main"}, "state": "Available"},
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(codespaces))

            result = find_existing_codespace("owner/repo", "feature")

            assert result is None

    def test_returns_none_when_codespace_not_available(self) -> None:
        """find_existing_codespace returns None when codespace not in Available state."""
        codespaces = [
            {"name": "cs-abc123", "gitStatus": {"ref": "feature"}, "state": "Starting"},
        ]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(codespaces))

            result = find_existing_codespace("owner/repo", "feature")

            assert result is None

    def test_returns_none_on_error(self) -> None:
        """find_existing_codespace returns None when gh command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

            result = find_existing_codespace("owner/repo", "feature")

            assert result is None


class TestCreateCodespace:
    """Tests for create_codespace function."""

    def test_creates_codespace_without_devcontainer(self) -> None:
        """create_codespace calls gh codespace create correctly."""
        with patch("erk.core.codespace.run_subprocess_with_context") as mock_run:
            mock_run.return_value = MagicMock(stdout="cs-new123\n")

            result = create_codespace("owner/repo", "feature")

            assert result == "cs-new123"
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "gh",
                "codespace",
                "create",
                "--repo",
                "owner/repo",
                "--branch",
                "feature",
            ]

    def test_creates_codespace_with_devcontainer(self) -> None:
        """create_codespace includes devcontainer path when specified."""
        with patch("erk.core.codespace.run_subprocess_with_context") as mock_run:
            mock_run.return_value = MagicMock(stdout="cs-new123\n")

            result = create_codespace("owner/repo", "feature", ".devcontainer/custom.json")

            assert result == "cs-new123"
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "gh",
                "codespace",
                "create",
                "--repo",
                "owner/repo",
                "--branch",
                "feature",
                "--devcontainer-path",
                ".devcontainer/custom.json",
            ]


class TestWaitForCodespace:
    """Tests for wait_for_codespace function."""

    def test_returns_true_when_immediately_available(self) -> None:
        """wait_for_codespace returns True when codespace is already available."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps({"state": "Available"})
            )

            result = wait_for_codespace("cs-abc123", timeout_seconds=10)

            assert result is True

    def test_returns_true_after_becoming_available(self) -> None:
        """wait_for_codespace returns True when codespace becomes available."""
        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return MagicMock(returncode=0, stdout=json.dumps({"state": "Starting"}))
            return MagicMock(returncode=0, stdout=json.dumps({"state": "Available"}))

        with (
            patch("subprocess.run", side_effect=mock_run_side_effect),
            patch("time.sleep"),
        ):
            result = wait_for_codespace("cs-abc123", timeout_seconds=60)

            assert result is True

    def test_returns_false_on_timeout(self) -> None:
        """wait_for_codespace returns False when timeout expires."""
        with (
            patch("subprocess.run") as mock_run,
            patch("time.sleep"),
            patch("time.monotonic", side_effect=[0, 5, 10, 100, 200, 400]),
        ):
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps({"state": "Starting"})
            )

            result = wait_for_codespace("cs-abc123", timeout_seconds=50)

            assert result is False


class TestGetOrCreateCodespace:
    """Tests for get_or_create_codespace function."""

    def test_returns_existing_codespace(self, tmp_path: Path) -> None:
        """get_or_create_codespace returns existing codespace if found."""
        with (
            patch("erk.core.codespace.get_repo_name", return_value="owner/repo"),
            patch("erk.core.codespace.get_current_branch", return_value="feature"),
            patch("erk.core.codespace.find_existing_codespace", return_value="cs-existing"),
        ):
            result = get_or_create_codespace(tmp_path)

            assert result == "cs-existing"

    def test_creates_new_codespace_when_none_exists(self, tmp_path: Path) -> None:
        """get_or_create_codespace creates new codespace if none found."""
        with (
            patch("erk.core.codespace.get_repo_name", return_value="owner/repo"),
            patch("erk.core.codespace.get_current_branch", return_value="feature"),
            patch("erk.core.codespace.find_existing_codespace", return_value=None),
            patch("erk.core.codespace.create_codespace", return_value="cs-new"),
            patch("erk.core.codespace.wait_for_codespace", return_value=True),
        ):
            result = get_or_create_codespace(tmp_path)

            assert result == "cs-new"

    def test_raises_error_on_timeout(self, tmp_path: Path) -> None:
        """get_or_create_codespace raises CodespaceError on timeout."""
        with (
            patch("erk.core.codespace.get_repo_name", return_value="owner/repo"),
            patch("erk.core.codespace.get_current_branch", return_value="feature"),
            patch("erk.core.codespace.find_existing_codespace", return_value=None),
            patch("erk.core.codespace.create_codespace", return_value="cs-new"),
            patch("erk.core.codespace.wait_for_codespace", return_value=False),
        ):
            with pytest.raises(CodespaceError, match="did not become available"):
                get_or_create_codespace(tmp_path)
