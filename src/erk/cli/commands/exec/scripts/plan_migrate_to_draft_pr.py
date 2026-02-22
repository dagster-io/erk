"""Migrate an issue-based plan to a draft-PR-based plan.

Reads an existing erk-plan GitHub issue, creates a draft PR using the
draft_pr backend, then closes the original issue with a migration notice.

Usage:
    erk exec plan-migrate-to-draft-pr <plan_number>
    erk exec plan-migrate-to-draft-pr <plan_number> --dry-run
    erk exec plan-migrate-to-draft-pr <plan_number> --format display

Options:
    --dry-run: Preview the migration without making any changes
    --format json|display: Output format (default: json)

Exit Codes:
    0: Success
    1: Error (issue not found, not an erk-plan, etc.)
"""

import json

import click

from erk.core.branch_slug_generator import generate_slug_or_fallback
from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_prompt_executor,
    require_repo_root,
    require_time,
)
from erk_shared.naming import generate_draft_pr_branch_name
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import PlanNotFound


def _output_error(output_format: str, message: str, error_type: str) -> None:
    """Emit an error in the requested format."""
    if output_format == "display":
        click.echo(f"Error: {message}", err=True)
    else:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": error_type,
                    "message": message,
                }
            )
        )


def _output_dry_run(
    output_format: str,
    *,
    plan_number: int,
    title: str,
    branch_name: str,
    trunk: str,
) -> None:
    """Emit dry-run preview in the requested format."""
    if output_format == "display":
        click.echo(f"[dry-run] Would migrate issue #{plan_number}: {title}")
        click.echo(f"[dry-run] Would create branch: {branch_name} from {trunk}")
        click.echo("[dry-run] Would create draft PR from branch")
        click.echo(f"[dry-run] Would close issue #{plan_number}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "dry_run": True,
                    "original_plan_number": plan_number,
                    "title": title,
                    "branch_name": branch_name,
                    "trunk": trunk,
                }
            )
        )


@click.command(name="plan-migrate-to-draft-pr")
@click.argument("plan_number", type=int)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview the migration without making any changes",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.pass_context
def plan_migrate_to_draft_pr(
    ctx: click.Context,
    plan_number: int,
    *,
    dry_run: bool,
    output_format: str,
) -> None:
    """Migrate an issue-based plan to a draft-PR-based plan.

    Reads the plan from the specified GitHub issue, creates a new draft PR
    with the same content and metadata, then closes the original issue with
    a migration notice pointing to the new draft PR.

    Preserves: title, plan content, labels (including erk-learn), objective
    link, and created_from_session from the original issue.
    """
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    github = require_github(ctx)
    issues = require_issues(ctx)
    now = require_time(ctx).now()

    # Fetch the issue plan via GitHubPlanStore
    issue_store = GitHubPlanStore(issues)
    plan = issue_store.get_plan(repo_root, str(plan_number))
    if isinstance(plan, PlanNotFound):
        _output_error(
            output_format,
            f"Issue #{plan_number} not found",
            "issue_not_found",
        )
        raise SystemExit(1)

    # Validate it has the erk-plan label
    if "erk-plan" not in plan.labels:
        _output_error(
            output_format,
            f"Issue #{plan_number} does not have the 'erk-plan' label",
            "not_an_erk_plan",
        )
        raise SystemExit(1)

    # Generate draft-PR branch name from trunk with LLM-generated slug
    trunk = git.branch.detect_trunk_branch(cwd)
    executor = require_prompt_executor(ctx)
    slug = generate_slug_or_fallback(executor, plan.title)
    branch_name = generate_draft_pr_branch_name(
        slug,
        now,
        objective_id=plan.objective_id,
    )

    if dry_run:
        _output_dry_run(
            output_format,
            plan_number=plan_number,
            title=plan.title,
            branch_name=branch_name,
            trunk=trunk,
        )
        return

    # Create branch from trunk, commit plan file directly (no checkout), push
    git.branch.create_branch(cwd, branch_name, trunk, force=False)
    git.commit.commit_files_to_branch(
        repo_root,
        branch=branch_name,
        files={f"{IMPL_CONTEXT_DIR}/plan.md": plan.body},
        message=f"Add plan: {plan.title}",
    )
    git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)

    # Build metadata for draft PR, preserving key fields from original issue
    created_from_session = plan.header_fields.get("created_from_session")
    metadata: dict[str, object] = {
        k: v
        for k, v in {
            "branch_name": branch_name,
            "trunk_branch": trunk,
            "objective_issue": plan.objective_id,
            "created_from_session": created_from_session,
        }.items()
        if v is not None
    }

    # Create draft PR via DraftPRPlanBackend
    draft_backend = DraftPRPlanBackend(github, issues, time=require_time(ctx))
    result = draft_backend.create_plan(
        repo_root=repo_root,
        title=plan.title,
        content=plan.body,
        labels=tuple(plan.labels),
        metadata=metadata,
    )
    pr_number = int(result.plan_id)
    pr_url = result.url

    # Carry over operational metadata from the source issue's plan-header.
    # create_plan sets these to None; update_metadata restores historical data.
    _FIELDS_HANDLED_BY_CREATE = {
        "schema_version",
        "created_at",
        "created_by",
        "branch_name",
        "plan_comment_id",
        "source_repo",
        "objective_issue",
        "created_from_session",
        "created_from_workflow_run_url",
    }
    operational_fields: dict[str, object] = {
        k: v
        for k, v in plan.header_fields.items()
        if k not in _FIELDS_HANDLED_BY_CREATE and v is not None
    }
    if operational_fields:
        draft_backend.update_metadata(repo_root, str(pr_number), operational_fields)

    # Comment on original issue with migration notice, then close it
    migration_comment = (
        f"Migrated to draft PR #{pr_number}: {pr_url}\n\n"
        "This issue has been superseded by the draft PR above."
    )
    issues.add_comment(repo_root, plan_number, migration_comment)
    issues.close_issue(repo_root, plan_number)

    if output_format == "display":
        click.echo(f"Migrated plan #{plan_number} → draft PR #{pr_number}")
        click.echo(f"Title: {plan.title}")
        click.echo(f"PR URL: {pr_url}")
        click.echo(f"Branch: {branch_name}")
        click.echo(f"Original issue #{plan_number} closed.")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "original_plan_number": plan_number,
                    "plan_number": pr_number,
                    "plan_url": pr_url,
                    "branch_name": branch_name,
                }
            )
        )
