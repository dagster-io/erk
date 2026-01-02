"""Sync agent documentation index files.

This command generates index.md files for docs/learned/ from frontmatter metadata.
"""

from pathlib import Path

import click

from erk.agent_docs.operations import sync_agent_docs
from erk.cli.subprocess_utils import run_with_error_reporting


@click.command(name="sync")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without writing files.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Check if files are in sync without writing. Exit 1 if changes needed.",
)
def sync_command(*, dry_run: bool, check: bool) -> None:
    """Regenerate index files from frontmatter.

    Generates index.md files for:
    - docs/learned/index.md (root index with categories and uncategorized docs)
    - docs/learned/<category>/index.md (for categories with 2+ docs)

    Index files are auto-generated and should not be manually edited.

    Exit codes:
    - 0: Sync completed successfully (or --check passes)
    - 1: Error during sync (or --check finds files out of sync)
    """
    # --check implies dry-run behavior
    effective_dry_run = dry_run or check

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

    agent_docs_dir = project_root / "docs" / "learned"
    if not agent_docs_dir.exists():
        click.echo(click.style("No docs/learned/ directory found", fg="cyan"), err=True)
        raise SystemExit(0)

    # Sync index files
    sync_result = sync_agent_docs(project_root, dry_run=effective_dry_run)

    # Report results
    if effective_dry_run:
        click.echo(click.style("Dry run - no files written", fg="cyan", bold=True), err=True)
        click.echo(err=True)

    total_changes = len(sync_result.created) + len(sync_result.updated)

    if sync_result.created:
        action = "Would create" if effective_dry_run else "Created"
        click.echo(f"{action} {len(sync_result.created)} file(s):", err=True)
        for path in sync_result.created:
            click.echo(f"  + {path}", err=True)
        click.echo(err=True)

    if sync_result.updated:
        action = "Would update" if effective_dry_run else "Updated"
        click.echo(f"{action} {len(sync_result.updated)} file(s):", err=True)
        for path in sync_result.updated:
            click.echo(f"  ~ {path}", err=True)
        click.echo(err=True)

    if sync_result.unchanged:
        click.echo(f"Unchanged: {len(sync_result.unchanged)} file(s)", err=True)
        click.echo(err=True)

    # Report tripwires
    if sync_result.tripwires_count > 0:
        click.echo(f"Tripwires: {sync_result.tripwires_count} collected", err=True)
        click.echo(err=True)

    if sync_result.skipped_invalid > 0:
        click.echo(
            click.style(
                f"Skipped {sync_result.skipped_invalid} doc(s) with invalid frontmatter",
                fg="yellow",
            ),
            err=True,
        )
        click.echo("  Run 'erk docs validate' to see errors", err=True)
        click.echo(err=True)

    # Summary
    if total_changes == 0 and sync_result.skipped_invalid == 0:
        click.echo(click.style("All files are up to date", fg="green"), err=True)
    elif total_changes > 0:
        if check:
            msg = f"Files out of sync: {total_changes} change(s) needed"
            click.echo(click.style(msg, fg="red", bold=True), err=True)
            click.echo(err=True)
            click.echo("Run 'erk docs sync' to regenerate files from frontmatter.", err=True)
            raise SystemExit(1)
        elif effective_dry_run:
            click.echo(
                click.style(f"Would make {total_changes} change(s)", fg="cyan", bold=True),
                err=True,
            )
        else:
            click.echo(
                click.style(f"Sync complete: {total_changes} change(s)", fg="green"),
                err=True,
            )
