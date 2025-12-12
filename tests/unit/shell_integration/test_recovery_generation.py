"""Unit tests for recovery script generation."""

from pathlib import Path

from erk.cli.commands.prepare_cwd_recovery import generate_recovery_script
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.script_writer import RealScriptWriter
from erk_shared.git.fake import FakeGit
from tests.fakes.context import create_test_context


def build_ctx(repo_root: Path | None, erk_root: Path, cwd: Path | None = None) -> ErkContext:
    """Create a ErkContext with test fakes and real script writer for integration testing."""
    git_common_dirs: dict[Path, Path] = {}
    existing_paths: set[Path] = {erk_root}

    if repo_root is not None:
        git_common_dirs[repo_root] = repo_root / ".git"
        existing_paths.update({repo_root, repo_root / ".git"})

    # Add cwd to existing_paths if specified and different from repo_root
    if cwd is not None and cwd != repo_root:
        existing_paths.add(cwd)

    git_ops = FakeGit(git_common_dirs=git_common_dirs, existing_paths=existing_paths)
    global_config_ops = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)
    return create_test_context(
        git=git_ops,
        global_config=global_config_ops,
        script_writer=RealScriptWriter(),  # Use real script writer for integration tests
        cwd=cwd or repo_root or erk_root,
        dry_run=False,
    )


# Tests for generate_recovery_script function


def test_returns_script_path_when_in_repo(tmp_path: Path) -> None:
    """Function returns a script path when cwd is inside a repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    ctx = build_ctx(repo, erk_root, cwd=repo)

    result = generate_recovery_script(ctx)

    assert result is not None
    assert isinstance(result, Path)
    assert result.exists()
    assert result.suffix == ".sh"
    # Clean up
    result.unlink(missing_ok=True)


def test_returns_none_when_not_in_repo(tmp_path: Path) -> None:
    """Function returns None when cwd is not inside a repository."""
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # No repo_root = not in a git repo
    ctx = build_ctx(None, erk_root, cwd=tmp_path)

    result = generate_recovery_script(ctx)

    assert result is None


def test_returns_none_when_cwd_missing(tmp_path: Path) -> None:
    """Function returns None when cwd doesn't exist."""
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    vanished = tmp_path / "vanished"
    # Don't create vanished directory - it doesn't exist

    ctx = build_ctx(None, erk_root, cwd=vanished)

    result = generate_recovery_script(ctx)

    assert result is None


def test_script_contains_cd_command(tmp_path: Path) -> None:
    """Generated script should contain cd command to repo root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    ctx = build_ctx(repo, erk_root, cwd=repo)

    result = generate_recovery_script(ctx)

    assert result is not None
    script_content = result.read_text(encoding="utf-8")

    # Script should cd to repo root (with single quotes for shell safety)
    assert f"cd '{repo}'" in script_content

    # Clean up
    result.unlink(missing_ok=True)


def test_script_is_executable(tmp_path: Path) -> None:
    """Generated script should be executable."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    ctx = build_ctx(repo, erk_root, cwd=repo)

    result = generate_recovery_script(ctx)

    assert result is not None
    # Check if file has execute permission
    assert result.stat().st_mode & 0o100  # Owner execute bit

    # Clean up
    result.unlink(missing_ok=True)


def test_handles_nested_directory_in_repo(tmp_path: Path) -> None:
    """Function works when cwd is a subdirectory of the repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    # Create nested directory
    nested = repo / "src" / "subdir"
    nested.mkdir(parents=True)

    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # cwd is nested inside repo
    ctx = build_ctx(repo, erk_root, cwd=nested)

    result = generate_recovery_script(ctx)

    assert result is not None
    assert result.exists()

    # Clean up
    result.unlink(missing_ok=True)


def test_multiple_calls_create_unique_scripts(tmp_path: Path) -> None:
    """Each call should create a unique temporary script."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    ctx = build_ctx(repo, erk_root, cwd=repo)

    result1 = generate_recovery_script(ctx)
    result2 = generate_recovery_script(ctx)

    assert result1 is not None
    assert result2 is not None
    assert result1 != result2  # Different paths
    assert result1.exists()
    assert result2.exists()

    # Clean up
    result1.unlink(missing_ok=True)
    result2.unlink(missing_ok=True)
