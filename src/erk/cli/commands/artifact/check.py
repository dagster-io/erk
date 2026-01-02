"""Check artifact sync status."""

from pathlib import Path

import click

from erk.artifacts.artifact_health import (
    ArtifactStatus,
    find_missing_artifacts,
    find_orphaned_artifacts,
    get_artifact_health,
    is_erk_managed,
)
from erk.artifacts.discovery import discover_artifacts
from erk.artifacts.models import InstalledArtifact
from erk.artifacts.staleness import check_staleness
from erk.artifacts.state import load_artifact_state


def _display_orphan_warnings(orphans: dict[str, list[str]]) -> None:
    """Display orphan warnings with remediation commands."""
    total_orphans = sum(len(files) for files in orphans.values())
    click.echo(click.style("⚠️  ", fg="yellow") + f"Found {total_orphans} orphaned artifact(s)")
    click.echo("   Orphaned files (not in current erk package):")
    for folder, files in sorted(orphans.items()):
        click.echo(f"     {folder}/:")
        for filename in sorted(files):
            click.echo(f"       - {filename}")

    click.echo("")
    click.echo("   To remove:")
    for folder, files in sorted(orphans.items()):
        for filename in sorted(files):
            # Workflows are in .github/, not .claude/
            if folder.startswith(".github"):
                click.echo(f"     rm {folder}/{filename}")
            else:
                click.echo(f"     rm .claude/{folder}/{filename}")


def _display_missing_warnings(missing: dict[str, list[str]]) -> None:
    """Display missing artifact warnings."""
    total_missing = sum(len(files) for files in missing.values())
    click.echo(click.style("⚠️  ", fg="yellow") + f"Found {total_missing} missing artifact(s)")
    click.echo("   Missing from project:")
    for folder, files in sorted(missing.items()):
        click.echo(f"     {folder}:")
        for filename in sorted(files):
            click.echo(f"       - {filename}")
    click.echo("")
    click.echo("   Run 'erk artifact sync' to install missing artifacts")


def _format_artifact_path(artifact: InstalledArtifact) -> str:
    """Format artifact as a display path string."""
    if artifact.artifact_type == "command":
        # Commands can be namespaced (local:foo) or top-level (foo)
        if ":" in artifact.name:
            namespace, name = artifact.name.split(":", 1)
            return f"commands/{namespace}/{name}.md"
        return f"commands/{artifact.name}.md"
    if artifact.artifact_type == "skill":
        return f"skills/{artifact.name}"
    if artifact.artifact_type == "agent":
        return f"agents/{artifact.name}"
    if artifact.artifact_type == "workflow":
        return f".github/workflows/{artifact.name}.yml"
    if artifact.artifact_type == "hook":
        return f"hooks/{artifact.name} (settings.json)"
    return artifact.name


def _display_installed_artifacts(project_dir: Path) -> None:
    """Display list of artifacts actually installed in project."""
    artifacts = discover_artifacts(project_dir)

    if not artifacts:
        click.echo("   (no artifacts installed)")
        return

    for artifact in artifacts:
        suffix = "" if is_erk_managed(artifact) else " (unmanaged)"
        click.echo(f"   {_format_artifact_path(artifact)}{suffix}")


def _format_artifact_status(artifact: ArtifactStatus, show_hashes: bool) -> str:
    """Format artifact status for verbose output.

    Args:
        artifact: The artifact status to format
        show_hashes: If True, show hash comparison details
    """
    if artifact.status == "up-to-date":
        icon = click.style("✓", fg="green")
        detail = f"{artifact.current_version} (up-to-date)"
    elif artifact.status == "changed-upstream":
        icon = click.style("⚠", fg="yellow")
        if artifact.installed_version:
            detail = f"{artifact.installed_version} → {artifact.current_version} (changed upstream)"
        else:
            detail = f"→ {artifact.current_version} (new in this version)"
    elif artifact.status == "locally-modified":
        icon = click.style("⚠", fg="yellow")
        detail = f"{artifact.current_version} (locally modified)"
    else:  # not-installed
        icon = click.style("✗", fg="red")
        detail = "(not installed)"

    lines = [f"  {icon} {artifact.name}: {detail}"]

    if show_hashes:
        # Show state.toml values
        if artifact.installed_version is not None and artifact.installed_hash is not None:
            ver = artifact.installed_version
            h = artifact.installed_hash
            lines.append(f"       state.toml: version={ver}, hash={h}")
        else:
            lines.append("       state.toml: (not tracked)")

        # Show current source values
        if artifact.current_hash is not None:
            ver = artifact.current_version
            h = artifact.current_hash
            lines.append(f"       source:     version={ver}, hash={h}")
        else:
            lines.append("       source:     (not installed)")

    return "\n".join(lines)


def _display_verbose_status(project_dir: Path, show_hashes: bool) -> bool:
    """Display per-artifact status breakdown.

    Shows two sections:
    1. Erk-managed artifacts with version tracking status
    2. Project artifacts (local commands, custom skills, etc.)

    Args:
        project_dir: Path to the project root
        show_hashes: If True, show hash comparison details for each artifact

    Returns True if any erk-managed artifacts need attention (not up-to-date).
    """
    state = load_artifact_state(project_dir)
    saved_files = dict(state.files) if state else {}

    health_result = get_artifact_health(project_dir, saved_files)

    if health_result.skipped_reason is not None:
        return False

    click.echo("")
    click.echo("Erk-managed artifacts:")

    has_issues = False
    for artifact in health_result.artifacts:
        click.echo(_format_artifact_status(artifact, show_hashes))
        if artifact.status != "up-to-date":
            has_issues = True

    # Also show project-specific artifacts (non-erk-managed)
    all_artifacts = discover_artifacts(project_dir)
    project_artifacts = [a for a in all_artifacts if not is_erk_managed(a)]

    if project_artifacts:
        click.echo("")
        click.echo("Project artifacts (unmanaged):")
        for artifact in project_artifacts:
            click.echo(f"   {_format_artifact_path(artifact)}")

    return has_issues


@click.command("check")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Show per-artifact status. Use -vv to also show hash comparisons.",
)
def check_cmd(verbose: int) -> None:
    """Check if artifacts are in sync with erk version.

    Compares the version recorded in .erk/state.toml against
    the currently installed erk package version. Also checks
    for orphaned files that should be removed.

    Examples:

    \b
      # Check sync status
      erk artifact check

    \b
      # Show per-artifact breakdown
      erk artifact check -v

    \b
      # Show hash comparisons (state.toml vs source)
      erk artifact check -vv
    """
    project_dir = Path.cwd()

    staleness_result = check_staleness(project_dir)
    orphan_result = find_orphaned_artifacts(project_dir)
    missing_result = find_missing_artifacts(project_dir)

    has_errors = False
    show_per_artifact = verbose >= 1
    show_hashes = verbose >= 2

    # Check staleness
    if staleness_result.reason == "erk-repo":
        click.echo(click.style("✓ ", fg="green") + "Development mode (artifacts read from source)")
        if not show_per_artifact:
            _display_installed_artifacts(project_dir)
    elif staleness_result.reason == "not-initialized":
        click.echo(click.style("⚠️  ", fg="yellow") + "Artifacts not initialized")
        click.echo(f"   Current erk version: {staleness_result.current_version}")
        click.echo("   Run 'erk artifact sync' to initialize")
        has_errors = True
    elif staleness_result.reason == "version-mismatch":
        click.echo(click.style("⚠️  ", fg="yellow") + "Artifacts out of sync")
        click.echo(f"   Installed version: {staleness_result.installed_version}")
        click.echo(f"   Current erk version: {staleness_result.current_version}")
        click.echo("   Run 'erk artifact sync' to update")
        has_errors = True
    else:
        click.echo(
            click.style("✓ ", fg="green")
            + f"Artifacts up to date (v{staleness_result.current_version})"
        )
        if not show_per_artifact:
            _display_installed_artifacts(project_dir)

    # Show verbose per-artifact breakdown if requested
    if show_per_artifact and staleness_result.reason != "not-initialized":
        verbose_has_issues = _display_verbose_status(project_dir, show_hashes)
        # In dev mode (erk-repo), don't report issues - artifacts come from source
        if verbose_has_issues and staleness_result.reason != "erk-repo":
            has_errors = True

    # Check for orphans (skip if erk-repo or no-claude-dir)
    if orphan_result.skipped_reason is None:
        if orphan_result.orphans:
            _display_orphan_warnings(orphan_result.orphans)
            has_errors = True
        else:
            click.echo(click.style("✓ ", fg="green") + "No orphaned artifacts")

    # Check for missing artifacts (skip if erk-repo or no-claude-dir)
    if missing_result.skipped_reason is None:
        if missing_result.missing:
            _display_missing_warnings(missing_result.missing)
            has_errors = True
        else:
            click.echo(click.style("✓ ", fg="green") + "No missing artifacts")

    if has_errors:
        raise SystemExit(1)
