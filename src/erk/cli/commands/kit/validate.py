"""Validate command for checking artifact integrity."""

from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.operations.validation import validate_project


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation information",
)
def validate(verbose: bool) -> None:
    """Validate installed kit artifacts."""
    project_dir = Path.cwd()

    results = validate_project(project_dir)

    if len(results) == 0:
        user_output("No artifacts found to validate")
        return

    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    # Show results
    if verbose or invalid_count > 0:
        for result in results:
            status = "✓" if result.is_valid else "✗"
            rel_path = result.artifact_path.relative_to(project_dir)
            user_output(f"{status} {rel_path}")

            if not result.is_valid:
                for error in result.errors:
                    user_output(f"  - {error}")

    # Summary
    user_output()
    user_output(f"Validated {len(results)} artifacts:")
    user_output(f"  ✓ Valid: {valid_count}")

    if invalid_count > 0:
        user_output(f"  ✗ Invalid: {invalid_count}")
        raise SystemExit(1)
    else:
        user_output("All artifacts are valid!")
