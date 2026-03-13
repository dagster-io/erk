"""Dispatch logic for consolidate-learn-plans workflow via RemoteGitHub REST API.

Creates a branch, draft PR, and dispatches the consolidate-learn-plans workflow
entirely via the GitHub REST API. Follows the one-shot dispatch pattern.
"""

import time
from dataclasses import dataclass
from datetime import UTC

import click

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
from erk_shared.naming import format_branch_timestamp_suffix
from erk_shared.output.output import format_duration, user_output
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body

CONSOLIDATE_LEARN_PLANS_WORKFLOW = "consolidate-learn-plans.yml"

BRANCH_PREFIX = "consolidate-learn-plans"


@dataclass(frozen=True)
class ConsolidateLearnPlansDispatchResult:
    """Result of a successful consolidate-learn-plans dispatch."""

    pr_number: int
    run_id: str
    branch_name: str


def _generate_branch_name(*, time_gateway: Time) -> str:
    """Generate a branch name for consolidate-learn-plans.

    Format: consolidate-learn-plans-{MM-DD-HHMM}

    No LLM slug needed — the purpose is fixed.
    """
    timestamp = format_branch_timestamp_suffix(time_gateway.now())
    return f"{BRANCH_PREFIX}{timestamp}"


def dispatch_consolidate_learn_plans(
    *,
    remote: RemoteGitHub,
    owner: str,
    repo: str,
    model: str | None,
    dry_run: bool,
    ref: str | None,
    time_gateway: Time,
) -> ConsolidateLearnPlansDispatchResult | None:
    """Execute the full remote dispatch sequence for consolidate-learn-plans.

    Creates branch, commits prompt file, creates draft PR, and dispatches
    workflow — all via GitHub REST API.

    Returns ConsolidateLearnPlansDispatchResult, or None in dry-run mode.
    """
    submitted_by = remote.get_authenticated_user()
    user_output(click.style(f"  \u2713 Authenticated as {submitted_by}", dim=True))

    trunk = remote.get_default_branch_name(owner=owner, repo=repo)
    pr_title = "Consolidate learn PRs"

    branch_name = _generate_branch_name(time_gateway=time_gateway)

    if dry_run:
        user_output(
            click.style("Dry-run mode:", fg="cyan", bold=True) + " No changes will be made\n"
        )
        user_output(f"Target: {owner}/{repo} (remote)")
        user_output(f"Branch: {branch_name}")
        user_output(f"PR title: {pr_title}")
        user_output(f"Base branch: {trunk}")
        user_output(f"Submitted by: {submitted_by}")
        if model is not None:
            user_output(f"Model: {model}")
        user_output(f"Workflow: {CONSOLIDATE_LEARN_PLANS_WORKFLOW}")
        if ref is not None:
            user_output(f"Ref: {ref}")
        return None

    user_output(click.style("Dispatching consolidate-learn-plans (remote)...", bold=True))
    user_output(click.style(f"  Target: {owner}/{repo}", dim=True))
    if model is not None:
        user_output(click.style(f"  Model: {model}", dim=True))
    user_output("")

    start_monotonic = time.monotonic()
    current_step = "Generating branch name"

    try:
        user_output("Creating branch...")
        user_output(click.style(f"  \u2192 Branch: {branch_name}", dim=True))

        # Get trunk SHA for branch creation
        current_step = "Getting trunk SHA"
        trunk_sha = remote.get_default_branch_sha(owner=owner, repo=repo)

        # Create branch from trunk
        current_step = "Creating branch"
        remote.create_ref(
            owner=owner,
            repo=repo,
            ref=f"refs/heads/{branch_name}",
            sha=trunk_sha,
        )
        user_output(click.style("  \u2713 Branch created", dim=True))

        # Write static prompt to .erk/impl-context/prompt.md
        current_step = "Committing prompt file"
        user_output("Committing prompt file...")
        prompt_content = (
            "Consolidate all open erk-learn PRs into a single documentation update.\n"
            "Run /erk:system:consolidate-learn-plans-plan to query, consolidate, and implement.\n"
        )
        remote.create_file_commit(
            owner=owner,
            repo=repo,
            path=".erk/impl-context/prompt.md",
            content=prompt_content,
            message="Consolidate learn PRs",
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
            objective_issue=None,
            created_from_session=None,
            created_from_workflow_run_url=None,
            created_from_workflow_run_id=None,
            last_learn_session=None,
            last_learn_at=None,
            learn_status=None,
            learn_plan_issue=None,
            learn_plan_pr=None,
            learned_from_issue=None,
            lifecycle_stage="prompted",
        )
        placeholder_content = "_Consolidating learn PRs: content will be populated by workflow._"
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

        # Add plan labels (including erk-learn)
        remote.add_labels(
            owner=owner,
            repo=repo,
            issue_number=pr_number,
            labels=("erk-pr", "erk-learn"),
        )
        user_output(click.style(f"  \u2192 PR #{pr_number}", dim=True))

        # Build workflow inputs
        inputs: dict[str, str] = {
            "branch_name": branch_name,
            "pr_number": str(pr_number),
            "submitted_by": submitted_by,
        }
        if model is not None:
            inputs["model_name"] = model

        # Dispatch workflow
        current_step = "Dispatching consolidate-learn-plans workflow"
        user_output("Dispatching consolidate-learn-plans workflow...")
        dispatch_ref = ref if ref is not None else trunk
        run_id = remote.dispatch_workflow(
            owner=owner,
            repo=repo,
            workflow=CONSOLIDATE_LEARN_PLANS_WORKFLOW,
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
                validation_results={"pr_is_open": True, "has_erk_pr_title": True},
                expected_workflow="consolidate-learn-plans",
            )
            comment_body = render_erk_issue_event(
                title="\U0001f504 Consolidate Learn Plans Dispatched",
                metadata=metadata_block,
                description=(
                    f"Consolidation submitted by **{submitted_by}** at {queued_at}.\n\n"
                    f"**Workflow run:** {run_url}"
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
    except Exception:
        user_output(click.style(f"Failed during: {current_step}", fg="red"))
        raise

    # Display results
    elapsed = time.monotonic() - start_monotonic
    duration_str = format_duration(elapsed)
    user_output("")
    user_output(click.style(f"Done! ({duration_str})", fg="green", bold=True))
    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    user_output(f"PR: {click.style(pr_url, fg='cyan')}")
    user_output(f"Run: {click.style(run_url, fg='cyan')}")

    return ConsolidateLearnPlansDispatchResult(
        pr_number=pr_number,
        run_id=run_id,
        branch_name=branch_name,
    )
