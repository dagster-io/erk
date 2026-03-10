"""Core operation for one-shot dispatch (transport-independent).

Contains the request type and operation function that both the
human command (one_shot/cli.py) and machine command (one_shot/json_cli.py) share.
"""

from dataclasses import dataclass

from erk.cli.commands.implement_shared import normalize_model_name
from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchParams,
    OneShotDispatchResult,
    OneShotDryRunResult,
    dispatch_one_shot_remote,
)
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.ensure import UserFacingCliError
from erk.core.context import ErkContext, NoRepoSentinel
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.real import RealRemoteGitHub


@dataclass(frozen=True)
class OneShotRequest:
    """Request type for one-shot dispatch."""

    prompt: str
    model: str | None = None
    dry_run: bool = False
    plan_only: bool = False
    slug: str | None = None
    dispatch_ref: str | None = None
    ref_current: bool = False
    target_repo: str | None = None


def _get_remote_github(ctx: ErkContext) -> RemoteGitHub:
    """Get or construct a RemoteGitHub from context."""
    if ctx.remote_github is not None:
        return ctx.remote_github

    if ctx.http_client is None:
        raise UserFacingCliError(
            "GitHub authentication required.\nRun 'gh auth login' to authenticate.",
            error_type="auth_required",
        )

    return RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)


def run_one_shot(
    ctx: ErkContext,
    request: OneShotRequest,
) -> OneShotDispatchResult | OneShotDryRunResult | MachineCommandError:
    """Execute one-shot dispatch operation.

    Pure operation that can be called from either human or machine command.

    Args:
        ctx: ErkContext with all dependencies
        request: Validated request parameters

    Returns:
        Dispatch result, dry-run result, or error
    """
    prompt = request.prompt

    # Validate prompt is non-empty
    if not prompt.strip():
        return MachineCommandError(error_type="invalid_input", message="Prompt must not be empty")

    # Normalize model name
    model = normalize_model_name(request.model)

    extra = {"plan_only": "true"} if request.plan_only else {}

    params = OneShotDispatchParams(
        prompt=prompt,
        model=model,
        extra_workflow_inputs=extra,
        slug=request.slug,
    )

    # Resolve owner/repo
    if request.target_repo is not None:
        if "/" not in request.target_repo or request.target_repo.count("/") != 1:
            return MachineCommandError(
                error_type="invalid_repo",
                message=(
                    f"Invalid --repo format: '{request.target_repo}'\n"
                    "Expected format: owner/repo (e.g., dagster-io/erk)"
                ),
            )
        owner, repo_name = request.target_repo.split("/")
    else:
        if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
            return MachineCommandError(
                error_type="cli_error",
                message=(
                    "Cannot determine target repository.\n"
                    "Use --repo owner/repo or run from inside a git repository."
                ),
            )
        owner, repo_name = ctx.repo.github.owner, ctx.repo.github.repo

    # Resolve dispatch ref
    if request.target_repo is not None:
        ref = request.dispatch_ref
    else:
        ref = resolve_dispatch_ref(
            ctx, dispatch_ref=request.dispatch_ref, ref_current=request.ref_current
        )

    remote = _get_remote_github(ctx)

    result = dispatch_one_shot_remote(
        remote=remote,
        owner=owner,
        repo=repo_name,
        params=params,
        dry_run=request.dry_run,
        ref=ref,
        time_gateway=ctx.time,
        prompt_executor=ctx.prompt_executor,
    )

    return result
