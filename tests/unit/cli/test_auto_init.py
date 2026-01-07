"""Tests for auto-init functionality.

Auto-init automatically initializes erk when:
- User runs a meaningful erk command (not --help, doctor, init, etc.)
- Current directory is in a git repository
- Repository hasn't been erk-ified yet (.erk/config.toml doesn't exist)
"""

from pathlib import Path

from erk.core.auto_init import SKIP_AUTO_INIT_COMMANDS, auto_init_repo, should_auto_init
from erk_shared.git.fake import FakeGit


def test_should_auto_init_returns_false_for_bare_command() -> None:
    """Auto-init should not trigger for bare 'erk' with no subcommand."""
    result = should_auto_init(invoked_subcommand=None, is_help_invoked=False)
    assert result is False


def test_should_auto_init_returns_false_for_help() -> None:
    """Auto-init should not trigger when --help is invoked."""
    result = should_auto_init(invoked_subcommand="plan", is_help_invoked=True)
    assert result is False


def test_should_auto_init_returns_false_for_init_command() -> None:
    """Auto-init should not trigger for 'erk init' command."""
    result = should_auto_init(invoked_subcommand="init", is_help_invoked=False)
    assert result is False


def test_should_auto_init_returns_false_for_doctor_command() -> None:
    """Auto-init should not trigger for 'erk doctor' command."""
    result = should_auto_init(invoked_subcommand="doctor", is_help_invoked=False)
    assert result is False


def test_should_auto_init_returns_false_for_completion_command() -> None:
    """Auto-init should not trigger for 'erk completion' command."""
    result = should_auto_init(invoked_subcommand="completion", is_help_invoked=False)
    assert result is False


def test_should_auto_init_returns_false_for_upgrade_command() -> None:
    """Auto-init should not trigger for 'erk upgrade' command."""
    result = should_auto_init(invoked_subcommand="upgrade", is_help_invoked=False)
    assert result is False


def test_should_auto_init_returns_true_for_plan_command() -> None:
    """Auto-init should trigger for 'erk plan' command."""
    result = should_auto_init(invoked_subcommand="plan", is_help_invoked=False)
    assert result is True


def test_should_auto_init_returns_true_for_branch_command() -> None:
    """Auto-init should trigger for 'erk branch' command."""
    result = should_auto_init(invoked_subcommand="branch", is_help_invoked=False)
    assert result is True


def test_should_auto_init_returns_true_for_wt_command() -> None:
    """Auto-init should trigger for 'erk wt' command."""
    result = should_auto_init(invoked_subcommand="wt", is_help_invoked=False)
    assert result is True


def test_skip_auto_init_commands_contains_expected_commands() -> None:
    """Verify SKIP_AUTO_INIT_COMMANDS contains all expected commands."""
    expected = {"init", "doctor", "completion", "upgrade", "admin"}
    assert SKIP_AUTO_INIT_COMMANDS == expected


def test_auto_init_creates_config_file(tmp_path: Path) -> None:
    """Auto-init should create .erk/config.toml in the repo."""
    # Set up a fake git repo
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    git = FakeGit(
        repository_roots={repo_root: repo_root},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    result = auto_init_repo(cwd=repo_root, git=git, erk_root=tmp_path / ".erk")

    assert result == "initialized"
    assert (repo_root / ".erk" / "config.toml").exists()


def test_auto_init_creates_version_file(tmp_path: Path) -> None:
    """Auto-init should create .erk/required-erk-uv-tool-version."""
    # Set up a fake git repo
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    git = FakeGit(
        repository_roots={repo_root: repo_root},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    auto_init_repo(cwd=repo_root, git=git, erk_root=tmp_path / ".erk")

    version_file = repo_root / ".erk" / "required-erk-uv-tool-version"
    assert version_file.exists()
    version_content = version_file.read_text(encoding="utf-8").strip()
    assert version_content  # Should have some version string


def test_auto_init_updates_gitignore(tmp_path: Path) -> None:
    """Auto-init should add standard entries to .gitignore."""
    # Set up a fake git repo with a .gitignore
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")

    git = FakeGit(
        repository_roots={repo_root: repo_root},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    auto_init_repo(cwd=repo_root, git=git, erk_root=tmp_path / ".erk")

    gitignore_content = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore_content
    assert ".erk/scratch/" in gitignore_content
    assert ".impl/" in gitignore_content


def test_auto_init_returns_already_initialized_for_erkified_repo(tmp_path: Path) -> None:
    """Auto-init should skip if repo is already erk-ified."""
    # Set up an already erk-ified repo
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    erk_dir = repo_root / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[project]", encoding="utf-8")

    git = FakeGit(
        repository_roots={repo_root: repo_root},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    result = auto_init_repo(cwd=repo_root, git=git, erk_root=tmp_path / ".erk")

    assert result == "already-initialized"


def test_auto_init_returns_not_in_repo_outside_git_repo(tmp_path: Path) -> None:
    """Auto-init should return not-in-repo if not in a git repository."""
    # Set up a directory without .git
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    git = FakeGit()  # No repository_roots configured

    result = auto_init_repo(cwd=not_a_repo, git=git, erk_root=tmp_path / ".erk")

    assert result == "not-in-repo"


def test_auto_init_does_not_prompt_for_shell_integration(tmp_path: Path) -> None:
    """Auto-init should not configure shell integration (non-interactive)."""
    # This is implicitly tested by the fact that auto_init_repo doesn't
    # call any shell setup functions. We verify the config file doesn't
    # contain shell_setup_complete=True (since that's a global setting anyway)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    git = FakeGit(
        repository_roots={repo_root: repo_root},
        git_common_dirs={repo_root: repo_root / ".git"},
    )

    result = auto_init_repo(cwd=repo_root, git=git, erk_root=tmp_path / ".erk")

    assert result == "initialized"
    # Verify no global config was created (shell integration is global)
    # Global config would be at erk_root / "config.toml", not repo_root / ".erk" / "config.toml"
    assert not (tmp_path / ".erk" / "config.toml").exists()
