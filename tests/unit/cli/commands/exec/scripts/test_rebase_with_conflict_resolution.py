"""Tests for rebase-with-conflict-resolution exec command.

Tests the rebase workflow with conflict resolution using Claude, with
all dependencies injected via ErkContext for testability.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.rebase_with_conflict_resolution import (
    CONFLICT_RESOLUTION_PROMPT,
    RebaseError,
    RebaseSuccess,
    _build_summary_prompt,
    _rebase_with_conflict_resolution_impl,
    rebase_with_conflict_resolution,
)
from erk_shared.context.context import ErkContext
from erk_shared.core.claude_executor import PromptResult
from erk_shared.core.fakes import FakeClaudeExecutor
from erk_shared.git.abc import RebaseResult
from erk_shared.git.fake import FakeGit


def test_build_summary_prompt_no_conflicts() -> None:
    """Test prompt building when no conflicts occurred."""
    prompt = _build_summary_prompt(
        branch_name="feature-branch",
        target_branch="main",
        commits_behind=3,
        conflicts_resolved=(),
    )

    assert "feature-branch" in prompt
    assert "main" in prompt
    assert "3 commit(s) behind" in prompt
    assert "No merge conflicts occurred" in prompt


def test_build_summary_prompt_with_conflicts() -> None:
    """Test prompt building when conflicts were resolved."""
    prompt = _build_summary_prompt(
        branch_name="feature-branch",
        target_branch="main",
        commits_behind=5,
        conflicts_resolved=("src/config.py", "tests/test_api.py"),
    )

    assert "feature-branch" in prompt
    assert "main" in prompt
    assert "5 commit(s) behind" in prompt
    assert "Merge conflicts were automatically resolved" in prompt
    assert "- src/config.py" in prompt
    assert "- tests/test_api.py" in prompt


def test_rebase_already_up_to_date(tmp_path: Path) -> None:
    """Test when branch is already up-to-date (0 commits behind)."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (2, 0)},  # 2 ahead, 0 behind
    )
    fake_claude = FakeClaudeExecutor()

    result = _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=5,
    )

    assert isinstance(result, RebaseSuccess)
    assert result.action == "already-up-to-date"
    assert result.commits_behind == 0
    assert result.conflicts_resolved == ()
    # Claude should not be invoked when already up-to-date
    assert len(fake_claude.passthrough_calls) == 0


def test_rebase_success_no_conflicts(tmp_path: Path) -> None:
    """Test successful rebase with no conflicts."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 3)},  # 0 ahead, 3 behind
        rebase_onto_result=RebaseResult(success=True, conflict_files=()),
        rebase_in_progress=False,
    )
    fake_claude = FakeClaudeExecutor()

    result = _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=5,
    )

    assert isinstance(result, RebaseSuccess)
    assert result.action == "rebased"
    assert result.commits_behind == 3
    assert result.conflicts_resolved == ()
    # Claude should not be invoked when no conflicts
    assert len(fake_claude.passthrough_calls) == 0
    # Push should have been called
    assert len(fake_git.pushed_branches) == 1
    pushed = fake_git.pushed_branches[0]
    assert pushed.branch == "feature-branch"
    assert pushed.force is True


def test_rebase_with_conflicts_resolved_by_claude(tmp_path: Path) -> None:
    """Test rebase with conflicts that Claude resolves successfully."""
    # Create a custom fake that simulates:
    # 1. Initial rebase fails with conflicts (is_rebase_in_progress returns True first)
    # 2. After Claude resolves, rebase is no longer in progress (returns False)
    call_count = 0

    class RebaseProgressTrackingGit(FakeGit):
        def is_rebase_in_progress(self, cwd: Path) -> bool:
            nonlocal call_count
            call_count += 1
            # First call returns True (rebase in progress), subsequent return False
            return call_count == 1

    fake_git = RebaseProgressTrackingGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 2)},
        rebase_onto_result=RebaseResult(success=False, conflict_files=("src/config.py",)),
        conflicted_files=["src/config.py"],
    )
    fake_claude = FakeClaudeExecutor(passthrough_exit_code=0)

    result = _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=5,
    )

    assert isinstance(result, RebaseSuccess)
    assert result.action == "rebased"
    assert result.commits_behind == 2
    assert "src/config.py" in result.conflicts_resolved
    # Claude should have been invoked once to resolve the conflict
    assert len(fake_claude.passthrough_calls) == 1


def test_rebase_fails_after_max_attempts(tmp_path: Path) -> None:
    """Test that rebase fails after exhausting max attempts."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 2)},
        rebase_onto_result=RebaseResult(success=False, conflict_files=("src/config.py",)),
        rebase_in_progress=True,  # Stays in progress (Claude can't resolve)
        conflicted_files=["src/config.py"],
    )
    fake_claude = FakeClaudeExecutor(passthrough_exit_code=1)  # Claude fails

    result = _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=3,
    )

    assert isinstance(result, RebaseError)
    assert result.error == "rebase-failed"
    assert "3 attempts" in result.message
    # Claude should have been called max_attempts times
    assert len(fake_claude.passthrough_calls) == 3


def test_rebase_fetch_failure(tmp_path: Path) -> None:
    """Test error handling when fetch fails."""

    class FetchFailingGit(FakeGit):
        def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
            raise RuntimeError("Network error")

    fake_git = FetchFailingGit()
    fake_claude = FakeClaudeExecutor()

    result = _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=5,
    )

    assert isinstance(result, RebaseError)
    assert result.error == "fetch-failed"
    assert "Network error" in result.message


def test_rebase_push_failure(tmp_path: Path) -> None:
    """Test error handling when push fails."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 2)},
        rebase_onto_result=RebaseResult(success=True, conflict_files=()),
        rebase_in_progress=False,
        push_to_remote_raises=RuntimeError("Push rejected"),
    )
    fake_claude = FakeClaudeExecutor()

    result = _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=5,
    )

    assert isinstance(result, RebaseError)
    assert result.error == "push-failed"
    assert "Push rejected" in result.message


def test_cli_context_not_initialized() -> None:
    """Test that CLI exits when context is not initialized."""
    runner = CliRunner()

    result = runner.invoke(
        rebase_with_conflict_resolution,
        ["--target-branch", "main", "--branch-name", "feature"],
    )

    assert result.exit_code == 1
    assert "Context not initialized" in result.output


def test_cli_already_up_to_date(tmp_path: Path) -> None:
    """Test CLI output when branch is already up-to-date."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 0)},
    )
    fake_claude = FakeClaudeExecutor()

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=fake_git,
        claude_executor=fake_claude,
    )

    runner = CliRunner()
    result = runner.invoke(
        rebase_with_conflict_resolution,
        ["--target-branch", "main", "--branch-name", "feature-branch"],
        obj=test_ctx,
    )

    assert result.exit_code == 0
    assert "already up-to-date" in result.output
    assert "feature-branch" in result.output
    assert "main" in result.output


def test_cli_successful_rebase_generates_summary(tmp_path: Path) -> None:
    """Test CLI calls Claude to generate summary after successful rebase."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 3)},
        rebase_onto_result=RebaseResult(success=True, conflict_files=()),
        rebase_in_progress=False,
    )
    fake_claude = FakeClaudeExecutor(
        prompt_results=[
            PromptResult(
                success=True,
                output="Rebased `feature-branch` onto `main`, resolving 3 commits.",
                error=None,
            )
        ]
    )

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=fake_git,
        claude_executor=fake_claude,
    )

    runner = CliRunner()
    result = runner.invoke(
        rebase_with_conflict_resolution,
        ["--target-branch", "main", "--branch-name", "feature-branch"],
        obj=test_ctx,
    )

    assert result.exit_code == 0
    assert "Rebased `feature-branch` onto `main`" in result.output
    # Verify summary generation was called
    assert len(fake_claude.prompt_calls) == 1
    prompt_call = fake_claude.prompt_calls[0]
    assert "feature-branch" in prompt_call.prompt
    assert "main" in prompt_call.prompt


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI exits with code 1 on error."""

    class FetchFailingGit(FakeGit):
        def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
            raise RuntimeError("Network error")

    fake_git = FetchFailingGit()
    fake_claude = FakeClaudeExecutor()

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=fake_git,
        claude_executor=fake_claude,
    )

    runner = CliRunner()
    result = runner.invoke(
        rebase_with_conflict_resolution,
        ["--target-branch", "main", "--branch-name", "feature-branch"],
        obj=test_ctx,
    )

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_conflict_resolution_uses_correct_prompt(tmp_path: Path) -> None:
    """Test that conflict resolution uses the expected prompt."""
    # Create a custom fake that simulates rebase being in progress initially,
    # then cleared after Claude is invoked (simulating successful resolution)
    call_count = 0

    class RebaseProgressTrackingGit(FakeGit):
        def is_rebase_in_progress(self, cwd: Path) -> bool:
            nonlocal call_count
            call_count += 1
            # First call returns True (rebase in progress), subsequent return False
            return call_count == 1

    fake_git = RebaseProgressTrackingGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 2)},
        rebase_onto_result=RebaseResult(success=False, conflict_files=("src/config.py",)),
        conflicted_files=["src/config.py"],
    )
    fake_claude = FakeClaudeExecutor(passthrough_exit_code=0)

    _rebase_with_conflict_resolution_impl(
        git=fake_git,
        claude_executor=fake_claude,
        cwd=tmp_path,
        target_branch="main",
        branch_name="feature-branch",
        model="claude-sonnet-4-5",
        max_attempts=5,
    )

    # Verify the conflict resolution prompt was used
    assert len(fake_claude.passthrough_calls) == 1
    passthrough_call = fake_claude.passthrough_calls[0]
    assert passthrough_call.prompt == CONFLICT_RESOLUTION_PROMPT
    assert passthrough_call.dangerous is True
    assert passthrough_call.cwd == tmp_path


def test_model_parameter_passed_correctly(tmp_path: Path) -> None:
    """Test that the model parameter is passed to Claude calls."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 2)},
        rebase_onto_result=RebaseResult(success=True, conflict_files=()),
        rebase_in_progress=False,
    )
    fake_claude = FakeClaudeExecutor(
        prompt_results=[PromptResult(success=True, output="Summary text", error=None)]
    )

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=fake_git,
        claude_executor=fake_claude,
    )

    runner = CliRunner()
    runner.invoke(
        rebase_with_conflict_resolution,
        [
            "--target-branch",
            "main",
            "--branch-name",
            "feature-branch",
            "--model",
            "claude-opus-4",
        ],
        obj=test_ctx,
    )

    # Verify model was passed to summary generation
    assert len(fake_claude.prompt_calls) == 1
    assert fake_claude.prompt_calls[0].model == "claude-opus-4"


def test_max_attempts_parameter(tmp_path: Path) -> None:
    """Test that max-attempts parameter limits retry count."""
    fake_git = FakeGit(
        ahead_behind={(tmp_path, "feature-branch"): (0, 2)},
        rebase_onto_result=RebaseResult(success=False, conflict_files=("src/config.py",)),
        rebase_in_progress=True,  # Stays in progress
        conflicted_files=["src/config.py"],
    )
    fake_claude = FakeClaudeExecutor(passthrough_exit_code=1)

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        git=fake_git,
        claude_executor=fake_claude,
    )

    runner = CliRunner()
    result = runner.invoke(
        rebase_with_conflict_resolution,
        [
            "--target-branch",
            "main",
            "--branch-name",
            "feature-branch",
            "--max-attempts",
            "2",
        ],
        obj=test_ctx,
    )

    assert result.exit_code == 1
    assert "2 attempts" in result.output
    # Claude should have been called exactly 2 times
    assert len(fake_claude.passthrough_calls) == 2
