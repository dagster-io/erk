"""Create a git tag for the current version."""

from pathlib import Path

import click

from erk_dev.commands.bump_version.command import find_repo_root, get_current_version
from erk_dev.context import ErkDevContext, create_context


@click.command("release-tag")
@click.option("--push", is_flag=True, help="Push tag to remote after creation")
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.pass_context
def release_tag_command(ctx: click.Context, push: bool, dry_run: bool) -> None:
    """Create a git tag for the current version.

    Creates an annotated tag `v{version}` for the current version in pyproject.toml.
    Use after updating CHANGELOG and committing the release.
    """
    # Use dry-run context if --dry-run flag is set
    if dry_run:
        ctx.obj = create_context(dry_run=True)

    erk_ctx: ErkDevContext = ctx.obj
    git = erk_ctx.git

    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise click.ClickException("Could not find repository root")

    current_version = get_current_version(repo_root)
    if current_version is None:
        raise click.ClickException("Could not determine current version from pyproject.toml")

    tag_name = f"v{current_version}"

    if git.tag_exists(repo_root, tag_name):
        click.echo(f"Tag {tag_name} already exists")
        return

    message = f"Release {current_version}"
    git.create_tag(repo_root, tag_name, message)
    click.echo(f"Created tag: {tag_name}")

    if push:
        git.push_tag(repo_root, "origin", tag_name)
        click.echo("Pushed tag to origin")
