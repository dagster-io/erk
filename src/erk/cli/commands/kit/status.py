"""Status command for showing installed kits."""

from pathlib import Path

import click

from erk.kits.cli.list_formatting import (
    format_item_name,
    format_kit_reference,
    format_metadata,
    format_section_header,
)
from erk.kits.cli.output import user_output
from erk.kits.io.discovery import discover_installed_artifacts
from erk.kits.io.state import require_project_config

# Reusable option decorator
verbose_option = click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed installation information",
)


def _show_status(verbose: bool) -> None:
    """Implementation of status display logic."""
    project_dir = Path.cwd()

    # Load project config for managed kits
    project_config = require_project_config(project_dir)

    # Discover artifacts in filesystem
    discovered = discover_installed_artifacts(project_dir, project_config)

    # Determine managed vs unmanaged
    managed_kits = set(project_config.kits.keys()) if project_config else set()
    all_installed = set(discovered.keys())
    unmanaged_kits = all_installed - managed_kits

    # Display managed kits section
    user_output(format_section_header("Managed Kits:"))
    if managed_kits and project_config:
        for kit_id in sorted(managed_kits):
            kit = project_config.kits[kit_id]
            kit_name = format_item_name(kit_id)
            version_ref = format_kit_reference(kit_id, kit.version)
            source = format_metadata(f"({kit.source_type})")
            user_output(f"  {kit_name} {version_ref} {source}")
            if verbose:
                artifact_types = discovered.get(kit_id, set())
                if artifact_types:
                    types_str = format_metadata(", ".join(sorted(artifact_types)))
                    user_output(f"    Artifacts: {types_str}")
    else:
        user_output(f"  {format_metadata('(none)')}")

    user_output()

    # Display unmanaged artifacts section
    user_output(format_section_header("Unmanaged Artifacts:"))
    if unmanaged_kits:
        for kit_id in sorted(unmanaged_kits):
            artifact_types = discovered[kit_id]
            types_str = format_metadata(", ".join(sorted(artifact_types)))
            kit_name = format_item_name(kit_id)
            user_output(f"  {kit_name} ({types_str})")
    else:
        user_output(f"  {format_metadata('(none)')}")

    user_output(
        f"\n{format_metadata('Use dot-agent artifact list for detailed artifact inspection')}"
    )


@click.command()
@verbose_option
def status(verbose: bool) -> None:
    """Show status of kits and artifacts (alias: st).

    Displays managed kits (tracked in config) and unmanaged artifacts
    (present in .claude/ but not tracked).
    """
    _show_status(verbose)


@click.command(name="st", hidden=True)
@verbose_option
def st(verbose: bool) -> None:
    """Show status of kits and artifacts (alias for status)."""
    _show_status(verbose)
