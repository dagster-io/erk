"""Install command for installing or updating kits."""

import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import NamedTuple

import click

from erk.kits.cli.output import user_output
from erk.kits.hooks.installer import install_hooks, remove_hooks
from erk.kits.hooks.settings import load_settings, save_settings
from erk.kits.io.git import resolve_project_dir
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.io.state import create_default_config, load_project_config, save_project_config
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.models.installation import InstallationContext
from erk.kits.operations.artifact_operations import create_artifact_operations
from erk.kits.operations.install import install_kit
from erk.kits.operations.user_install import get_installation_context, install_kit_to_project
from erk.kits.sources.bundled import BundledKitSource
from erk.kits.sources.exceptions import (
    KitNotFoundError,
    KitResolutionError,
    ResolverNotConfiguredError,
    SourceAccessError,
)
from erk.kits.sources.resolver import KitResolver, ResolvedKit
from erk.kits.sources.standalone import StandalonePackageSource
from erk.kits.utils.content_hash import is_file_modified


def check_for_local_modifications(
    installed: InstalledKit,
    project_dir: Path,
) -> list[str]:
    """Check which installed artifacts have been locally modified.

    Args:
        installed: The installed kit with artifact hashes
        project_dir: Project root directory

    Returns:
        List of paths to files that have been locally modified
    """
    modified: list[str] = []
    for artifact_path, stored_hash in installed.artifacts.items():
        full_path = project_dir / artifact_path
        if is_file_modified(full_path, stored_hash):
            modified.append(artifact_path)
    return modified


class UpdateCheckResult(NamedTuple):
    """Result of checking for kit updates."""

    has_update: bool
    resolved: ResolvedKit | None
    error_message: str | None


@dataclass(frozen=True)
class UpdateResult:
    """Result of updating an installed kit."""

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


def update_installed_kit(
    kit_id: str,
    installed: InstalledKit,
    resolved: ResolvedKit,
    project_dir: Path,
    force: bool = False,
) -> UpdateResult:
    """Update an installed kit to a new version.

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
        return UpdateResult(
            kit_id=kit_id,
            old_version=old_version,
            new_version=new_version,
            was_updated=False,
            artifacts_updated=0,
            updated_kit=None,
        )

    # Remove old artifacts
    operations = create_artifact_operations()
    operations.remove_artifacts(installed.artifacts, project_dir)

    # Install new version with overwrite enabled
    new_installed = install_kit(
        resolved,
        project_dir,
        overwrite=True,
    )

    return UpdateResult(
        kit_id=kit_id,
        old_version=old_version,
        new_version=new_version,
        was_updated=True,
        artifacts_updated=len(new_installed.artifacts),
        updated_kit=new_installed,
    )


def _handle_update_workflow(
    kit_id: str,
    installed: InstalledKit,
    resolver: KitResolver,
    config: ProjectConfig,
    project_dir: Path,
    force: bool,
) -> bool:
    """Handle the update workflow for an already installed kit.

    Args:
        kit_id: Kit identifier
        installed: Currently installed kit info
        resolver: Kit resolver instance
        config: Project configuration
        project_dir: Project root directory
        force: Whether to force reinstall

    Returns:
        True if kit was updated, False if already up to date

    Raises:
        SystemExit: If resolution fails or kit not found
    """
    check_result = check_for_updates(installed, resolver, force=force)

    # Handle resolution errors - fail loudly rather than assuming up-to-date
    if check_result.error_message:
        user_output(f"Error: Failed to check for updates: {check_result.error_message}")
        raise SystemExit(1)

    # No update available and not forcing - report and exit
    if not check_result.has_update:
        user_output(f"Kit '{kit_id}' is already up to date (v{installed.version})")
        return False

    # resolved must be non-None at this point (error_message would be set otherwise)
    if check_result.resolved is None:
        user_output("Error: Internal error - resolved kit is None")
        raise SystemExit(1)

    # Check for locally modified files before overwriting
    if not force:
        modified_files = check_for_local_modifications(installed, project_dir)
        if modified_files:
            user_output(f"Warning: {len(modified_files)} file(s) have been locally modified:")
            for path in modified_files[:5]:  # Show first 5
                user_output(f"  - {path}")
            if len(modified_files) > 5:
                user_output(f"  ... and {len(modified_files) - 5} more")
            user_output("")
            user_output("Use --force to overwrite local modifications.")
            raise SystemExit(1)

    # Update the kit
    user_output(f"Updating {kit_id} to v{check_result.resolved.version}...")
    result = update_installed_kit(
        kit_id, installed, check_result.resolved, project_dir, force=force
    )

    if not result.was_updated:
        user_output(f"Kit '{kit_id}' was already up to date")
        return False

    # Process successful update
    _process_update_result(kit_id, result, check_result.resolved, config, project_dir)
    return True


def _process_update_result(
    kit_id: str,
    result: UpdateResult,
    resolved: ResolvedKit,
    config: ProjectConfig,
    project_dir: Path,
) -> None:
    """Process the result of a successful kit update.

    Args:
        kit_id: Kit identifier
        result: Update operation result
        resolved: Resolved kit information
        config: Project configuration
        project_dir: Project root directory
    """
    user_output(f"✓ Updated {kit_id}: {result.old_version} → {result.new_version}")
    user_output(f"  Artifacts: {result.artifacts_updated}")

    # Handle hooks atomically
    manifest = load_kit_manifest(resolved.manifest_path)
    hooks_count = _perform_atomic_hook_update(
        kit_id=manifest.name,
        manifest_hooks=manifest.hooks,
        kit_path=resolved.artifacts_base,
        project_dir=project_dir,
    )

    # Save updated config with new hooks
    if result.updated_kit is not None:
        updated_kit = result.updated_kit
        if manifest.hooks:
            updated_kit = replace(updated_kit, hooks=manifest.hooks)
        updated_config = config.update_kit(updated_kit)
        save_project_config(project_dir, updated_config)

        if hooks_count > 0:
            user_output(f"  Installed {hooks_count} hook(s)")

        # Update registry entry with new version (non-blocking)
        try:
            from erk.kits.io.registry import create_kit_registry_file, generate_registry_entry

            entry_content = generate_registry_entry(
                kit_id, updated_kit.version, manifest, updated_kit
            )
            create_kit_registry_file(kit_id, entry_content, project_dir)
            # No need to call add_kit_to_registry - @-include already exists
        except Exception as e:
            user_output(f"  Warning: Failed to update registry: {e!s}")


def _handle_fresh_install(
    kit_id: str,
    resolver: KitResolver,
    config: ProjectConfig,
    context: InstallationContext,
    project_dir: Path,
    force: bool,
) -> None:
    """Handle fresh installation of a kit.

    Args:
        kit_id: Kit identifier
        resolver: Kit resolver instance
        config: Project configuration
        context: Installation context
        project_dir: Project root directory
        force: Whether to force overwrite

    Raises:
        SystemExit: If kit not found
    """
    resolved = resolver.resolve(kit_id)
    if resolved is None:
        user_output(f"Error: Kit '{kit_id}' not found")
        raise SystemExit(1)

    # Load manifest
    manifest = load_kit_manifest(resolved.manifest_path)

    # Install the kit
    user_output(f"Installing {kit_id} v{resolved.version} to {context.get_claude_dir()}...")
    installed_kit = install_kit_to_project(
        resolved,
        context,
        overwrite=force,
        filtered_artifacts=None,  # Always install all artifacts
    )

    # Install hooks atomically
    hooks_count = _perform_atomic_hook_update(
        kit_id=manifest.name,
        manifest_hooks=manifest.hooks,
        kit_path=resolved.artifacts_base,
        project_dir=project_dir,
    )

    # Update installed kit with hooks if present
    if manifest.hooks:
        installed_kit = replace(installed_kit, hooks=manifest.hooks)

    # Update config
    updated_config = config.update_kit(installed_kit)
    save_project_config(project_dir, updated_config)

    # Show success message
    artifact_count = len(installed_kit.artifacts)
    user_output(f"✓ Installed {kit_id} v{installed_kit.version} ({artifact_count} artifacts)")

    if hooks_count > 0:
        user_output(f"  Installed {hooks_count} hook(s)")

    user_output(f"  Location: {context.get_claude_dir()}")

    # Update registry (non-blocking - failure doesn't stop installation)
    try:
        from erk.kits.io.registry import (
            add_kit_to_registry,
            create_kit_registry_file,
            generate_registry_entry,
        )

        entry_content = generate_registry_entry(
            kit_id, installed_kit.version, manifest, installed_kit
        )
        create_kit_registry_file(kit_id, entry_content, project_dir)
        add_kit_to_registry(kit_id, project_dir, installed_kit.version, installed_kit.source_type)
    except Exception as e:
        user_output(f"  Warning: Failed to update registry: {e!s}")


def _perform_atomic_hook_update(
    kit_id: str,
    manifest_hooks: list | None,
    kit_path: Path,
    project_dir: Path,
) -> int:
    """Perform atomic hook update with rollback on failure.

    This ensures that if hook installation fails, the old hooks remain intact.

    Args:
        kit_id: Kit identifier
        manifest_hooks: List of hook definitions from manifest (can be None)
        kit_path: Path to kit directory containing hook scripts
        project_dir: Project root directory

    Returns:
        Count of installed hooks

    Raises:
        Exception: Re-raises any exception after attempting rollback
    """
    # No hooks to install - just remove old ones
    if not manifest_hooks:
        remove_hooks(kit_id, project_dir)
        return 0

    # Save current state for rollback
    settings_path = project_dir / ".claude" / "settings.json"
    hooks_dir = project_dir / ".claude" / "hooks" / kit_id

    # Backup current settings
    original_settings = None
    if settings_path.exists():
        original_settings = load_settings(settings_path)

    # Backup current hooks directory if it exists
    hooks_backup = None
    if hooks_dir.exists():
        with tempfile.TemporaryDirectory() as temp_dir:
            hooks_backup = Path(temp_dir) / "hooks_backup"
            shutil.copytree(hooks_dir, hooks_backup)

            try:
                # Remove old hooks - this modifies settings.json and deletes hooks_dir
                remove_hooks(kit_id, project_dir)

                # Attempt to install new hooks
                hooks_count = install_hooks(
                    kit_id=kit_id,
                    hooks=manifest_hooks,
                    project_root=project_dir,
                )

                return hooks_count

            except Exception as e:
                # Rollback on failure
                user_output(f"  Hook installation failed: {e}")
                user_output("  Attempting to restore previous hooks...")

                # Restore settings if we have a backup
                if original_settings is not None:
                    save_settings(settings_path, original_settings)

                # Restore hooks directory if we have a backup
                if hooks_backup and hooks_backup.exists():
                    if hooks_dir.exists():
                        shutil.rmtree(hooks_dir)
                    shutil.copytree(hooks_backup, hooks_dir)
                    user_output("  Previous hooks restored successfully")

                # Re-raise the original exception
                raise
    else:
        # No existing hooks to backup - simpler flow
        try:
            hooks_count = install_hooks(
                kit_id=kit_id,
                hooks=manifest_hooks,
                project_root=project_dir,
            )
            return hooks_count
        except Exception:
            # Clean up any partial installation and restore settings
            if original_settings is not None:
                save_settings(settings_path, original_settings)
            if hooks_dir.exists():
                shutil.rmtree(hooks_dir)
            raise


def _handle_install_all(
    *,
    resolver: KitResolver,
    config: ProjectConfig,
    context: InstallationContext,
    project_dir: Path,
    force: bool,
) -> None:
    """Install or update all bundled kits.

    Args:
        resolver: Kit resolver to find kit sources
        config: Project configuration
        context: Installation context
        project_dir: Project root directory
        force: If True, force reinstall even if up to date
    """
    # Get list of all bundled kits
    bundled_source = BundledKitSource()
    kit_ids = bundled_source.list_available()

    if not kit_ids:
        user_output("No bundled kits found")
        return

    user_output(f"Installing {len(kit_ids)} bundled kits...")

    installed_count = 0
    updated_count = 0
    skipped_count = 0
    errors: list[tuple[str, str]] = []

    for kit_id in sorted(kit_ids):
        try:
            if kit_id in config.kits:
                # Kit already installed - update workflow
                result = _handle_update_workflow(
                    kit_id=kit_id,
                    installed=config.kits[kit_id],
                    resolver=resolver,
                    config=config,
                    project_dir=project_dir,
                    force=force,
                )
                # Reload config after update
                loaded_config = load_project_config(project_dir)
                if loaded_config is not None:
                    config = loaded_config
                if result:
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                # Fresh install
                _handle_fresh_install(
                    kit_id=kit_id,
                    resolver=resolver,
                    config=config,
                    context=context,
                    project_dir=project_dir,
                    force=force,
                )
                # Reload config after install
                loaded_config = load_project_config(project_dir)
                if loaded_config is not None:
                    config = loaded_config
                installed_count += 1
        except Exception as e:
            errors.append((kit_id, str(e)))

    # Summary
    user_output("")
    user_output("Summary:")
    if installed_count > 0:
        user_output(f"  {installed_count} kits installed")
    if updated_count > 0:
        user_output(f"  {updated_count} kits updated")
    if skipped_count > 0:
        user_output(f"  {skipped_count} kits already up to date")
    if errors:
        user_output(f"  {len(errors)} errors:")
        for kit_id, error in errors:
            user_output(f"    {kit_id}: {error}")
        raise SystemExit(1)

    user_output("Done")


@click.command()
@click.argument("kit-id", required=False)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinstall even if already up to date",
)
@click.option(
    "--all",
    "install_all",
    is_flag=True,
    help="Install or update all bundled kits",
)
def install(kit_id: str | None, force: bool, install_all: bool) -> None:
    """Install a kit or update it if already installed.

    This command is idempotent - it will install the kit if not present,
    or update it to the latest version if already installed.

    Examples:

        # Install or update a kit
        erk kit install devrun

        # Force reinstall a kit
        erk kit install devrun --force

        # Install or update all bundled kits
        erk kit install --all
    """
    # Validate arguments
    if install_all and kit_id:
        user_output("Error: Cannot specify both kit-id and --all")
        raise SystemExit(1)
    if not install_all and not kit_id:
        user_output("Error: Must specify kit-id or use --all")
        raise SystemExit(1)

    # Get installation context
    project_dir = resolve_project_dir(Path.cwd())
    context = get_installation_context(project_dir)

    # Load project config
    loaded_config = load_project_config(project_dir)
    config = loaded_config if loaded_config is not None else create_default_config()

    # Resolve kit source (use both bundled and package sources)
    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])

    if install_all:
        # Install all bundled kits
        _handle_install_all(
            resolver=resolver,
            config=config,
            context=context,
            project_dir=project_dir,
            force=force,
        )
    else:
        # Single kit install (kit_id is guaranteed non-None by validation above)
        assert kit_id is not None  # Guaranteed by validation at function start
        if kit_id in config.kits:
            # Kit already installed - update workflow
            _handle_update_workflow(
                kit_id=kit_id,
                installed=config.kits[kit_id],
                resolver=resolver,
                config=config,
                project_dir=project_dir,
                force=force,
            )
        else:
            # Kit not installed - fresh install workflow
            _handle_fresh_install(
                kit_id=kit_id,
                resolver=resolver,
                config=config,
                context=context,
                project_dir=project_dir,
                force=force,
            )
