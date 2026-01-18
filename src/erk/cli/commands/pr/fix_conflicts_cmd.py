"""Fix merge conflicts with AI-powered resolution.

Uses Claude to resolve merge conflicts on the current branch without
any Graphite stack manipulation. Invokes the /erk:fix-conflicts
Claude slash command.
"""

import click

from erk.cli.output import stream_fix_conflicts
from erk.core.context import ErkContext


@click.command("fix-conflicts")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def pr_fix_conflicts(ctx: ErkContext, *, dangerous: bool) -> None:
    """Fix merge conflicts with AI-powered resolution.

    Resolves merge conflicts on the current branch using Claude.
    Does not require or interact with Graphite stacks.

    Examples:

    \b
      # Fix conflicts with Claude
      erk pr fix-conflicts --dangerous

    To disable the --dangerous flag requirement:

    \b
      erk config set fix_conflicts_require_dangerous_flag false
    """
    # Runtime validation: require --dangerous unless config disables requirement
    if not dangerous:
        require_flag = (
            ctx.global_config is None or ctx.global_config.fix_conflicts_require_dangerous_flag
        )
        if require_flag:
            raise click.UsageError(
                "Missing option '--dangerous'.\n"
                "To disable: erk config set fix_conflicts_require_dangerous_flag false"
            )

    cwd = ctx.cwd

    # Check for conflicts
    conflicted_files = ctx.git.get_conflicted_files(cwd)
    if not conflicted_files:
        click.echo("No merge conflicts detected.")
        return

    # Check Claude availability
    executor = ctx.claude_executor
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI is required for conflict resolution.\n\n"
            "Install from: https://claude.com/download"
        )

    # Show conflict info
    click.echo(
        click.style(
            f"Found {len(conflicted_files)} conflicted file(s). Invoking Claude...",
            fg="yellow",
        )
    )

    # Execute conflict resolution
    result = stream_fix_conflicts(executor, cwd)

    if result.requires_interactive:
        raise click.ClickException("Semantic conflict requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Conflict resolution failed")

    click.echo(click.style("\n✅ Conflicts resolved!", fg="green", bold=True))
