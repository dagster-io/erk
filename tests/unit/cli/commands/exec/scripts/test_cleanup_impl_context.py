"""Tests for cleanup-impl-context exec command.

Tests the idempotent cleanup of .erk/impl-context/ staging directory.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.cleanup_impl_context import cleanup_impl_context
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR


def _create_impl_context(repo_root: Path) -> Path:
    """Create a .erk/impl-context/ directory with test content."""
    impl_context_dir = repo_root / IMPL_CONTEXT_DIR
    impl_context_dir.mkdir(parents=True)
    (impl_context_dir / "plan.md").write_text("# Test Plan", encoding="utf-8")
    (impl_context_dir / "ref.json").write_text("{}", encoding="utf-8")
    return impl_context_dir


def test_cleanup_removes_existing_impl_context(tmp_path: Path) -> None:
    """Cleans up .erk/impl-context/ when it exists."""
    _create_impl_context(tmp_path)
    git = FakeGit(current_branches={tmp_path: "plnd/test-branch-01-15-1430"})
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(cleanup_impl_context, obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["cleaned"] is True

    # Directory should be removed from filesystem
    assert not (tmp_path / IMPL_CONTEXT_DIR).exists()

    # Git operations should have been invoked (staged_files clears after commit)
    assert len(git.commit.commits) > 0
    assert git.commit.commits[0].message == "Remove .erk/impl-context/ before implementation"
    assert ".erk/impl-context/" in git.commit.commits[0].staged_files


def test_cleanup_not_found_when_no_impl_context(tmp_path: Path) -> None:
    """Reports not_found when .erk/impl-context/ doesn't exist."""
    git = FakeGit(current_branches={tmp_path: "P123-feature"})
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(cleanup_impl_context, obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["cleaned"] is False
    assert output["reason"] == "not_found"

    # No git operations should have been invoked
    assert len(git.commit.staged_files) == 0
    assert len(git.commit.commits) == 0


def test_cleanup_pushes_to_current_branch(tmp_path: Path) -> None:
    """Pushes the cleanup commit to the current branch."""
    _create_impl_context(tmp_path)
    git = FakeGit(current_branches={tmp_path: "plnd/my-plan-01-15-1430"})
    ctx = ErkContext.for_test(cwd=tmp_path, git=git, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(cleanup_impl_context, obj=ctx)

    assert result.exit_code == 0
    assert len(git.remote.pushed_branches) > 0
    push = git.remote.pushed_branches[0]
    assert push.branch == "plnd/my-plan-01-15-1430"
