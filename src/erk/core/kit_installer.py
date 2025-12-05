"""Bridge module for integrating dot-agent-kit with erk.

This module provides erk-specific kit installation functionality,
wrapping the dot-agent-kit public API with erk's workflow requirements.
"""

from pathlib import Path

from erk_shared.output.output import user_output

from dot_agent_kit.api import KitInstallResult, install_bundled_kits, sync_installed_kits
from dot_agent_kit.sources.exceptions import KitNotFoundError

# Default kits to install for erk workflow
# These are core to the erk development experience
DEFAULT_KITS = ["erk", "devrun", "dignified-python", "fake-driven-testing"]


def install_erk_kits(repo_root: Path, *, use_graphite: bool = True) -> list[KitInstallResult]:
    """Install default Claude Code kits for erk workflow.

    This function installs the core kits that enhance the erk development
    experience with Claude Code. It handles:
    - Selecting appropriate kits based on configuration
    - Installing via dot-agent-kit API
    - Providing user feedback
    - Graceful error handling

    Args:
        repo_root: Root directory of the repository
        use_graphite: Whether to include Graphite-specific kit (default: True)

    Returns:
        List of KitInstallResult for successfully installed kits

    Raises:
        Exception: For fatal installation errors (re-raised after logging)
    """
    # Build kit list based on configuration
    kits = DEFAULT_KITS.copy()
    if use_graphite:
        kits.append("gt")

    try:
        results = install_bundled_kits(
            project_dir=repo_root,
            kit_ids=kits,
            overwrite=False,
        )

        # Report successful installations
        newly_installed = [r for r in results if r.was_updated]
        if newly_installed:
            user_output("\nInstalled Claude Code artifacts:")
            for result in newly_installed:
                count = result.artifacts_installed
                plural = "artifacts" if count != 1 else "artifact"
                user_output(f"  ✓ {result.kit_id} v{result.version} ({count} {plural})")

        return results

    except KitNotFoundError as e:
        # Specific error: kit doesn't exist
        user_output(f"Warning: Kit not found: {e}")
        user_output("Continuing without Claude Code artifacts.")
        return []
    except FileNotFoundError as e:
        # Project directory doesn't exist
        user_output(f"Warning: Could not install kits: {e}")
        return []
    except Exception as e:
        # Unexpected error: log and continue (kits are optional)
        user_output(f"Warning: Failed to install Claude Code artifacts: {e}")
        user_output("Continuing init. You can install manually with 'dot-agent kit install'.")
        return []


def sync_erk_kits(repo_root: Path) -> list[KitInstallResult]:
    """Sync all installed erk kits to latest versions.

    This function updates all installed kits to the versions bundled
    with the current erk installation. Typically called during version
    upgrade to keep artifacts in sync.

    Args:
        repo_root: Root directory of the repository

    Returns:
        List of KitInstallResult for synced kits

    Raises:
        FileNotFoundError: If repo_root doesn't exist or no dot-agent.toml found
    """
    # Check that dot-agent.toml exists first
    config_path = repo_root / "dot-agent.toml"
    if not config_path.exists():
        # No kits installed yet, nothing to sync
        return []

    try:
        results = sync_installed_kits(
            project_dir=repo_root,
            force=True,
        )

        # Report updates
        updated = [r for r in results if r.was_updated]
        if updated:
            user_output("\nUpdated Claude Code artifacts:")
            for result in updated:
                count = result.artifacts_installed
                plural = "artifacts" if count != 1 else "artifact"
                user_output(f"  ✓ {result.kit_id} v{result.version} ({count} {plural})")

        return results

    except FileNotFoundError:
        # Config disappeared between check and sync (rare race condition)
        return []
    except Exception as e:
        # Log error but don't fail (sync is best-effort)
        user_output(f"Warning: Could not sync Claude Code artifacts: {e}")
        return []
