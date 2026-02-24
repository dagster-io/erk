"""Command to list workflow runs associated with a plan."""

import json
from dataclasses import dataclass

import click
from rich.console import Console
from rich.table import Table

from erk.cli.constants import PLAN_ASSOCIATED_WORKFLOWS
from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.display_utils import (
    format_submission_time,
    format_workflow_outcome,
    format_workflow_run_id,
)
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.gateway.github.parsing import (
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.gateway.github.types import WorkflowRun
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class _RunEntry:
    workflow: str
    run: WorkflowRun


@click.command("runs")
@click.argument("identifier", required=False, default=None)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def plan_runs(ctx: ErkContext, identifier: str | None, *, output_json: bool) -> None:
    """List workflow runs associated with a plan.

    IDENTIFIER can be a plain number (e.g., "42"), P-prefixed ("P42"),
    or a GitHub issue URL. If not provided, infers from the current branch.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Resolve plan: explicit argument or infer from branch
    if identifier is not None:
        issue_number = parse_issue_identifier(identifier)
        plan_id = str(issue_number)
    else:
        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            user_output(
                click.style("Error: ", fg="red")
                + "No identifier specified and could not infer from branch name"
            )
            raise SystemExit(1)
        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo_root, branch)
        if plan_id is None:
            user_output(
                click.style("Error: ", fg="red")
                + "No identifier specified and could not infer from branch name"
            )
            raise SystemExit(1)

    # Fetch plan to verify it exists
    result = ctx.plan_store.get_plan(repo_root, plan_id)
    if isinstance(result, PlanNotFound):
        user_output(click.style("Error: ", fg="red") + f"Plan #{plan_id} not found")
        raise SystemExit(1)
    plan = result

    # Get branch name from plan-header metadata
    all_meta = ctx.plan_backend.get_all_metadata_fields(repo_root, plan_id)
    if isinstance(all_meta, PlanNotFound):
        user_output(
            click.style("Error: ", fg="red") + f"Could not read metadata for plan #{plan_id}"
        )
        raise SystemExit(1)

    branch_name = all_meta.get(BRANCH_NAME)
    if not isinstance(branch_name, str) or not branch_name:
        user_output(
            click.style("Error: ", fg="red") + f"Plan #{plan_id} has no branch_name in metadata"
        )
        raise SystemExit(1)

    # Extract owner/repo for constructing workflow URLs
    owner_repo = extract_owner_repo_from_github_url(plan.url) if plan.url else None

    # Collect runs across all plan-associated workflows
    entries: list[_RunEntry] = []
    for display_name, workflow_file in PLAN_ASSOCIATED_WORKFLOWS.items():
        runs = ctx.github.list_workflow_runs(repo_root, workflow_file, branch=branch_name)
        for run in runs:
            entries.append(_RunEntry(workflow=display_name, run=run))

    if not entries:
        user_output(f"No workflow runs found for plan #{plan_id} (branch: {branch_name})")
        return

    if output_json:
        _output_json(entries)
    else:
        _output_table(entries, owner_repo)


def _output_json(entries: list[_RunEntry]) -> None:
    """Render entries as JSON to stdout."""
    json_rows = []
    for entry in entries:
        run = entry.run
        json_rows.append(
            {
                "workflow": entry.workflow,
                "run_id": run.run_id,
                "status": run.status,
                "conclusion": run.conclusion,
                "created_at": (run.created_at.isoformat() if run.created_at else None),
            }
        )
    click.echo(json.dumps(json_rows, indent=2))


def _output_table(
    entries: list[_RunEntry],
    owner_repo: tuple[str, str] | None,
) -> None:
    """Render entries as a Rich table to stderr."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("workflow", no_wrap=True)
    table.add_column("run-id", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True, width=14)
    table.add_column("submitted", no_wrap=True, width=11)

    for entry in entries:
        run = entry.run

        workflow_url = None
        if owner_repo is not None:
            workflow_url = construct_workflow_run_url(owner_repo[0], owner_repo[1], run.run_id)

        table.add_row(
            entry.workflow,
            format_workflow_run_id(run, workflow_url),
            format_workflow_outcome(run),
            format_submission_time(run.created_at),
        )

    console = Console(stderr=True, width=200, force_terminal=True)
    console.print(table)
    console.print()
