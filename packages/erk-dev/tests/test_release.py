"""Tests for release command functions."""

from unittest.mock import MagicMock, patch

from erk_dev.commands.release.command import (
    _run_git_command,
    _tag_exists,
    _working_directory_clean,
)


class TestTagExists:
    """Tests for _tag_exists function."""

    def test_returns_true_when_tag_exists(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="v1.0.0\nv1.1.0\nv1.2.0\n",
            )
            assert _tag_exists("v1.1.0") is True

    def test_returns_false_when_tag_not_exists(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="v1.0.0\nv1.1.0\n",
            )
            assert _tag_exists("v1.2.0") is False

    def test_returns_false_for_empty_output(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
            )
            assert _tag_exists("v1.0.0") is False


class TestWorkingDirectoryClean:
    """Tests for _working_directory_clean function."""

    def test_returns_true_when_clean(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
            )
            assert _working_directory_clean() is True

    def test_returns_false_when_dirty(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=" M packages/erk/src/erk/cli.py\n",
            )
            assert _working_directory_clean() is False


class TestRunGitCommand:
    """Tests for _run_git_command function."""

    def test_dry_run_returns_true_without_executing(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            result = _run_git_command(
                ["branch", "-f", "release", "HEAD"],
                dry_run=True,
                description="create release branch",
            )
            assert result is True
            mock_run.assert_not_called()

    def test_returns_true_on_success(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _run_git_command(
                ["branch", "-f", "release", "HEAD"],
                dry_run=False,
                description="create release branch",
            )
            assert result is True
            mock_run.assert_called_once()

    def test_returns_false_on_failure(self) -> None:
        with patch("erk_dev.commands.release.command.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="fatal: not a git repository",
            )
            result = _run_git_command(
                ["branch", "-f", "release", "HEAD"],
                dry_run=False,
                description="create release branch",
            )
            assert result is False
