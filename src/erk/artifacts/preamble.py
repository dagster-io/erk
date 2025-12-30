"""CLI preamble check for artifact staleness."""

import sys
from pathlib import Path

import click

from erk.artifacts.staleness import check_staleness
from erk.artifacts.sync import sync_artifacts
from erk.core.repo_discovery import in_erk_repo


def check_and_prompt_artifact_sync(project_dir: Path, *, no_sync: bool) -> None:
    """Check for stale artifacts and prompt to sync.

    Called from CLI callback before command execution.

    Args:
        project_dir: Project root directory
        no_sync: If True, skip the staleness check entirely
    """
    if no_sync:
        return

    # Skip in erk repo - artifacts read from source
    if in_erk_repo(project_dir):
        return

    result = check_staleness(project_dir)

    if not result.is_stale:
        return

    # Skip silently if not initialized - artifacts are optional
    # Users can run 'erk init' or 'erk artifacts sync' to enable artifact sync
    if result.reason == "not-initialized":
        return

    # Handle "version mismatch" case
    if not sys.stdin.isatty():
        # Non-TTY: fail with instructions
        click.echo(
            click.style("Error: ", fg="red")
            + f"Artifacts out of sync (installed: {result.installed_version}, "
            f"current: {result.current_version}).\n"
            "Run 'erk artifacts sync' or use --no-sync to skip.",
            err=True,
        )
        raise SystemExit(1)

    # TTY: prompt user
    click.echo(
        click.style("⚠️  Erk artifacts out of sync", fg="yellow")
        + f" (installed: {result.installed_version}, current: {result.current_version})\n"
        "Out-of-sync artifacts may cause erk commands to malfunction."
    )

    if click.confirm("Sync now?", default=True):
        sync_result = sync_artifacts(project_dir)
        click.echo(
            click.style("✓ ", fg="green") + f"Synced {sync_result.artifacts_installed} artifacts"
        )
