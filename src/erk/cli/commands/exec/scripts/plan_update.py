"""Update an existing plan's content.

Usage:
    erk exec plan-update --plan-number N [OPTIONS]

This command updates the plan content comment on an existing GitHub issue:
1. Find plan file (from session scratch, --plan-path, or ~/.claude/plans/)
2. Update plan content via PlanBackend
3. Update issue title from plan H1 heading

Options:
    --plan-number N: Plan number to update (required)
    --session-id ID: Session ID to find plan file in scratch storage
    --plan-path PATH: Direct path to plan file (overrides session lookup)

Output:
    --format json (default): {"success": true, ...}
    --format display: Formatted text

Exit Codes:
    0: Success - plan comment updated
    1: Error - plan not found, no plan found, etc.
"""

import json
from pathlib import Path

import click

from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_git,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.plan_utils import extract_title_from_plan, get_title_tag_from_labels


@click.command(name="plan-update")
@click.option(
    "--plan-number",
    type=int,
    required=True,
    help="Plan number to update",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.option(
    "--plan-path",
    type=click.Path(exists=True, path_type=Path),
    help="Direct path to plan file (overrides session lookup)",
)
@click.option(
    "--session-id",
    help="Session ID to find plan file in scratch storage",
)
@click.option(
    "--summary",
    help="AI-generated summary to display above the collapsed plan in the PR body",
)
@click.pass_context
def plan_update(
    ctx: click.Context,
    *,
    plan_number: int,
    output_format: str,
    plan_path: Path | None,
    session_id: str | None,
    summary: str | None,
) -> None:
    """Update an existing plan's content."""

    def _handle_update_error(error_msg: str, cause: Exception | None = None) -> None:
        """Output error message and exit with code 1."""
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        if cause is not None:
            raise SystemExit(1) from cause
        raise SystemExit(1)

    # Get dependencies from context
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    claude_installation = require_claude_installation(ctx)

    # Step 1: Find plan content (priority: plan_path > session > latest)
    if plan_path is not None:
        plan_content = plan_path.read_text(encoding="utf-8")
    else:
        plan_content = claude_installation.get_latest_plan(cwd, session_id=session_id)

    if not plan_content:
        _handle_update_error("No plan found in ~/.claude/plans/")

    # Narrow type for type checker (None case handled above)
    assert plan_content is not None

    # Step 2: Check plan exists via PlanBackend
    plan_id = str(plan_number)
    plan_result = backend.get_plan(repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        _handle_update_error(f"Plan #{plan_number} not found")

    # Narrow type for type checker (PlanNotFound case exits above)
    assert not isinstance(plan_result, PlanNotFound)

    # Step 3: Update plan content via PlanBackend
    try:
        backend.update_plan_content(repo_root, plan_id, plan_content.strip(), summary=summary or "")
    except RuntimeError as e:
        _handle_update_error(f"Failed to update comment: {e}", cause=e)

    # Step 4: Update issue title from plan content
    new_title = extract_title_from_plan(plan_content)
    title_tag = get_title_tag_from_labels(plan_result.labels)
    full_title = f"{title_tag} {new_title}"

    try:
        backend.update_plan_title(repo_root, plan_id, full_title)
    except RuntimeError as e:
        _handle_update_error(f"Failed to update title: {e}", cause=e)

    # Step 5: Push updated plan to branch (best-effort)
    branch_name: str | None = None
    branch_updated = False
    raw_branch = plan_result.header_fields.get(BRANCH_NAME)
    if isinstance(raw_branch, str):
        branch_name = raw_branch
        git = require_git(ctx)
        git.commit.commit_files_to_branch(
            repo_root,
            branch=branch_name,
            files={f"{IMPL_CONTEXT_DIR}/plan.md": plan_content.strip()},
            message=f"Update plan: {new_title}",
        )
        push_result = git.remote.push_to_remote(
            cwd, "origin", branch_name, set_upstream=False, force=False
        )
        branch_updated = not isinstance(push_result, PushError)

    # Step 6: Output success
    if output_format == "display":
        click.echo(f"Plan #{plan_number} updated")
        click.echo(f"Title: {full_title}")
        click.echo(f"URL: {plan_result.url}")
        if branch_updated:
            click.echo(f"Branch {branch_name} synced")
        elif branch_name is not None:
            click.echo(f"Warning: branch push to {branch_name} failed")
    else:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "plan_number": plan_number,
                    "plan_url": plan_result.url,
                    "title": full_title,
                    "branch_name": branch_name,
                    "branch_updated": branch_updated,
                }
            )
        )
