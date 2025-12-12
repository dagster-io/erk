"""Artifact list command implementation."""

from pathlib import Path

import click

from erk.cli.commands.artifact.formatting import format_compact_list, format_verbose_list
from erk.kits.cli.output import user_output
from erk.kits.io.state import load_project_config
from erk.kits.models.artifact import ArtifactLevel, ArtifactSource
from erk.kits.models.config import ProjectConfig
from erk.kits.repositories.filesystem_artifact_repository import FilesystemArtifactRepository

# Reusable option decorators
level_filter_options = [
    click.option(
        "--user",
        "level_filter",
        flag_value="user",
        help="Show only user-level artifacts",
    ),
    click.option(
        "--project",
        "level_filter",
        flag_value="project",
        help="Show only project-level artifacts",
    ),
    click.option(
        "--all",
        "level_filter",
        flag_value="all",
        default=True,
        help="Show all levels (default)",
    ),
]

type_option = click.option(
    "--type",
    "artifact_type",
    type=click.Choice(["skill", "command", "agent", "hook", "doc"]),
    help="Filter by artifact type",
)

verbose_option = click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed information",
)

managed_option = click.option(
    "--managed",
    is_flag=True,
    help="Show only artifacts installed from kits (exclude local artifacts)",
)


def _list_artifacts_impl(
    level_filter: str, artifact_type: str | None, verbose: bool, managed: bool
) -> None:
    """Implementation of list command logic."""
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

    # Discover bundled kits
    bundled_kits = repository.discover_bundled_kits(user_path, project_path, project_config)

    # Filter by level
    if level_filter == "user":
        all_artifacts = [a for a in all_artifacts if a.level == ArtifactLevel.USER]
        bundled_kits = {k: v for k, v in bundled_kits.items() if v.level == "user"}
    elif level_filter == "project":
        all_artifacts = [a for a in all_artifacts if a.level == ArtifactLevel.PROJECT]
        bundled_kits = {k: v for k, v in bundled_kits.items() if v.level == "project"}

    # Filter by type
    if artifact_type:
        all_artifacts = [a for a in all_artifacts if a.artifact_type == artifact_type]

    # Filter by source (managed vs local)
    if managed:
        all_artifacts = [a for a in all_artifacts if a.source == ArtifactSource.MANAGED]

    # Display results
    if not all_artifacts and not bundled_kits:
        user_output("No artifacts found.")
        raise SystemExit(1)

    if verbose:
        output = format_verbose_list(all_artifacts, bundled_kits, user_path, project_path)
    else:
        output = format_compact_list(all_artifacts, bundled_kits)

    user_output(output)


def _apply_options(func):
    """Apply all list options to a command function."""
    for option in reversed(level_filter_options):
        func = option(func)
    func = type_option(func)
    func = verbose_option(func)
    func = managed_option(func)
    return func


@click.command(name="list")
@_apply_options
def list_artifacts(
    level_filter: str, artifact_type: str | None, verbose: bool, managed: bool
) -> None:
    """List installed Claude artifacts (alias: ls)."""
    _list_artifacts_impl(level_filter, artifact_type, verbose, managed)


@click.command(name="ls", hidden=True)
@_apply_options
def ls(level_filter: str, artifact_type: str | None, verbose: bool, managed: bool) -> None:
    """List installed Claude artifacts (alias for list)."""
    _list_artifacts_impl(level_filter, artifact_type, verbose, managed)
