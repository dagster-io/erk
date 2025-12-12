"""Artifact show command implementation."""

from pathlib import Path

import click

from erk.cli.commands.artifact.formatting import format_artifact_header, format_hook_metadata
from erk.kits.cli.output import user_output
from erk.kits.io.state import load_project_config
from erk.kits.models.config import ProjectConfig
from erk.kits.repositories.filesystem_artifact_repository import FilesystemArtifactRepository


@click.command(name="show")
@click.argument("name")
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "hook"]),
    help="Artifact type hint",
)
def show_artifact(name: str, artifact_type: str | None) -> None:
    """Display artifact content and metadata."""
    # Get paths
    user_path = Path.home() / ".claude"
    project_path = Path.cwd() / ".claude"

    # Load project config
    project_config = load_project_config(Path.cwd())
    if project_config is None:
        project_config = ProjectConfig(version="1", kits={})

    # Discover artifacts
    repository = FilesystemArtifactRepository()
    all_artifacts = repository.discover_multi_level(user_path, project_path, project_config)

    # Filter by name (case-insensitive)
    name_lower = name.lower()
    matching = [a for a in all_artifacts if a.artifact_name.lower() == name_lower]

    # Further filter by type if provided
    if artifact_type:
        matching = [a for a in matching if a.artifact_type == artifact_type]

    # Handle no matches
    if not matching:
        user_output(f"No artifact found with name '{name}'")
        user_output("\nTip: Use 'dot-agent artifact list' to see all available artifacts")
        raise SystemExit(1)

    # Display all matches (handles both single and multiple matches)
    for i, artifact in enumerate(matching):
        if i > 0:
            user_output("\n" + "=" * 60 + "\n")

        # Compute absolute path for display
        if artifact.level.value == "user":
            base_dir = user_path
        else:
            base_dir = project_path

        artifact_path = base_dir / artifact.file_path
        absolute_path = artifact_path.resolve() if artifact_path.exists() else None

        # Display metadata header
        user_output(format_artifact_header(artifact, absolute_path))

        # Add hook-specific metadata
        if artifact.artifact_type == "hook":
            hook_meta = format_hook_metadata(artifact)
            if hook_meta:
                user_output(hook_meta)

        user_output("\n" + "-" * 60 + "\n")

        # Display file content
        # Construct absolute path based on level
        if artifact.level.value == "user":
            base_dir = user_path
        else:
            base_dir = project_path

        file_path = base_dir / artifact.file_path

        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            user_output(content)
        else:
            user_output(f"Warning: File not found at {file_path}")
