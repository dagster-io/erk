"""Tests for navigation helper ensure functions."""

from pathlib import Path

import pytest

from erk.cli.commands.navigation_helpers import ensure_graphite_enabled
from erk.core.config_store import GlobalConfig
from erk.core.context import context_for_test
from erk_shared.git.fake import FakeGit


class TestEnsureGraphiteEnabled:
    """Tests for ensure_graphite_enabled function."""

    def test_succeeds_when_graphite_enabled(self, tmp_path: Path) -> None:
        """ensure_graphite_enabled succeeds when use_graphite is True."""
        # Arrange
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()
        erk_root = tmp_path / "erks"
        erk_root.mkdir()

        git = FakeGit(
            local_branches={repo_root: ["main"]},
            remote_branches={repo_root: []},
            git_common_dirs={repo_root: git_dir},
        )

        global_config = GlobalConfig.test(
            erk_root,
            use_graphite=True,  # Graphite enabled
            shell_setup_complete=False,
            show_pr_info=False,
        )

        ctx = context_for_test(git=git, cwd=repo_root, global_config=global_config)

        # Act & Assert - should not raise
        ensure_graphite_enabled(ctx)

    def test_exits_when_graphite_disabled(self, tmp_path: Path) -> None:
        """ensure_graphite_enabled raises SystemExit when use_graphite is False."""
        # Arrange
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()
        erk_root = tmp_path / "erks"
        erk_root.mkdir()

        git = FakeGit(
            local_branches={repo_root: ["main"]},
            remote_branches={repo_root: []},
            git_common_dirs={repo_root: git_dir},
        )

        global_config = GlobalConfig.test(
            erk_root,
            use_graphite=False,  # Graphite disabled
            shell_setup_complete=False,
            show_pr_info=False,
        )

        ctx = context_for_test(git=git, cwd=repo_root, global_config=global_config)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            ensure_graphite_enabled(ctx)

        assert exc_info.value.code == 1

    def test_exits_when_global_config_none(self, tmp_path: Path) -> None:
        """ensure_graphite_enabled raises SystemExit when global_config is None."""
        # Arrange
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()

        git = FakeGit(
            local_branches={repo_root: ["main"]},
            remote_branches={repo_root: []},
            git_common_dirs={repo_root: git_dir},
        )

        ctx = context_for_test(
            git=git,
            cwd=repo_root,
            global_config=None,  # No global config
        )

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            ensure_graphite_enabled(ctx)

        assert exc_info.value.code == 1

    def test_error_message_includes_command(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """ensure_graphite_enabled outputs helpful error message."""
        # Arrange
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        git_dir = repo_root / ".git"
        git_dir.mkdir()
        erk_root = tmp_path / "erks"
        erk_root.mkdir()

        git = FakeGit(
            local_branches={repo_root: ["main"]},
            remote_branches={repo_root: []},
            git_common_dirs={repo_root: git_dir},
        )

        global_config = GlobalConfig.test(
            erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=False,
        )

        ctx = context_for_test(git=git, cwd=repo_root, global_config=global_config)

        # Act
        with pytest.raises(SystemExit):
            ensure_graphite_enabled(ctx)

        # Assert
        captured = capsys.readouterr()
        # user_output routes to stderr for shell integration
        assert "Error:" in captured.err
        assert "requires Graphite to be enabled" in captured.err
        assert "erk config set use_graphite true" in captured.err
