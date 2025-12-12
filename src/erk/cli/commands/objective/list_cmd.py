"""Command to list all objectives in the repository."""

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("list")
@click.pass_obj
def list_objectives(ctx: ErkContext) -> None:
    """List all objectives in the repository.

    Shows objectives defined in the .erk/objectives/ directory.

    Example:
        erk objective list
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    objectives = ctx.objectives.list_objectives(repo_root)

    if not objectives:
        user_output("No objectives found in .erk/objectives/ directory.")
        return

    user_output(f"Found {len(objectives)} objective(s):\n")

    for name in objectives:
        try:
            definition = ctx.objectives.get_objective_definition(repo_root, name)
            type_str = definition.objective_type.value
            user_output(f"  {click.style(name, bold=True)} ({type_str})")
        except ValueError:
            # Gracefully handle malformed objectives
            user_output(f"  {click.style(name, bold=True)} (parse error)")
