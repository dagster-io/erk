"""Command to dispatch a task for fully autonomous remote execution.

No local planning — the remote Claude explores the codebase, plans the change,
implements it, and creates a PR.

Usage:
    erk one-shot "fix the import in config.py"
    erk one-shot "add type hints to utils.py" --model opus
    erk one-shot "fix the typo in README.md" --dry-run
"""

import click

from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("one-shot", hidden=True)
@click.argument("instruction")
@click.option(
    "-m",
    "--model",
    type=str,
    default=None,
    help="Model to use (haiku/h, sonnet/s, opus/o)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without executing",
)
@click.pass_obj
def one_shot(
    ctx: ErkContext,
    *,
    instruction: str,
    model: str | None,
    dry_run: bool,
) -> None:
    """Submit a task for fully autonomous remote execution.

    Creates a branch, draft PR, and dispatches a GitHub Actions workflow
    where Claude autonomously explores, plans, implements, and submits.

    Examples:

    \b
      erk one-shot "fix the import in config.py"
      erk one-shot "add type hints to utils.py" --model opus
      erk one-shot "fix the typo in README.md" --dry-run
    """
    # Validate instruction is non-empty
    Ensure.invariant(
        len(instruction.strip()) > 0,
        "Instruction must not be empty",
    )

    # Normalize model name
    model = normalize_model_name(model)

    params = OneShotDispatchParams(
        instruction=instruction,
        model=model,
        extra_workflow_inputs={},
    )

    dispatch_one_shot(ctx, params=params, dry_run=dry_run)
