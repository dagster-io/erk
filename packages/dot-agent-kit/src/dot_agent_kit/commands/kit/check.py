"""Check command for validating kit artifact references."""

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io.kit_reference_validation import validate_kit_references
from dot_agent_kit.sources.bundled import BundledKitSource


@click.command()
@click.argument("kit_name", required=False)
@click.option(
    "--all-bundled",
    is_flag=True,
    help="Check all bundled kits",
)
def check(kit_name: str | None, all_bundled: bool) -> None:
    """Validate kit artifact references are complete.

    Checks that all @ references in kit artifacts (skills, docs, etc.)
    point to files that are declared in the kit manifest. This catches
    issues where a skill references a doc that won't be installed.

    Examples:

      dot-agent kit check dignified-python

      dot-agent kit check --all-bundled
    """
    if kit_name is None and not all_bundled:
        click.echo("Error: Either specify a kit name or use --all-bundled", err=True)
        raise SystemExit(1)

    bundled_source = BundledKitSource()

    if all_bundled:
        kit_names = bundled_source.list_available()
    else:
        kit_names = [kit_name] if kit_name else []

    total_errors = 0
    kits_with_errors: list[str] = []

    for name in kit_names:
        kit_path = bundled_source._get_bundled_kit_path(name)
        if kit_path is None:
            click.echo(f"Error: Kit '{name}' not found", err=True)
            raise SystemExit(1)

        manifest_path = kit_path / "kit.yaml"
        errors = validate_kit_references(manifest_path)

        if errors:
            kits_with_errors.append(name)
            user_output(f"\n✗ {name}:")
            for error in errors:
                user_output(f"  {error.source_artifact}:")
                user_output(f"    Reference: @{error.reference}")
                if error.suggested_fix:
                    user_output(f"    Fix: {error.suggested_fix}")
            total_errors += len(errors)

    # Summary
    user_output()
    if total_errors > 0:
        user_output(f"Found {total_errors} reference error(s) in {len(kits_with_errors)} kit(s)")
        raise SystemExit(1)
    else:
        user_output(f"✓ All {len(kit_names)} kit(s) passed reference validation")
