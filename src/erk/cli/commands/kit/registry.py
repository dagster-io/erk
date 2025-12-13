"""Registry management commands."""

from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.io.state import require_project_config


@click.group()
def registry() -> None:
    """View and validate kit documentation registry.

    Commands for inspecting the kit documentation registry that provides
    agent-facing documentation for installed kits.

    Note: The registry is automatically maintained by 'kit install'.
    """


@registry.command()
def show() -> None:
    """Display current registry contents.

    Shows the contents of the kit-registry.md file, which aggregates
    all installed kit documentation entries.
    """
    project_dir = Path.cwd()
    registry_path = project_dir / ".erk" / "kits" / "kit-registry.md"

    if not registry_path.exists():
        user_output("No registry found")
        user_output("Run 'erk kit install <kit-id>' to create the registry")
        raise SystemExit(1)

    content = registry_path.read_text(encoding="utf-8")
    click.echo(content)


@registry.command()
def validate() -> None:
    """Verify registry matches installed kits.

    Checks that:
    - All installed kits have registry entries
    - All registry entries correspond to installed kits
    - Registry entry files exist and are readable
    """
    project_dir = Path.cwd()
    config = require_project_config(project_dir)
    registry_path = project_dir / ".erk" / "kits" / "kit-registry.md"

    # Check registry file exists
    if not registry_path.exists():
        user_output("❌ Registry file not found: .erk/kits/kit-registry.md")
        user_output("Run 'erk kit install <kit-id>' to create it")
        raise SystemExit(1)

    # Read registry content
    content = registry_path.read_text(encoding="utf-8")

    # Check if new structured format
    if "<!-- BEGIN_ENTRIES -->" in content:
        from erk.kits.io.registry import parse_doc_registry_entries

        # Use structured parsing
        entries = parse_doc_registry_entries(content)
        registry_kits = {e.kit_id for e in entries}

        # Also validate versions match
        version_mismatches = []
        for entry in entries:
            if entry.kit_id in config.kits:
                installed = config.kits[entry.kit_id]
                if entry.version != installed.version:
                    version_mismatches.append(
                        f"{entry.kit_id}: version mismatch "
                        f"(registry={entry.version}, installed={installed.version})"
                    )
    else:
        # Old format - fallback to simple parsing
        registry_lines = [line.strip() for line in content.split("\n") if line.startswith("@")]
        registry_kits = set()
        for line in registry_lines:
            if line.startswith("@.erk/kits/") and line.endswith("/registry-entry.md"):
                kit_id = line.split("/")[2]
                registry_kits.add(kit_id)
        version_mismatches = []

    # Get installed kit IDs
    installed_kits = set(config.kits.keys())

    # Check for mismatches
    missing_from_registry = installed_kits - registry_kits
    extra_in_registry = registry_kits - installed_kits

    issues = []

    if missing_from_registry:
        issues.append(
            f"Installed kits missing from registry: {', '.join(sorted(missing_from_registry))}"
        )

    if extra_in_registry:
        issues.append(
            f"Registry entries for uninstalled kits: {', '.join(sorted(extra_in_registry))}"
        )

    # Add version mismatches to issues
    issues.extend(version_mismatches)

    # Check that registry entry files exist
    for kit_id in registry_kits:
        entry_path = project_dir / ".erk" / "kits" / kit_id / "registry-entry.md"
        if not entry_path.exists():
            issues.append(f"Registry entry file missing for {kit_id}: {entry_path}")

    if issues:
        user_output("❌ Registry validation failed:")
        for issue in issues:
            user_output(f"  - {issue}")
        user_output("\nRun 'erk kit install <kit-id> --force' to fix these issues")
        raise SystemExit(1)

    user_output(f"✓ Registry valid: {len(installed_kits)} kit(s) properly registered")
