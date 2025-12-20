"""Command to create the next plan for an objective."""

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


@click.command("next-plan")
@click.argument("name", type=str, shell_complete=complete_objective_names)
@click.option(
    "--prompt-only",
    is_flag=True,
    help="Output prompt without launching Claude",
)
@click.pass_obj
def next_plan(ctx: ErkContext, name: str, prompt_only: bool) -> None:
    """Create the next plan for an objective, launching Claude in plan mode.

    Evaluates the current codebase against the objective's desired state
    and generates a bounded plan if gaps are found. Claude is launched
    in plan mode to analyze and propose changes before implementation.

    By default, launches Claude interactively in plan mode with the evaluation prompt.
    Use --prompt-only to output the prompt for manual use.

    Example:
        erk objective next-plan cli-ensure-error-handling
        erk objective next-plan cli-ensure-error-handling --prompt-only
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

    # Default: Launch Claude interactively in plan mode
    claude_prompt = build_claude_prompt(prompt)
    ctx.claude_executor.execute_interactive(
        worktree_path=ctx.cwd,
        mode="plan",
        command=claude_prompt,
        target_subpath=None,
    )
    # Never returns - process is replaced by Claude
