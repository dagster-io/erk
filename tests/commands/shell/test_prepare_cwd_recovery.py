"""Tests for the __prepare_cwd_recovery hidden command."""

import os
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit

from erk.cli.commands.prepare_cwd_recovery import prepare_cwd_recovery_cmd
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from tests.fakes.context import create_test_context
from tests.fakes.script_writer import FakeScriptWriter


def build_ctx(repo_root: Path | None, erk_root: Path, cwd: Path | None = None) -> ErkContext:
    """Create a ErkContext with test fakes."""
    git_common_dirs: dict[Path, Path] = {}
    existing_paths: set[Path] = {erk_root}

    if repo_root is not None:
        git_common_dirs[repo_root] = repo_root / ".git"
        existing_paths.update({repo_root, repo_root / ".git"})

    # Add cwd to existing_paths if specified and different from repo_root
    if cwd is not None and cwd != repo_root:
        existing_paths.add(cwd)

    git_ops = FakeGit(git_common_dirs=git_common_dirs, existing_paths=existing_paths)
    script_writer = FakeScriptWriter()
    global_config_ops = GlobalConfig(
        erk_root=erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
    )
    return create_test_context(
        git=git_ops,
        script_writer=script_writer,
        global_config=global_config_ops,
        cwd=cwd or repo_root or erk_root,
        dry_run=False,
    )


def test_prepare_cwd_recovery_outputs_script(tmp_path: Path) -> None:
    """Command should emit a script path when inside a repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    ctx = build_ctx(repo, erk_root, cwd=repo)

    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(prepare_cwd_recovery_cmd, obj=ctx)
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0
    script_path = Path(result.output.strip())
    # Verify script was written to in-memory fake
    assert ctx.script_writer.get_script_content(script_path) is not None


def test_prepare_cwd_recovery_no_repo(tmp_path: Path) -> None:
    """Command should emit nothing outside a repository."""
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    ctx = build_ctx(None, erk_root)

    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(prepare_cwd_recovery_cmd, obj=ctx)
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0
    assert result.output == ""


def test_prepare_cwd_recovery_missing_cwd(tmp_path: Path) -> None:
    """Command should handle missing cwd gracefully."""
    ctx = build_ctx(None, tmp_path)

    broken_dir = tmp_path / "vanish"
    broken_dir.mkdir()

    runner = CliRunner()

    original_cwd = os.getcwd()
    try:
        os.chdir(broken_dir)
        broken_dir.rmdir()
        result = runner.invoke(prepare_cwd_recovery_cmd, obj=ctx)
    finally:
        os.chdir(original_cwd)

    assert result.exit_code == 0
    assert result.output == ""
