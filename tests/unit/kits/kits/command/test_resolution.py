"""Tests for command resolution logic."""

from pathlib import Path

import pytest

from erk_kits.data.kits.command.scripts.command.models import (
    CommandNotFoundError,
)
from erk_kits.data.kits.command.scripts.command.resolution import (
    resolve_command_file,
)


def test_resolves_flat_commands(tmp_path: Path) -> None:
    """Test resolution of flat commands in .claude/commands/."""
    # Setup: Create flat command file
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    test_command = commands_dir / "test.md"
    test_command.write_text("# Test Command")

    # Execute
    result = resolve_command_file("test", tmp_path)

    # Verify
    assert result == test_command.resolve()


def test_resolves_namespaced_commands(tmp_path: Path) -> None:
    """Test resolution of namespaced commands in .claude/commands/<namespace>/."""
    # Setup: Create namespaced command file
    commands_dir = tmp_path / ".claude" / "commands" / "gt"
    commands_dir.mkdir(parents=True)
    submit_branch = commands_dir / "submit-branch.md"
    submit_branch.write_text("# Submit Branch")

    # Execute
    result = resolve_command_file("gt:submit-branch", tmp_path)

    # Verify
    assert result == submit_branch.resolve()


def test_raises_command_not_found_for_missing_commands(tmp_path: Path) -> None:
    """Test that missing commands raise CommandNotFoundError."""
    # Setup: Create empty commands directory
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Execute & Verify
    with pytest.raises(CommandNotFoundError) as exc_info:
        resolve_command_file("nonexistent", tmp_path)

    assert "nonexistent" in str(exc_info.value)
    assert ".claude/commands/" in str(exc_info.value)


def test_handles_malformed_command_names_gracefully(tmp_path: Path) -> None:
    """Test that malformed command names are handled gracefully."""
    # Setup: Create commands directory
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    # Execute & Verify: Multiple colons
    with pytest.raises(CommandNotFoundError):
        resolve_command_file("foo:bar:baz", tmp_path)

    # Execute & Verify: Empty namespace
    with pytest.raises(CommandNotFoundError):
        resolve_command_file(":command", tmp_path)

    # Execute & Verify: Empty command name
    with pytest.raises(CommandNotFoundError):
        resolve_command_file("namespace:", tmp_path)


def test_prefers_namespaced_over_flat(tmp_path: Path) -> None:
    """Test that namespaced paths are checked before flat paths."""
    # Setup: Create both flat and namespaced versions
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    flat_command = commands_dir / "test.md"
    flat_command.write_text("# Flat Command")

    namespaced_dir = commands_dir / "ns"
    namespaced_dir.mkdir(parents=True)
    namespaced_command = namespaced_dir / "test.md"
    namespaced_command.write_text("# Namespaced Command")

    # Execute: Request namespaced version
    result = resolve_command_file("ns:test", tmp_path)

    # Verify: Gets namespaced, not flat
    assert result == namespaced_command.resolve()


def test_falls_back_to_flat_when_namespace_missing(tmp_path: Path) -> None:
    """Test fallback to flat path when namespaced path doesn't exist."""
    # Setup: Create only flat command
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    flat_command = commands_dir / "test:fallback.md"
    flat_command.write_text("# Flat Command with colon in name")

    # Execute: Request with what looks like namespace
    result = resolve_command_file("test:fallback", tmp_path)

    # Verify: Falls back to flat
    assert result == flat_command.resolve()
