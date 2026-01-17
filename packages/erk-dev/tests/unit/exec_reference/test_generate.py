"""Tests for exec command reference generation."""

from erk_dev.exec_reference.generate import (
    collect_exec_commands,
    generate_exec_reference,
)


def test_collect_exec_commands_returns_all_commands() -> None:
    """Test that collect_exec_commands returns all registered exec commands."""
    commands = collect_exec_commands()

    # Should have at least the commands we know exist
    command_names = [cmd.name for cmd in commands]

    # Check for some well-known commands
    assert "marker" in command_names, "Expected 'marker' command group"
    assert "impl-init" in command_names, "Expected 'impl-init' command"
    assert "impl-signal" in command_names, "Expected 'impl-signal' command"

    # Should have many commands (47+ as of plan writing)
    assert len(commands) >= 40, f"Expected at least 40 commands, got {len(commands)}"


def test_collect_exec_commands_includes_marker_subcommands() -> None:
    """Test that marker command includes its subcommands."""
    commands = collect_exec_commands()

    # Find marker command
    marker_cmd = next((cmd for cmd in commands if cmd.name == "marker"), None)
    assert marker_cmd is not None, "Expected 'marker' command"

    # Check subcommands
    subcommand_names = [sub.name for sub in marker_cmd.subcommands]
    assert "create" in subcommand_names, "Expected 'create' subcommand"
    assert "read" in subcommand_names, "Expected 'read' subcommand"
    assert "exists" in subcommand_names, "Expected 'exists' subcommand"
    assert "delete" in subcommand_names, "Expected 'delete' subcommand"


def test_collect_exec_commands_captures_params() -> None:
    """Test that command parameters are properly captured."""
    commands = collect_exec_commands()

    # Find marker command and its create subcommand
    marker_cmd = next((cmd for cmd in commands if cmd.name == "marker"), None)
    assert marker_cmd is not None

    create_cmd = next((sub for sub in marker_cmd.subcommands if sub.name == "create"), None)
    assert create_cmd is not None

    # Check it has the expected parameters
    param_names = [p.name for p in create_cmd.params]
    assert "name" in param_names, "Expected 'name' argument"
    assert "session_id" in param_names, "Expected 'session_id' option"
    assert "content" in param_names, "Expected 'content' option"


def test_generate_exec_reference_has_summary_and_details() -> None:
    """Test that generate_exec_reference produces expected structure."""
    commands = collect_exec_commands()
    content = generate_exec_reference(commands)

    # Check header
    assert "<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->" in content
    assert "erk exec Commands Reference" in content

    # Check summary section
    assert "## Summary" in content
    assert "| Command | Description |" in content

    # Check commands section
    assert "## Commands" in content

    # Check for specific command documentation
    assert "### marker" in content
    assert "#### create" in content

    # Check for usage and options
    assert "**Usage:**" in content
    assert "**Options:**" in content


def test_generate_exec_reference_includes_option_details() -> None:
    """Test that options include flag names and descriptions."""
    commands = collect_exec_commands()
    content = generate_exec_reference(commands)

    # Check marker create has --session-id documented
    assert "--session-id" in content
    assert "--content" in content


def test_generate_exec_reference_summary_includes_leaf_commands() -> None:
    """Test that summary table includes leaf commands, not groups."""
    commands = collect_exec_commands()
    content = generate_exec_reference(commands)

    # Summary should include "marker create", not just "marker"
    # Look for the pattern in the summary table
    lines = content.split("\n")
    summary_lines = []
    in_summary = False
    for line in lines:
        if "## Summary" in line:
            in_summary = True
        elif line.startswith("## ") and in_summary:
            break
        elif in_summary:
            summary_lines.append(line)

    summary_text = "\n".join(summary_lines)
    assert "marker create" in summary_text, "Summary should include 'marker create'"
    assert "marker read" in summary_text, "Summary should include 'marker read'"
