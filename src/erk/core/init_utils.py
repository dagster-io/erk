"""Pure business logic for init command operations.

This module contains testable functions for gitignore management.
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
