"""Layer 3 tests: Business logic for command execution over fakes."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from erk_kits.data.kits.command.scripts.command.execute import (
    execute,
    execute_command_impl,
)
from erk_kits.data.kits.command.scripts.command.ops import (
    FakeClaudeCliOps,
)


@pytest.fixture
def runner() -> CliRunner:
    """Create Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def fake_cli_ops() -> FakeClaudeCliOps:
    """Create fake CLI ops for testing."""
    return FakeClaudeCliOps()


def test_command_not_found_error(
    runner: CliRunner,
) -> None:
    """Test error handling when command file not found."""
    with runner.isolated_filesystem():
        # Setup: Create .claude/commands directory but no command file
        Path(".claude/commands").mkdir(parents=True)

        # Execute
        result = runner.invoke(execute, ["nonexistent"])

        # Verify
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "nonexistent" in result.output
        assert ".claude/commands/" in result.output


def test_successful_execution(
    fake_cli_ops: FakeClaudeCliOps,
    tmp_path: Path,
) -> None:
    """Test successful command execution with returncode 0."""
    # Setup: Create valid command file
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test")

    # Configure fake to return success
    fake_cli_ops.set_next_returncode(0)

    # Execute
    import os

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        exit_code = execute_command_impl("test", False, fake_cli_ops)
    finally:
        os.chdir(original_cwd)

    # Verify exit code
    assert exit_code == 0

    # Verify ops was called correctly
    assert fake_cli_ops.get_execution_count() == 1
    last_execution = fake_cli_ops.get_last_execution()
    assert last_execution is not None
    command_name, cwd, json_output = last_execution
    assert command_name == "test"
    assert cwd == tmp_path
    assert json_output is False


def test_failed_execution(
    fake_cli_ops: FakeClaudeCliOps,
    tmp_path: Path,
) -> None:
    """Test failed command execution with returncode 1."""
    # Setup: Create valid command file
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test")

    # Configure fake to return failure
    fake_cli_ops.set_next_returncode(1)

    # Execute
    import os

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        exit_code = execute_command_impl("test", False, fake_cli_ops)
    finally:
        os.chdir(original_cwd)

    # Verify exit code propagated
    assert exit_code == 1


def test_json_output_mode(
    fake_cli_ops: FakeClaudeCliOps,
    tmp_path: Path,
) -> None:
    """Test that --json flag is passed to ops layer."""
    # Setup: Create valid command file
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test")

    # Configure fake to return success
    fake_cli_ops.set_next_returncode(0)

    # Execute with JSON mode
    import os

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        execute_command_impl("test", True, fake_cli_ops)
    finally:
        os.chdir(original_cwd)

    # Verify JSON flag was passed
    last_execution = fake_cli_ops.get_last_execution()
    assert last_execution is not None
    _, _, json_output = last_execution
    assert json_output is True


def test_namespaced_command_execution(
    fake_cli_ops: FakeClaudeCliOps,
    tmp_path: Path,
) -> None:
    """Test execution of namespaced commands."""
    # Setup: Create namespaced command file
    commands_dir = tmp_path / ".claude" / "commands" / "gt"
    commands_dir.mkdir(parents=True)
    (commands_dir / "submit-branch.md").write_text("# Submit Branch")

    # Configure fake to return success
    fake_cli_ops.set_next_returncode(0)

    # Execute
    import os

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        execute_command_impl("gt:submit-branch", False, fake_cli_ops)
    finally:
        os.chdir(original_cwd)

    # Verify command name includes namespace
    last_execution = fake_cli_ops.get_last_execution()
    assert last_execution is not None
    command_name, _, _ = last_execution
    assert command_name == "gt:submit-branch"


def test_claude_cli_not_found_error_propagates(
    fake_cli_ops: FakeClaudeCliOps,
    tmp_path: Path,
) -> None:
    """Test that FileNotFoundError from ops layer propagates correctly."""
    # Setup: Create valid command file
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test.md").write_text("# Test")

    # Configure fake to raise FileNotFoundError
    fake_cli_ops.set_file_not_found_error(True)

    # Execute and verify exception propagates
    import os

    original_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            execute_command_impl("test", False, fake_cli_ops)
    finally:
        os.chdir(original_cwd)
