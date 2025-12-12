"""Command to run a turn for an objective."""

import click

from erk.cli.commands.completions import complete_objective_names
from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.objectives.turn import (
    build_claude_prompt,
    build_turn_prompt,
    format_turn_output,
)
from erk_shared.output.output import user_output


@click.command("turn")
@click.argument("name", type=str, shell_complete=complete_objective_names)
@click.option(
    "--prompt-only",
    is_flag=True,
    help="Output prompt without launching Claude",
)
@click.option(
    "--dangerous",
    is_flag=True,
    help="Skip permission prompts when launching Claude",
)
@click.pass_obj
def turn_objective(ctx: ErkContext, name: str, prompt_only: bool, dangerous: bool) -> None:
    """Run a turn for an objective, launching Claude to evaluate and create a plan.

    A turn evaluates the current codebase against the objective's desired
    state and generates a bounded plan if gaps are found.

    By default, launches Claude interactively with the evaluation prompt.
    Use --prompt-only to output the prompt for manual use.

    Example:
        erk objective turn cli-ensure-error-handling
        erk objective turn cli-ensure-error-handling --prompt-only
        erk objective turn cli-ensure-error-handling --dangerous
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Check objective exists
    if not ctx.objectives.objective_exists(repo_root, name):
        user_output(click.style(f"Objective not found: {name}", fg="red"))
        raise SystemExit(1)

    try:
        definition = ctx.objectives.get_objective_definition(repo_root, name)
        notes = ctx.objectives.get_notes(repo_root, name)
    except ValueError as e:
        user_output(click.style(f"Error parsing objective: {e}", fg="red"))
        raise SystemExit(1) from e

    # Build the turn prompt
    prompt = build_turn_prompt(definition, notes)

    if prompt_only:
        # Output the formatted prompt for manual use
        user_output(format_turn_output(prompt))
        user_output("")
        user_output(click.style("---", dim=True))
        user_output("")
        user_output(
            "Copy the above prompt to Claude to evaluate this objective "
            "against the current codebase."
        )
        user_output("")
        user_output("After evaluation, Claude will respond with:")
        user_output("  STATUS: COMPLETE    - if no gaps found")
        user_output("  STATUS: GAPS_FOUND  - with a proposed plan")
        return

    # Default: Launch Claude interactively
    claude_prompt = build_claude_prompt(prompt)
    exit_code = ctx.claude_executor.execute_interactive_command(
        claude_prompt,
        ctx.cwd,
        dangerous,
    )

    if exit_code != 0:
        raise SystemExit(exit_code)
