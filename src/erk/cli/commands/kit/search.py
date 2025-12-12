"""Search command for finding kits in the registry."""

import click

from erk.kits.cli.list_formatting import (
    format_item_name,
    format_kit_reference,
    format_metadata,
    format_section_header,
)
from erk.kits.cli.output import user_output
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.io.registry import load_registry
from erk.kits.models.types import SOURCE_TYPE_BUNDLED
from erk.kits.sources.bundled import BundledKitSource


@click.command()
@click.argument("query", required=False)
def search(query: str | None) -> None:
    """Search for kits or list all available bundled kits.

    When no query is provided, lists all available kits.
    When a query is provided, searches kit names, descriptions, and IDs.

    Examples:
        # List all available bundled kits
        erk kit search

        # Search for specific kits
        erk kit search github

        # Search by description
        erk kit search "workflow"
    """
    registry = load_registry()

    if len(registry) == 0:
        user_output("Registry is empty")
        return

    # Filter by query if provided
    if query is not None:
        query_lower = query.lower()
        filtered = [
            entry
            for entry in registry
            if query_lower in entry.kit_id.lower() or query_lower in entry.description.lower()
        ]
    else:
        filtered = registry

    if len(filtered) == 0:
        if query:
            user_output(f"No kits found matching '{query}'")
        else:
            user_output("No kits available")
        return

    # Display results
    if query:
        user_output(format_section_header(f"Found {len(filtered)} kit(s) matching '{query}':"))
    else:
        user_output(format_section_header(f"Available kits ({len(filtered)}):"))

    user_output()

    bundled_source = BundledKitSource()

    for entry in filtered:
        # Load manifest to get version and artifact counts
        version_str = ""
        artifacts_str = ""

        if entry.source_type == SOURCE_TYPE_BUNDLED and bundled_source.can_resolve(entry.kit_id):
            resolved = bundled_source.resolve(entry.kit_id)
            manifest = load_kit_manifest(resolved.manifest_path)

            version_str = f" {format_kit_reference(entry.kit_id, manifest.version)}"

            # Count artifacts by type
            artifact_counts = []
            for artifact_type, paths in manifest.artifacts.items():
                count = len(paths)
                if count > 0:
                    # Use singular or plural form based on count
                    type_name = artifact_type
                    if count == 1:
                        # Singularize: remove trailing 's' if present
                        if type_name.endswith("s"):
                            type_name = type_name[:-1]
                    else:
                        # Pluralize: add 's' if not already present
                        if not type_name.endswith("s"):
                            type_name = type_name + "s"
                    artifact_counts.append(f"{count} {type_name}")

            if artifact_counts:
                artifacts_str = f" • {format_metadata(', '.join(artifact_counts))}"

        kit_name = format_item_name(entry.kit_id)
        user_output(f"  {kit_name}{version_str}")
        description = format_metadata(entry.description)
        user_output(f"    → {description}{artifacts_str}")
        user_output()
