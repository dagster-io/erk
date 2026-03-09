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

from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchParams,
    OneShotDispatchResult,
    OneShotDryRunResult,
    dispatch_one_shot_remote,
)
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.ensure import Ensure, UserFacingCliError
from erk.cli.json_command import json_command
from erk.core.context import ErkContext, NoRepoSentinel
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.real import RealRemoteGitHub
from erk_shared.output.output import user_output


def _get_remote_github(ctx: ErkContext) -> RemoteGitHub:
    """Get or construct a RemoteGitHub from context.

    Uses ctx.remote_github if provided (tests inject FakeRemoteGitHub here).
    Otherwise constructs RealRemoteGitHub from ctx.http_client.

    Args:
        ctx: ErkContext with http_client and time

    Returns:
        RemoteGitHub instance

    Raises:
        UserFacingCliError: If no http_client is available
    """
    if ctx.remote_github is not None:
        return ctx.remote_github

    if ctx.http_client is None:
        raise UserFacingCliError(
            "GitHub authentication required.\nRun 'gh auth login' to authenticate.",
            error_type="auth_required",
        )

    return RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)


@json_command(
    exclude_json_input=frozenset({"file_path"}), required_json_input=frozenset({"prompt"})
)
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
    json_mode: bool,
    prompt: str | None,
    file_path: str | None,
    model: str | None,
    dry_run: bool,
    plan_only: bool,
    slug: str | None,
    dispatch_ref: str | None,
    ref_current: bool,
    target_repo: str | None,
) -> OneShotDispatchResult | OneShotDryRunResult:
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

    # Normalize model name
    model = normalize_model_name(model)

    extra = {"plan_only": "true"} if plan_only else {}

    params = OneShotDispatchParams(
        prompt=prompt,
        model=model,
        extra_workflow_inputs=extra,
        slug=slug,
    )

    # Resolve owner/repo: from --repo flag or from local git remote
    if target_repo is not None:
        if "/" not in target_repo or target_repo.count("/") != 1:
            raise UserFacingCliError(
                f"Invalid --repo format: '{target_repo}'\n"
                "Expected format: owner/repo (e.g., dagster-io/erk)",
                error_type="invalid_repo",
            )
        owner, repo_name = target_repo.split("/")
    else:
        if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
            raise UserFacingCliError(
                "Cannot determine target repository.\n"
                "Use --repo owner/repo or run from inside a git repository.",
                error_type="cli_error",
            )
        owner, repo_name = ctx.repo.github.owner, ctx.repo.github.repo

    # Resolve dispatch ref
    if target_repo is not None and ref_current:
        raise click.UsageError("--repo and --ref-current are mutually exclusive")
    if target_repo is not None:
        ref = dispatch_ref  # no local branch resolution for remote
    else:
        ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)

    remote = _get_remote_github(ctx)

    result = dispatch_one_shot_remote(
        remote=remote,
        owner=owner,
        repo=repo_name,
        params=params,
        dry_run=dry_run,
        ref=ref,
        time_gateway=ctx.time,
        prompt_executor=ctx.prompt_executor,
    )

    return result
