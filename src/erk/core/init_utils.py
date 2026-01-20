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


def build_envrc_example_content() -> str:
    """Build .envrc.example template content (committed to git).

    This template shows users the structure without shell-specific completions.
    Users copy this to .envrc and customize for their shell.

    Returns:
        Content for .envrc.example file
    """
    return """\
# .envrc.example - Copy to .envrc and customize
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load erk completions (uncomment for your shell)
# source <(erk completion bash)
# source <(erk completion zsh)
"""


def build_envrc_content(shell: str) -> str:
    """Build .envrc content with shell-specific completions.

    Args:
        shell: Shell type ("bash" or "zsh")

    Returns:
        Content for .envrc file with appropriate completion command
    """
    return f"""\
# .envrc - Local direnv configuration
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load erk completions ({shell})
source <(erk completion {shell})
"""
