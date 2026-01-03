"""Static CLI definition for erk-dev.

This module uses static imports instead of dynamic command loading to enable
shell completion. Click's completion mechanism requires all commands to be
available at import time for inspection.
"""

import click

from erk_dev.commands.branch_commit_count.command import (
    branch_commit_count_command,
)
from erk_dev.commands.bump_version.command import bump_version_command
from erk_dev.commands.changelog_commits.command import changelog_commits_command
from erk_dev.commands.check_forward_refs.command import check_forward_refs_command
from erk_dev.commands.clean_cache.command import clean_cache_command
from erk_dev.commands.codex_review.command import codex_review_command
from erk_dev.commands.completion.command import completion_command
from erk_dev.commands.create_agents_symlinks.command import (
    create_agents_symlinks_command,
)
from erk_dev.commands.publish_to_pypi.command import publish_to_pypi_command
from erk_dev.commands.release_check.command import release_check_command
from erk_dev.commands.release_info.command import release_info_command
from erk_dev.commands.release_tag.command import release_tag_command
from erk_dev.commands.release_update.command import release_update_command
from erk_dev.commands.reserve_pypi_name.command import (
    reserve_pypi_name_command,
)
from erk_dev.commands.slash_command.command import slash_command_command
from erk_dev.context import create_context

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(name="erk-dev", context_settings=CONTEXT_SETTINGS)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Development tools for erk."""
    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = create_context()


# Register all commands
cli.add_command(branch_commit_count_command)
cli.add_command(bump_version_command)
cli.add_command(changelog_commits_command)
cli.add_command(check_forward_refs_command)
cli.add_command(clean_cache_command)
cli.add_command(codex_review_command)
cli.add_command(completion_command)
cli.add_command(create_agents_symlinks_command)
cli.add_command(publish_to_pypi_command)
cli.add_command(release_check_command)
cli.add_command(release_info_command)
cli.add_command(release_tag_command)
cli.add_command(release_update_command)
cli.add_command(reserve_pypi_name_command)
cli.add_command(slash_command_command)
