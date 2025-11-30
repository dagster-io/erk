"""Unit tests for checkout command message generation logic.

Tests the four-case message logic in _perform_checkout() without going through
the full CLI command pipeline. These tests directly verify the message
generation business logic.
"""

from erk_shared.git.abc import WorktreeInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.commands.checkout import _perform_checkout
from erk.core.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def _graphite_with_branch_tracked(branch: str, parent: str = "main") -> FakeGraphite:
    """Create a FakeGraphite with a branch already tracked.

    This prevents the _ensure_graphite_tracking() function from prompting
    for confirmation, making direct _perform_checkout() calls possible.
    """
    return FakeGraphite(
        branches={
            branch: BranchMetadata(
                name=branch,
                parent=parent,
                children=[],
                is_trunk=False,
                commit_sha=None,
            )
        }
    )


def test_message_case_1_already_on_target_branch_in_current_worktree() -> None:
    """Test message when already on target branch in current worktree.

    Case 1: ctx.cwd == target_path AND current_branch == branch
    Expected: "Already on branch {branch} in worktree {name}"
    """
    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Build context with cwd=feature_wt (already in target location)
        test_ctx = env.build_context(git=git_ops, cwd=feature_wt)

        # Call _perform_checkout in script mode
        _perform_checkout(
            ctx=test_ctx,
            repo_root=env.cwd,
            target_worktree=WorktreeInfo(path=feature_wt, branch="feature-1"),
            branch="feature-1",
            script=True,
            is_newly_created=False,
        )

        # Verify script was written
        assert env.script_writer.last_script is not None
        script_content = env.script_writer.last_script.content

        # Verify message contains expected text
        assert "Already on branch" in script_content
        assert "feature-1" in script_content
        assert "in worktree" in script_content
        # Should not say "Switched"
        assert "Switched" not in script_content


def test_message_case_2_switched_to_existing_worktree_standard_naming() -> None:
    """Test message when switching to existing worktree with standard naming.

    Case 2: ctx.cwd != target_path AND current_branch == branch AND worktree_name == branch
    Expected: "Switched to worktree {name}"
    """
    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        # Standard naming: worktree name matches branch name
        feature_wt = work_dir / "feature-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Build context with cwd=env.cwd (root worktree, different from target)
        test_ctx = env.build_context(git=git_ops, cwd=env.cwd)

        # Call _perform_checkout in script mode
        _perform_checkout(
            ctx=test_ctx,
            repo_root=env.cwd,
            target_worktree=WorktreeInfo(path=feature_wt, branch="feature-1"),
            branch="feature-1",
            script=True,
            is_newly_created=False,
        )

        # Verify script was written
        assert env.script_writer.last_script is not None
        script_content = env.script_writer.last_script.content

        # Verify message contains expected text
        assert "Switched to worktree" in script_content
        assert "feature-1" in script_content
        # Should NOT say "Already"
        assert "Already" not in script_content
        # Should NOT mention branch separately (standard naming)
        assert "(branch" not in script_content


def test_message_case_2_switched_to_existing_worktree_nonstandard_naming() -> None:
    """Test message when switching to existing worktree with non-standard naming.

    Case 2: ctx.cwd != target_path AND current_branch == branch AND worktree_name != branch
    Expected: "Switched to worktree {name} (branch {branch})"
    """
    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        # Non-standard naming: worktree name differs from branch name
        feature_wt = work_dir / "custom-worktree-name"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Build context with cwd=env.cwd (root worktree, different from target)
        test_ctx = env.build_context(git=git_ops, cwd=env.cwd)

        # Call _perform_checkout in script mode
        _perform_checkout(
            ctx=test_ctx,
            repo_root=env.cwd,
            target_worktree=WorktreeInfo(path=feature_wt, branch="feature-1"),
            branch="feature-1",
            script=True,
            is_newly_created=False,
        )

        # Verify script was written
        assert env.script_writer.last_script is not None
        script_content = env.script_writer.last_script.content

        # Verify message contains expected text
        assert "Switched to worktree" in script_content
        assert "custom-worktree-name" in script_content
        # Should explicitly mention branch when names differ
        assert "(branch" in script_content
        assert "feature-1" in script_content


def test_message_case_3_switched_and_checked_out_branch() -> None:
    """Test message when switching to worktree and checking out different branch.

    Case 3: ctx.cwd != target_path AND current_branch != branch
    Expected: "Switched to worktree {name} and checked out branch {branch}"
    """
    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    # Worktree currently has different branch
                    WorktreeInfo(path=feature_wt, branch="other-branch"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Build context with cwd=env.cwd (root worktree)
        test_ctx = env.build_context(git=git_ops, cwd=env.cwd)

        # Call _perform_checkout in script mode - will checkout feature-1
        _perform_checkout(
            ctx=test_ctx,
            repo_root=env.cwd,
            target_worktree=WorktreeInfo(path=feature_wt, branch="other-branch"),
            branch="feature-1",
            script=True,
            is_newly_created=False,
        )

        # Verify git checkout was called
        assert len(git_ops.checked_out_branches) == 1
        assert git_ops.checked_out_branches[0] == (feature_wt, "feature-1")

        # Verify script was written
        assert env.script_writer.last_script is not None
        script_content = env.script_writer.last_script.content

        # Verify message contains expected text
        assert "Switched to worktree" in script_content
        assert "feature-wt" in script_content
        assert "and checked out branch" in script_content
        assert "feature-1" in script_content


def test_message_case_4_switched_to_newly_created_worktree() -> None:
    """Test message when switching to newly created worktree.

    Case 4: is_newly_created == True
    Expected: "Switched to new worktree {name}"
    """
    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        new_wt = work_dir / "new-feature"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=new_wt, branch="new-feature"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Build context with cwd=env.cwd (root worktree)
        test_ctx = env.build_context(git=git_ops, cwd=env.cwd)

        # Call _perform_checkout with is_newly_created=True
        _perform_checkout(
            ctx=test_ctx,
            repo_root=env.cwd,
            target_worktree=WorktreeInfo(path=new_wt, branch="new-feature"),
            branch="new-feature",
            script=True,
            is_newly_created=True,
        )

        # Verify script was written
        assert env.script_writer.last_script is not None
        script_content = env.script_writer.last_script.content

        # Verify message contains expected text
        assert "Switched to new worktree" in script_content
        assert "new-feature" in script_content
        # Should NOT say "and checked out" (worktree already has correct branch)
        assert "and checked out" not in script_content


def test_message_colorization_applied() -> None:
    """Test that messages include colorization (ANSI escape codes).

    Verifies that click.style() is being applied to branch and worktree names.
    """
    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, cwd=env.cwd)

        # Call _perform_checkout in script mode
        _perform_checkout(
            ctx=test_ctx,
            repo_root=env.cwd,
            target_worktree=WorktreeInfo(path=feature_wt, branch="feature-1"),
            branch="feature-1",
            script=True,
            is_newly_created=False,
        )

        # Verify script was written
        assert env.script_writer.last_script is not None
        script_content = env.script_writer.last_script.content

        # Check for ANSI escape codes (indicates colorization)
        # Yellow for branch names: \x1b[33m
        # Cyan for worktree names: \x1b[36m
        # Bold: \x1b[1m
        assert "\x1b[" in script_content, "Expected ANSI escape codes for colorization"


def test_message_non_script_mode_case_1() -> None:
    """Test non-script mode message for Case 1 (already there).

    Verifies that user_output() is called with correct message in non-script mode.
    """
    import sys
    from io import StringIO

    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        feature_wt = work_dir / "feature-1"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Pre-track branch to avoid confirmation prompt in non-script mode
        graphite = _graphite_with_branch_tracked("feature-1")
        test_ctx = env.build_context(git=git_ops, graphite=graphite, cwd=feature_wt)

        # Capture stderr (where user_output writes)
        captured_stderr = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_stderr

        try:
            # Call _perform_checkout in non-script mode
            _perform_checkout(
                ctx=test_ctx,
                repo_root=env.cwd,
                target_worktree=WorktreeInfo(path=feature_wt, branch="feature-1"),
                branch="feature-1",
                script=False,
                is_newly_created=False,
            )
        finally:
            sys.stderr = old_stderr

        output = captured_stderr.getvalue()

        # Verify message was written to stderr
        assert "Already on branch" in output
        assert "feature-1" in output
        assert "in worktree" in output


def test_message_non_script_mode_case_4() -> None:
    """Test non-script mode message for Case 4 (newly created).

    Verifies that user_output() is called with correct message in non-script mode.
    """
    import sys
    from io import StringIO

    from click.testing import CliRunner

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        work_dir = env.erk_root / env.cwd.name
        new_wt = work_dir / "new-feature"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=new_wt, branch="new-feature"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Pre-track branch to avoid confirmation prompt in non-script mode
        graphite = _graphite_with_branch_tracked("new-feature")
        test_ctx = env.build_context(git=git_ops, graphite=graphite, cwd=env.cwd)

        # Capture stderr (where user_output writes)
        captured_stderr = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured_stderr

        try:
            # Call _perform_checkout in non-script mode with is_newly_created=True
            _perform_checkout(
                ctx=test_ctx,
                repo_root=env.cwd,
                target_worktree=WorktreeInfo(path=new_wt, branch="new-feature"),
                branch="new-feature",
                script=False,
                is_newly_created=True,
            )
        finally:
            sys.stderr = old_stderr

        output = captured_stderr.getvalue()

        # Verify message was written to stderr
        assert "Switched to new worktree" in output
        assert "new-feature" in output
