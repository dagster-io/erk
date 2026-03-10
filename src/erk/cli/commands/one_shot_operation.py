"""Core operation for one-shot remote dispatch.

Pure business logic: takes a request dataclass with simple types,
resolves dependencies, dispatches the workflow, and returns a result.
No Click imports, no JSON output branching.
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
from erk.cli.repo_resolution import get_remote_github, resolve_owner_repo
from erk.core.context import ErkContext


@dataclass(frozen=True)
class OneShotRequest:
    """Request for one-shot dispatch with simple types only."""

    prompt: str
    model: str | None = None
    dry_run: bool = False
    plan_only: bool = False
    slug: str | None = None
    dispatch_ref: str | None = None
    ref_current: bool = False
    target_repo: str | None = None


def run_one_shot(
    request: OneShotRequest,
    *,
    ctx: ErkContext,
) -> OneShotDispatchResult | OneShotDryRunResult:
    """Execute a one-shot remote dispatch.

    Args:
        request: OneShotRequest with simple types
        ctx: ErkContext with all dependencies

    Returns:
        OneShotDispatchResult or OneShotDryRunResult
    """
    # Validate prompt
    if not request.prompt.strip():
        raise UserFacingCliError("Prompt must not be empty", error_type="invalid_input")

    # Normalize model name
    model = normalize_model_name(request.model)

    extra = {"plan_only": "true"} if request.plan_only else {}

    params = OneShotDispatchParams(
        prompt=request.prompt,
        model=model,
        extra_workflow_inputs=extra,
        slug=request.slug,
    )

    # Resolve owner/repo
    owner, repo_name = resolve_owner_repo(ctx, target_repo=request.target_repo)

    # Resolve dispatch ref
    if request.target_repo is not None and request.ref_current:
        raise UserFacingCliError(
            "--repo and --ref-current are mutually exclusive",
            error_type="invalid_input",
        )
    if request.target_repo is not None:
        ref = request.dispatch_ref
    else:
        ref = resolve_dispatch_ref(
            ctx, dispatch_ref=request.dispatch_ref, ref_current=request.ref_current
        )

    remote = get_remote_github(ctx)

    return dispatch_one_shot_remote(
        remote=remote,
        owner=owner,
        repo=repo_name,
        params=params,
        dry_run=request.dry_run,
        ref=ref,
        time_gateway=ctx.time,
        prompt_executor=ctx.prompt_executor,
    )
