"""Tests for erk objective next-plan command."""

from click.testing import CliRunner

from erk.cli.commands.objective import objective_group
from erk_shared.git.fake import FakeGit
from erk_shared.objectives.storage import FakeObjectiveStore
from erk_shared.objectives.types import (
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _create_test_objective() -> ObjectiveDefinition:
    """Create a sample objective for testing."""
    return ObjectiveDefinition(
        name="test-objective",
        objective_type=ObjectiveType.COMPLETABLE,
        desired_state="All tests pass.",
        rationale="Quality assurance.",
        examples=[],
        scope_includes=["src/"],
        scope_excludes=["tests/"],
        evaluation_prompt="Check test coverage.",
        plan_sizing_prompt="Fix 5 tests per plan.",
    )


def test_next_plan_prompt_only_outputs_prompt() -> None:
    """Test that --prompt-only outputs the prompt without launching Claude."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        objective = _create_test_objective()
        objectives_store = FakeObjectiveStore(
            objectives={"test-objective": objective},
            notes={"test-objective": ObjectiveNotes(entries=[])},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            objectives=objectives_store,
            claude_executor=claude_executor,
        )

        result = runner.invoke(
            objective_group, ["next-plan", "test-objective", "--prompt-only"], obj=ctx
        )

        assert result.exit_code == 0
        assert "# Turn: test-objective" in result.output
        assert "System Prompt" in result.output
        assert "User Prompt" in result.output
        assert "Copy the above prompt to Claude" in result.output
        # Should NOT have launched Claude
        assert len(claude_executor.interactive_calls) == 0


def test_next_plan_default_launches_claude_in_plan_mode() -> None:
    """Test that default behavior launches Claude in plan mode with the prompt."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        objective = _create_test_objective()
        objectives_store = FakeObjectiveStore(
            objectives={"test-objective": objective},
            notes={"test-objective": ObjectiveNotes(entries=[])},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            objectives=objectives_store,
            claude_executor=claude_executor,
        )

        result = runner.invoke(objective_group, ["next-plan", "test-objective"], obj=ctx)

        # execute_interactive doesn't return exit codes in tests (simulated)
        assert result.exit_code == 0
        # Should have launched Claude via execute_interactive
        assert len(claude_executor.interactive_calls) == 1
        worktree_path, mode, command, target_subpath = claude_executor.interactive_calls[0]

        # Verify the prompt contains expected content
        assert "test-objective" in command
        assert "All tests pass" in command
        assert "Check test coverage" in command
        # Should be in plan mode
        assert mode == "plan"
        assert target_subpath is None


def test_next_plan_fails_for_nonexistent_objective() -> None:
    """Test that next-plan fails when objective doesn't exist."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        objectives_store = FakeObjectiveStore(objectives={}, notes={})
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            objectives=objectives_store,
            claude_executor=claude_executor,
        )

        result = runner.invoke(objective_group, ["next-plan", "nonexistent-objective"], obj=ctx)

        assert result.exit_code == 1
        assert "Objective not found" in result.output
