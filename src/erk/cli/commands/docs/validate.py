"""Validate agent documentation frontmatter.

This command validates that all markdown files in docs/learned/ have valid
frontmatter with required fields: title and read_when.
"""

import subprocess
from pathlib import Path

import click

from erk.agent_docs.operations import validate_agent_docs


@click.command(name="validate")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show details for all files, not just errors.",
)
def validate_command(*, verbose: bool) -> None:
    """Validate agent documentation frontmatter.

    Checks that all markdown files in docs/learned/ have valid frontmatter:
    - title: Human-readable document title
    - read_when: List of conditions when agent should read this doc

    Index files (index.md) are skipped as they are auto-generated.

    Exit codes:
    - 0: All files are valid
    - 1: Validation errors found
    """
    # Find repository root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    project_root = Path(result.stdout.strip())

    if not project_root.exists():
        click.echo(click.style("Error: Repository root not found", fg="red"), err=True)
        raise SystemExit(1)

    agent_docs_dir = project_root / "docs" / "learned"
    if not agent_docs_dir.exists():
        click.echo(click.style("No docs/learned/ directory found", fg="cyan"), err=True)
        raise SystemExit(0)

    # Validate all files
    results = validate_agent_docs(project_root)

    if len(results) == 0:
        click.echo(click.style("No agent documentation files found", fg="cyan"), err=True)
        raise SystemExit(0)

    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count

    # Show results
    if verbose or invalid_count > 0:
        for validation_result in results:
            if validation_result.is_valid:
                if verbose:
                    status = click.style("OK", fg="green")
                    click.echo(f"{status} {validation_result.file_path}", err=True)
            else:
                status = click.style("FAIL", fg="red")
                click.echo(f"{status} {validation_result.file_path}", err=True)
                for error in validation_result.errors:
                    click.echo(f"    {error}", err=True)

    # Summary
    click.echo(err=True)
    if invalid_count == 0:
        click.echo(
            click.style("Agent docs validation: PASSED", fg="green", bold=True),
            err=True,
        )
        click.echo(err=True)
        click.echo(f"Files validated: {len(results)}", err=True)
        click.echo("All files have valid frontmatter!", err=True)
    else:
        click.echo(
            click.style("Agent docs validation: FAILED", fg="red", bold=True),
            err=True,
        )
        click.echo(err=True)
        click.echo(f"Files validated: {len(results)}", err=True)
        click.echo(f"  Valid: {valid_count}", err=True)
        click.echo(f"  Invalid: {invalid_count}", err=True)
        click.echo(err=True)
        click.echo("Required frontmatter format:", err=True)
        click.echo("  ---", err=True)
        click.echo("  title: Document Title", err=True)
        click.echo("  read_when:", err=True)
        click.echo('    - "when to read this doc"', err=True)
        click.echo("  ---", err=True)
        raise SystemExit(1)
