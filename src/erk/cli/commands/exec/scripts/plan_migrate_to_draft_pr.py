"""Migrate an issue-based plan to a draft PR plan.

Usage:
    erk exec plan-migrate-to-draft-pr <issue_number> [--dry-run] [--format json|display]

Reads the plan from a GitHub issue (via GitHubPlanStore), creates a draft PR
(via DraftPRPlanBackend), comments on and closes the original issue.

Exit Codes:
    0: Success
    1: Error (issue not found, not an erk-plan, or migration failure)
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


def _output_error(output_format: str, message: str) -> None:
    """Output an error in the requested format.

    Args:
        output_format: "json" or "display"
        message: Error message to output
    """
    if output_format == "display":
        click.echo(f"Error: {message}", err=True)
    else:
        click.echo(json.dumps({"success": False, "error": message}))


def _migrate(
    ctx: click.Context,
    *,
    issue_number: int,
    dry_run: bool,
    output_format: str,
) -> None:
    """Execute the migration from issue to draft PR.

    Args:
        ctx: Click context
        issue_number: GitHub issue number to migrate
        dry_run: If True, output what would happen without mutations
        output_format: "json" or "display"
    """
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    github = require_github(ctx)
    issues = require_issues(ctx)
    now = require_time(ctx).now()

    # Fetch the plan from the issue
    plan_store = GitHubPlanStore(issues)
    plan_result = plan_store.get_plan(repo_root, str(issue_number))
    if isinstance(plan_result, PlanNotFound):
        _output_error(output_format, f"Issue #{issue_number} not found")
        raise SystemExit(1)

    # Verify it has the erk-plan label
    if "erk-plan" not in plan_result.labels:
        _output_error(
            output_format,
            f"Issue #{issue_number} is not an erk-plan issue (missing 'erk-plan' label)",
        )
        raise SystemExit(1)

    # Extract metadata from the plan
    objective_id = plan_result.objective_id
    created_from_session = plan_result.header_fields.get("created_from_session")
    has_learn_label = "erk-learn" in plan_result.labels

    # Generate branch name
    branch_name = generate_draft_pr_branch_name(
        plan_result.title,
        now,
        objective_id=objective_id,
    )

    # Detect trunk branch
    trunk = git.branch.detect_trunk_branch(cwd)

    if dry_run:
        dry_run_data: dict[str, object] = {
            "dry_run": True,
            "original_issue_number": issue_number,
            "title": plan_result.title,
            "branch_name": branch_name,
            "trunk_branch": trunk,
            "objective_id": objective_id,
            "has_learn_label": has_learn_label,
        }
        if output_format == "display":
            click.echo(f"Dry run: would migrate issue #{issue_number} to draft PR")
            click.echo(f"Title: {plan_result.title}")
            click.echo(f"Branch: {branch_name}")
            click.echo(f"Trunk: {trunk}")
            if objective_id is not None:
                click.echo(f"Objective: #{objective_id}")
            if has_learn_label:
                click.echo("Labels: erk-plan, erk-learn")
        else:
            click.echo(json.dumps(dry_run_data))
        return

    # Create branch from trunk and commit plan file
    current_branch = git.branch.get_current_branch(cwd)
    start_point = trunk if trunk is not None else "HEAD"
    git.branch.create_branch(cwd, branch_name, start_point, force=False)

    # Checkout dance: save current branch -> checkout plan branch -> commit -> push -> restore
    git.branch.checkout_branch(cwd, branch_name)
    try:
        plan_dir = repo_root / ".erk" / "plan"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_file_path = plan_dir / "PLAN.md"
        plan_file_path.write_text(plan_result.body, encoding="utf-8")
        git.commit.stage_files(repo_root, [".erk/plan/PLAN.md"])
        git.commit.commit(repo_root, f"Add plan: {plan_result.title}")
        git.remote.push_to_remote(cwd, "origin", branch_name, set_upstream=True, force=False)
    finally:
        restore_point = current_branch if current_branch is not None else start_point
        git.branch.checkout_branch(cwd, restore_point)

    # Build metadata for draft PR creation
    metadata: dict[str, object] = {
        "branch_name": branch_name,
        "trunk_branch": trunk,
    }
    if objective_id is not None:
        metadata["objective_issue"] = objective_id
    if created_from_session is not None:
        metadata["created_from_session"] = created_from_session

    # Build labels
    labels: list[str] = ["erk-plan"]
    if has_learn_label:
        labels.append("erk-learn")

    # Create draft PR via backend
    backend = DraftPRPlanBackend(github)
    result = backend.create_plan(
        repo_root=repo_root,
        title=plan_result.title,
        content=plan_result.body,
        labels=tuple(labels),
        metadata=metadata,
    )

    if not result.plan_id.isdigit():
        msg = f"Expected numeric plan_id from draft PR creation, got: {result.plan_id!r}"
        raise RuntimeError(msg)
    pr_number = int(result.plan_id)

    # Comment on and close original issue
    migration_comment = (
        f"Migrated to draft PR #{pr_number}: {result.url}\n\n"
        "This issue has been superseded by the draft PR above."
    )
    issues.add_comment(repo_root, issue_number, migration_comment)
    issues.close_issue(repo_root, issue_number)

    # Output result
    if output_format == "display":
        click.echo(f"Migrated issue #{issue_number} to draft PR #{pr_number}")
        click.echo(f"Title: {plan_result.title}")
        click.echo(f"PR URL: {result.url}")
        click.echo(f"Branch: {branch_name}")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "original_issue_number": issue_number,
                    "pr_number": pr_number,
                    "pr_url": result.url,
                    "branch_name": branch_name,
                }
            )
        )


@click.command(name="plan-migrate-to-draft-pr")
@click.argument("issue_number", type=int)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would happen without making changes",
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
    *,
    issue_number: int,
    dry_run: bool,
    output_format: str,
) -> None:
    """Migrate an issue-based plan to a draft PR plan."""
    _migrate(
        ctx,
        issue_number=issue_number,
        dry_run=dry_run,
        output_format=output_format,
    )
