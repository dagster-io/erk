"""Sync command for synchronizing installed kits with their sources."""

from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.io.git import resolve_project_dir
from erk.kits.io.registry import rebuild_registry
from erk.kits.io.state import require_project_config, save_project_config
from erk.kits.operations.sync import check_for_updates, sync_all_kits, sync_kit
from erk.kits.sources.bundled import BundledKitSource
from erk.kits.sources.resolver import KitResolver
from erk.kits.sources.standalone import StandalonePackageSource


@click.command()
@click.argument("kit-id", required=False)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed sync information",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinstall even if versions match",
)
def sync(kit_id: str | None, verbose: bool, force: bool) -> None:
    """Sync installed kits with their sources and rebuild registry.

    This command updates one or all installed kits to their latest versions
    and automatically rebuilds the kit documentation registry. Use 'install'
    for installing/updating a specific kit, and 'sync' for bulk update
    operations across all installed kits or for repairing registry state.

    Examples:
        # Sync all installed kits and rebuild registry
        erk kit sync

        # Sync a specific kit and update registry
        erk kit sync github-workflows

        # Force sync all kits (reinstall even if up to date)
        erk kit sync --force

        # Repair registry (sync with no updates)
        erk kit sync
    """
    project_dir = resolve_project_dir(Path.cwd())

    config = require_project_config(project_dir)

    if len(config.kits) == 0:
        user_output("No kits installed")
        return

    resolver = KitResolver(sources=[BundledKitSource(), StandalonePackageSource()])

    # Sync specific kit or all kits
    if kit_id is not None:
        if kit_id not in config.kits:
            user_output(f"Error: Kit '{kit_id}' not installed")
            raise SystemExit(1)

        installed = config.kits[kit_id]
        check_result = check_for_updates(installed, resolver, force=force)

        if check_result.error_message:
            error_msg = f"Error: Failed to check for updates: {check_result.error_message}"
            user_output(error_msg)
            raise SystemExit(1)

        if not check_result.has_update or check_result.resolved is None:
            user_output(f"Kit '{kit_id}' is up to date")
            return

        result = sync_kit(kit_id, installed, check_result.resolved, project_dir, force=force)

        if result.was_updated:
            user_output(f"✓ Updated {kit_id}: {result.old_version} → {result.new_version}")
            if verbose:
                user_output(f"  Artifacts: {result.artifacts_updated}")

            # Save updated config
            if result.updated_kit is not None:
                updated_config = config.update_kit(result.updated_kit)
                save_project_config(project_dir, updated_config)

                # Rebuild registry to reflect updated kit
                rebuild_registry(project_dir, updated_config)
                if verbose:
                    user_output("  Registry updated")

    else:
        # Sync all kits
        results = sync_all_kits(config, project_dir, resolver, force=force)

        updated_count = sum(1 for r in results if r.was_updated)

        if verbose or updated_count > 0:
            for result in results:
                if result.was_updated:
                    user_output(f"✓ {result.kit_id}: {result.old_version} → {result.new_version}")
                elif verbose:
                    user_output(f"  {result.kit_id}: up to date")

        # Save updated config if any kits were updated
        updated_config = config
        if updated_count > 0:
            for result in results:
                if result.was_updated and result.updated_kit is not None:
                    updated_config = updated_config.update_kit(result.updated_kit)
            save_project_config(project_dir, updated_config)

        # Always rebuild registry (useful for repairing registry state)
        rebuild_registry(project_dir, updated_config)
        if verbose:
            user_output("Registry rebuilt")

        if updated_count == 0:
            user_output("All kits are up to date")
        else:
            user_output(f"\nUpdated {updated_count} kit(s)")
