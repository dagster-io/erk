"""Tests for planner connect command.

Note: The connect command uses os.execvp() which replaces the process.
These tests verify behavior up to (but not including) the execvp call,
and test error paths which don't reach execvp.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk.core.planner.registry_fake import FakePlannerRegistry
from erk.core.planner.types import RegisteredPlanner


def _make_planner(
    name: str = "test-planner",
    gh_name: str = "test-gh-name",
    repository: str = "test-owner/test-repo",
    configured: bool = True,
) -> RegisteredPlanner:
    """Helper to create test planners."""
    return RegisteredPlanner(
        name=name,
        gh_name=gh_name,
        repository=repository,
        configured=configured,
        registered_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        last_connected_at=None,
    )


def test_planner_without_subcommand_connects_to_default() -> None:
    """Test 'erk planner' (without subcommand) connects to default.

    This verifies the fix for Click 8.3+ Sentinel.UNSET handling.
    When invoked without subcommand, the planner group invokes connect_planner
    with name=None explicitly to avoid Sentinel.UNSET being passed instead.
    """
    registry = FakePlannerRegistry()
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()
    # Use bare "planner" command without subcommand
    result = runner.invoke(cli, ["planner"], obj=ctx)

    # Should show "No default planner set" error, not "No planner named 'Sentinel.UNSET'"
    assert result.exit_code == 1
    assert "No default planner set" in result.output
    assert "Sentinel.UNSET" not in result.output


def test_connect_no_planners_shows_error() -> None:
    """Test connect with no registered planners shows error."""
    registry = FakePlannerRegistry()
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()
    result = runner.invoke(cli, ["planner", "connect"], obj=ctx)

    assert result.exit_code == 1
    assert "No default planner set" in result.output


def test_connect_no_default_shows_error() -> None:
    """Test connect without default planner shows error."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[planner])  # No default set
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()
    result = runner.invoke(cli, ["planner", "connect"], obj=ctx)

    assert result.exit_code == 1
    assert "No default planner set" in result.output


def test_connect_named_planner_not_found() -> None:
    """Test connect with nonexistent named planner shows error."""
    planner = _make_planner(name="existing")
    registry = FakePlannerRegistry(planners=[planner])
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()
    result = runner.invoke(cli, ["planner", "connect", "nonexistent"], obj=ctx)

    assert result.exit_code == 1
    assert "No planner named 'nonexistent' found" in result.output


def test_connect_warns_if_not_configured() -> None:
    """Test connect warns when planner is not configured.

    Note: We mock os.execvp to prevent process replacement.
    """
    planner = _make_planner(name="unconfigured", configured=False)
    registry = FakePlannerRegistry(planners=[planner], default_planner="unconfigured")
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()

    # Mock os.execvp to prevent process replacement
    with patch("os.execvp") as mock_execvp:
        result = runner.invoke(cli, ["planner", "connect"], obj=ctx)

    # Should show warning about not configured
    assert "has not been configured yet" in result.output
    # But still attempt to connect (via VS Code by default)
    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "gh"  # First arg is program name
    assert "code" in call_args[0][1]


def test_connect_updates_last_connected_timestamp() -> None:
    """Test that connect updates the last_connected_at timestamp."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[planner], default_planner="my-planner")
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()

    # Mock os.execvp to prevent process replacement
    with patch("os.execvp"):
        runner.invoke(cli, ["planner", "connect"], obj=ctx)

    # Verify timestamp was updated
    assert len(registry.updated_connections) == 1
    name, timestamp = registry.updated_connections[0]
    assert name == "my-planner"
    assert timestamp is not None


def test_connect_with_named_planner() -> None:
    """Test connect with explicit planner name."""
    planner1 = _make_planner(name="planner-1", gh_name="gh-name-1")
    planner2 = _make_planner(name="planner-2", gh_name="gh-name-2")
    registry = FakePlannerRegistry(planners=[planner1, planner2], default_planner="planner-1")
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()

    # Connect to planner-2 (not the default)
    with patch("os.execvp") as mock_execvp:
        runner.invoke(cli, ["planner", "connect", "planner-2"], obj=ctx)

    # Should use the named planner's gh_name
    call_args = mock_execvp.call_args
    args_list = call_args[0][1]
    assert "gh-name-2" in args_list


def test_connect_default_opens_vscode() -> None:
    """Test that connect (without --ssh) opens VS Code desktop."""
    planner = _make_planner(name="my-planner", gh_name="my-gh-codespace")
    registry = FakePlannerRegistry(planners=[planner], default_planner="my-planner")
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()

    with patch("os.execvp") as mock_execvp:
        result = runner.invoke(cli, ["planner", "connect"], obj=ctx)

    # Verify VS Code is opened
    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "gh"
    args_list = call_args[0][1]
    assert args_list == ["gh", "codespace", "code", "-c", "my-gh-codespace"]

    # Verify setup instructions are printed
    assert "Opening VS Code..." in result.output
    assert "Run in VS Code terminal:" in result.output
    assert "git pull && uv sync && source .venv/bin/activate" in result.output
    assert "--allow-dangerously-skip-permissions" in result.output


def test_connect_with_ssh_flag_uses_ssh() -> None:
    """Test that connect --ssh runs claude via SSH in a bash login shell."""
    planner = _make_planner(name="my-planner", gh_name="my-gh-codespace")
    registry = FakePlannerRegistry(planners=[planner], default_planner="my-planner")
    ctx = context_for_test(planner_registry=registry)

    runner = CliRunner()

    with patch("os.execvp") as mock_execvp:
        runner.invoke(cli, ["planner", "connect", "--ssh"], obj=ctx)

    # Verify the correct command was called
    mock_execvp.assert_called_once()
    call_args = mock_execvp.call_args
    assert call_args[0][0] == "gh"
    args_list = call_args[0][1]
    assert "gh" in args_list
    assert "codespace" in args_list
    assert "ssh" in args_list
    assert "-c" in args_list
    assert "my-gh-codespace" in args_list
    # SSH concatenates command args with spaces without preserving grouping.
    # The entire remote command must be a single argument after -t to work correctly.
    # Format: bash -l -c '<setup_commands> && claude'
    assert "--" in args_list
    dash_dash_idx = args_list.index("--")
    remaining_args = args_list[dash_dash_idx + 1 :]
    # The remote command is now a single combined string
    expected_remote_cmd = (
        "bash -l -c 'git pull && uv sync && source .venv/bin/activate "
        "&& claude --allow-dangerously-skip-permissions --verbose'"
    )
    assert remaining_args == ["-t", expected_remote_cmd]
