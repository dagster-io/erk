"""Check agent documentation health.

This command runs both frontmatter validation and sync checking in a single pass.
It's the unified health check for agent docs, combining:
- erk docs validate (frontmatter schema check)
- erk docs sync --check (generated files in sync check)
"""

from pathlib import Path

import click

from erk.agent_docs.operations import (
    sync_agent_docs,
    validate_agent_docs,
    validate_tripwires_index,
)
from erk.cli.subprocess_utils import run_with_error_reporting


def run_check(project_root: Path) -> None:
    """Run agent documentation health checks against a project root.

    This is the testable core of the check command. It validates frontmatter
    and checks that generated index/tripwire files are in sync.

    Raises:
        SystemExit: With code 0 if no docs found, code 1 if checks fail.
    """
    agent_docs_dir = project_root / "docs" / "learned"
    if not agent_docs_dir.exists():
        click.echo(click.style("No docs/learned/ directory found", fg="cyan"), err=True)
        raise SystemExit(0)

    # Phase 1: Validate frontmatter
    click.echo(click.style("Validating frontmatter...", fg="cyan"), err=True)
    click.echo(err=True)

    validation_results = validate_agent_docs(project_root)
    tripwires_index_result = validate_tripwires_index(project_root)

    if len(validation_results) == 0:
        click.echo(click.style("No agent documentation files found", fg="cyan"), err=True)
        raise SystemExit(0)

    invalid_count = sum(1 for r in validation_results if not r.is_valid)

    # Show validation errors only
    if invalid_count > 0:
        for validation_result in validation_results:
            if not validation_result.is_valid:
                status = click.style("FAIL", fg="red")
                click.echo(f"{status} {validation_result.file_path}", err=True)
                for error in validation_result.errors:
                    click.echo(f"    {error}", err=True)

    # Show tripwires index errors
    if not tripwires_index_result.is_valid:
        if invalid_count > 0:
            click.echo(err=True)
        status = click.style("FAIL", fg="red")
        click.echo(f"{status} tripwires-index.md", err=True)
        for error in tripwires_index_result.errors:
            click.echo(f"    {error}", err=True)

    validation_passed = invalid_count == 0 and tripwires_index_result.is_valid

    if validation_passed:
        message = f"Frontmatter validation passed ({len(validation_results)} files)"
        click.echo(
            click.style(message, fg="green"),
            err=True,
        )
    else:
        click.echo(
            click.style("Frontmatter validation failed", fg="red"),
            err=True,
        )

    click.echo(err=True)

    # Phase 2: Check sync
    click.echo(click.style("Checking generated files...", fg="cyan"), err=True)
    click.echo(err=True)

    sync_result = sync_agent_docs(project_root, dry_run=True)

    # Show out-of-sync files
    if sync_result.created:
        click.echo(f"Would create {len(sync_result.created)} file(s):", err=True)
        for path in sync_result.created:
            click.echo(f"  + {path}", err=True)
        click.echo(err=True)

    if sync_result.updated:
        click.echo(f"Would update {len(sync_result.updated)} file(s):", err=True)
        for path in sync_result.updated:
            click.echo(f"  ~ {path}", err=True)
        click.echo(err=True)

    total_changes = len(sync_result.created) + len(sync_result.updated)
    sync_passed = total_changes == 0

    if sync_passed:
        click.echo(
            click.style("Generated files in sync", fg="green"),
            err=True,
        )
    else:
        click.echo(
            click.style(f"Generated files out of sync ({total_changes} changes needed)", fg="red"),
            err=True,
        )

    click.echo(err=True)

    # Summary
    all_passed = validation_passed and sync_passed

    click.echo(click.style("=" * 60, fg="cyan"), err=True)
    if all_passed:
        click.echo(
            click.style("Agent docs health check: PASSED", fg="green", bold=True),
            err=True,
        )
        click.echo(err=True)
        click.echo(f"Files validated: {len(validation_results)}", err=True)
        total_generated = (
            len(sync_result.created) + len(sync_result.updated) + len(sync_result.unchanged)
        )
        click.echo(f"Generated files: {total_generated}", err=True)
    else:
        click.echo(
            click.style("Agent docs health check: FAILED", fg="red", bold=True),
            err=True,
        )
        click.echo(err=True)
        if not validation_passed:
            click.echo(f"  Frontmatter validation: {invalid_count} invalid file(s)", err=True)
            if not tripwires_index_result.is_valid:
                click.echo("  Tripwires index: incomplete", err=True)
        if not sync_passed:
            click.echo(f"  Generated files: {total_changes} change(s) needed", err=True)
            click.echo(err=True)
            click.echo("Run 'erk docs sync' to regenerate files from frontmatter.", err=True)

        raise SystemExit(1)


@click.command(name="check")
def check_command() -> None:
    """Check agent documentation health.

    Runs two validation phases:
    1. Frontmatter validation - ensures all docs have required fields
    2. Sync check - ensures generated index/tripwire files are up to date

    This is the unified health check command used in CI.

    Exit codes:
    - 0: All checks passed
    - 1: One or more checks failed
    """
    # Find repository root
    result = run_with_error_reporting(
        ["git", "rev-parse", "--show-toplevel"],
        error_prefix="Failed to find repository root",
        troubleshooting=["Ensure you're running from within a git repository"],
    )
    project_root = Path(result.stdout.strip())

    if not project_root.exists():
        click.echo(click.style("Error: Repository root not found", fg="red"), err=True)
        raise SystemExit(1)

    run_check(project_root)
