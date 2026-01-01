"""Pure business logic for init command operations.

This module contains testable functions for detecting project configuration,
discovering presets, and rendering templates, without I/O side effects.
"""

import re
import tomllib
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


def detect_root_project_name(repo_root: Path) -> str | None:
    """Return the declared project name at the repo root, if any.

    Checks root `pyproject.toml`'s `[project].name`. If absent, tries to heuristically
    extract from `setup.py` by matching `name="..."` or `name='...'`.

    Args:
        repo_root: Path to the repository root

    Returns:
        Project name if found, None otherwise

    Example:
        >>> repo_root = Path("/path/to/repo")
        >>> # Assuming pyproject.toml exists with [project] name = "my-project"
        >>> detect_root_project_name(repo_root)
        'my-project'
    """
    root_pyproject = repo_root / "pyproject.toml"
    if root_pyproject.exists():
        data = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
        project = data.get("project") or {}
        name = project.get("name")
        if isinstance(name, str) and name:
            return name

    setup_py = repo_root / "setup.py"
    if setup_py.exists():
        text = setup_py.read_text(encoding="utf-8")
        m = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", text)
        if m:
            return m.group(1)

    return None


def is_repo_named(repo_root: Path, expected_name: str) -> bool:
    """Return True if the root project name matches `expected_name` (case-insensitive).

    Args:
        repo_root: Path to the repository root
        expected_name: Expected project name to match

    Returns:
        True if project name matches (case-insensitive), False otherwise

    Example:
        >>> repo_root = Path("/path/to/repo")
        >>> is_repo_named(repo_root, "dagster")
        True
    """
    name = detect_root_project_name(repo_root)
    return (name or "").lower() == expected_name.lower()


def discover_presets(presets_dir: Path) -> list[str]:
    """Discover available preset names by scanning the presets directory.

    Args:
        presets_dir: Path to the directory containing preset files

    Returns:
        Sorted list of preset names (without .toml extension)

    Example:
        >>> presets_dir = Path("/path/to/erk/presets")
        >>> discover_presets(presets_dir)
        ['dagster', 'generic', 'python']
    """
    if not presets_dir.exists():
        return []

    return sorted(p.stem for p in presets_dir.glob("*.toml") if p.is_file())


def render_config_template(presets_dir: Path, preset: str | None) -> str:
    """Return default config TOML content, optionally using a preset.

    If preset is None, uses the "generic" preset by default.

    Args:
        presets_dir: Path to the directory containing preset files
        preset: Name of the preset to use, or None for "generic"

    Returns:
        Content of the preset file as a string

    Raises:
        ValueError: If the specified preset file doesn't exist

    Example:
        >>> presets_dir = Path("/path/to/erk/presets")
        >>> content = render_config_template(presets_dir, "dagster")
        >>> "trunk_branch" in content
        True
    """
    preset_name = preset if preset is not None else "generic"
    preset_file = presets_dir / f"{preset_name}.toml"

    if not preset_file.exists():
        raise ValueError(f"Preset '{preset_name}' not found at {preset_file}")

    return preset_file.read_text(encoding="utf-8")


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
