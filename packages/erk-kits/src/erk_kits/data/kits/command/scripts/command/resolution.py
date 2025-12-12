"""Command resolution for Claude Code slash commands."""

from pathlib import Path

from erk_kits.data.kits.command.scripts.command.models import (
    CommandNotFoundError,
)


def resolve_command_file(command_name: str, cwd: Path) -> Path:
    """Resolve command name to its file path.

    Supports both flat and namespaced commands:
    - "ensure-ci" -> .claude/commands/ensure-ci.md
    - "gt:submit-branch" -> .claude/commands/gt/submit-branch.md

    Args:
        command_name: Command name (e.g., "ensure-ci" or "gt:submit-branch")
        cwd: Current working directory to search from

    Returns:
        Absolute path to command file

    Raises:
        CommandNotFoundError: If command file not found
    """
    # Parse namespace if present
    if ":" in command_name:
        namespace, name = command_name.split(":", 1)
        namespaced_path = cwd / ".claude" / "commands" / namespace / f"{name}.md"

        # Check namespaced path first
        if namespaced_path.exists():
            return namespaced_path.resolve()

    # Check flat path
    flat_path = cwd / ".claude" / "commands" / f"{command_name}.md"
    if flat_path.exists():
        return flat_path.resolve()

    # Not found
    raise CommandNotFoundError(f"Command '{command_name}' not found in .claude/commands/")
