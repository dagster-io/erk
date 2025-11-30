"""Tests for erk plan verb behavior (invoke_without_command).

These tests verify that `erk plan` (without subcommand) invokes planning mode,
while `erk plan <subcommand>` still works for plan management.
"""

from click.testing import CliRunner

from erk.cli.commands.plan import plan_group
from erk.core.codespace import FakeCodespace


def test_plan_without_subcommand_calls_remote_planning() -> None:
    """Test that 'erk plan' without subcommand invokes remote planning."""
    runner = CliRunner()
    fake = FakeCodespace()

    result = runner.invoke(plan_group, [], obj=fake)

    # Should call remote planning with empty description
    assert result.exit_code == 0
    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0] == ("fake-codespace", "/erk:craft-plan")


def test_plan_with_description_passes_to_remote_planning() -> None:
    """Test that 'erk plan -d "description"' passes description to remote planning."""
    runner = CliRunner()
    fake = FakeCodespace()

    result = runner.invoke(plan_group, ["-d", "add user authentication"], obj=fake)

    assert result.exit_code == 0
    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0] == ("fake-codespace", "/erk:craft-plan add user authentication")


def test_plan_local_flag_calls_local_planning() -> None:
    """Test that 'erk plan --local' invokes local planning."""
    runner = CliRunner()
    fake = FakeCodespace()

    result = runner.invoke(plan_group, ["--local"], obj=fake)

    assert result.exit_code == 0
    assert len(fake.local_commands) == 1
    assert fake.local_commands[0] == "/erk:craft-plan"


def test_plan_local_with_description() -> None:
    """Test that 'erk plan --local -d "description"' passes description to local planning."""
    runner = CliRunner()
    fake = FakeCodespace()

    result = runner.invoke(plan_group, ["--local", "-d", "refactor database layer"], obj=fake)

    assert result.exit_code == 0
    assert len(fake.local_commands) == 1
    assert fake.local_commands[0] == "/erk:craft-plan refactor database layer"


def test_plan_local_exits_when_claude_unavailable() -> None:
    """Test that 'erk plan --local' exits when Claude CLI is not available."""
    runner = CliRunner()
    fake = FakeCodespace(claude_available=False)

    result = runner.invoke(plan_group, ["--local"], obj=fake)

    assert result.exit_code == 1
    assert "Claude CLI not found" in result.output


def test_plan_help_shows_verb_and_noun_usage() -> None:
    """Test that 'erk plan --help' shows both verb and noun usage."""
    runner = CliRunner()

    result = runner.invoke(plan_group, ["--help"])

    assert result.exit_code == 0
    # Should show verb usage (planning mode)
    assert "erk plan" in result.output
    assert "--local" in result.output
    assert "--desc" in result.output or "-d" in result.output
    # Should show noun usage (subcommands)
    assert "list" in result.output
    assert "get" in result.output
    assert "create" in result.output


def test_plan_subcommand_list_works() -> None:
    """Test that 'erk plan list' correctly invokes the list subcommand."""
    runner = CliRunner()

    # Use the plan_group directly; list command requires context
    # This test verifies the subcommand is properly recognized
    result = runner.invoke(plan_group, ["list", "--help"])

    assert result.exit_code == 0
    assert "List plans" in result.output or "plans" in result.output.lower()


def test_plan_subcommand_get_works() -> None:
    """Test that 'erk plan get --help' correctly invokes the get subcommand."""
    runner = CliRunner()

    result = runner.invoke(plan_group, ["get", "--help"])

    assert result.exit_code == 0
    # get subcommand should show its help


def test_plan_subcommand_create_works() -> None:
    """Test that 'erk plan create --help' correctly invokes the create subcommand."""
    runner = CliRunner()

    result = runner.invoke(plan_group, ["create", "--help"])

    assert result.exit_code == 0
    # Should show the --file option
    assert "--file" in result.output or "file" in result.output.lower()


def test_plan_reuses_existing_codespace() -> None:
    """Test that remote planning reuses an existing codespace when available."""
    from erk.core.codespace import CodespaceInfo

    runner = CliRunner()
    fake = FakeCodespace(
        existing_codespaces=[
            CodespaceInfo(
                name="existing-cs",
                state="Available",
                repository="owner/repo",
                branch="main",
            )
        ]
    )

    result = runner.invoke(plan_group, [], obj=fake)

    assert result.exit_code == 0
    # Should reuse existing codespace, not create new one
    assert len(fake.created_codespaces) == 0
    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0][0] == "existing-cs"


def test_plan_creates_codespace_when_none_exists() -> None:
    """Test that remote planning creates a codespace when none exists."""
    runner = CliRunner()
    fake = FakeCodespace(
        existing_codespaces=[],  # No existing codespaces
        created_codespace_name="new-cs",
    )

    result = runner.invoke(plan_group, [], obj=fake)

    assert result.exit_code == 0
    # Should create a new codespace
    assert len(fake.created_codespaces) == 1
    assert fake.created_codespaces[0] == ("owner/repo", "main")
    # Should wait for it to become available
    assert "new-cs" in fake.waited_for
    # Then SSH to it
    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0][0] == "new-cs"
