"""Tests for erk exec objective-update-after-land command.

This standalone exec script calls Claude to update the linked objective
after a PR has been merged. Tests verify:
- Success path: correct Claude command, success message
- Failure path: error message with retry command
- Always exits 0 (fail-open)
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.env_helpers import erk_inmem_env


def test_objective_update_after_land_success() -> None:
    """Test successful objective update calls Claude with correct arguments."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        executor = FakePromptExecutor()

        test_ctx = env.build_context(
            prompt_executor=executor,
        )

        result = runner.invoke(
            cli,
            [
                "exec",
                "objective-update-after-land",
                "--objective=42",
                "--pr=123",
                "--branch=P42-my-feature",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Should show objective info and success message
        assert "Linked to Objective #42" in result.output
        assert "Starting objective update..." in result.output
        assert "Objective updated successfully" in result.output

        # Should have called Claude executor with correct command
        assert len(executor.executed_commands) == 1
        cmd, _path, dangerous, _verbose, _model = executor.executed_commands[0]
        expected = (
            "/erk:objective-update-with-landed-pr "
            "--pr 123 --objective 42 --branch P42-my-feature --auto-close"
        )
        assert cmd == expected
        assert dangerous is True


def test_objective_update_after_land_failure_shows_retry() -> None:
    """Test that failure shows warning and retry command."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        executor = FakePromptExecutor(command_should_fail=True)

        test_ctx = env.build_context(
            prompt_executor=executor,
        )

        result = runner.invoke(
            cli,
            [
                "exec",
                "objective-update-after-land",
                "--objective=42",
                "--pr=123",
                "--branch=P42-my-feature",
            ],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Always exits 0 (fail-open)
        assert result.exit_code == 0

        assert "Starting objective update..." in result.output
        assert "failed" in result.output.lower()
        assert "/erk:objective-update-with-landed-pr" in result.output
        assert "manually" in result.output.lower()

        # Should have tried to call Claude executor
        assert len(executor.executed_commands) == 1
