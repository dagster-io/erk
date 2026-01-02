"""List artifacts installed in the project."""

from pathlib import Path

import click

from erk.artifacts.artifact_health import is_erk_managed
from erk.artifacts.discovery import discover_artifacts
from erk.artifacts.models import ArtifactType


@click.command("list")
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "workflow", "hook"]),
    help="Filter by artifact type",
)
@click.option("--verbose", "-v", is_flag=True, help="Show additional details")
def list_cmd(artifact_type: str | None, verbose: bool) -> None:
    """List all artifacts in project.

    Examples:

    \b
      # List all artifacts
      erk artifact list

    \b
      # List only skills
      erk artifact list --type skill

    \b
      # List with details
      erk artifact list --verbose
    """
    project_dir = Path.cwd()
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        click.echo("No .claude/ directory found in current directory", err=True)
        raise SystemExit(1)

    artifacts = discover_artifacts(project_dir)

    # Filter by type if specified
    if artifact_type is not None:
        typed_filter: ArtifactType = artifact_type  # type: ignore[assignment]
        artifacts = [a for a in artifacts if a.artifact_type == typed_filter]

    if not artifacts:
        if artifact_type:
            click.echo(f"No {artifact_type} artifacts found")
        else:
            click.echo("No artifacts found")
        return

    # Group by type for display
    current_type: str | None = None
    for artifact in artifacts:
        if artifact.artifact_type != current_type:
            if current_type is not None:
                click.echo("")  # Blank line between types
            current_type = artifact.artifact_type
            # Special headers for types with non-standard locations/display
            if current_type == "workflow":
                header = "Github Workflows (.github/workflows):"
            elif current_type == "hook":
                header = "Hooks (.claude/settings.json):"
            else:
                # Capitalize first letter only (e.g., "Commands:")
                header = current_type.capitalize() + "s:"
            click.echo(click.style(header, bold=True))

        # Format badge based on management status
        is_managed = is_erk_managed(artifact)
        if is_managed:
            badge = click.style(" [erk]", fg="cyan")
        else:
            badge = click.style(" [unmanaged]", fg="yellow")

        if verbose:
            click.echo(f"    {artifact.name}{badge}")
            click.echo(click.style(f"      Path: {artifact.path}", dim=True))
            if is_managed and artifact.content_hash:
                click.echo(click.style(f"      Hash: {artifact.content_hash}", dim=True))
        else:
            click.echo(f"    {artifact.name}{badge}")
