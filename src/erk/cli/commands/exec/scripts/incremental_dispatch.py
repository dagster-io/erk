"""Dispatch a local plan against an existing PR for remote implementation.

Usage:
    erk exec incremental-dispatch --plan-file <path> --pr <number> [OPTIONS]

Commits the plan as impl-context to the PR's branch and triggers the
plan-implement workflow. Unlike regular dispatch, this does not require
the erk-plan label — just an OPEN PR.
"""

import json
from pathlib import Path

import click

from erk.cli.commands.pr.dispatch_cmd import load_workflow_config
from erk.cli.commands.pr.dispatch_helpers import ensure_trunk_synced, sync_branch_to_sha
from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.commands.ref_resolution import resolve_dispatch_ref
from erk.cli.constants import DISPATCH_WORKFLOW_NAME
from erk_shared.context.helpers import (
    require_branch_manager,
    require_context,
    require_git,
    require_github,
    require_plan_backend,
    require_repo_root,
    require_time,
)
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.parsing import (
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.impl_context import build_impl_context_files
from erk_shared.output.output import user_output


@click.command(name="incremental-dispatch")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to plan markdown file",
)
@click.option("--pr", "pr_number", type=int, required=True, help="PR number to dispatch against")
@click.option("--ref", "dispatch_ref", default=None, help="Branch to dispatch workflow from")
@click.option(
    "--ref-current",
    is_flag=True,
    default=False,
    help="Dispatch workflow from the current branch",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format",
)
@click.pass_context
def incremental_dispatch(
    ctx: click.Context,
    *,
    plan_file: Path,
    pr_number: int,
    dispatch_ref: str | None,
    ref_current: bool,
    output_format: str,
) -> None:
    """Dispatch a local plan against an existing PR for remote implementation."""
    erk_ctx = require_context(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    github = require_github(ctx)
    time = require_time(ctx)

    ref = resolve_dispatch_ref(erk_ctx, dispatch_ref=dispatch_ref, ref_current=ref_current)

    # Validate PR exists and is OPEN
    pr_result = github.get_pr(repo_root, pr_number)
    if isinstance(pr_result, PRNotFound):
        _output_error(output_format, f"PR #{pr_number} not found")
        raise SystemExit(1)

    if pr_result.state != "OPEN":
        _output_error(output_format, f"PR #{pr_number} is {pr_result.state}, must be OPEN")
        raise SystemExit(1)

    branch_name = pr_result.head_ref_name

    # Read plan content
    plan_content = plan_file.read_text(encoding="utf-8")

    # Ensure trunk is synced
    repo = erk_ctx.repo
    if isinstance(repo, NoRepoSentinel):
        _output_error(output_format, "Not in a git repository")
        raise SystemExit(1)
    ensure_trunk_synced(erk_ctx, repo)

    # Sync local branch ref to remote (no checkout required)
    user_output(f"Syncing branch: {click.style(branch_name, fg='cyan')}")
    git.remote.fetch_branch(repo_root, "origin", branch_name)
    checked_out_path = git.worktree.is_branch_checked_out(repo_root, branch_name)
    if checked_out_path is None:
        git.branch.create_branch(repo_root, branch_name, f"origin/{branch_name}", force=True)
    else:
        remote_sha = git.branch.get_branch_head(repo_root, f"origin/{branch_name}")
        if remote_sha is not None:
            sync_branch_to_sha(erk_ctx, repo_root, branch_name, remote_sha)

    # Build and commit impl-context files to branch
    user_output("Committing plan to branch...")
    files = build_impl_context_files(
        plan_content=plan_content,
        plan_id=str(pr_number),
        url=pr_result.url,
        provider="incremental-dispatch",
        objective_id=None,
        now_iso=time.now().isoformat(),
        node_ids=None,
    )
    git.commit.commit_files_to_branch(
        repo_root,
        branch=branch_name,
        files=files,
        message=f"Incremental dispatch for PR #{pr_number}\n\n{plan_content}",
    )

    # Update Graphite tracking after plumbing commit advanced the branch
    branch_manager = require_branch_manager(ctx)
    branch_manager.retrack_branch(repo_root, branch_name)

    # If branch is checked out, write files to disk and stage so git status is clean
    if checked_out_path is not None:
        for rel_path, content in files.items():
            abs_path = checked_out_path / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
        git.commit.stage_files(checked_out_path, list(files.keys()), force=True)

    # Push
    push_result = git.remote.push_to_remote(
        repo_root, "origin", branch_name, set_upstream=False, force=False
    )
    if isinstance(push_result, PushError):
        _output_error(output_format, f"Push failed: {push_result.message}")
        raise SystemExit(1)
    user_output(click.style("✓", fg="green") + " Branch pushed to remote")

    # Get username for workflow inputs
    _, username, _ = github.check_auth_status()
    submitted_by = username or "unknown"

    # Determine base branch from PR
    trunk = git.branch.detect_trunk_branch(repo_root)

    # Load workflow config and trigger
    workflow_config = load_workflow_config(repo_root, DISPATCH_WORKFLOW_NAME)

    inputs = {
        "plan_id": str(pr_number),
        "submitted_by": submitted_by,
        "plan_title": pr_result.title,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        "base_branch": trunk,
        "plan_backend": "planned_pr",
        "dispatch_type": "incremental",
        **workflow_config,
    }

    user_output(f"Dispatching workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")
    run_id = github.trigger_workflow(
        repo_root=repo_root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs=inputs,
        ref=ref,
    )
    user_output(click.style("✓", fg="green") + " Workflow dispatched")

    # Update plan-header dispatch metadata (best-effort)
    try:
        plan_backend = require_plan_backend(ctx)
        write_dispatch_metadata(
            plan_backend=plan_backend,
            github=github,
            repo_root=repo_root,
            plan_number=pr_number,
            run_id=run_id,
            dispatched_at=time.now().isoformat(),
        )
        user_output(click.style("✓", fg="green") + " Dispatch metadata written")
    except Exception as e:
        user_output(
            click.style("Warning: ", fg="yellow") + f"Failed to update dispatch metadata: {e}"
        )

    # Build workflow URL
    owner_repo = extract_owner_repo_from_github_url(pr_result.url)
    if owner_repo is not None:
        owner, repo = owner_repo
        workflow_url = construct_workflow_run_url(owner, repo, run_id)
    else:
        workflow_url = f"https://github.com/actions/runs/{run_id}"

    if output_format == "json":
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "pr_number": pr_number,
                    "branch_name": branch_name,
                    "workflow_run_id": run_id,
                    "workflow_url": workflow_url,
                }
            )
        )
    else:
        user_output(f"PR: {pr_result.url}")
        user_output(f"Workflow: {workflow_url}")


def _output_error(output_format: str, message: str) -> None:
    """Output error in the requested format."""
    if output_format == "json":
        click.echo(json.dumps({"success": False, "error": message}))
    else:
        user_output(click.style("Error: ", fg="red") + message)
