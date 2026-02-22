"""Command to dispatch a task for fully autonomous remote execution.

No local planning — the remote Claude explores the codebase, plans the change,
implements it, and creates a PR.

Usage:
    erk one-shot "fix the import in config.py"
    erk one-shot --file prompt.md
    erk one-shot "add type hints to utils.py" --model opus
    erk one-shot "fix the typo in README.md" --dry-run
    erk one-shot "rename issue_number to plan_number in impl_init.py" --plan-only
"""

from pathlib import Path

import click

from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("one-shot", hidden=True)
@click.argument("prompt", required=False, default=None)
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Read prompt from a file instead of a CLI argument",
)
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
@click.option(
    "--plan-only",
    is_flag=True,
    help="Create a plan remotely without implementing it",
)
@click.pass_obj
def one_shot(
    ctx: ErkContext,
    *,
    prompt: str | None,
    file_path: str | None,
    model: str | None,
    dry_run: bool,
    plan_only: bool,
) -> None:
    """Submit a task for fully autonomous remote execution.

    Creates a branch, draft PR, and dispatches a GitHub Actions workflow
    where Claude autonomously explores, plans, implements, and submits.

    Provide prompt as an argument or via --file (not both).

    Examples:

    \b
      erk one-shot "fix the import in config.py"
      erk one-shot --file prompt.md
      erk one-shot "add type hints to utils.py" --model opus
      erk one-shot "fix the typo in README.md" --dry-run
      erk one-shot "rename issue_number to plan_number" --plan-only
    """
    # Resolve prompt from argument or file
    if file_path is not None and prompt is not None:
        Ensure.invariant(False, "Provide prompt as argument or --file, not both")

    if file_path is not None:
        prompt = Path(file_path).read_text(encoding="utf-8")
    elif prompt is None:
        Ensure.invariant(False, "Provide a prompt argument or --file")

    assert prompt is not None  # type narrowing after guard

    # Validate prompt is non-empty
    Ensure.invariant(
        len(prompt.strip()) > 0,
        "Prompt must not be empty",
    )

    # Normalize model name
    model = normalize_model_name(model)

    extra = {"plan_only": "true"} if plan_only else {}

    params = OneShotDispatchParams(
        prompt=prompt,
        model=model,
        extra_workflow_inputs=extra,
    )

    dispatch_one_shot(ctx, params=params, dry_run=dry_run)
