"""Helpers for CLI testing with REAL git operations and CLI assertions.

This module provides utilities for setting up isolated test environments
for CLI command tests that require REAL git operations (not fakes), plus
reusable assertion helpers to reduce CLI test boilerplate.

IMPORTANT: For 95% of CLI tests, use `erk_isolated_fs_env()` from
`tests.test_utils.env_helpers` instead. That helper uses FakeGit and
is faster, better isolated, and easier to use.

Only use `cli_test_repo()` when you specifically need:
- Real git operations (hooks, worktree edge cases)
- Actual filesystem permissions testing
- Real subprocess interactions
- Integration tests requiring actual git behavior

See: tests.test_utils.env_helpers.erk_isolated_fs_env() for the recommended pattern.
"""

import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from click.testing import Result


@dataclass
class CLITestRepo:
    """Test environment for CLI tests with isolated git repo and config.

    Attributes:
        repo: Path to git repository (with initial commit)
        erk_root: Path to erks directory
        tmp_path: Path to test root directory (contains .erk config)
    """

    repo: Path
    erk_root: Path
    tmp_path: Path


@contextmanager
def cli_test_repo(tmp_path: Path) -> Generator[CLITestRepo]:
    """Set up isolated git repo with REAL git for CLI testing.

    ⚠️ WARNING: Only use this helper when you NEED real git operations!
    For 95% of CLI tests, use `erk_isolated_fs_env()` instead (from
    tests.test_utils.env_helpers), which is faster and better isolated.

    Creates a complete test environment with:
    - Isolated .erk config directory with basic settings
    - REAL git repository with main branch and initial commit (subprocess calls)
    - erk_root directory structure
    - Configured git user (test@example.com / Test User)

    This helper handles boilerplate setup for CLI tests requiring REAL git.
    It does NOT create the CliRunner itself - tests must create that with
    isolated HOME environment and handle directory changes manually.

    When to use this helper:
    - Testing git hooks or git worktree edge cases
    - Testing actual filesystem permissions
    - Integration tests requiring actual git behavior

    When NOT to use this helper:
    - Regular CLI command tests → Use erk_isolated_fs_env() instead
    - Unit tests of core logic → Use FakeGit directly
    - Tests that can use fakes → Use erk_isolated_fs_env() instead

    Args:
        tmp_path: Pytest's tmp_path fixture providing isolated test directory

    Yields:
        CLITestRepo with repo path, erk_root, and tmp_path

    Example (real git required):
        ```python
        from click.testing import CliRunner
        from erk.cli.cli import cli
        from tests.test_utils.cli_helpers import cli_test_repo

        def test_git_hook_integration(tmp_path: Path) -> None:
            with cli_test_repo(tmp_path) as test_env:
                # Set up CliRunner with isolated HOME
                env_vars = os.environ.copy()
                env_vars["HOME"] = str(test_env.tmp_path)
                runner = CliRunner(env=env_vars)

                # Run test from repo directory
                original_cwd = os.getcwd()
                try:
                    os.chdir(test_env.repo)
                    result = runner.invoke(cli, ["wt", "create", "feature"])
                    assert result.exit_code == 0
                finally:
                    os.chdir(original_cwd)
        ```

    Better alternative for most tests:
        ```python
        from click.testing import CliRunner
        from tests.test_utils.env_helpers import erk_isolated_fs_env

        def test_create_command() -> None:
            runner = CliRunner()
            with erk_isolated_fs_env(runner) as env:
                # Much simpler! No HOME setup, no os.chdir, uses fakes
                git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
                test_ctx = context_for_test(git=git_ops, cwd=env.cwd)
                result = runner.invoke(cli, ["wt", "create", "feature"], obj=test_ctx)
        ```

    See Also:
        tests.test_utils.env_helpers.erk_isolated_fs_env() - Recommended helper
    """
    # Set up isolated global config
    global_config_dir = tmp_path / ".erk"
    global_config_dir.mkdir()
    erk_root = tmp_path / "erks"
    (global_config_dir / "config.toml").write_text(
        f'erk_root = "{erk_root}"\nuse_graphite = false\n',
        encoding="utf-8",
    )

    # Set up real git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create initial commit
    (repo / "README.md").write_text("test", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    yield CLITestRepo(repo=repo, erk_root=erk_root, tmp_path=tmp_path)


def assert_cli_success(result: Result, *expected_messages: str) -> None:
    """Assert CLI command succeeded and output contains expected messages.

    Reduces boilerplate in CLI tests by combining exit code check with message
    verification in a single assertion that provides clear error messages.

    Args:
        result: Click CliRunner test result
        *expected_messages: Messages that should appear in command output

    Raises:
        AssertionError: If command failed or expected messages not found

    Example:
        ```python
        from click.testing import CliRunner
        from tests.test_utils.cli_helpers import assert_cli_success

        def test_create_command() -> None:
            runner = CliRunner()
            result = runner.invoke(cli, ["wt", "create", "feature"])

            # Before (3 lines with generic error messages):
            assert result.exit_code == 0
            assert "Created" in result.output
            assert "feature" in result.output

            # After (1 line with clear error message):
            assert_cli_success(result, "Created", "feature")
        ```
    """
    if result.exit_code != 0:
        msg = f"Command failed with exit code {result.exit_code}\nOutput:\n{result.output}"
        raise AssertionError(msg)

    for message in expected_messages:
        if message not in result.output:
            msg = f"Expected message '{message}' not found in output\nOutput:\n{result.output}"
            raise AssertionError(msg)


def assert_cli_error(
    result: Result,
    exit_code: int = 1,
    *expected_messages: str,
) -> None:
    """Assert CLI command failed with specific error.

    Reduces boilerplate in CLI error handling tests by combining exit code
    check with error message verification.

    Args:
        result: Click CliRunner test result
        exit_code: Expected non-zero exit code (default: 1)
        *expected_messages: Error messages that should appear in output

    Raises:
        AssertionError: If exit code is wrong or messages not found

    Example:
        ```python
        from click.testing import CliRunner
        from tests.test_utils.cli_helpers import assert_cli_error

        def test_create_invalid_branch() -> None:
            runner = CliRunner()
            result = runner.invoke(cli, ["wt", "create", "invalid@name"])

            # Before (3 lines):
            assert result.exit_code == 1
            assert "invalid" in result.output
            assert "branch" in result.output

            # After (1 line):
            assert_cli_error(result, 1, "invalid", "branch")
        ```
    """
    if result.exit_code != exit_code:
        msg = f"Expected exit code {exit_code}, got {result.exit_code}\nOutput:\n{result.output}"
        raise AssertionError(msg)

    for message in expected_messages:
        if message not in result.output:
            msg = (
                f"Expected error message '{message}' not found in output\nOutput:\n{result.output}"
            )
            raise AssertionError(msg)


def assert_cli_output_contains(result: Result, *patterns: str) -> None:
    """Assert output contains patterns (doesn't check exit code).

    Useful for checking intermediate output regardless of success/failure.
    When you care about what's in the output but not whether the command
    succeeded or failed.

    Args:
        result: Click CliRunner test result
        *patterns: Patterns that should appear in output

    Raises:
        AssertionError: If any pattern not found

    Example:
        ```python
        from click.testing import CliRunner
        from tests.test_utils.cli_helpers import assert_cli_output_contains

        def test_status_displays_worktree_name() -> None:
            runner = CliRunner()
            result = runner.invoke(cli, ["status"])

            # Verify output contains key info, regardless of exit code
            assert_cli_output_contains(result, "feature-1", "main")
        ```
    """
    for pattern in patterns:
        if pattern not in result.output:
            msg = f"Expected pattern '{pattern}' not found in output\nOutput:\n{result.output}"
            raise AssertionError(msg)
