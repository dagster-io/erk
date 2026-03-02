"""Workflow smoke test logic for erk doctor workflow.

Creates throwaway branches and PRs to verify the GitHub Actions
infrastructure works end-to-end by dispatching through the production
one-shot code path.
"""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.gateway.github.parsing import construct_workflow_run_url

SMOKE_TEST_SLUG = "smoke-test"
SMOKE_TEST_BRANCH_PREFIX = "plnd/smoke-test-"
SMOKE_TEST_PROMPT = "Add a code comment to any file."


@dataclass(frozen=True)
class SmokeTestResult:
    """Result of a successful smoke test dispatch."""

    branch_name: str
    pr_number: int
    run_id: str
    run_url: str | None


@dataclass(frozen=True)
class SmokeTestError:
    """Error during smoke test dispatch."""

    step: str
    message: str


@dataclass(frozen=True)
class CleanupItem:
    """A single smoke test artifact that was cleaned up."""

    branch_name: str
    pr_number: int | None
    closed_pr: bool
    deleted_branch: bool


def run_smoke_test(
    ctx: ErkContext, dispatch_ref: str | None = None
) -> SmokeTestResult | SmokeTestError:
    """Dispatch a smoke test through the production one-shot code path.

    Delegates to dispatch_one_shot() to create a branch, PR with proper
    plan-header metadata, and trigger the one-shot workflow — exactly
    as a real one-shot dispatch would.

    Args:
        ctx: ErkContext with git/github gateways
        dispatch_ref: Branch to dispatch from (defaults to config dispatch_ref)

    Returns:
        SmokeTestResult on success, SmokeTestError on failure
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        return SmokeTestError(step="validation", message="Not in a git repository")
    repo: RepoContext = ctx.repo

    params = OneShotDispatchParams(
        prompt=SMOKE_TEST_PROMPT,
        model=None,
        extra_workflow_inputs={},
        slug=SMOKE_TEST_SLUG,
    )

    ref = dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref
    try:
        result = dispatch_one_shot(ctx, params=params, dry_run=False, ref=ref)
    except SystemExit as exc:
        return SmokeTestError(step="dispatch", message=f"Exit code {exc.code}")
    except (click.ClickException, RuntimeError, ValueError, KeyError) as exc:
        return SmokeTestError(step="dispatch", message=str(exc))

    if result is None:
        return SmokeTestError(step="dispatch", message="dispatch_one_shot returned None")

    # Compute run URL from result
    run_url: str | None = None
    if repo.github is not None:
        run_url = construct_workflow_run_url(repo.github.owner, repo.github.repo, result.run_id)

    return SmokeTestResult(
        branch_name=result.branch_name,
        pr_number=result.pr_number,
        run_id=result.run_id,
        run_url=run_url,
    )


def cleanup_smoke_tests(ctx: ErkContext) -> list[CleanupItem]:
    """Find and remove smoke test branches and their PRs.

    Args:
        ctx: ErkContext with git/github gateways

    Returns:
        List of cleaned up items
    """
    if isinstance(ctx.repo, NoRepoSentinel):
        return []
    repo: RepoContext = ctx.repo

    # List remote branches matching plnd/smoke-test-*
    remote_branches = ctx.git.branch.list_remote_branches(repo.root)
    smoke_branches = [
        b for b in remote_branches if _extract_branch_name(b).startswith(SMOKE_TEST_BRANCH_PREFIX)
    ]

    if not smoke_branches:
        return []

    cleaned: list[CleanupItem] = []
    for remote_branch in smoke_branches:
        branch_name = _extract_branch_name(remote_branch)

        # Find associated PR
        pr_number = _find_pr_for_branch(ctx, repo.root, branch_name)

        closed_pr = False
        if pr_number is not None:
            ctx.github.close_pr(repo.root, pr_number)
            closed_pr = True

        # Delete remote branch
        deleted = ctx.github.delete_remote_branch(repo.root, branch_name)

        cleaned.append(
            CleanupItem(
                branch_name=branch_name,
                pr_number=pr_number,
                closed_pr=closed_pr,
                deleted_branch=deleted,
            )
        )

    return cleaned


def _extract_branch_name(remote_branch: str) -> str:
    """Extract branch name from remote branch ref.

    Remote branches come as 'origin/branch-name'. Strip the remote prefix.
    """
    if "/" in remote_branch:
        # origin/plnd/smoke-test-01-15-1430 -> plnd/smoke-test-01-15-1430
        return remote_branch.split("/", 1)[1]
    return remote_branch


def _find_pr_for_branch(ctx: ErkContext, repo_root: Path, branch_name: str) -> int | None:
    """Find the PR number associated with a branch, if any."""
    prs = ctx.github.list_prs(repo_root, state="all")
    if branch_name in prs:
        return prs[branch_name].number
    return None
