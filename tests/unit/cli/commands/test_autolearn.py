"""Unit tests for autolearn helper module."""

from pathlib import Path

from erk.cli.commands.autolearn import maybe_run_autolearn
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from tests.fakes.claude_executor import FakeClaudeExecutor


def test_autolearn_disabled_does_nothing(tmp_path: Path) -> None:
    """Test that autolearn does nothing when config disabled."""
    executor = FakeClaudeExecutor()
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=False)

    ctx = context_for_test(
        claude_executor=executor,
        cwd=tmp_path,
        global_config=global_config,
    )

    maybe_run_autolearn(ctx, repo_root=tmp_path, branch="P42-feature-branch")

    # No execution should happen
    assert executor.interactive_calls == []


def test_autolearn_no_plan_prefix_does_nothing(tmp_path: Path) -> None:
    """Test that autolearn does nothing for branches without plan prefix."""
    executor = FakeClaudeExecutor()
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        claude_executor=executor,
        cwd=tmp_path,
        global_config=global_config,
    )

    maybe_run_autolearn(ctx, repo_root=tmp_path, branch="feature-branch")

    # No execution should happen (no plan prefix)
    assert executor.interactive_calls == []


def test_autolearn_runs_learn_workflow(tmp_path: Path) -> None:
    """Test that autolearn runs the learn workflow for plan branches."""
    executor = FakeClaudeExecutor()
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        claude_executor=executor,
        cwd=tmp_path,
        global_config=global_config,
    )

    maybe_run_autolearn(ctx, repo_root=tmp_path, branch="P42-add-feature")

    # Should execute the learn command
    assert len(executor.interactive_calls) == 1
    worktree_path, dangerous, command, target_subpath, model, permission_mode = (
        executor.interactive_calls[0]
    )
    assert worktree_path == tmp_path
    assert dangerous is False
    assert command == "/erk:learn 42"
    assert target_subpath is None


def test_autolearn_with_none_global_config_does_nothing(tmp_path: Path) -> None:
    """Test that autolearn does nothing when global_config is None."""
    executor = FakeClaudeExecutor()

    ctx = context_for_test(
        claude_executor=executor,
        cwd=tmp_path,
        global_config=None,
    )

    maybe_run_autolearn(ctx, repo_root=tmp_path, branch="P42-feature-branch")

    # No execution should happen
    assert executor.interactive_calls == []


def test_autolearn_extracts_issue_number_correctly(tmp_path: Path) -> None:
    """Test that autolearn correctly extracts issue number from various branch formats."""
    executor = FakeClaudeExecutor()
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        claude_executor=executor,
        cwd=tmp_path,
        global_config=global_config,
    )

    # Test with different branch name formats
    maybe_run_autolearn(ctx, repo_root=tmp_path, branch="P123-some-feature-01-15")

    assert len(executor.interactive_calls) == 1
    _, _, command, _, _, _ = executor.interactive_calls[0]
    assert command == "/erk:learn 123"
