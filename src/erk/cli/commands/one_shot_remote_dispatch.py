"""Dispatch logic for one-shot execution via RemoteGitHub REST API.

Uses RemoteGitHub gateway to create branches, commit files, create PRs,
and dispatch workflows entirely via the GitHub REST API. This is the
canonical dispatch path for all one-shot commands.
"""

import time
from dataclasses import dataclass
from datetime import UTC
from typing import Any

import click

from erk.core.branch_slug_generator import generate_branch_slug
from erk_shared.core.prompt_executor import PromptExecutor
from erk_shared.gateway.github.metadata.core import (
    create_submission_queued_block,
    render_erk_issue_event,
)
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.parsing import construct_workflow_run_url
from erk_shared.gateway.github.pr_footer import build_pr_body_footer
from erk_shared.gateway.http.abc import HttpError
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import (
    format_branch_timestamp_suffix,
    generate_planned_pr_branch_name,
    sanitize_worktree_name,
)
from erk_shared.output.output import format_duration, user_output
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body

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
    pr_url: str
    run_url: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "dry_run": False,
            "pr_number": self.pr_number,
            "run_id": self.run_id,
            "branch_name": self.branch_name,
            "pr_url": self.pr_url,
            "run_url": self.run_url,
        }


@dataclass(frozen=True)
class OneShotDryRunResult:
    """Result of a dry-run one-shot dispatch (preview only, no mutations)."""

    branch_name: str
    prompt: str
    target: str
    pr_title: str
    base_branch: str
    submitted_by: str
    model: str | None
    workflow: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "dry_run": True,
            "branch_name": self.branch_name,
            "prompt": self.prompt,
            "target": self.target,
            "pr_title": self.pr_title,
            "base_branch": self.base_branch,
            "submitted_by": self.submitted_by,
            "model": self.model,
            "workflow": self.workflow,
        }


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
        from erk.core.branch_slug_generator import generate_branch_slug

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


def dispatch_one_shot_remote(
    *,
    remote: RemoteGitHub,
    owner: str,
    repo: str,
    params: OneShotDispatchParams,
    dry_run: bool,
    ref: str | None,
    time_gateway: Time,
    prompt_executor: PromptExecutor | None,
) -> OneShotDispatchResult | OneShotDryRunResult:
    """Execute the full remote dispatch sequence for a one-shot workflow.

    Creates branch, commits prompt file, creates draft PR, and dispatches
    workflow — all via GitHub REST API without a local git clone.

    Args:
        remote: RemoteGitHub gateway for API calls
        owner: Repository owner
        repo: Repository name
        params: Dispatch parameters
        dry_run: If True, print preview without executing
        ref: Branch to dispatch workflow from, or None for default branch
        time_gateway: Time gateway for timestamps
        prompt_executor: PromptExecutor for slug generation, or None

    Returns:
        OneShotDispatchResult on success, OneShotDryRunResult in dry-run mode
    """
    # Get authenticated user
    submitted_by = remote.get_authenticated_user()
    user_output(click.style(f"  \u2713 Authenticated as {submitted_by}", dim=True))

    # Detect trunk branch
    trunk = remote.get_default_branch_name(owner=owner, repo=repo)

    # Build PR title
    max_title_len = 60
    suffix = "..." if len(params.prompt) > max_title_len else ""
    pr_title = f"One-shot: {params.prompt[:max_title_len]}{suffix}"

    if dry_run:
        branch_name = generate_branch_name(
            params.prompt,
            time=time_gateway,
            prompt_executor=None,
            slug=params.slug,
        )
        user_output(
            click.style("Dry-run mode:", fg="cyan", bold=True) + " No changes will be made\n"
        )
        user_output(f"Prompt: {params.prompt}")
        user_output(f"Target: {owner}/{repo} (remote)")
        user_output(f"Branch: {branch_name}")
        user_output(f"PR title: {pr_title}")
        user_output(f"Base branch: {trunk}")
        user_output(f"Submitted by: {submitted_by}")
        if params.model is not None:
            user_output(f"Model: {params.model}")
        user_output(f"Workflow: {ONE_SHOT_WORKFLOW}")
        if ref is not None:
            user_output(f"Ref: {ref}")
        if params.extra_workflow_inputs:
            for key, value in params.extra_workflow_inputs.items():
                user_output(f"Extra input: {key}={value}")
        return OneShotDryRunResult(
            branch_name=branch_name,
            prompt=params.prompt,
            target=f"{owner}/{repo}",
            pr_title=pr_title,
            base_branch=trunk,
            submitted_by=submitted_by,
            model=params.model,
            workflow=ONE_SHOT_WORKFLOW,
        )

    # --- Summary block ---
    user_output(click.style("Dispatching one-shot (remote)...", bold=True))
    prompt_preview = params.prompt[:80] + ("..." if len(params.prompt) > 80 else "")
    user_output(click.style(f"  Prompt: {prompt_preview}", dim=True))
    user_output(click.style(f"  Target: {owner}/{repo}", dim=True))
    if params.model is not None:
        user_output(click.style(f"  Model: {params.model}", dim=True))
    user_output("")

    start_monotonic = time.monotonic()

    current_step = "Generating branch name"

    try:
        objective_issue_str = params.extra_workflow_inputs.get("objective_issue")
        objective_id = int(objective_issue_str) if objective_issue_str else None

        # Generate branch name
        user_output("Generating branch name...")
        if params.slug is not None:
            slug = params.slug
            user_output(click.style(f"  \u2713 Slug: {slug} (pre-generated)", dim=True))
        else:
            if prompt_executor is not None:
                slug = generate_branch_slug(prompt_executor, params.prompt)
            else:
                slug = sanitize_worktree_name(params.prompt)[:25].rstrip("-")
            user_output(click.style(f"  \u2713 Slug: {slug}", dim=True))

        branch_name = generate_planned_pr_branch_name(
            slug,
            time_gateway.now(),
            objective_id=objective_id,
        )
        user_output(click.style(f"  \u2192 Branch: {branch_name}", dim=True))

        # Get trunk SHA for branch creation
        current_step = "Getting trunk SHA"
        trunk_sha = remote.get_default_branch_sha(owner=owner, repo=repo)

        # Create branch from trunk
        current_step = "Creating branch"
        user_output("Creating branch...")
        remote.create_ref(
            owner=owner,
            repo=repo,
            ref=f"refs/heads/{branch_name}",
            sha=trunk_sha,
        )
        user_output(click.style("  \u2713 Branch created", dim=True))

        # Write prompt to .erk/impl-context/prompt.md
        current_step = "Committing prompt file"
        user_output("Committing prompt file...")
        remote.create_file_commit(
            owner=owner,
            repo=repo,
            path=".erk/impl-context/prompt.md",
            content=params.prompt + "\n",
            message=f"One-shot: {params.prompt[:60]}",
            branch=branch_name,
        )
        user_output(click.style("  \u2713 Committed", dim=True))

        # Create draft PR
        current_step = "Creating draft PR"
        user_output("Creating draft PR...")
        created_at = time_gateway.now().replace(tzinfo=UTC).isoformat()
        metadata_body = format_plan_header_body(
            created_at=created_at,
            created_by=submitted_by,
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
        pr_number = remote.create_pull_request(
            owner=owner,
            repo=repo,
            head=branch_name,
            base=trunk,
            title=pr_title,
            body=pr_body_initial,
            draft=True,
        )

        # Add footer now that we have the PR number
        footer = build_pr_body_footer(pr_number)
        remote.update_pull_request_body(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            body=pr_body_initial + footer,
        )

        # Add plan labels
        remote.add_labels(
            owner=owner,
            repo=repo,
            issue_number=pr_number,
            labels=("erk-pr", "erk-plan"),
        )
        user_output(click.style(f"  \u2192 PR #{pr_number}", dim=True))

        # Build workflow inputs
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
        inputs["plan_issue_number"] = str(pr_number)
        inputs.update(params.extra_workflow_inputs)

        # Dispatch workflow
        current_step = "Dispatching one-shot workflow"
        user_output("Dispatching one-shot workflow...")
        dispatch_ref = ref if ref is not None else branch_name
        run_id = remote.dispatch_workflow(
            owner=owner,
            repo=repo,
            workflow=ONE_SHOT_WORKFLOW,
            ref=dispatch_ref,
            inputs=inputs,
        )
        user_output(click.style(f"  \u2192 Run ID: {run_id}", dim=True))

        # Post queued comment (best-effort)
        run_url = construct_workflow_run_url(owner, repo, run_id)
        queued_at = time_gateway.now().replace(tzinfo=UTC).isoformat()

        current_step = "Posting queued event comment"
        try:
            metadata_block = create_submission_queued_block(
                queued_at=queued_at,
                submitted_by=submitted_by,
                plan_number=pr_number,
                validation_results={"issue_is_open": True, "has_erk_plan_label": True},
                expected_workflow="one-shot",
            )
            comment_body = render_erk_issue_event(
                title="\U0001f504 One-Shot Dispatched",
                metadata=metadata_block,
                description=(
                    f"One-shot submitted by **{submitted_by}** at {queued_at}.\n\n"
                    f"**Workflow run:** {run_url}\n\n"
                    f"**Prompt:** {params.prompt}"
                ),
            )
            remote.add_issue_comment(
                owner=owner,
                repo=repo,
                issue_number=pr_number,
                body=comment_body,
            )
            user_output(click.style("\u2713", fg="green") + " Queued event comment posted")
        except HttpError as e:
            user_output(
                click.style("Warning: ", fg="yellow") + f"Failed to post queued comment: {e}"
            )

    except SystemExit:
        raise
    except Exception as exc:
        user_output(click.style(f"Failed during: {current_step}", fg="red"))
        raise exc from exc

    # Display results
    elapsed = time.monotonic() - start_monotonic
    duration_str = format_duration(elapsed)
    user_output("")
    user_output(click.style(f"Done! ({duration_str})", fg="green", bold=True))
    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    user_output(f"PR: {click.style(pr_url, fg='cyan')}")
    user_output(f"Run: {click.style(run_url, fg='cyan')}")

    return OneShotDispatchResult(
        pr_number=pr_number,
        run_id=run_id,
        branch_name=branch_name,
        pr_url=pr_url,
        run_url=run_url,
    )
