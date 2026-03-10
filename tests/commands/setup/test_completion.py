"""Test shell completion generation commands.

This module tests the CLI commands that generate shell completion scripts
for bash, zsh, and fish shells using FakeCompletion for dependency injection.

For E2E tests that validate subprocess behavior with special environment variables,
see tests/integration/test_completion_e2e.py.
"""

from click.testing import CliRunner

from erk.cli.commands.completion import completion_bash, completion_fish, completion_zsh
from tests.fakes.gateway.completion import FakeCompletion
from tests.fakes.tests.context import create_test_context

# Unit tests using FakeCompletion


def test_bash_cmd_generation() -> None:
    """Test bash completion command generation."""
    # Setup fake with bash completion script
    bash_script = (
        "_erk_completion() {\n"
        "    COMPREPLY=()\n"
        "    local word\n"
        "    complete -F _erk_completion erk\n"
        "}"
    )
    completion_ops = FakeCompletion(bash_script=bash_script, erk_path="/usr/local/bin/erk")

    ctx = create_test_context(completion=completion_ops)
    runner = CliRunner()
    result = runner.invoke(completion_bash, obj=ctx)

    # Verify command executed successfully
    assert result.exit_code == 0
    assert "_erk_completion" in result.output
    assert "COMPREPLY" in result.output

    # Verify generation was called
    assert "bash" in completion_ops.generation_calls


def test_bash_cmd_includes_all_commands() -> None:
    """Test bash completion includes all commands."""
    # Simulate a more complete bash completion output
    completion_script = """
_erk_completion() {
    local IFS=$'\t'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" _ERK_COMPLETE=bash_complete erk)

    local commands="create list status switch up down rm rename move gc"
    COMPREPLY=($(compgen -W "$commands" -- "${COMP_WORDS[COMP_CWORD]}"))
}

complete -F _erk_completion erk
"""
    completion_ops = FakeCompletion(bash_script=completion_script)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_bash, obj=ctx)

    assert result.exit_code == 0
    # Check for common commands in the output
    assert "create" in result.output
    assert "switch" in result.output
    assert "complete -F _erk_completion erk" in result.output


def test_bash_cmd_handles_special_chars() -> None:
    """Test bash completion handles special characters properly."""
    # Test with script containing special chars that need escaping
    completion_script = """
_erk_completion() {
    local word="${COMP_WORDS[COMP_CWORD]}"
    # Handle branch names with special chars
    local branches="feature/test feature-123 bug#456"
    COMPREPLY=($(compgen -W "$branches" -- "$word"))
}
complete -F _erk_completion erk
"""
    completion_ops = FakeCompletion(bash_script=completion_script)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_bash, obj=ctx)

    assert result.exit_code == 0
    assert "COMP_WORDS" in result.output
    assert "compgen" in result.output


def test_zsh_cmd_generation() -> None:
    """Test zsh completion command generation."""
    zsh_completion = """#compdef erk
_erk() {
    local -a commands
    commands=(
        'create:Create a new workspace'
        'list:List all workspaces'
        'status:Show workspace status'
    )
    _describe 'command' commands
}
compdef _erk erk
"""
    completion_ops = FakeCompletion(zsh_script=zsh_completion)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_zsh, obj=ctx)

    assert result.exit_code == 0
    assert "#compdef erk" in result.output
    assert "_erk" in result.output
    assert "compdef" in result.output

    # Verify generation was called
    assert "zsh" in completion_ops.generation_calls


def test_zsh_cmd_includes_descriptions() -> None:
    """Test zsh completion includes command descriptions."""
    zsh_completion = """#compdef erk
_erk() {
    local -a commands
    commands=(
        'create:Create a new workspace with an optional branch'
        'list:List all workspaces in the repository'
        'rm:Remove a workspace and its associated branch'
        'switch:Switch to a different workspace'
    )
    _describe 'command' commands
}
"""
    completion_ops = FakeCompletion(zsh_script=zsh_completion)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_zsh, obj=ctx)

    assert result.exit_code == 0
    assert "Create a new workspace" in result.output
    assert "_describe" in result.output


def test_zsh_cmd_handles_options() -> None:
    """Test zsh completion handles command options."""
    zsh_completion = """#compdef erk
_erk() {
    local context state state_descr line
    typeset -A opt_args

    _arguments \
        '--help[Show help message]' \
        '--version[Show version]' \
        '--verbose[Enable verbose output]' \
        '*::arg:->args'

    case $state in
        args)
            _erk_commands
            ;;
    esac
}
"""
    completion_ops = FakeCompletion(zsh_script=zsh_completion)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_zsh, obj=ctx)

    assert result.exit_code == 0
    assert "_arguments" in result.output
    assert "--help" in result.output


def test_fish_cmd_generation() -> None:
    """Test fish completion command generation."""
    fish_completion = """
complete -c erk -n "__fish_use_subcommand" -a create -d "Create a new workspace"
complete -c erk -n "__fish_use_subcommand" -a list -d "List all workspaces"
complete -c erk -n "__fish_use_subcommand" -a status -d "Show workspace status"
complete -c erk -l help -d "Show help message"
"""
    completion_ops = FakeCompletion(fish_script=fish_completion)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_fish, obj=ctx)

    assert result.exit_code == 0
    assert "complete -c erk" in result.output
    assert "__fish_use_subcommand" in result.output

    # Verify generation was called
    assert "fish" in completion_ops.generation_calls


def test_fish_cmd_includes_subcommands() -> None:
    """Test fish completion includes subcommands."""
    fish_completion = """
# Main commands
complete -c erk -n "__fish_use_subcommand" -a create -d "Create a new workspace"
complete -c erk -n "__fish_use_subcommand" -a switch -d "Switch to a workspace"

# Subcommands for 'create'
complete -c erk -n "__fish_seen_subcommand_from create" -s f -l force -d "Force creation"
complete -c erk -n "__fish_seen_subcommand_from create" -s b -l branch -d "Specify branch"
"""
    completion_ops = FakeCompletion(fish_script=fish_completion)
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_fish, obj=ctx)

    assert result.exit_code == 0
    assert "__fish_seen_subcommand_from" in result.output
    assert "-l force" in result.output


def test_completion_with_invalid_shell() -> None:
    """Test completion with empty script (simulates error condition)."""
    # Configure fake with empty script to simulate error condition
    completion_ops = FakeCompletion(bash_script="")
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_bash, obj=ctx)

    # Command completes successfully but outputs empty script
    assert result.exit_code == 0
    assert result.output == ""


def test_completion_subprocess_error_handling() -> None:
    """Test completion handles subprocess errors gracefully (integration test context)."""
    # This test verifies error behavior when RealCompletion subprocess fails.
    # Since we now use fakes in unit tests, subprocess errors are tested at integration level.
    # For unit test of error paths, we test with fake returning error-like output.
    completion_ops = FakeCompletion(bash_script="")
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_bash, obj=ctx)

    # With fake returning empty string, command succeeds with empty output
    assert result.exit_code == 0


def test_bash_cmd_with_custom_path() -> None:
    """Test bash completion with custom erk path."""
    completion_ops = FakeCompletion(bash_script="completion script", erk_path="/custom/path/erk")
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_bash, obj=ctx)

    assert result.exit_code == 0
    # Verify path is available via get_erk_path()
    assert completion_ops.get_erk_path() == "/custom/path/erk"


def test_zsh_cmd_with_custom_path() -> None:
    """Test zsh completion with custom erk path."""
    completion_ops = FakeCompletion(zsh_script="#compdef erk", erk_path="/usr/bin/erk")
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_zsh, obj=ctx)

    assert result.exit_code == 0
    assert completion_ops.get_erk_path() == "/usr/bin/erk"


def test_fish_cmd_with_custom_path() -> None:
    """Test fish completion with custom erk path."""
    completion_ops = FakeCompletion(fish_script="complete -c erk", erk_path="./erk")
    ctx = create_test_context(completion=completion_ops)

    runner = CliRunner()
    result = runner.invoke(completion_fish, obj=ctx)

    assert result.exit_code == 0
    assert completion_ops.get_erk_path() == "./erk"
