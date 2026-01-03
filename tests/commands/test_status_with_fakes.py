"""CLI tests for erk status command.

This file focuses on CLI-specific concerns for the status command:
- Command execution and exit codes
- Output formatting and display
- Path resolution (subdirectories, worktree detection)
- Error handling and messages

The status command orchestrates multiple collectors (git, PR, stack, plan).
The business logic of these collectors is tested in their respective unit test files:
- tests/unit/status/test_github_pr_collector.py - PR collector logic
- tests/unit/status/test_graphite_stack_collector.py - Stack collector logic
- tests/unit/status/test_plan_collector.py - Plan collector logic
- tests/unit/status/test_orchestrator.py - Collector orchestration

This file trusts that unit layer and only tests CLI integration.
"""

import os
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.status import status_cmd
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.fakes.context import create_test_context
from tests.test_utils.builders import WorktreeScenario


def test_status_cmd_in_root_worktree(simple_repo: WorktreeScenario) -> None:
    """Test status command when in the root worktree (CLI layer)."""
    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(simple_repo.repo_root)

    try:
        result = runner.invoke(status_cmd, obj=simple_repo.ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - CLI integration
    assert result.exit_code == 0
    assert "main" in result.output
    assert "Git Status:" in result.output


def test_status_cmd_in_feature_worktree(repo_with_feature: WorktreeScenario) -> None:
    """Test status command when in a feature worktree (CLI layer)."""
    runner = CliRunner()
    worktree_path = repo_with_feature.repo_dir / "feature"
    original_dir = os.getcwd()
    os.chdir(worktree_path)

    try:
        result = runner.invoke(status_cmd, obj=repo_with_feature.ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - CLI integration
    assert result.exit_code == 0
    assert "feature" in result.output
    assert "Git Status:" in result.output


def test_status_cmd_in_subdirectory_of_worktree(tmp_path: Path) -> None:
    """Test status command finds worktree when run from subdirectory (CLI layer)."""
    # Arrange - Create subdirectory structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()

    worktree_path = tmp_path / "erks" / "repo" / "feature"
    worktree_path.mkdir(parents=True)
    subdir = worktree_path / "src" / "nested"
    subdir.mkdir(parents=True)

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=worktree_path, branch="feature"),
            ]
        },
        current_branches={worktree_path: "feature", subdir: "feature"},
        git_common_dirs={worktree_path: git_dir, subdir: git_dir},
        file_statuses={worktree_path: ([], [], []), subdir: ([], [], [])},
        ahead_behind={(worktree_path, "feature"): (0, 0), (subdir, "feature"): (0, 0)},
        recent_commits={worktree_path: [], subdir: []},
    )
    global_config = GlobalConfig.test(
        tmp_path / "erks",
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )
    ctx = create_test_context(git=git_ops, global_config=global_config, cwd=subdir)

    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(subdir)  # Run from nested subdirectory

    try:
        result = runner.invoke(status_cmd, obj=ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - Should find worktree and succeed
    assert result.exit_code == 0
    assert "feature" in result.output


def test_status_cmd_displays_all_collector_sections(tmp_path: Path) -> None:
    """Smoke test: status command integrates all collectors (CLI layer).

    This is a thin integration test that verifies all collector outputs appear in
    the CLI display. The actual collector logic is tested in unit layer.
    """
    # Arrange - Use WorktreeScenario builder for cleaner setup
    scenario = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feature")
        .with_pr("feature", number=123, checks_passing=True)
        .with_graphite_stack(["main", "feature"])
    )

    # Create .impl/ folder with plan.md and progress.md
    impl_folder = scenario.repo_dir / "feature" / ".impl"
    impl_folder.mkdir(parents=True, exist_ok=True)
    plan_file = impl_folder / "plan.md"
    plan_file.write_text("# Feature Plan\n## Overview\nImplement new feature", encoding="utf-8")
    progress_file = impl_folder / "progress.md"
    progress_file.write_text("# Progress Tracking\n\n- [ ] Step 1\n- [ ] Step 2", encoding="utf-8")

    scenario = scenario.build()

    # Update context with correct cwd for feature worktree
    feature_dir = scenario.repo_dir / "feature"
    ctx = context_for_test(
        git=scenario.ctx.git,
        global_config=scenario.ctx.global_config,
        github=scenario.ctx.github,
        graphite=scenario.ctx.graphite,
        shell=scenario.ctx.shell,
        cwd=feature_dir,
        dry_run=scenario.ctx.dry_run,
    )

    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(feature_dir)

    try:
        result = runner.invoke(status_cmd, obj=ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - Just verify sections are present (trust unit layer for content)
    assert result.exit_code == 0
    assert "Git Status:" in result.output
    assert "#123" in result.output or "123" in result.output  # PR section
    assert "Stack:" in result.output or "Graphite" in result.output  # Stack section
    # Implementation section
    assert "Implementation:" in result.output or "Feature Plan" in result.output


def test_status_cmd_not_in_git_repo(tmp_path: Path) -> None:
    """Test status command fails when not in a git repository (error handling)."""
    # Arrange
    non_git_dir = tmp_path / "not-a-repo"
    non_git_dir.mkdir()

    git_ops = FakeGit(
        git_common_dirs={},  # No git directories
        worktrees={},
    )

    global_config = GlobalConfig.test(
        tmp_path / "erks", use_graphite=False, shell_setup_complete=False
    )

    ctx = create_test_context(git=git_ops, global_config=global_config)

    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(non_git_dir)

    try:
        result = runner.invoke(status_cmd, obj=ctx)
    finally:
        os.chdir(original_dir)

    # Assert - CLI error handling
    assert result.exit_code != 0
