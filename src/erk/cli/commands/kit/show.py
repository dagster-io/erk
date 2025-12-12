"""Show command for displaying detailed kit information."""

from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.io.registry import load_registry
from erk.kits.io.state import load_project_config
from erk.kits.sources.bundled import BundledKitSource


@click.command()
@click.argument("kit_id")
def show(kit_id: str) -> None:
    """Show detailed information about a kit.

    Displays comprehensive information including:
    - Metadata (name, version, description, license, homepage)
    - Artifacts grouped by type (skills, commands, agents, hooks)
    - Hook definitions with trigger events and descriptions
    - Installation status (installed version vs available version)

    Examples:
        # Show details for a specific kit
        erk kit show gt

        # Show details for another kit
        erk kit show dignified-python
    """
    registry = load_registry()

    # Find kit in registry
    registry_entry = None
    for entry in registry:
        if entry.kit_id == kit_id:
            registry_entry = entry
            break

    if registry_entry is None:
        user_output(f"Error: Kit '{kit_id}' not found in registry")
        raise SystemExit(1)

    # Load kit manifest
    bundled_source = BundledKitSource()
    if not bundled_source.can_resolve(registry_entry.kit_id):
        user_output(
            f"Error: Cannot resolve kit '{kit_id}' from bundled source",
        )
        raise SystemExit(1)

    resolved = bundled_source.resolve(registry_entry.kit_id)
    manifest = load_kit_manifest(resolved.manifest_path)

    # Load installation status
    project_dir = Path.cwd()
    config = load_project_config(project_dir)
    installed_kit = None
    if config is not None and kit_id in config.kits:
        installed_kit = config.kits[kit_id]

    # Display kit information
    _display_metadata(manifest, registry_entry.kit_id)
    _display_artifacts(manifest)
    _display_hooks(manifest)
    _display_installation_status(manifest, installed_kit)


def _display_metadata(manifest, kit_id: str) -> None:
    """Display metadata section."""
    user_output(f"{manifest.name}")
    user_output("=" * len(manifest.name))
    user_output()
    user_output(f"ID:          {kit_id}")
    user_output(f"Version:     {manifest.version}")
    user_output(f"Description: {manifest.description}")

    if manifest.license is not None:
        user_output(f"License:     {manifest.license}")

    if manifest.homepage is not None:
        user_output(f"Homepage:    {manifest.homepage}")

    user_output()


def _display_artifacts(manifest) -> None:
    """Display artifacts section grouped by type."""
    if not manifest.artifacts:
        return

    user_output("Artifacts:")
    user_output("-" * 50)

    # Group and display artifacts by type
    for artifact_type, paths in manifest.artifacts.items():
        if not paths:
            continue

        # Display type header
        type_display = artifact_type.capitalize()
        user_output(f"\n{type_display} ({len(paths)}):")

        # Display each artifact
        for path in paths:
            # Extract readable name from path
            path_obj = Path(path)

            # For standard artifact files (SKILL.md, AGENT.md, COMMAND.md),
            # use the parent directory name instead
            if path_obj.stem.upper() in ["SKILL", "AGENT", "COMMAND", "HOOK"]:
                display_name = path_obj.parent.name
            elif path_obj.suffix == ".md":
                # For other markdown files, use filename without extension
                display_name = path_obj.stem
            else:
                # For directories or other files, use the name
                display_name = path_obj.name

            user_output(f"  • {display_name}")
            user_output(f"    {path}")

    user_output()


def _display_hooks(manifest) -> None:
    """Display hooks section."""
    if not manifest.hooks:
        return

    user_output("Hooks:")
    user_output("-" * 50)

    for hook in manifest.hooks:
        user_output(f"\n{hook.id}")
        user_output(f"  Lifecycle:   {hook.lifecycle}")

        if hook.matcher is not None:
            user_output(f"  Matcher:     {hook.matcher}")

        user_output(f"  Invocation:  {hook.invocation}")
        user_output(f"  Description: {hook.description}")
        user_output(f"  Timeout:     {hook.timeout}s")

    user_output()


def _display_installation_status(manifest, installed_kit) -> None:
    """Display installation status section."""
    user_output("Installation Status:")
    user_output("-" * 50)

    if installed_kit is None:
        user_output("Not installed")
    else:
        user_output(f"Installed:        {installed_kit.version}")
        user_output(f"Available:        {manifest.version}")

        # Check for version mismatch
        if installed_kit.version != manifest.version:
            user_output(
                f"\n⚠️  Version mismatch: installed={installed_kit.version}, "
                f"available={manifest.version}"
            )
            user_output("   Run 'erk kit sync' to update")

    user_output()
