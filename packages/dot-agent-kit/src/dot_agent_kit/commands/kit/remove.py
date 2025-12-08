"""Remove command for uninstalling kits."""

from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.hooks.installer import remove_hooks
from dot_agent_kit.io.git import resolve_project_dir
from dot_agent_kit.io.state import require_project_config, save_project_config
from dot_agent_kit.models.config import ProjectConfig

# Reusable argument decorator
kit_id_argument = click.argument("kit-id")


def _remove_kit_impl(kit_id: str) -> None:
    """Implementation of kit removal logic."""
    project_dir = resolve_project_dir(Path.cwd())

    # Load project config
    config = require_project_config(project_dir)

    # Check if kit is installed
    if kit_id not in config.kits:
        user_output(
            f"Error: Kit '{kit_id}' not installed in project directory (./.claude)",
        )
        raise SystemExit(1)

    installed = config.kits[kit_id]

    # Remove hooks if present
    hooks_removed = 0
    if installed.hooks:
        hooks_removed = remove_hooks(kit_id, project_dir)

    # Remove artifact files
    removed_count = 0
    failed_count = 0

    for artifact_path in installed.artifacts:
        artifact_file = project_dir / artifact_path
        if artifact_file.exists():
            artifact_file.unlink()
            removed_count += 1
        else:
            # File already removed or doesn't exist
            failed_count += 1

    # Remove kit from config
    new_kits = {k: v for k, v in config.kits.items() if k != kit_id}
    updated_config = ProjectConfig(
        version=config.version,
        kits=new_kits,
    )

    # Save updated config
    save_project_config(project_dir, updated_config)

    # Show success message
    user_output(f"✓ Removed {kit_id} v{installed.version}")
    user_output(f"  Deleted {removed_count} artifact(s)")

    if hooks_removed > 0:
        user_output(f"  Removed {hooks_removed} hook(s)")

    if failed_count > 0:
        user_output(
            f"  Note: {failed_count} artifact(s) were already removed",
        )

    # Remove from registry (non-blocking)
    try:
        from dot_agent_kit.io.registry import remove_kit_from_registry

        remove_kit_from_registry(kit_id, project_dir)
    except Exception as e:
        user_output(f"  Warning: Failed to update registry: {e!s}")


@click.command()
@kit_id_argument
def remove(kit_id: str) -> None:
    """Remove an installed kit (alias: rm).

    This removes all artifacts installed by the kit and updates the configuration.

    Examples:

        # Remove kit from project directory
        dot-agent remove github-workflows
    """
    _remove_kit_impl(kit_id)


@click.command(name="rm", hidden=True)
@kit_id_argument
def rm(kit_id: str) -> None:
    """Remove an installed kit (alias for remove)."""
    _remove_kit_impl(kit_id)
