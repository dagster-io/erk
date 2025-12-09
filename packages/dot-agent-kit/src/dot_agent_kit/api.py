"""Public API for dot-agent-kit.

This module provides a stable, high-level interface for external tools
(like erk) to use dot-agent-kit as a library. All functions operate on
bundled kits only.

Example usage:
    from pathlib import Path
    from dot_agent_kit.api import install_bundled_kits, sync_installed_kits

    # Install kits during tool initialization
    results = install_bundled_kits(
        project_dir=Path("/path/to/repo"),
        kit_ids=["erk", "devrun", "dignified-python"],
        overwrite=False,
    )

    # Sync kits after tool upgrade
    results = sync_installed_kits(
        project_dir=Path("/path/to/repo"),
        force=True,
    )
"""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.io.state import (
    create_default_config,
    load_project_config,
    save_project_config,
)
from dot_agent_kit.operations.install import install_kit
from dot_agent_kit.operations.sync import sync_all_kits
from dot_agent_kit.sources.bundled import BundledKitSource
from dot_agent_kit.sources.exceptions import KitNotFoundError
from dot_agent_kit.sources.resolver import KitResolver

__all__ = [
    "KitInstallResult",
    "install_bundled_kits",
    "sync_installed_kits",
    "get_bundled_kit_version",
]


@dataclass(frozen=True)
class KitInstallResult:
    """Result of installing or syncing a kit."""

    kit_id: str
    version: str
    artifacts_installed: int
    was_updated: bool


def install_bundled_kits(
    project_dir: Path,
    kit_ids: list[str],
    *,
    overwrite: bool = False,
) -> list[KitInstallResult]:
    """Install bundled kits to project's .claude/ directory.

    This is the primary function for tools like erk to install Claude Code
    artifacts during initialization. It:
    - Creates dot-agent.toml if it doesn't exist
    - Installs specified bundled kits
    - Skips kits that are already installed (unless overwrite=True)
    - Returns results for each kit

    Args:
        project_dir: Root directory of the project (must exist)
        kit_ids: List of bundled kit IDs to install (e.g., ["erk", "devrun"])
        overwrite: Whether to overwrite existing artifacts (default: False)

    Returns:
        List of KitInstallResult for each kit (successful or not)

    Raises:
        FileNotFoundError: If project_dir doesn't exist
        KitNotFoundError: If any kit_id is not a bundled kit
        Exception: For other installation errors (filesystem permissions, etc.)

    Example:
        >>> from pathlib import Path
        >>> from dot_agent_kit.api import install_bundled_kits
        >>> results = install_bundled_kits(
        ...     project_dir=Path("/repo"),
        ...     kit_ids=["erk", "devrun"],
        ... )
        >>> for result in results:
        ...     print(f"{result.kit_id} v{result.version}: {result.artifacts_installed} artifacts")
    """
    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory does not exist: {project_dir}")

    # Load or create config
    config = load_project_config(project_dir)
    if config is None:
        config = create_default_config()

    # Create resolver for bundled kits only
    bundled_source = BundledKitSource()
    resolver = KitResolver(sources=[bundled_source])

    results: list[KitInstallResult] = []

    for kit_id in kit_ids:
        # Check if kit is already installed
        if kit_id in config.kits and not overwrite:
            installed = config.kits[kit_id]
            results.append(
                KitInstallResult(
                    kit_id=kit_id,
                    version=installed.version,
                    artifacts_installed=len(installed.artifacts),
                    was_updated=False,
                )
            )
            continue

        # Resolve and install kit
        try:
            resolved = resolver.resolve(kit_id)
        except KitNotFoundError as e:
            raise KitNotFoundError(kit_id, ["bundled"]) from e

        installed_kit = install_kit(
            resolved=resolved,
            project_dir=project_dir,
            overwrite=overwrite,
        )

        # Update config
        config = config.update_kit(installed_kit)

        results.append(
            KitInstallResult(
                kit_id=kit_id,
                version=installed_kit.version,
                artifacts_installed=len(installed_kit.artifacts),
                was_updated=True,
            )
        )

    # Save updated config
    save_project_config(project_dir, config)

    return results


def sync_installed_kits(
    project_dir: Path,
    *,
    force: bool = False,
) -> list[KitInstallResult]:
    """Sync all installed kits to latest bundled versions.

    This function updates all installed bundled kits to their latest versions.
    Useful when the tool (e.g., erk) is upgraded and bundles new kit versions.

    Args:
        project_dir: Root directory of the project (must exist)
        force: Whether to reinstall even if versions match (default: False)

    Returns:
        List of KitInstallResult for each synced kit

    Raises:
        FileNotFoundError: If project_dir doesn't exist or no dot-agent.toml found
        Exception: For sync errors

    Example:
        >>> from pathlib import Path
        >>> from dot_agent_kit.api import sync_installed_kits
        >>> results = sync_installed_kits(
        ...     project_dir=Path("/repo"),
        ...     force=True,
        ... )
        >>> updated = [r for r in results if r.was_updated]
        >>> print(f"Updated {len(updated)} kits")
    """
    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory does not exist: {project_dir}")

    config = load_project_config(project_dir)
    if config is None:
        raise FileNotFoundError(f"No dot-agent.toml found in: {project_dir}")

    # Create resolver for bundled kits only
    bundled_source = BundledKitSource()
    resolver = KitResolver(sources=[bundled_source])

    # Sync all kits
    sync_results = sync_all_kits(
        config=config,
        project_dir=project_dir,
        resolver=resolver,
        force=force,
    )

    # Convert sync results to API results
    results: list[KitInstallResult] = []
    for sync_result in sync_results:
        results.append(
            KitInstallResult(
                kit_id=sync_result.kit_id,
                version=sync_result.new_version,
                artifacts_installed=sync_result.artifacts_updated,
                was_updated=sync_result.was_updated,
            )
        )

        # Update config with new kit version if updated
        if sync_result.was_updated and sync_result.updated_kit is not None:
            config = config.update_kit(sync_result.updated_kit)

    # Save updated config
    save_project_config(project_dir, config)

    return results


def get_bundled_kit_version(kit_id: str) -> str:
    """Get version of a bundled kit.

    Args:
        kit_id: Bundled kit identifier

    Returns:
        Version string (e.g., "0.3.1")

    Raises:
        KitNotFoundError: If kit_id is not a bundled kit

    Example:
        >>> from dot_agent_kit.api import get_bundled_kit_version
        >>> version = get_bundled_kit_version("erk")
        >>> print(f"erk v{version}")
    """
    bundled_source = BundledKitSource()

    if not bundled_source.can_resolve(kit_id):
        raise KitNotFoundError(kit_id, ["bundled"])

    resolved = bundled_source.resolve(kit_id)
    manifest = load_kit_manifest(resolved.manifest_path)

    return manifest.version
