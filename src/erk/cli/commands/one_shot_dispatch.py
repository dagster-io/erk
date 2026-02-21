"""Shared dispatch logic for one-shot autonomous execution.

Extracts the branch-create/push/PR/workflow-trigger sequence into reusable
pieces so both `erk one-shot` and `erk objective plan --one-shot` can
dispatch tasks through the same CI workflow.
"""

import logging
from dataclasses import dataclass
from datetime import UTC

import click

from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.metadata.core import (
    create_submission_queued_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.parsing import construct_workflow_run_url
from erk_shared.gateway.github.plan_issues import create_plan_issue
from erk_shared.gateway.github.pr_footer import build_pr_body_footer
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import (
    format_branch_timestamp_suffix,
    generate_draft_pr_branch_name,
    generate_issue_branch_name,
    sanitize_worktree_name,
)
from erk_shared.output.output import user_output
from erk_shared.plan_store.draft_pr_lifecycle import build_plan_stage_body

logger = logging.getLogger(__name__)

ONE_SHOT_WORKFLOW = "one-shot.yml"


@dataclass(frozen=True)
class OneShotDispatchParams:
    """Parameters for dispatching a one-shot workflow."""

    prompt: str
    model: str | None
    extra_workflow_inputs: dict[str, str]


@dataclass(frozen=True)
class OneShotDispatchResult:
    """Result of a successful one-shot dispatch."""

    pr_number: int
    run_id: str
    branch_name: str


def generate_branch_name(
    prompt: str,
    *,
    time: Time,
    plan_issue_number: int | None,
    objective_id: int | None,
) -> str:
    """Generate a branch name from the prompt.

    Format: P{N}-{slug}-{MM-DD-HHMM} (with optional O{M} objective encoding)
    when plan_issue_number is provided, otherwise oneshot-{slug}-{MM-DD-HHMM}.

    Args:
        prompt: The task description
        time: Time gateway for deterministic timestamps
        plan_issue_number: If provided, delegate to generate_issue_branch_name
        objective_id: If provided with plan_issue_number, encode O{N} in branch name

    Returns:
        Branch name string
    """
    if plan_issue_number is not None:
        return generate_issue_branch_name(
            plan_issue_number, prompt, time.now(), objective_id=objective_id
        )
    slug = sanitize_worktree_name(prompt)
    prefix = "oneshot-"
    max_slug_len = 31 - len(prefix)
    if len(slug) > max_slug_len:
        slug = slug[:max_slug_len].rstrip("-")
    timestamp = format_branch_timestamp_suffix(time.now())
    return f"{prefix}{slug}{timestamp}"


def dispatch_one_shot(
    ctx: ErkContext,
    *,
    params: OneShotDispatchParams,
    dry_run: bool,
) -> OneShotDispatchResult | None:
    """Execute the full dispatch sequence for a one-shot workflow.

    Creates branch, pushes, creates draft PR, triggers workflow,
    then restores original branch. In dry-run mode, prints what
    would happen without executing.

    Args:
        ctx: Erk context with git/github gateways
        params: Dispatch parameters
        dry_run: If True, print preview without executing

    Returns:
        OneShotDispatchResult with pr_number, run_id, branch_name,
        or None in dry-run mode
    """
    # Validate we're in a git repo
    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )
    assert not isinstance(ctx.repo, NoRepoSentinel)
    repo: RepoContext = ctx.repo

    # Validate GitHub authentication
    Ensure.gh_authenticated(ctx)

    # Get GitHub username
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Detect trunk branch
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # Build PR title
    max_title_len = 60
    suffix = "..." if len(params.prompt) > max_title_len else ""
    pr_title = f"One-shot: {params.prompt[:max_title_len]}{suffix}"

    if dry_run:
        # In dry-run, show preview without creating skeleton issue
        branch_name = generate_branch_name(
            params.prompt,
            time=ctx.time,
            plan_issue_number=None,
            objective_id=None,
        )
        user_output(
            click.style("Dry-run mode:", fg="cyan", bold=True) + " No changes will be made\n"
        )
        user_output(f"Prompt: {params.prompt}")
        user_output(f"Branch: {branch_name}")
        user_output(f"PR title: {pr_title}")
        user_output(f"Base branch: {trunk}")
        user_output(f"Submitted by: {submitted_by}")
        if params.model is not None:
            user_output(f"Model: {params.model}")
        user_output(f"Workflow: {ONE_SHOT_WORKFLOW}")
        if params.extra_workflow_inputs:
            for key, value in params.extra_workflow_inputs.items():
                user_output(f"Extra input: {key}={value}")
        return None

    objective_issue_str = params.extra_workflow_inputs.get("objective_issue")
    objective_id = int(objective_issue_str) if objective_issue_str else None

    is_draft_pr = ctx.plan_backend.get_provider_name() == "github-draft-pr"

    # --- Backend-conditional entity creation ---
    # github backend: create skeleton issue first for P<N>- branch naming
    # draft_pr backend: skip skeleton issue, use plan/ branch naming, PR is the plan
    plan_issue_number: int | None = None
    if not is_draft_pr:
        skeleton_plan_content = (
            f"_One-shot: plan content will be populated by one-shot workflow._\n\n"
            f"**Prompt:** {params.prompt}"
        )
        skeleton_result = create_plan_issue(
            github_issues=ctx.github.issues,
            repo_root=repo.root,
            plan_content=skeleton_plan_content,
            title=f"One-shot: {params.prompt[:max_title_len]}{suffix}",
            extra_labels=None,
            title_tag=None,
            source_repo=None,
            objective_id=objective_id,
            created_from_session=None,
            created_from_workflow_run_url=None,
            learned_from_issue=None,
            lifecycle_stage="prompted",
        )
        plan_issue_number = skeleton_result.issue_number

    # Generate branch name
    if is_draft_pr:
        # draft_pr: plan/ prefix (no issue number needed)
        branch_name = generate_draft_pr_branch_name(
            params.prompt,
            ctx.time.now(),
            objective_id=objective_id,
        )
    else:
        # github: P<N>- prefix using skeleton issue number
        branch_name = generate_branch_name(
            params.prompt,
            time=ctx.time,
            plan_issue_number=plan_issue_number,
            objective_id=objective_id,
        )

    # Save current branch for restoration after workflow trigger
    original_branch = ctx.git.branch.get_current_branch(repo.root)
    if original_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Not on a branch (detached HEAD state). Cannot submit from here."
        )
        raise SystemExit(1)

    # Create branch from trunk
    user_output("Creating branch...")
    ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)

    try:
        ctx.branch_manager.checkout_branch(repo.root, branch_name)

        # Write prompt to .worker-impl/prompt.md so it's committed to the branch
        # (.impl/ is in .gitignore; .worker-impl/ is the committable counterpart
        # that the remote workflow copies into .impl/)
        worker_impl_dir = repo.root / ".worker-impl"
        worker_impl_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = worker_impl_dir / "prompt.md"
        prompt_file.write_text(params.prompt + "\n", encoding="utf-8")

        # Stage and commit with prompt file
        ctx.git.commit.stage_files(repo.root, [".worker-impl/prompt.md"])
        ctx.git.commit.commit(repo.root, f"One-shot: {params.prompt[:60]}")

        # Push to remote
        user_output("Pushing to remote...")
        push_result = ctx.git.remote.push_to_remote(
            repo.root, "origin", branch_name, set_upstream=True, force=False
        )
        if isinstance(push_result, PushError):
            Ensure.invariant(False, f"Failed to push branch: {push_result.message}")

        # --- Create draft PR ---
        user_output("Creating draft PR...")
        if is_draft_pr:
            # draft_pr: create PR with plan-header metadata block
            _, username_for_header, _ = ctx.github.check_auth_status()
            created_at = ctx.time.now().replace(tzinfo=UTC).isoformat()
            metadata_body = format_plan_header_body(
                created_at=created_at,
                created_by=username_for_header or "unknown",
                worktree_name=None,
                branch_name=branch_name,
                plan_comment_id=None,
                last_dispatched_run_id=None,
                last_dispatched_node_id=None,
                last_dispatched_at=None,
                last_local_impl_at=None,
                last_local_impl_event=None,
                last_local_impl_session=None,
                last_local_impl_user=None,
                last_remote_impl_at=None,
                last_remote_impl_run_id=None,
                last_remote_impl_session_id=None,
                source_repo=None,
                objective_issue=objective_id,
                created_from_session=None,
                created_from_workflow_run_url=None,
                last_learn_session=None,
                last_learn_at=None,
                learn_status=None,
                learn_plan_issue=None,
                learn_plan_pr=None,
                learned_from_issue=None,
                lifecycle_stage="prompted",
            )
            placeholder_content = (
                f"_One-shot: plan content will be populated by one-shot workflow._\n\n"
                f"**Prompt:** {params.prompt}"
            )
            pr_body_initial = build_plan_stage_body(metadata_body, placeholder_content)
            pr_number = ctx.github.create_pr(
                repo.root,
                branch_name,
                pr_title,
                pr_body_initial,
                trunk,
                draft=True,
            )
            # Add footer now that we have the PR number.
            # No issue_number — draft PR IS the plan, Closes #N would be self-referential.
            footer = build_pr_body_footer(pr_number, issue_number=None, plans_repo=None)
            ctx.github.update_pr_body(repo.root, pr_number, pr_body_initial + footer)
            # Add erk-plan label
            ctx.github.add_label_to_pr(repo.root, pr_number, "erk-plan")

            # Key: set plan_issue_number = pr_number so downstream code
            # (workflow inputs, metadata writing, comments) targets the PR
            plan_issue_number = pr_number
        else:
            # github: create plain draft PR with closing reference
            closing_ref = ""
            if plan_issue_number is not None:
                plans_repo = ctx.local_config.plans_repo
                closing_ref = (
                    f"\n\nCloses {plans_repo}#{plan_issue_number}"
                    if plans_repo
                    else f"\n\nCloses #{plan_issue_number}"
                )
            pr_number = ctx.github.create_pr(
                repo.root,
                branch_name,
                pr_title,
                f"Autonomous one-shot execution.\n\n**Prompt:** {params.prompt}{closing_ref}",
                trunk,
                draft=True,
            )
        user_output(f"Created draft PR #{pr_number}")

        # Build workflow inputs
        # Truncate prompt for workflow input (full text is in .worker-impl/prompt.md)
        max_input_len = 500
        truncated_prompt = params.prompt[:max_input_len]
        if len(params.prompt) > max_input_len:
            truncated_prompt += "... (full prompt committed to .worker-impl/prompt.md)"

        inputs: dict[str, str] = {
            "prompt": truncated_prompt,
            "branch_name": branch_name,
            "pr_number": str(pr_number),
            "submitted_by": submitted_by,
        }
        if params.model is not None:
            inputs["model_name"] = params.model
        if plan_issue_number is not None:
            inputs["plan_issue_number"] = str(plan_issue_number)

        # Merge extra workflow inputs
        inputs.update(params.extra_workflow_inputs)

        # Trigger workflow
        user_output("Triggering one-shot workflow...")
        run_id = ctx.github.trigger_workflow(
            repo_root=repo.root,
            workflow=ONE_SHOT_WORKFLOW,
            inputs=inputs,
        )

        # Compute run_url and queued_at for use in PR body update, metadata, and comment
        run_url: str | None = None
        if repo.github is not None:
            run_url = construct_workflow_run_url(repo.github.owner, repo.github.repo, run_id)
        queued_at = ctx.time.now().replace(tzinfo=UTC).isoformat()

        # Update PR body with workflow run link (best-effort)
        # For github backend: rewrite with prompt + run link + closing ref
        # For draft_pr backend: skip — metadata block body should not be overwritten
        if not is_draft_pr and run_url is not None:
            try:
                closing_ref = ""
                if plan_issue_number is not None:
                    plans_repo = ctx.local_config.plans_repo
                    closing_ref = (
                        f"\n\nCloses {plans_repo}#{plan_issue_number}"
                        if plans_repo
                        else f"\n\nCloses #{plan_issue_number}"
                    )
                pr_body = (
                    f"Autonomous one-shot execution.\n\n"
                    f"**Prompt:** {params.prompt}\n\n"
                    f"**Workflow run:** {run_url}{closing_ref}"
                )
                ctx.github.update_pr_body(repo.root, pr_number, pr_body)
            except Exception as e:
                logger.warning("Failed to update stub PR body with workflow run link: %s", e)

        # Write dispatch metadata and post queued comment (best-effort)
        if plan_issue_number is not None:
            # Write dispatch metadata to plan entity (issue for github, PR for draft_pr)
            try:
                write_dispatch_metadata(
                    plan_backend=ctx.plan_backend,
                    github=ctx.github,
                    repo_root=repo.root,
                    issue_number=plan_issue_number,
                    run_id=run_id,
                    dispatched_at=queued_at,
                )
                user_output(click.style("\u2713", fg="green") + " Dispatch metadata written")
            except Exception as e:
                user_output(
                    click.style("Warning: ", fg="yellow")
                    + f"Failed to update dispatch metadata: {e}"
                )

            # Post queued event comment to plan entity
            try:
                metadata_block = create_submission_queued_block(
                    queued_at=queued_at,
                    submitted_by=submitted_by,
                    issue_number=plan_issue_number,
                    validation_results={"issue_is_open": True, "has_erk_plan_label": True},
                    expected_workflow="one-shot",
                )
                comment_body = render_erk_issue_event(
                    title="\U0001f504 One-Shot Dispatched",
                    metadata=metadata_block,
                    description=(
                        f"One-shot submitted by **{submitted_by}** at {queued_at}.\n\n"
                        f"**Workflow run:** {run_url or 'N/A'}\n\n"
                        f"**Prompt:** {params.prompt}"
                    ),
                )
                ctx.issues.add_comment(repo.root, plan_issue_number, comment_body)
                user_output(click.style("\u2713", fg="green") + " Queued event comment posted")
            except Exception as e:
                user_output(
                    click.style("Warning: ", fg="yellow") + f"Failed to post queued comment: {e}"
                )

        # Restore original branch after successful workflow trigger
        ctx.branch_manager.checkout_branch(repo.root, original_branch)

        # Display results
        user_output("")
        user_output(click.style("Done!", fg="green", bold=True))
        if repo.github is not None and run_url is not None:
            pr_url = f"https://github.com/{repo.github.owner}/{repo.github.repo}/pull/{pr_number}"
            user_output(f"PR: {click.style(pr_url, fg='cyan')}")
            user_output(f"Run: {click.style(run_url, fg='cyan')}")
        else:
            user_output(f"PR #{pr_number} created, workflow run {run_id} triggered")

        return OneShotDispatchResult(
            pr_number=pr_number,
            run_id=run_id,
            branch_name=branch_name,
        )
    finally:
        # Always ensure we're back on original branch, even on error
        current = ctx.git.branch.get_current_branch(repo.root)
        if current != original_branch:
            user_output(click.style("Restoring original branch...", fg="yellow"))
            ctx.branch_manager.checkout_branch(repo.root, original_branch)
