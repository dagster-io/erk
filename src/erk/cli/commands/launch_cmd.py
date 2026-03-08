"""Dispatch GitHub Actions workflows via unified interface.

All workflows dispatch via RemoteGitHub. When a local repo is available,
it provides enrichments: owner/repo inference, branch-based PR inference,
dispatch ref from config, and plan metadata updates.

Usage examples:
    erk launch pr-address --pr 456
    erk launch pr-rebase --pr 456
    erk launch pr-rebase --pr 456 --no-squash
    erk launch learn --plan 789
    erk launch one-shot --pr 456 --prompt "fix the auth bug"
    erk launch one-shot --pr 456 -f prompt.md
    erk launch pr-rebase --pr 456 --repo owner/repo
    erk launch consolidate-learn-plans
"""

from pathlib import Path

import click

from erk.cli.commands.consolidate_learn_plans_dispatch import (
    dispatch_consolidate_learn_plans,
)
from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.constants import WORKFLOW_COMMAND_MAP
from erk.cli.ensure import Ensure, UserFacingCliError
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel
from erk_shared.gateway.github.types import GitHubRepoId, PRNotFound
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.remote_github.types import RemotePRNotFound
from erk_shared.gateway.time.abc import Time
from erk_shared.output.output import user_output


def _get_workflow_file(workflow_name: str) -> str:
    """Get the actual workflow filename for a command name."""
    if workflow_name not in WORKFLOW_COMMAND_MAP:
        available = ", ".join(sorted(WORKFLOW_COMMAND_MAP.keys()))
        raise click.UsageError(
            f"Unknown workflow '{workflow_name}'. Available workflows: {available}"
        )
    return WORKFLOW_COMMAND_MAP[workflow_name]


def _add_optional_model(inputs: dict[str, str], *, model: str | None) -> None:
    if model is not None:
        inputs["model_name"] = model


def _dispatch_workflow(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    workflow_name: str,
    inputs: dict[str, str],
    ref: str,
) -> str:
    """Dispatch a workflow via RemoteGitHub and report the run URL.

    Returns:
        Workflow run ID for post-dispatch enrichment.
    """
    workflow_file = _get_workflow_file(workflow_name)
    run_id = remote.dispatch_workflow(
        owner=owner,
        repo=repo_name,
        workflow=workflow_file,
        ref=ref,
        inputs=inputs,
    )
    user_output(click.style("\u2713", fg="green") + " Workflow dispatched")

    user_output("")
    run_url = f"https://github.com/{owner}/{repo_name}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")
    return run_id


# --- Per-workflow handlers ---
# Each takes RemoteGitHub + explicit params, looks up PR, validates,
# builds inputs, dispatches, and returns (branch_name, run_id).


def _dispatch_pr_rebase(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
    no_squash: bool,
    plan_id: str | None,
    model: str | None,
    ref: str,
) -> tuple[str, str]:
    """Dispatch pr-rebase workflow. Returns (branch_name, run_id)."""
    user_output("Checking PR status...")
    pr = remote.get_pr(owner=owner, repo=repo_name, number=pr_number)
    Ensure.invariant(
        not isinstance(pr, RemotePRNotFound),
        f"No pull request found with number #{pr_number}",
    )
    assert not isinstance(pr, RemotePRNotFound)

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot rebase {pr.state} PR - only OPEN PRs can be rebased",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output(f"Base branch: {pr.base_ref_name}")
    user_output("")

    inputs: dict[str, str] = {
        "branch_name": pr.head_ref_name,
        "base_branch": pr.base_ref_name,
        "pr_number": str(pr_number),
        "squash": "false" if no_squash else "true",
        "plan_number": plan_id if plan_id is not None else "",
    }
    _add_optional_model(inputs, model=model)

    user_output("Dispatching pr-rebase workflow...")
    run_id = _dispatch_workflow(
        remote,
        owner=owner,
        repo_name=repo_name,
        workflow_name="pr-rebase",
        inputs=inputs,
        ref=ref,
    )
    return (pr.head_ref_name, run_id)


def _dispatch_pr_address(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
    plan_id: str | None,
    model: str | None,
    ref: str,
) -> tuple[str, str]:
    """Dispatch pr-address workflow. Returns (branch_name, run_id)."""
    user_output("Checking PR status...")
    pr = remote.get_pr(owner=owner, repo=repo_name, number=pr_number)
    Ensure.invariant(
        not isinstance(pr, RemotePRNotFound),
        f"No pull request found with number #{pr_number}",
    )
    assert not isinstance(pr, RemotePRNotFound)

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot address comments on {pr.state} PR - only OPEN PRs can be addressed",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output("")

    inputs: dict[str, str] = {
        "pr_number": str(pr_number),
        "plan_number": plan_id if plan_id is not None else "",
    }
    _add_optional_model(inputs, model=model)

    user_output("Dispatching pr-address workflow...")
    run_id = _dispatch_workflow(
        remote,
        owner=owner,
        repo_name=repo_name,
        workflow_name="pr-address",
        inputs=inputs,
        ref=ref,
    )
    return (pr.head_ref_name, run_id)


def _dispatch_pr_rewrite(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
    plan_id: str | None,
    model: str | None,
    ref: str,
) -> tuple[str, str]:
    """Dispatch pr-rewrite workflow. Returns (branch_name, run_id)."""
    user_output("Checking PR status...")
    pr = remote.get_pr(owner=owner, repo=repo_name, number=pr_number)
    Ensure.invariant(
        not isinstance(pr, RemotePRNotFound),
        f"No pull request found with number #{pr_number}",
    )
    assert not isinstance(pr, RemotePRNotFound)

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot rewrite {pr.state} PR - only OPEN PRs can be rewritten",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output(f"Base branch: {pr.base_ref_name}")
    user_output("")

    inputs: dict[str, str] = {
        "branch_name": pr.head_ref_name,
        "base_branch": pr.base_ref_name,
        "pr_number": str(pr_number),
        "plan_number": plan_id if plan_id is not None else "",
    }
    _add_optional_model(inputs, model=model)

    user_output("Dispatching pr-rewrite workflow...")
    run_id = _dispatch_workflow(
        remote,
        owner=owner,
        repo_name=repo_name,
        workflow_name="pr-rewrite",
        inputs=inputs,
        ref=ref,
    )
    return (pr.head_ref_name, run_id)


def _dispatch_learn(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    issue: int,
    ref: str,
) -> None:
    """Dispatch learn workflow."""
    user_output(f"Dispatching learn workflow for plan #{issue}...")

    inputs: dict[str, str] = {
        "plan_number": str(issue),
    }

    _dispatch_workflow(
        remote,
        owner=owner,
        repo_name=repo_name,
        workflow_name="learn",
        inputs=inputs,
        ref=ref,
    )


def _dispatch_consolidate_learn_plans(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    model: str | None,
    ref: str | None,
    time_gateway: Time,
) -> None:
    """Dispatch consolidate-learn-plans workflow with branch + PR creation."""
    dispatch_consolidate_learn_plans(
        remote=remote,
        owner=owner,
        repo=repo_name,
        model=model,
        dry_run=False,
        ref=ref,
        time_gateway=time_gateway,
    )


def _dispatch_one_shot(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
    prompt: str,
    model: str | None,
    ref: str,
) -> tuple[str, str]:
    """Dispatch one-shot workflow. Returns (branch_name, run_id)."""
    user_output("Checking PR status...")
    pr = remote.get_pr(owner=owner, repo=repo_name, number=pr_number)
    Ensure.invariant(
        not isinstance(pr, RemotePRNotFound),
        f"No pull request found with number #{pr_number}",
    )
    assert not isinstance(pr, RemotePRNotFound)

    Ensure.invariant(
        pr.state == "OPEN",
        f"Cannot run one-shot on {pr.state} PR - only OPEN PRs can be targeted",
    )

    user_output(f"PR #{pr_number}: {click.style(pr.title, fg='cyan')} ({pr.state})")
    user_output("")

    submitted_by = remote.get_authenticated_user()

    inputs: dict[str, str] = {
        "prompt": prompt,
        "branch_name": pr.head_ref_name,
        "pr_number": str(pr_number),
        "submitted_by": submitted_by,
    }
    _add_optional_model(inputs, model=model)

    user_output("Dispatching one-shot workflow...")
    run_id = _dispatch_workflow(
        remote,
        owner=owner,
        repo_name=repo_name,
        workflow_name="one-shot",
        inputs=inputs,
        ref=ref,
    )
    return (pr.head_ref_name, run_id)


# --- Entry point ---


@click.command("launch")
@click.argument("workflow_name", type=str)
@click.option(
    "--pr",
    "pr_number",
    type=int,
    help="PR number (required for pr-rebase and pr-address)",
)
@click.option(
    "--plan",
    "plan_number",
    type=int,
    help="Plan number (required for learn)",
)
@click.option(
    "--no-squash",
    is_flag=True,
    help="Skip squashing commits before rebase (pr-rebase only)",
)
@click.option(
    "--model",
    type=str,
    help="Claude model to use (for workflows that support it)",
)
@click.option(
    "--prompt",
    type=str,
    default=None,
    help="Prompt text for one-shot workflow",
)
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Read prompt from a file (one-shot only)",
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
@resolved_repo_option
@click.pass_obj
def launch(
    ctx: ErkContext,
    workflow_name: str,
    *,
    pr_number: int | None,
    plan_number: int | None,
    no_squash: bool,
    model: str | None,
    prompt: str | None,
    file_path: str | None,
    dispatch_ref: str | None,
    ref_current: bool,
    repo_id: GitHubRepoId,
) -> None:
    """Dispatch a GitHub Actions workflow.

    WORKFLOW_NAME is the workflow to dispatch. Available workflows:

    \b
      pr-rebase                  - Rebase PR with AI-powered conflict resolution
      pr-address                 - Address PR review comments remotely
      pr-rewrite                 - Rebase PR and regenerate AI PR summary
      learn                      - Extract insights from a plan issue
      one-shot                   - Run one-shot workflow against an existing PR
      consolidate-learn-plans    - Consolidate open learn plans into one PR

    Examples:

    \b
      # Rebase current branch's PR
      erk launch pr-rebase

    \b
      # Rebase specific PR
      erk launch pr-rebase --pr 123

    \b
      # Address PR review comments
      erk launch pr-address --pr 456

    \b
      # Dispatch learn for a plan issue
      erk launch learn --plan 123

    \b
      # Run one-shot against a PR with inline prompt
      erk launch one-shot --pr 456 --prompt "fix the auth bug"

    \b
      # Run one-shot against a PR with prompt from file
      erk launch one-shot --pr 456 -f prompt.md

    Requirements:

    \b
    - GitHub authentication required (via gh auth login or API token)
    - Required GitHub Actions secrets must be configured
    """
    # 1. Get RemoteGitHub instance
    remote = get_remote_github(ctx)

    # 2. Auth check via remote
    is_authenticated, _, _ = remote.check_auth_status()
    if not is_authenticated:
        raise UserFacingCliError(
            "GitHub is not authenticated\n\n"
            "Authenticate with: gh auth login\n\n"
            "This is required before dispatching workflows."
        )

    # 3. Validate workflow name
    _ = _get_workflow_file(workflow_name)

    has_local_repo = not isinstance(ctx.repo, NoRepoSentinel)

    # 4. Resolve dispatch ref — local enrichments when available, fallback to default branch
    if ref_current and not has_local_repo:
        raise click.UsageError("--ref-current requires a local git repository")

    ref: str | None
    if has_local_repo:
        ref = resolve_dispatch_ref(ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)
    else:
        ref = dispatch_ref

    if ref is None:
        ref = remote.get_default_branch_name(owner=repo_id.owner, repo=repo_id.repo)

    # 5. Local enrichment: pr-rebase branch inference when no --pr
    inferred_branch: str | None = None
    if workflow_name == "pr-rebase" and pr_number is None:
        if not has_local_repo:
            raise UserFacingCliError(
                "--pr is required for pr-rebase without a local repo"
                " (no local branch to infer from)"
            )
        assert not isinstance(ctx.repo, NoRepoSentinel)
        current_branch = Ensure.not_none(
            ctx.git.branch.get_current_branch(ctx.cwd),
            "Not on a branch - checkout a branch or provide --pr",
        )
        pr_for_branch = ctx.github.get_pr_for_branch(ctx.repo.root, current_branch)
        Ensure.invariant(
            not isinstance(pr_for_branch, PRNotFound),
            f"No pull request found for branch '{current_branch}'",
        )
        assert not isinstance(pr_for_branch, PRNotFound)
        pr_number = pr_for_branch.number
        inferred_branch = current_branch

    # 6. Local enrichment: plan ID resolution
    plan_id: str | None = None
    if has_local_repo and inferred_branch is not None:
        assert not isinstance(ctx.repo, NoRepoSentinel)
        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(ctx.repo.root, inferred_branch)

    # 7. Dispatch to unified handler
    branch_name: str | None = None
    run_id: str | None = None

    if workflow_name == "pr-rebase":
        assert pr_number is not None  # Resolved via --pr or branch inference above
        branch_name, run_id = _dispatch_pr_rebase(
            remote,
            owner=repo_id.owner,
            repo_name=repo_id.repo,
            pr_number=pr_number,
            no_squash=no_squash,
            plan_id=plan_id,
            model=model,
            ref=ref,
        )
    elif workflow_name == "pr-address":
        Ensure.invariant(
            pr_number is not None,
            "--pr is required for pr-address workflow",
        )
        assert pr_number is not None
        branch_name, run_id = _dispatch_pr_address(
            remote,
            owner=repo_id.owner,
            repo_name=repo_id.repo,
            pr_number=pr_number,
            plan_id=plan_id,
            model=model,
            ref=ref,
        )
    elif workflow_name == "pr-rewrite":
        Ensure.invariant(
            pr_number is not None,
            "--pr is required for pr-rewrite workflow",
        )
        assert pr_number is not None
        branch_name, run_id = _dispatch_pr_rewrite(
            remote,
            owner=repo_id.owner,
            repo_name=repo_id.repo,
            pr_number=pr_number,
            plan_id=plan_id,
            model=model,
            ref=ref,
        )
    elif workflow_name == "learn":
        Ensure.invariant(
            plan_number is not None,
            "--plan is required for learn workflow",
        )
        assert plan_number is not None
        _dispatch_learn(
            remote,
            owner=repo_id.owner,
            repo_name=repo_id.repo,
            issue=plan_number,
            ref=ref,
        )
    elif workflow_name == "one-shot":
        Ensure.invariant(
            pr_number is not None,
            "--pr is required for one-shot workflow",
        )
        assert pr_number is not None
        Ensure.invariant(
            not (prompt is not None and file_path is not None),
            "--prompt and --file are mutually exclusive",
        )
        resolved_prompt: str | None = prompt
        if file_path is not None:
            resolved_prompt = Path(file_path).read_text(encoding="utf-8").strip()
        Ensure.invariant(
            resolved_prompt is not None and len(resolved_prompt) > 0,
            "--prompt or --file is required for one-shot workflow",
        )
        assert resolved_prompt is not None
        branch_name, run_id = _dispatch_one_shot(
            remote,
            owner=repo_id.owner,
            repo_name=repo_id.repo,
            pr_number=pr_number,
            prompt=resolved_prompt,
            model=model,
            ref=ref,
        )
    elif workflow_name == "consolidate-learn-plans":
        _dispatch_consolidate_learn_plans(
            remote,
            owner=repo_id.owner,
            repo_name=repo_id.repo,
            model=model,
            ref=ref,
            time_gateway=ctx.time,
        )
    elif workflow_name == "plan-implement":
        raise click.UsageError(
            "Use 'erk pr dispatch' instead of 'erk launch plan-implement'.\n"
            "The plan-implement workflow requires branch and PR setup that "
            "'erk pr dispatch' handles automatically."
        )
    else:
        # Should never reach here due to _get_workflow_file validation
        raise click.UsageError(f"Unknown workflow: {workflow_name}")

    # 8. Post-dispatch: plan metadata update (local repo only)
    if has_local_repo and branch_name is not None and run_id is not None:
        assert not isinstance(ctx.repo, NoRepoSentinel)
        maybe_update_plan_dispatch_metadata(ctx, ctx.repo, branch_name, run_id)
