"""Command to display objective details."""

import click

from erk.cli.commands.completions import complete_objective_names
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


@click.command("get")
@click.argument("name", type=str, shell_complete=complete_objective_names)
@click.pass_obj
def get_objective(ctx: ErkContext, name: str) -> None:
    """Display details for a specific objective.

    Shows the objective definition including desired state, scope,
    and turn configuration.

    Example:
        erk objective get cli-ensure-error-handling
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Check objective exists
    if not ctx.objectives.objective_exists(repo_root, name):
        user_output(click.style(f"Objective not found: {name}", fg="red"))
        raise SystemExit(1)

    try:
        definition = ctx.objectives.get_objective_definition(repo_root, name)
    except ValueError as e:
        user_output(click.style(f"Error parsing objective: {e}", fg="red"))
        raise SystemExit(1) from e

    # Display objective details
    user_output(click.style(f"# Objective: {definition.name}", bold=True))
    user_output("")
    user_output(f"Type: {click.style(definition.objective_type.value, fg='cyan')}")
    user_output("")

    user_output(click.style("## Desired State", bold=True))
    user_output(definition.desired_state)
    user_output("")

    user_output(click.style("## Rationale", bold=True))
    user_output(definition.rationale)
    user_output("")

    if definition.scope_includes or definition.scope_excludes:
        user_output(click.style("## Scope", bold=True))
        if definition.scope_includes:
            user_output("In Scope:")
            for item in definition.scope_includes:
                user_output(f"  - {item}")
        if definition.scope_excludes:
            user_output("Out of Scope:")
            for item in definition.scope_excludes:
                user_output(f"  - {item}")
        user_output("")

    if definition.examples:
        user_output(click.style("## Examples", bold=True))
        for example in definition.examples:
            user_output(example)
        user_output("")

    # Show notes summary if any
    notes = ctx.objectives.get_notes(repo_root, name)
    if notes.entries:
        user_output(click.style("## Accumulated Notes", bold=True))
        user_output(f"{len(notes.entries)} note(s) from previous turns")
        user_output("")

    user_output(click.style("## Turn Configuration", bold=True))
    user_output("Evaluation Prompt: (configured)")
    user_output("Plan Sizing: (configured)")
