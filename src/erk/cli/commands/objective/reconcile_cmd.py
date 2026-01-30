"""Reconcile auto-advance objectives."""

import os
import shutil

import click

from erk.cli.alias import alias
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.interactive_claude import build_claude_args
from erk_shared.context.types import InteractiveClaudeConfig, RepoContext
from erk_shared.gateway.github.issues.types import IssueNotFound


@alias("rec")
@click.command("reconcile")
@click.argument("objective", type=int, required=True)
@click.pass_obj
def reconcile_objectives(ctx: ErkContext, objective: int) -> None:
    """Launch Claude to create a plan for an objective step.

    OBJECTIVE: The objective issue number to work on.
    """
    # Use ctx.repo if it's a valid RepoContext, otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Validate objective exists and has erk-objective label
    if not ctx.github.issues.issue_exists(repo.root, objective):
        click.echo(f"Error: Issue #{objective} not found", err=True)
        raise SystemExit(1)

    issue = ctx.github.issues.get_issue(repo.root, objective)
    if isinstance(issue, IssueNotFound):
        click.echo(f"Error: Issue #{issue.issue_number} not found", err=True)
        raise SystemExit(1)
    if "erk-objective" not in issue.labels:
        click.echo(f"Error: Issue #{objective} is not an erk-objective", err=True)
        raise SystemExit(1)

    # Launch Claude with full codebase access
    if shutil.which("claude") is None:
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    command = f"/erk:objective-next-plan {objective}"

    # Get interactive Claude config with plan mode override
    if ctx.global_config is None:
        ic_config = InteractiveClaudeConfig.default()
    else:
        ic_config = ctx.global_config.interactive_claude
    config = ic_config.with_overrides(
        permission_mode_override="plan",
        model_override=None,
        dangerous_override=None,
        allow_dangerous_override=None,
    )

    # Build Claude CLI arguments
    cmd_args = build_claude_args(config, command=command)

    # Replace current process with Claude
    os.execvp("claude", cmd_args)
