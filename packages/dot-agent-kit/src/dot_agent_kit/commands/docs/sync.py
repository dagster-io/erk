"""Sync agent documentation index files.

This command generates index.md files for docs/agent/ from frontmatter metadata.
"""

import subprocess
from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.operations.agent_docs import sync_agent_docs


@click.command(name="sync")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without writing files.",
)
def sync_command(*, dry_run: bool) -> None:
    """Regenerate index files from frontmatter.

    Generates index.md files for:
    - docs/agent/index.md (root index with categories and uncategorized docs)
    - docs/agent/<category>/index.md (for categories with 2+ docs)

    Index files are auto-generated and should not be manually edited.

    Exit codes:
    - 0: Sync completed successfully
    - 1: Error during sync
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
        user_output(click.style("✗ Error: Repository root not found", fg="red"))
        raise SystemExit(1)

    agent_docs_dir = project_root / "docs" / "agent"
    if not agent_docs_dir.exists():
        user_output(click.style("ℹ️  No docs/agent/ directory found", fg="cyan"))
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
        user_output(f"{action} {len(sync_result.created)} index file(s):")
        for path in sync_result.created:
            user_output(f"  + {path}")
        user_output()

    if sync_result.updated:
        action = "Would update" if dry_run else "Updated"
        user_output(f"{action} {len(sync_result.updated)} index file(s):")
        for path in sync_result.updated:
            user_output(f"  ~ {path}")
        user_output()

    if sync_result.unchanged:
        user_output(f"Unchanged: {len(sync_result.unchanged)} index file(s)")
        user_output()

    if sync_result.skipped_invalid > 0:
        user_output(
            click.style(
                f"⚠ Skipped {sync_result.skipped_invalid} doc(s) with invalid frontmatter",
                fg="yellow",
            )
        )
        user_output("  Run 'dot-agent docs validate' to see errors")
        user_output()

    # Summary
    if total_changes == 0 and sync_result.skipped_invalid == 0:
        user_output(click.style("✓ All index files are up to date", fg="green"))
    elif total_changes > 0:
        if dry_run:
            user_output(click.style(f"Would make {total_changes} change(s)", fg="cyan", bold=True))
        else:
            user_output(click.style(f"✓ Sync complete: {total_changes} change(s)", fg="green"))
