"""Migrate an issue-based plan to a draft-PR-based plan.

Reads an existing erk-plan GitHub issue, creates a draft PR using the
draft_pr backend, then closes the original issue with a migration notice.

Usage:
    erk exec plan-migrate-to-draft-pr <issue_number>
    erk exec plan-migrate-to-draft-pr <issue_number> --dry-run
    erk exec plan-migrate-to-draft-pr <issue_number> --format display

Options:
    --dry-run: Preview the migration without making any changes
    --format json|display: Output format (default: json)

Exit Codes:
    0: Success
    1: Error (issue not found, not an erk-plan, etc.)
"""

import json

import click

from erk_shared.context.helpers import (
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_repo_root,
    require_time,
)
from erk_shared.naming import generate_draft_pr_branch_name
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
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
    issue_number: int,
    title: str,
    branch_name: str,
    trunk: str,
) -> None:
    """Emit dry-run preview in the requested format."""
    if output_format == "display":
        click.echo(f"[dry-run] Would migrate issue #{issue_number}: {title}")
        click.echo(f"[dry-run] Would create branch: {branch_name} from {trunk}")
        click.echo("[dry-run] Would create draft PR from branch")
        click.echo(f"[dry-run] Would close issue #{issue_number}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "dry_run": True,
                    "original_issue_number": issue_number,
                    "title": title,
                    "branch_name": branch_name,
                    "trunk": trunk,
                }
            )
        )


@click.command(name="plan-migrate-to-draft-pr")
@click.argument("issue_number", type=int)
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
    issue_number: int,
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
    plan = issue_store.get_plan(repo_root, str(issue_number))
    if isinstance(plan, PlanNotFound):
        _output_error(
            output_format,
            f"Issue #{issue_number} not found",
            "issue_not_found",
        )
        raise SystemExit(1)

    # Validate it has the erk-plan label
    if "erk-plan" not in plan.labels:
        _output_error(
            output_format,
            f"Issue #{issue_number} does not have the 'erk-plan' label",
            "not_an_erk_plan",
        )
        raise SystemExit(1)

    # Generate draft-PR branch name from trunk
    trunk = git.branch.detect_trunk_branch(cwd)
    branch_name = generate_draft_pr_branch_name(
        plan.title,
        now,
        objective_id=plan.objective_id,
    )

    if dry_run:
        _output_dry_run(
            output_format,
            issue_number=issue_number,
            title=plan.title,
            branch_name=branch_name,
            trunk=trunk,
        )
        return

    # Save current branch so we can restore after checkout dance
    current_branch = git.branch.get_current_branch(cwd)
    restore_branch = current_branch or "HEAD"

    # Create branch from trunk, commit plan file, push
    git.branch.create_branch(cwd, branch_name, trunk, force=False)
    git.branch.checkout_branch(cwd, branch_name)
    try:
        branch_data_dir = repo_root / ".erk" / "branch-data"
        branch_data_dir.mkdir(parents=True, exist_ok=True)
        plan_file = branch_data_dir / "plan.md"
        plan_file.write_text(plan.body, encoding="utf-8")
        git.commit.stage_files(repo_root, [".erk/branch-data/plan.md"])
        git.commit.commit(repo_root, f"Add plan: {plan.title}")
        git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)
    finally:
        git.branch.checkout_branch(cwd, restore_branch)

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

    # Comment on original issue with migration notice, then close it
    migration_comment = (
        f"Migrated to draft PR #{pr_number}: {pr_url}\n\n"
        "This issue has been superseded by the draft PR above."
    )
    issues.add_comment(repo_root, issue_number, migration_comment)
    issues.close_issue(repo_root, issue_number)

    if output_format == "display":
        click.echo(f"Migrated plan #{issue_number} → draft PR #{pr_number}")
        click.echo(f"Title: {plan.title}")
        click.echo(f"PR URL: {pr_url}")
        click.echo(f"Branch: {branch_name}")
        click.echo(f"Original issue #{issue_number} closed.")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "original_issue_number": issue_number,
                    "pr_number": pr_number,
                    "pr_url": pr_url,
                    "branch_name": branch_name,
                }
            )
        )
