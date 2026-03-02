"""Shared dispatch logic for one-shot autonomous execution.

Extracts the branch-create/push/PR/workflow-dispatch sequence into reusable
pieces so both `erk one-shot` and `erk objective plan --one-shot` can
dispatch tasks through the same CI workflow.
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC

import click

from erk.cli.commands.pr.metadata_helpers import write_dispatch_metadata
from erk.cli.ensure import Ensure
from erk.core.branch_slug_generator import (
    BRANCH_SLUG_SYSTEM_PROMPT,
    _postprocess_slug,
    generate_branch_slug,
)
from erk.core.context import ErkContext, NoRepoSentinel, RepoContext
from erk.core.fast_llm import AnthropicLlmCaller, LlmResponse
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.metadata.core import (
    create_submission_queued_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.parsing import construct_workflow_run_url
from erk_shared.gateway.github.pr_footer import build_pr_body_footer
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import (
    format_branch_timestamp_suffix,
    generate_planned_pr_branch_name,
    sanitize_worktree_name,
)
from erk_shared.output.output import format_duration, user_output
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body

logger = logging.getLogger(__name__)

ONE_SHOT_WORKFLOW = "one-shot.yml"


@dataclass(frozen=True)
class OneShotDispatchParams:
    """Parameters for dispatching a one-shot workflow."""

    prompt: str
    model: str | None
    extra_workflow_inputs: dict[str, str]
    slug: str | None


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
    prompt_executor: PromptExecutor | None,
    slug: str | None,
) -> str:
    """Generate a branch name from the prompt.

    Format: oneshot-{slug}-{MM-DD-HHMM}

    When slug is provided, uses it directly (no LLM call). When
    prompt_executor is provided, uses LLM to generate a concise slug
    from the prompt. When None (e.g., dry-run mode), falls back to
    sanitize_worktree_name.

    Args:
        prompt: The task description
        time: Time gateway for deterministic timestamps
        prompt_executor: PromptExecutor for LLM slug generation, or None to skip
        slug: Pre-generated slug to use directly, or None to generate one

    Returns:
        Branch name string
    """
    if slug is not None:
        title = slug
    elif prompt_executor is not None:
        title = generate_branch_slug(prompt_executor, prompt)
    else:
        title = prompt

    sanitized = sanitize_worktree_name(title)
    prefix = "oneshot-"
    max_slug_len = 31 - len(prefix)
    if len(sanitized) > max_slug_len:
        sanitized = sanitized[:max_slug_len].rstrip("-")
    timestamp = format_branch_timestamp_suffix(time.now())
    return f"{prefix}{sanitized}{timestamp}"


def dispatch_one_shot(
    ctx: ErkContext,
    *,
    params: OneShotDispatchParams,
    dry_run: bool,
) -> OneShotDispatchResult | None:
    """Execute the full dispatch sequence for a one-shot workflow.

    Creates branch, commits prompt file directly to branch (no checkout),
    pushes, creates draft PR, and dispatches workflow. In dry-run mode,
    prints what would happen without executing.

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
    current_step = "Validating GitHub authentication"
    user_output("Validating GitHub authentication...")
    Ensure.gh_authenticated(ctx)

    # Get GitHub username
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"
    user_output(click.style(f"  \u2713 Authenticated as {submitted_by}", dim=True))

    # Detect trunk branch
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)

    # Build PR title
    max_title_len = 60
    suffix = "..." if len(params.prompt) > max_title_len else ""
    pr_title = f"One-shot: {params.prompt[:max_title_len]}{suffix}"

    if dry_run:
        # In dry-run, show preview without executing
        branch_name = generate_branch_name(
            params.prompt,
            time=ctx.time,
            prompt_executor=None,
            slug=params.slug,
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

    # --- Summary block ---
    user_output(click.style("Dispatching one-shot...", bold=True))
    prompt_preview = params.prompt[:80] + ("..." if len(params.prompt) > 80 else "")
    user_output(click.style(f"  Prompt: {prompt_preview}", dim=True))
    if params.model is not None:
        user_output(click.style(f"  Model: {params.model}", dim=True))
    backend_name = ctx.plan_backend.get_provider_name()
    user_output(click.style(f"  Backend: {backend_name}", dim=True))
    user_output("")

    start_monotonic = time.monotonic()

    try:
        objective_issue_str = params.extra_workflow_inputs.get("objective_issue")
        objective_id = int(objective_issue_str) if objective_issue_str else None

        plan_number: int | None = None

        # Generate branch name with LLM-generated slug
        current_step = "Generating branch name"
        user_output("Generating branch name...")
        if params.slug is not None:
            slug = params.slug
            user_output(click.style(f"  \u2713 Slug: {slug} (pre-generated)", dim=True))
        else:
            result = AnthropicLlmCaller().call(
                params.prompt, system_prompt=BRANCH_SLUG_SYSTEM_PROMPT
            )
            slug = _postprocess_slug(result.text) if isinstance(result, LlmResponse) else None
            if slug is None:
                slug = sanitize_worktree_name(params.prompt)[:25].rstrip("-")
                user_output(click.style(f"  \u2713 Slug: {slug} (sanitized)", dim=True))
            else:
                user_output(click.style(f"  \u2713 Slug: {slug}", dim=True))
        # planned_pr: plnd/ prefix (no issue number needed)
        branch_name = generate_planned_pr_branch_name(
            slug,
            ctx.time.now(),
            objective_id=objective_id,
        )
        user_output(click.style(f"  \u2192 Branch: {branch_name}", dim=True))

        # Guard against detached HEAD state
        current_branch = ctx.git.branch.get_current_branch(repo.root)
        if current_branch is None:
            user_output(
                click.style("Error: ", fg="red")
                + "Not on a branch (detached HEAD state). Cannot submit from here."
            )
            raise SystemExit(1)

        # Create branch from trunk
        current_step = "Creating branch"
        user_output("Creating branch...")
        ctx.git.branch.create_branch(repo.root, branch_name, trunk, force=False)
        user_output(click.style("  \u2713 Branch created", dim=True))

        # Write prompt to .erk/impl-context/prompt.md directly on the branch (no checkout)
        current_step = "Committing prompt file"
        user_output("Committing prompt file...")
        ctx.git.commit.commit_files_to_branch(
            repo.root,
            branch=branch_name,
            files={".erk/impl-context/prompt.md": params.prompt + "\n"},
            message=f"One-shot: {params.prompt[:60]}",
        )
        user_output(click.style("  \u2713 Committed", dim=True))

        # Push to remote
        current_step = "Pushing to remote"
        user_output("Pushing to remote...")
        push_start = time.monotonic()
        push_result = ctx.git.remote.push_to_remote(
            repo.root, "origin", branch_name, set_upstream=True, force=False
        )
        if isinstance(push_result, PushError):
            Ensure.invariant(False, f"Failed to push branch: {push_result.message}")
        push_elapsed = time.monotonic() - push_start
        user_output(click.style(f"  \u2713 Pushed ({format_duration(push_elapsed)})", dim=True))

        # --- Create draft PR ---
        current_step = "Creating draft PR"
        user_output("Creating draft PR...")
        # planned_pr: create PR with plan-header metadata block
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
        pr_body_initial = build_plan_stage_body(metadata_body, placeholder_content, summary="")
        pr_number = ctx.github.create_pr(
            repo.root,
            branch_name,
            pr_title,
            pr_body_initial,
            trunk,
            draft=True,
        )
        # Add footer now that we have the PR number.
        footer = build_pr_body_footer(pr_number)
        ctx.github.update_pr_body(repo.root, pr_number, pr_body_initial + footer)
        # Add plan labels
        ctx.github.add_label_to_pr(repo.root, pr_number, "erk-pr")
        ctx.github.add_label_to_pr(repo.root, pr_number, "erk-plan")

        # Key: set plan_number = pr_number so downstream code
        # (workflow inputs, metadata writing, comments) targets the PR
        plan_number = pr_number
        user_output(click.style(f"  \u2192 PR #{pr_number}", dim=True))

        # Build workflow inputs
        # Truncate prompt for workflow input (full text committed to branch)
        max_input_len = 500
        truncated_prompt = params.prompt[:max_input_len]
        if len(params.prompt) > max_input_len:
            truncated_prompt += "... (full prompt committed to .erk/impl-context/prompt.md)"

        inputs: dict[str, str] = {
            "prompt": truncated_prompt,
            "branch_name": branch_name,
            "pr_number": str(pr_number),
            "submitted_by": submitted_by,
            "plan_backend": "planned_pr",
        }
        if params.model is not None:
            inputs["model_name"] = params.model
        if plan_number is not None:
            inputs["plan_issue_number"] = str(plan_number)

        # Merge extra workflow inputs
        inputs.update(params.extra_workflow_inputs)

        # Dispatch workflow
        current_step = "Dispatching one-shot workflow"
        user_output("Dispatching one-shot workflow...")
        run_id = ctx.github.trigger_workflow(
            repo_root=repo.root,
            workflow=ONE_SHOT_WORKFLOW,
            inputs=inputs,
            ref=ctx.local_config.dispatch_ref,
        )
        user_output(click.style(f"  \u2192 Run ID: {run_id}", dim=True))

        # Compute run_url and queued_at for use in PR body update, metadata, and comment
        run_url: str | None = None
        if repo.github is not None:
            run_url = construct_workflow_run_url(repo.github.owner, repo.github.repo, run_id)
        queued_at = ctx.time.now().replace(tzinfo=UTC).isoformat()

        # Write dispatch metadata and post queued comment (best-effort)
        current_step = "Writing dispatch metadata"
        if plan_number is not None:
            # Write dispatch metadata to plan entity (PR)
            try:
                write_dispatch_metadata(
                    plan_backend=ctx.plan_backend,
                    github=ctx.github,
                    repo_root=repo.root,
                    plan_number=plan_number,
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
            current_step = "Posting queued event comment"
            try:
                metadata_block = create_submission_queued_block(
                    queued_at=queued_at,
                    submitted_by=submitted_by,
                    plan_number=plan_number,
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
                ctx.issues.add_comment(repo.root, plan_number, comment_body)
                user_output(click.style("\u2713", fg="green") + " Queued event comment posted")
            except Exception as e:
                user_output(
                    click.style("Warning: ", fg="yellow") + f"Failed to post queued comment: {e}"
                )

    except SystemExit:
        raise
    except Exception as exc:
        user_output(click.style(f"Failed during: {current_step}", fg="red"))
        raise exc from None

    # Display results
    elapsed = time.monotonic() - start_monotonic
    duration_str = format_duration(elapsed)
    user_output("")
    user_output(click.style(f"Done! ({duration_str})", fg="green", bold=True))
    if repo.github is not None and run_url is not None:
        pr_url = f"https://github.com/{repo.github.owner}/{repo.github.repo}/pull/{pr_number}"
        user_output(f"PR: {click.style(pr_url, fg='cyan')}")
        user_output(f"Run: {click.style(run_url, fg='cyan')}")
    else:
        user_output(f"PR #{pr_number} created, workflow run {run_id} dispatched")

    return OneShotDispatchResult(
        pr_number=pr_number,
        run_id=run_id,
        branch_name=branch_name,
    )
