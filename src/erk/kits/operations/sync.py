"""Sync operations for kits."""

from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from erk.kits.cli.output import user_output
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.operations.artifact_operations import create_artifact_operations
from erk.kits.operations.install import install_kit
from erk.kits.sources.exceptions import (
    KitNotFoundError,
    KitResolutionError,
    ResolverNotConfiguredError,
    SourceAccessError,
)
from erk.kits.sources.resolver import KitResolver, ResolvedKit


class UpdateCheckResult(NamedTuple):
    """Result of checking for kit updates."""

    has_update: bool
    resolved: ResolvedKit | None
    error_message: str | None


@dataclass(frozen=True)
class SyncResult:
    """Result of syncing a kit."""

    kit_id: str
    old_version: str
    new_version: str
    was_updated: bool
    artifacts_updated: int
    updated_kit: InstalledKit | None = None


def check_for_updates(
    installed: InstalledKit,
    resolver: KitResolver,
    force: bool = False,
) -> UpdateCheckResult:
    """Check if an installed kit has updates available.

    Args:
        installed: The currently installed kit
        resolver: Kit resolver to find the source
        force: If True, always return True (forces reinstall regardless of version)

    Returns:
        UpdateCheckResult with has_update, resolved kit, and error message
    """
    try:
        resolved = resolver.resolve(installed.kit_id)
    except KitNotFoundError as e:
        # Kit was removed from all sources
        return UpdateCheckResult(
            has_update=False,
            resolved=None,
            error_message=f"Kit no longer available: {e}",
        )
    except ResolverNotConfiguredError as e:
        # Resolver configuration changed (e.g., BundledKitSource removed)
        return UpdateCheckResult(
            has_update=False,
            resolved=None,
            error_message=f"Resolver configuration changed: {e}",
        )
    except SourceAccessError as e:
        # Network or filesystem access failed
        return UpdateCheckResult(
            has_update=False,
            resolved=None,
            error_message=f"Source access failed: {e}",
        )
    except KitResolutionError as e:
        # Other resolution errors
        return UpdateCheckResult(
            has_update=False,
            resolved=None,
            error_message=f"Resolution error: {e}",
        )

    if force:
        # Force mode: always consider as having an update
        return UpdateCheckResult(has_update=True, resolved=resolved, error_message=None)

    manifest = load_kit_manifest(resolved.manifest_path)

    # Simple version comparison (should use semver in production)
    has_update = manifest.version != installed.version

    return UpdateCheckResult(has_update=has_update, resolved=resolved, error_message=None)


def sync_kit(
    kit_id: str,
    installed: InstalledKit,
    resolved: ResolvedKit,
    project_dir: Path,
    force: bool = False,
) -> SyncResult:
    """Sync an installed kit with its source.

    Args:
        kit_id: The kit identifier
        installed: The currently installed kit
        resolved: The resolved kit from the source
        project_dir: Project directory path
        force: If True, reinstall even if versions match
    """
    old_version = installed.version
    manifest = load_kit_manifest(resolved.manifest_path)
    new_version = manifest.version

    if old_version == new_version and not force:
        return SyncResult(
            kit_id=kit_id,
            old_version=old_version,
            new_version=new_version,
            was_updated=False,
            artifacts_updated=0,
            updated_kit=None,
        )

    # Remove old artifacts using appropriate strategy
    operations = create_artifact_operations(project_dir, resolved)
    skipped = operations.remove_artifacts(installed.artifacts, project_dir)

    # Report skipped artifacts
    if skipped:
        user_output("  Skipping symlinked artifacts in dev mode:")
        for artifact_path in skipped:
            user_output(f"    {artifact_path}")

    # Install new version with overwrite enabled
    new_installed = install_kit(
        resolved,
        project_dir,
        overwrite=True,
    )

    return SyncResult(
        kit_id=kit_id,
        old_version=old_version,
        new_version=new_version,
        was_updated=True,
        artifacts_updated=len(new_installed.artifacts),
        updated_kit=new_installed,
    )


def sync_all_kits(
    config: ProjectConfig,
    project_dir: Path,
    resolver: KitResolver,
    force: bool = False,
) -> list[SyncResult]:
    """Sync all installed kits.

    Args:
        config: Project configuration
        project_dir: Project directory path
        resolver: Kit resolver
        force: If True, reinstall even if versions match
    """
    results: list[SyncResult] = []

    for kit_id, installed in config.kits.items():
        check_result = check_for_updates(installed, resolver, force=force)

        if not check_result.has_update or check_result.resolved is None:
            results.append(
                SyncResult(
                    kit_id=kit_id,
                    old_version=installed.version,
                    new_version=installed.version,
                    was_updated=False,
                    artifacts_updated=0,
                    updated_kit=None,
                )
            )
            continue

        sync_result = sync_kit(kit_id, installed, check_result.resolved, project_dir, force=force)
        results.append(sync_result)

    return results
