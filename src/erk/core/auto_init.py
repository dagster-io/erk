"""Auto-initialization logic for erk.

This module handles automatic repository initialization when a user runs
an erk command in a git repo that hasn't been erk-ified yet.

Auto-init triggers when:
- User runs a meaningful erk command (not --help, doctor, init, etc.)
- Current directory is in a git repository
- Repository hasn't been erk-ified yet (.erk/config.toml doesn't exist)

Auto-init does:
- Creates .erk/config.toml with auto-detected preset
- Sets up Claude hooks in .claude/settings.json
- Updates .gitignore with erk patterns
- Syncs managed artifacts (skills, commands, agents, workflows, actions)

Auto-init does NOT:
- Shell integration setup
- Statusline configuration
- Interactive prompts
"""

from pathlib import Path
from typing import Literal

import click

from erk.artifacts.sync import sync_artifacts
from erk.core.init_utils import (
    add_gitignore_entries_non_interactive,
    is_repo_erk_ified,
    is_repo_named,
    render_config_template,
)
from erk.core.release_notes import get_current_version
from erk.core.repo_discovery import (
    NoRepoSentinel,
    discover_repo_or_sentinel,
    ensure_erk_metadata_dir,
)
from erk_shared.git.abc import Git

# Commands that skip auto-init
# These commands should work without requiring repo initialization
SKIP_AUTO_INIT_COMMANDS = frozenset(
    {
        "init",  # User explicitly running init
        "doctor",  # Diagnostic, should work without init
        "completion",  # Shell completion setup
        "upgrade",  # Global tool upgrade
        "admin",  # Admin commands are internal
    }
)


AutoInitResult = Literal["initialized", "already-initialized", "not-in-repo", "skipped"]


def should_auto_init(
    invoked_subcommand: str | None,
    is_help_invoked: bool,
) -> bool:
    """Determine if auto-init should be triggered based on command context.

    Args:
        invoked_subcommand: The subcommand being invoked, or None if bare 'erk'
        is_help_invoked: True if --help/-h was passed

    Returns:
        True if auto-init should be attempted, False otherwise
    """
    # Don't auto-init for bare 'erk' (no subcommand)
    if invoked_subcommand is None:
        return False

    # Don't auto-init for help
    if is_help_invoked:
        return False

    # Don't auto-init for certain commands
    if invoked_subcommand in SKIP_AUTO_INIT_COMMANDS:
        return False

    return True


def _get_presets_dir() -> Path:
    """Get the path to the presets directory."""
    return Path(__file__).parent.parent / "cli" / "presets"


def auto_init_repo(
    *,
    cwd: Path,
    git: Git,
    erk_root: Path,
) -> AutoInitResult:
    """Automatically initialize erk for a repository.

    This is a non-interactive initialization that runs automatically when
    a user runs an erk command in a git repo that hasn't been erk-ified.

    Args:
        cwd: Current working directory
        git: Git gateway for repository operations
        erk_root: Root directory for erk metadata (usually ~/.erk)

    Returns:
        Result indicating what happened:
        - "initialized": Successfully initialized the repo
        - "already-initialized": Repo was already erk-ified
        - "not-in-repo": Not in a git repository
        - "skipped": Auto-init skipped for some reason
    """
    # Discover repository
    repo_or_sentinel = discover_repo_or_sentinel(cwd, erk_root, git)
    if isinstance(repo_or_sentinel, NoRepoSentinel):
        return "not-in-repo"

    repo_root = repo_or_sentinel.root

    # Check if already erk-ified
    if is_repo_erk_ified(repo_root):
        return "already-initialized"

    # Print brief message so user knows what's happening
    click.echo(
        click.style("  ", fg="cyan") + "Initializing erk for this repository...",
        err=True,
    )

    # Create .erk directory
    erk_dir = repo_root / ".erk"
    erk_dir.mkdir(parents=True, exist_ok=True)

    # Ensure metadata directory exists
    ensure_erk_metadata_dir(repo_or_sentinel)

    # Auto-detect preset
    presets_dir = _get_presets_dir()
    is_dagster = is_repo_named(repo_root, "dagster")
    effective_preset = "dagster" if is_dagster else "generic"

    # Write config.toml
    config_content = render_config_template(presets_dir, effective_preset)
    config_path = erk_dir / "config.toml"
    config_path.write_text(config_content, encoding="utf-8")

    # Create required version file
    version_file = erk_dir / "required-erk-uv-tool-version"
    version_file.write_text(f"{get_current_version()}\n", encoding="utf-8")

    # Sync artifacts (skills, commands, agents, workflows, actions, hooks)
    sync_artifacts(repo_root, force=False)

    # Update .gitignore with erk patterns
    add_gitignore_entries_non_interactive(repo_root)

    click.echo(
        click.style("  ✓", fg="green") + " Erk initialized. Run 'erk doctor' to verify setup.",
        err=True,
    )

    return "initialized"
