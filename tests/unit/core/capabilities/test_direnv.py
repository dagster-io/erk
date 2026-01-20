"""Tests for DirenvCapability.

These tests verify the direnv capability installation and detection behavior.
"""

from pathlib import Path
from unittest.mock import patch

from erk.core.capabilities.direnv import DirenvCapability, _detect_shell
from erk.core.init_utils import build_envrc_content, build_envrc_example_content


def test_is_installed_returns_false_when_no_repo_root() -> None:
    """Test is_installed returns False when repo_root is None."""
    capability = DirenvCapability()
    assert capability.is_installed(repo_root=None) is False


def test_is_installed_returns_false_when_envrc_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when .envrc doesn't exist."""
    capability = DirenvCapability()
    assert capability.is_installed(repo_root=tmp_path) is False


def test_is_installed_returns_true_when_envrc_exists(tmp_path: Path) -> None:
    """Test is_installed returns True when .envrc exists."""
    envrc_path = tmp_path / ".envrc"
    envrc_path.write_text("# existing envrc\n", encoding="utf-8")

    capability = DirenvCapability()
    assert capability.is_installed(repo_root=tmp_path) is True


def test_preflight_returns_success_when_direnv_installed() -> None:
    """Test preflight returns success when direnv is installed."""
    capability = DirenvCapability()

    with patch("shutil.which", return_value="/usr/local/bin/direnv"):
        result = capability.preflight(repo_root=Path("/tmp"))

    assert result.success is True


def test_preflight_returns_error_when_direnv_not_installed() -> None:
    """Test preflight returns error with install instructions when direnv not installed."""
    capability = DirenvCapability()

    with patch("shutil.which", return_value=None):
        result = capability.preflight(repo_root=Path("/tmp"))

    assert result.success is False
    assert "direnv not installed" in result.message
    assert "https://direnv.net" in result.message


def test_install_creates_envrc_files_when_direnv_available(tmp_path: Path) -> None:
    """Test install creates .envrc and .envrc.example when direnv is available."""
    capability = DirenvCapability()

    with (
        patch("shutil.which", return_value="/usr/local/bin/direnv"),
        patch("subprocess.run") as mock_run,
        patch.dict("os.environ", {"SHELL": "/bin/zsh"}),
    ):
        result = capability.install(repo_root=tmp_path)

    assert result.success is True
    assert "Created .envrc and .envrc.example" in result.message
    assert ".envrc" in result.created_files
    assert ".envrc.example" in result.created_files

    # Verify files were created
    assert (tmp_path / ".envrc").exists()
    assert (tmp_path / ".envrc.example").exists()

    # Verify content
    envrc_content = (tmp_path / ".envrc").read_text(encoding="utf-8")
    assert "erk completion zsh" in envrc_content

    example_content = (tmp_path / ".envrc.example").read_text(encoding="utf-8")
    assert "# source <(erk completion bash)" in example_content

    # Verify direnv allow was called
    mock_run.assert_called_once_with(["direnv", "allow"], cwd=tmp_path, check=False)


def test_install_does_not_modify_gitignore(tmp_path: Path) -> None:
    """Test install does NOT modify .gitignore.

    Note: .envrc should be added to .gitignore via the init command's
    gitignore prompts, not automatically by this capability.
    """
    # Create existing .gitignore
    gitignore_path = tmp_path / ".gitignore"
    original_content = "*.pyc\n"
    gitignore_path.write_text(original_content, encoding="utf-8")

    capability = DirenvCapability()

    with (
        patch("shutil.which", return_value="/usr/local/bin/direnv"),
        patch("subprocess.run"),
        patch.dict("os.environ", {"SHELL": "/bin/bash"}),
    ):
        result = capability.install(repo_root=tmp_path)

    assert result.success is True

    # Verify .gitignore was NOT modified
    gitignore_content = gitignore_path.read_text(encoding="utf-8")
    assert gitignore_content == original_content


def test_install_uses_correct_shell_completion_for_bash(tmp_path: Path) -> None:
    """Test install uses bash completion when SHELL is bash."""
    capability = DirenvCapability()

    with (
        patch("shutil.which", return_value="/usr/local/bin/direnv"),
        patch("subprocess.run"),
        patch.dict("os.environ", {"SHELL": "/bin/bash"}),
    ):
        result = capability.install(repo_root=tmp_path)

    assert result.success is True

    envrc_content = (tmp_path / ".envrc").read_text(encoding="utf-8")
    assert "erk completion bash" in envrc_content


def test_install_uses_correct_shell_completion_for_zsh(tmp_path: Path) -> None:
    """Test install uses zsh completion when SHELL is zsh."""
    capability = DirenvCapability()

    with (
        patch("shutil.which", return_value="/usr/local/bin/direnv"),
        patch("subprocess.run"),
        patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"}),
    ):
        result = capability.install(repo_root=tmp_path)

    assert result.success is True

    envrc_content = (tmp_path / ".envrc").read_text(encoding="utf-8")
    assert "erk completion zsh" in envrc_content


def test_install_is_idempotent(tmp_path: Path) -> None:
    """Test install succeeds without changes when .envrc already exists."""
    # Create existing .envrc
    envrc_path = tmp_path / ".envrc"
    existing_content = "# my custom envrc\n"
    envrc_path.write_text(existing_content, encoding="utf-8")

    capability = DirenvCapability()

    with patch("shutil.which", return_value="/usr/local/bin/direnv"):
        result = capability.install(repo_root=tmp_path)

    assert result.success is True
    assert ".envrc already exists" in result.message

    # Verify content was not changed
    assert envrc_path.read_text(encoding="utf-8") == existing_content


def test_install_fails_without_repo_root() -> None:
    """Test install returns failure when repo_root is None."""
    capability = DirenvCapability()
    result = capability.install(repo_root=None)

    assert result.success is False
    assert "requires repo_root" in result.message


def test_uninstall_removes_envrc_files(tmp_path: Path) -> None:
    """Test uninstall removes .envrc and .envrc.example files."""
    # Create the files first
    envrc_path = tmp_path / ".envrc"
    example_path = tmp_path / ".envrc.example"
    envrc_path.write_text("# test envrc\n", encoding="utf-8")
    example_path.write_text("# test example\n", encoding="utf-8")

    capability = DirenvCapability()
    result = capability.uninstall(repo_root=tmp_path)

    assert result.success is True
    assert ".envrc" in result.message
    assert ".envrc.example" in result.message
    assert not envrc_path.exists()
    assert not example_path.exists()


def test_uninstall_succeeds_when_no_files_exist(tmp_path: Path) -> None:
    """Test uninstall succeeds gracefully when no direnv files exist."""
    capability = DirenvCapability()
    result = capability.uninstall(repo_root=tmp_path)

    assert result.success is True
    assert "No direnv files to remove" in result.message


def test_uninstall_fails_without_repo_root() -> None:
    """Test uninstall returns failure when repo_root is None."""
    capability = DirenvCapability()
    result = capability.uninstall(repo_root=None)

    assert result.success is False
    assert "requires repo_root" in result.message


def test_capability_properties() -> None:
    """Test capability has correct name, description, and scope."""
    capability = DirenvCapability()

    assert capability.name == "direnv"
    assert "direnv" in capability.description.lower()
    assert capability.scope == "project"
    assert capability.required is False
    assert capability.installation_check_description == ".envrc file exists in repo root"


def test_capability_artifacts() -> None:
    """Test capability declares correct artifacts."""
    capability = DirenvCapability()
    artifacts = capability.artifacts

    assert len(artifacts) == 2
    paths = [a.path for a in artifacts]
    assert ".envrc" in paths
    assert ".envrc.example" in paths


def test_detect_shell_returns_zsh_for_zsh_path() -> None:
    """Test _detect_shell returns zsh when SHELL contains zsh."""
    with patch.dict("os.environ", {"SHELL": "/usr/local/bin/zsh"}):
        assert _detect_shell() == "zsh"


def test_detect_shell_returns_bash_for_bash_path() -> None:
    """Test _detect_shell returns bash when SHELL contains bash."""
    with patch.dict("os.environ", {"SHELL": "/bin/bash"}):
        assert _detect_shell() == "bash"


def test_detect_shell_defaults_to_bash_for_unknown() -> None:
    """Test _detect_shell defaults to bash for unknown shells."""
    with patch.dict("os.environ", {"SHELL": "/bin/fish"}):
        assert _detect_shell() == "bash"


def test_detect_shell_defaults_to_bash_when_shell_not_set() -> None:
    """Test _detect_shell defaults to bash when SHELL env var not set."""
    with patch.dict("os.environ", {}, clear=True):
        assert _detect_shell() == "bash"


def test_build_envrc_example_content() -> None:
    """Test build_envrc_example_content returns correct template."""
    content = build_envrc_example_content()

    assert ".envrc.example" in content
    assert "source .venv/bin/activate" in content
    assert "# source <(erk completion bash)" in content
    assert "# source <(erk completion zsh)" in content


def test_build_envrc_content_for_bash() -> None:
    """Test build_envrc_content returns correct content for bash."""
    content = build_envrc_content("bash")

    assert "source .venv/bin/activate" in content
    assert "source <(erk completion bash)" in content
    assert "(bash)" in content


def test_build_envrc_content_for_zsh() -> None:
    """Test build_envrc_content returns correct content for zsh."""
    content = build_envrc_content("zsh")

    assert "source .venv/bin/activate" in content
    assert "source <(erk completion zsh)" in content
    assert "(zsh)" in content
