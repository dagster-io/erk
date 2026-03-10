"""Command to dispatch a task for fully autonomous remote execution.

No local planning — the remote Claude explores the codebase, plans the change,
implements it, and creates a PR.

Usage:
    erk one-shot "fix the import in config.py"
    erk one-shot --file prompt.md
    erk one-shot "add type hints to utils.py" --model opus
    erk one-shot "fix the typo in README.md" --dry-run
    erk one-shot "rename issue_number to plan_number in impl_init.py" --plan-only
    erk one-shot "fix config bug" --repo owner/repo
"""

from pathlib import Path

import click

from erk.cli.commands.one_shot_operation import OneShotRequest, run_one_shot
from erk.cli.ensure import Ensure, UserFacingCliError
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.output.output import user_output


@click.command("one-shot")
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
@click.option(
    "--slug",
    type=str,
    default=None,
    help="Pre-generated branch slug (skips LLM slug generation)",
)
@click.option(
    "--ref",
    "dispatch_ref",
    type=str,
    default=None,
    help="Branch to dispatch workflow from (overrides config dispatch_ref)",
)
@click.option(
    "--ref-current",
    is_flag=True,
    default=False,
    help="Dispatch workflow from the current branch",
)
@click.option(
    "--repo",
    "target_repo",
    type=str,
    default=None,
    help="Target repo (owner/repo) for remote dispatch without local git clone",
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
    slug: str | None,
    dispatch_ref: str | None,
    ref_current: bool,
    target_repo: str | None,
) -> None:
    """Submit a task for fully autonomous remote execution.

    Creates a branch, draft PR, and dispatches a GitHub Actions workflow
    where Claude autonomously explores, plans, implements, and submits.

    Provide prompt as an argument or via --file (not both).

    Use --repo owner/repo to dispatch to a remote repository without
    needing a local git clone.

    Examples:

    \b
      erk one-shot "fix the import in config.py"
      erk one-shot --file prompt.md
      erk one-shot "add type hints to utils.py" --model opus
      erk one-shot "fix the typo in README.md" --dry-run
      erk one-shot "rename issue_number to plan_number" --plan-only
      erk one-shot "fix config bug" --repo dagster-io/erk
    """
    # Resolve prompt from argument or file
    if file_path is not None and prompt is not None:
        Ensure.invariant(False, "Provide prompt as argument or --file, not both")

    if file_path is not None:
        user_output(click.style(f"  Reading prompt from: {file_path}", dim=True))
        prompt = Path(file_path).read_text(encoding="utf-8")
    elif prompt is None:
        Ensure.invariant(False, "Provide a prompt argument or --file")

    assert prompt is not None  # type narrowing after guard

    # Validate prompt is non-empty
    if not prompt.strip():
        raise UserFacingCliError("Prompt must not be empty", error_type="invalid_input")

    request = OneShotRequest(
        prompt=prompt,
        model=model,
        dry_run=dry_run,
        plan_only=plan_only,
        slug=slug,
        dispatch_ref=dispatch_ref,
        ref_current=ref_current,
        repo=target_repo,
    )

    result = run_one_shot(request, ctx=ctx)
    if isinstance(result, MachineCommandError):
        raise UserFacingCliError(result.message, error_type=result.error_type)
