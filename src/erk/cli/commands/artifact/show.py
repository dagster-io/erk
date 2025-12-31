"""Show artifact content."""

from pathlib import Path

import click

from erk.artifacts.discovery import get_artifact_by_name
from erk.artifacts.models import ArtifactType


@click.command("show")
@click.argument("name")
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent"]),
    help="Artifact type (optional, helps disambiguate)",
)
def show_cmd(name: str, artifact_type: str | None) -> None:
    """Display the content of an artifact.

    Examples:

    \b
      # Show a skill
      erk artifact show dignified-python

    \b
      # Show a command (use colon for namespaced commands)
      erk artifact show erk:plan-implement

    \b
      # Disambiguate by type
      erk artifact show my-artifact --type skill
    """
    claude_dir = Path.cwd() / ".claude"
    if not claude_dir.exists():
        click.echo("No .claude/ directory found in current directory", err=True)
        raise SystemExit(1)

    type_filter: ArtifactType | None = None
    if artifact_type is not None:
        type_filter = artifact_type  # type: ignore[assignment]

    artifact = get_artifact_by_name(claude_dir, name, type_filter)

    if artifact is None:
        click.echo(f"Artifact not found: {name}", err=True)
        raise SystemExit(1)

    # Display metadata
    click.echo(click.style(f"# {artifact.name}", bold=True))
    click.echo(click.style(f"Type: {artifact.artifact_type}", dim=True))
    click.echo(click.style(f"Path: {artifact.path}", dim=True))
    click.echo("")

    # Display content
    content = artifact.path.read_text(encoding="utf-8")
    click.echo(content)
