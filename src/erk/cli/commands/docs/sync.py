"""Sync agent documentation index files.

This command generates index.md files for .erk/docs/agent/ from frontmatter metadata.
"""

import subprocess
from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk.kits.operations.agent_docs import sync_agent_docs


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
    - .erk/docs/agent/index.md (root index with categories and uncategorized docs)
    - .erk/docs/agent/<category>/index.md (for categories with 2+ docs)

    Index files are auto-generated and should not be manually edited.

    Exit codes:
    - 0: Sync completed successfully (or --check passes)
    - 1: Error during sync (or --check finds files out of sync)
    """
    # --check implies dry-run behavior
    if check:
        dry_run = True
    # Find repository root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    project_root = Path(result.stdout.strip())

    if not project_root.exists():
        user_output(click.style("✗ Error: Repository root not found", fg="red"))
        raise SystemExit(1)

    agent_docs_dir = project_root / ".erk" / "docs" / "agent"
    if not agent_docs_dir.exists():
        user_output(click.style("ℹ️  No .erk/docs/agent/ directory found", fg="cyan"))
        raise SystemExit(0)

    # Sync index files
    sync_result = sync_agent_docs(project_root, dry_run=dry_run)

    # Report results
    if dry_run:
        user_output(click.style("Dry run - no files written", fg="cyan", bold=True))
        user_output()

    total_changes = len(sync_result.created) + len(sync_result.updated)

    if sync_result.created:
        action = "Would create" if dry_run else "Created"
        user_output(f"{action} {len(sync_result.created)} file(s):")
        for path in sync_result.created:
            user_output(f"  + {path}")
        user_output()

    if sync_result.updated:
        action = "Would update" if dry_run else "Updated"
        user_output(f"{action} {len(sync_result.updated)} file(s):")
        for path in sync_result.updated:
            user_output(f"  ~ {path}")
        user_output()

    if sync_result.unchanged:
        user_output(f"Unchanged: {len(sync_result.unchanged)} file(s)")
        user_output()

    # Report tripwires
    if sync_result.tripwires_count > 0:
        user_output(f"Tripwires: {sync_result.tripwires_count} collected")
        user_output()

    if sync_result.skipped_invalid > 0:
        user_output(
            click.style(
                f"⚠ Skipped {sync_result.skipped_invalid} doc(s) with invalid frontmatter",
                fg="yellow",
            )
        )
        user_output("  Run 'erk docs validate' to see errors")
        user_output()

    # Summary
    if total_changes == 0 and sync_result.skipped_invalid == 0:
        user_output(click.style("✓ All files are up to date", fg="green"))
    elif total_changes > 0:
        if check:
            msg = f"✗ Files out of sync: {total_changes} change(s) needed"
            user_output(click.style(msg, fg="red", bold=True))
            user_output()
            user_output("Run 'erk docs sync' to regenerate files from frontmatter.")
            raise SystemExit(1)
        elif dry_run:
            user_output(click.style(f"Would make {total_changes} change(s)", fg="cyan", bold=True))
        else:
            user_output(click.style(f"✓ Sync complete: {total_changes} change(s)", fg="green"))
