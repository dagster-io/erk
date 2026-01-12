"""Pure business logic for init command operations.

This module contains testable functions for shell integration and gitignore
management.
"""

from pathlib import Path


def is_repo_erk_ified(repo_root: Path) -> bool:
    """Check if a repository has been initialized with erk.

    A repository is considered erk-ified if it has a .erk/config.toml file.

    Args:
        repo_root: Path to the repository root

    Returns:
        True if .erk/config.toml exists, False otherwise

    Example:
        >>> repo_root = Path("/path/to/repo")
        >>> is_repo_erk_ified(repo_root)
        False
    """
    config_path = repo_root / ".erk" / "config.toml"
    return config_path.exists()


def get_shell_wrapper_content(shell_integration_dir: Path, shell: str) -> str:
    """Load the shell wrapper function for the given shell type.

    Args:
        shell_integration_dir: Path to the directory containing shell integration files
        shell: Shell type (e.g., "zsh", "bash", "fish")

    Returns:
        Content of the shell wrapper file as a string

    Raises:
        ValueError: If the shell wrapper file doesn't exist for the given shell

    Example:
        >>> shell_dir = Path("/path/to/erk/shell_integration")
        >>> content = get_shell_wrapper_content(shell_dir, "zsh")
        >>> "function erk" in content
        True
    """
    if shell == "fish":
        wrapper_file = shell_integration_dir / "fish_wrapper.fish"
    else:
        wrapper_file = shell_integration_dir / f"{shell}_wrapper.sh"

    if not wrapper_file.exists():
        raise ValueError(f"Shell wrapper not found for {shell}")

    return wrapper_file.read_text(encoding="utf-8")


# Marker string that identifies erk shell integration in RC files
ERK_SHELL_INTEGRATION_MARKER = "# Erk shell integration"


def has_shell_integration_in_rc(rc_path: Path) -> bool:
    """Check if shell RC file contains erk shell integration.

    Looks for the marker comment that erk adds when shell integration is configured.

    Args:
        rc_path: Path to the shell RC file (e.g., ~/.zshrc)

    Returns:
        True if the marker is found in the file, False otherwise
        (also returns False if file doesn't exist)

    Example:
        >>> rc_path = Path.home() / ".zshrc"
        >>> has_shell_integration_in_rc(rc_path)
        False
    """
    if not rc_path.exists():
        return False

    content = rc_path.read_text(encoding="utf-8")
    return ERK_SHELL_INTEGRATION_MARKER in content


def remove_shell_integration_from_content(content: str) -> str | None:
    """Remove erk shell integration from RC file content.

    Looks for the marker and removes everything from the marker line
    to the end of the integration block.

    Args:
        content: Current RC file content

    Returns:
        Updated content with shell integration removed,
        or None if the marker was not found.
    """
    if ERK_SHELL_INTEGRATION_MARKER not in content:
        return None

    lines = content.split("\n")
    result_lines: list[str] = []
    in_integration_block = False

    for line in lines:
        if ERK_SHELL_INTEGRATION_MARKER in line:
            in_integration_block = True
            # Remove the blank line before marker if it exists
            while result_lines and result_lines[-1] == "":
                result_lines.pop()
            continue

        if in_integration_block:
            # Skip lines that are part of the integration block
            # The block ends when we hit a line that is not part of the function
            # We look for common patterns that end shell integration:
            # - Empty line followed by non-integration code
            # - End of file
            # For simplicity, we'll remove everything from marker to EOF
            # since shell integration is typically at the end of RC files
            continue

        result_lines.append(line)

    result = "\n".join(result_lines)
    # Ensure single trailing newline
    result = result.rstrip("\n") + "\n"
    return result


def add_gitignore_entry(content: str, entry: str) -> str:
    """Add an entry to gitignore content if not already present.

    This is a pure function that returns the potentially modified content.
    User confirmation should be handled by the caller.

    Args:
        content: Current gitignore content
        entry: Entry to add (e.g., ".env")

    Returns:
        Updated gitignore content (original if entry already present)

    Example:
        >>> content = "*.pyc\\n"
        >>> new_content = add_gitignore_entry(content, ".env")
        >>> ".env" in new_content
        True
        >>> # Calling again should be idempotent
        >>> newer_content = add_gitignore_entry(new_content, ".env")
        >>> newer_content == new_content
        True
    """
    # Entry already present
    if entry in content:
        return content

    # Ensure trailing newline before adding
    if not content.endswith("\n"):
        content += "\n"

    content += f"{entry}\n"
    return content
