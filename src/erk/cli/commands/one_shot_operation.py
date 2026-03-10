"""Core request/result contract for one-shot dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchParams,
    OneShotDispatchResult,
    OneShotDryRunResult,
    dispatch_one_shot_remote,
)
from erk.core.context import ErkContext, NoRepoSentinel
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.real import RealRemoteGitHub

_MODEL_ALIASES: dict[str, str] = {
    "h": "haiku",
    "s": "sonnet",
    "o": "opus",
}
_VALID_MODELS = {"haiku", "sonnet", "opus"}


@dataclass(frozen=True)
class OneShotRequest:
    """Canonical request for one-shot dispatch."""

    prompt: str
    model: str | None = None
    dry_run: bool = False
    plan_only: bool = False
    slug: str | None = None
    dispatch_ref: str | None = None
    ref_current: bool = False
    repo: str | None = None


def run_one_shot(
    request: OneShotRequest,
    *,
    ctx: ErkContext,
) -> OneShotDispatchResult | OneShotDryRunResult | MachineCommandError:
    """Execute one-shot dispatch from the canonical request contract."""

    if not request.prompt.strip():
        return MachineCommandError(
            error_type="invalid_input",
            message="Prompt must not be empty",
        )

    normalized_model = _normalize_model_name(request.model)
    if isinstance(normalized_model, MachineCommandError):
        return normalized_model

    owner_repo = _resolve_owner_repo(ctx, repo=request.repo)
    if isinstance(owner_repo, MachineCommandError):
        return owner_repo
    owner, repo_name = owner_repo

    resolved_ref = _resolve_dispatch_ref(
        ctx,
        dispatch_ref=request.dispatch_ref,
        ref_current=request.ref_current,
        repo=request.repo,
    )
    if isinstance(resolved_ref, MachineCommandError):
        return resolved_ref

    remote = _resolve_remote_github(ctx)
    if isinstance(remote, MachineCommandError):
        return remote

    extra_workflow_inputs = {"plan_only": "true"} if request.plan_only else {}
    params = OneShotDispatchParams(
        prompt=request.prompt,
        model=normalized_model,
        extra_workflow_inputs=extra_workflow_inputs,
        slug=request.slug,
    )

    return dispatch_one_shot_remote(
        remote=remote,
        owner=owner,
        repo=repo_name,
        params=params,
        dry_run=request.dry_run,
        ref=resolved_ref,
        time_gateway=ctx.time,
        prompt_executor=ctx.prompt_executor,
    )


def _normalize_model_name(model: str | None) -> str | None | MachineCommandError:
    if model is None:
        return None

    normalized = _MODEL_ALIASES.get(model.lower(), model.lower())
    if normalized not in _VALID_MODELS:
        valid_options = ", ".join(sorted(_VALID_MODELS | set(_MODEL_ALIASES.keys())))
        return MachineCommandError(
            error_type="cli_error",
            message=f"Invalid model: '{model}'\nValid options: {valid_options}",
        )
    return normalized


def _resolve_owner_repo(
    ctx: ErkContext,
    *,
    repo: str | None,
) -> tuple[str, str] | MachineCommandError:
    if repo is not None:
        if "/" not in repo or repo.count("/") != 1:
            return MachineCommandError(
                error_type="invalid_repo",
                message=(
                    f"Invalid --repo format: '{repo}'\n"
                    "Expected format: owner/repo (e.g., dagster-io/erk)"
                ),
            )
        owner, repo_name = repo.split("/")
        return (owner, repo_name)

    if isinstance(ctx.repo, NoRepoSentinel) or ctx.repo.github is None:
        return MachineCommandError(
            error_type="cli_error",
            message=(
                "Cannot determine target repository.\n"
                "Use --repo owner/repo or run from inside a git repository."
            ),
        )

    return (ctx.repo.github.owner, ctx.repo.github.repo)


def _resolve_dispatch_ref(
    ctx: ErkContext,
    *,
    dispatch_ref: str | None,
    ref_current: bool,
    repo: str | None,
) -> str | None | MachineCommandError:
    if repo is not None and ref_current:
        return MachineCommandError(
            error_type="cli_error",
            message="--repo and --ref-current are mutually exclusive",
        )

    if ref_current and dispatch_ref is not None:
        return MachineCommandError(
            error_type="cli_error",
            message="--ref and --ref-current are mutually exclusive",
        )

    if repo is not None:
        return dispatch_ref

    if ref_current:
        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            return MachineCommandError(
                error_type="cli_error",
                message="--ref-current requires being on a branch (not detached HEAD)",
            )
        return branch

    if dispatch_ref is not None:
        return dispatch_ref

    return ctx.local_config.dispatch_ref


def _resolve_remote_github(ctx: ErkContext) -> RemoteGitHub | MachineCommandError:
    if ctx.remote_github is not None:
        return ctx.remote_github

    if ctx.http_client is None:
        return MachineCommandError(
            error_type="auth_required",
            message="GitHub authentication required.\nRun 'gh auth login' to authenticate.",
        )

    return RealRemoteGitHub(http_client=ctx.http_client, time=ctx.time)
