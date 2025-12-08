"""Install command for installing or updating kits."""

import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.hooks.installer import install_hooks, remove_hooks
from dot_agent_kit.hooks.settings import load_settings, save_settings
from dot_agent_kit.io.git import resolve_project_dir
from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.io.state import create_default_config, load_project_config, save_project_config
from dot_agent_kit.models.config import InstalledKit, ProjectConfig
from dot_agent_kit.models.installation import InstallationContext
from dot_agent_kit.operations.sync import SyncResult, check_for_updates, sync_kit
from dot_agent_kit.operations.user_install import get_installation_context, install_kit_to_project
from dot_agent_kit.sources.bundled import BundledKitSource
from dot_agent_kit.sources.resolver import KitResolver, ResolvedKit
from dot_agent_kit.sources.standalone import StandalonePackageSource


def _all_artifacts_are_symlinks(installed: InstalledKit, project_dir: Path) -> bool:
    """Check if all installed artifacts are symlinks.

    Args:
        installed: Installed kit information
        project_dir: Project root directory

    Returns:
        True if all artifacts exist and are symlinks, False otherwise
    """
    if not installed.artifacts:
        return False

    for artifact_path in installed.artifacts:
        full_path = project_dir / artifact_path
        if not full_path.exists():
            return False
        if not full_path.is_symlink():
            return False

    return True


def _handle_update_workflow(
    kit_id: str,
    installed: InstalledKit,
    resolver: KitResolver,
    config: ProjectConfig,
    project_dir: Path,
    force: bool,
) -> None:
    """Handle the update workflow for an already installed kit.

    Args:
        kit_id: Kit identifier
        installed: Currently installed kit info
        resolver: Kit resolver instance
        config: Project configuration
        project_dir: Project root directory
        force: Whether to force reinstall

    Raises:
        SystemExit: If resolution fails or kit not found
    """
    # Skip reinstall if artifacts are already symlinks (dev_mode)
    if _all_artifacts_are_symlinks(installed, project_dir):
        user_output(
            f"ℹ Kit '{kit_id}' already installed as symlinks (dev_mode)",
        )
        user_output("  No action needed - edits to .claude/ already affect source")
        return

    check_result = check_for_updates(installed, resolver, force=force)

    # Handle resolution errors - fail loudly rather than assuming up-to-date
    if check_result.error_message:
        user_output(f"Error: Failed to check for updates: {check_result.error_message}")
        raise SystemExit(1)

    # No update available and not forcing - report and exit
    if not check_result.has_update:
        user_output(f"Kit '{kit_id}' is already up to date (v{installed.version})")
        return

    # resolved must be non-None at this point (error_message would be set otherwise)
    if check_result.resolved is None:
        user_output("Error: Internal error - resolved kit is None")
        raise SystemExit(1)

    # Update the kit using sync
    user_output(f"Updating {kit_id} to v{check_result.resolved.version}...")
    result = sync_kit(kit_id, installed, check_result.resolved, project_dir, force=force)

    if not result.was_updated:
        user_output(f"Kit '{kit_id}' was already up to date")
        return

    # Process successful update
    _process_update_result(kit_id, result, check_result.resolved, config, project_dir)


def _process_update_result(
    kit_id: str,
    result: SyncResult,
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
            from dot_agent_kit.io.registry import create_kit_registry_file, generate_registry_entry

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
        from dot_agent_kit.io.registry import (
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


@click.command()
@click.argument("kit-id")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinstall even if already up to date",
)
def install(kit_id: str, force: bool) -> None:
    """Install a kit or update it if already installed.

    This command is idempotent - it will install the kit if not present,
    or update it to the latest version if already installed.

    Examples:

        # Install or update a kit
        dot-agent kit install devrun

        # Force reinstall a kit
        dot-agent kit install devrun --force
    """
    # Get installation context
    project_dir = resolve_project_dir(Path.cwd())
    context = get_installation_context(project_dir)

    # Load project config
    loaded_config = load_project_config(project_dir)
    config = loaded_config if loaded_config is not None else create_default_config()

    # Resolve kit source (use both bundled and package sources)
    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])

    # Route to appropriate workflow
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
