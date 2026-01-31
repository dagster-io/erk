"""Tests for checkout_helpers error handling.

Layer 4 (business logic over fakes) tests for ensure_branch_has_worktree
when add_worktree raises RuntimeError.
"""

from pathlib import Path

import pytest

from erk.cli.commands.checkout_helpers import ensure_branch_has_worktree
from erk.core.context import ErkContext
from erk_shared.context.types import RepoContext
from erk_shared.gateway.git.fake import FakeGit


def test_ensure_branch_has_worktree_raises_on_add_error(tmp_path: Path) -> None:
    """Test that ensure_branch_has_worktree raises RuntimeError on add_worktree failure."""
    worktrees_dir = tmp_path / "worktrees"
    worktrees_dir.mkdir()

    git = FakeGit(
        add_worktree_error="fatal: branch already checked out",
    )
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path / ".erk",
        worktrees_dir=worktrees_dir,
        pool_json_path=tmp_path / ".erk" / "pool.json",
    )

    with pytest.raises(RuntimeError, match="fatal: branch already checked out"):
        ensure_branch_has_worktree(
            ctx,
            repo,
            branch_name="feature",
            no_slot=True,
            force=False,
        )
