"""Unit tests for implement_shared helpers."""

from click.testing import CliRunner

from erk.cli.commands.implement_shared import extract_plan_from_current_branch
from erk_shared.git.fake import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_extract_plan_from_current_branch_with_p_prefix() -> None:
    """Test extraction from branch with P prefix."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["P123-fix-bug-01-16-1200"]},
            current_branches={env.cwd: "P123-fix-bug-01-16-1200"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result == "123"


def test_extract_plan_from_current_branch_with_large_issue_number() -> None:
    """Test extraction works with large issue numbers."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["P4567-feature-branch-01-16-1200"]},
            current_branches={env.cwd: "P4567-feature-branch-01-16-1200"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result == "4567"


def test_extract_plan_from_current_branch_returns_none_for_non_plan_branch() -> None:
    """Test returns None for non-plan branches."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["feature-branch"]},
            current_branches={env.cwd: "feature-branch"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result is None


def test_extract_plan_from_current_branch_returns_none_for_main() -> None:
    """Test returns None for main branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result is None


def test_extract_plan_handles_no_current_branch() -> None:
    """Test returns None when no current branch (detached HEAD)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: []},
            # current_branches not set means get_current_branch returns None
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        assert result is None


def test_extract_plan_from_legacy_branch_format() -> None:
    """Test extraction from legacy branch format without P prefix."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["123-fix-bug-01-16-1200"]},
            current_branches={env.cwd: "123-fix-bug-01-16-1200"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = extract_plan_from_current_branch(ctx)

        # Legacy format is supported
        assert result == "123"
