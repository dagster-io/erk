"""Command to fetch and display a single objective."""

from datetime import datetime

import click
from rich.cells import cell_len
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from erk.cli.alias import alias
from erk.cli.commands.exec.scripts.objective_roadmap_shared import (
    compute_summary,
    find_next_step,
    parse_roadmap,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import UserFacingCliError
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.display_utils import format_relative_time
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.output.output import user_output


def _format_field(label: str, value: str) -> str:
    """Format a field with dimmed label and consistent width.

    Uses a fixed width of 12 characters for label alignment across all
    objective view output fields.

    Args:
        label: The field label (e.g., "State", "ID")
        value: The value to display

    Returns:
        Formatted string with styled label and value
    """
    label_width = 12
    styled_label = click.style(f"{label}:".ljust(label_width), dim=True)
    return f"{styled_label} {value}"


def _format_step_status(status: str, *, plan: str | None) -> str:
    """Format step status indicator with emoji and Rich markup.

    Args:
        status: Step status ("done", "in_progress", "pending", "blocked", "skipped")
        plan: Plan reference (e.g., "#6464") or None

    Returns:
        Rich markup string with emoji and color
    """
    if status == "done":
        return "[green]✅ done[/green]"
    if status == "in_progress":
        ref_text = f" plan {escape(plan)}" if plan else ""
        return f"[yellow]🔄 in_progress{ref_text}[/yellow]"
    if status == "blocked":
        return "[red]🚫 blocked[/red]"
    if status == "skipped":
        return "[dim]⏭ skipped[/dim]"
    # Default: pending
    return "[dim]⏳ pending[/dim]"


def _format_timestamp(dt_value: datetime, *, label: str) -> str:
    """Format a timestamp with relative time.

    Args:
        dt_value: Datetime value to format
        label: Field label for display

    Returns:
        Formatted string with absolute date and relative time
    """
    absolute_str = dt_value.strftime("%Y-%m-%d")
    relative_str = format_relative_time(dt_value.isoformat())
    display = f"{absolute_str} ({relative_str})" if relative_str else absolute_str
    return _format_field(label, display)


@alias("v")
@click.command("view")
@click.argument("objective_ref", type=str)
@click.pass_obj
def view_objective(ctx: ErkContext, objective_ref: str) -> None:
    """Fetch and display an objective by identifier.

    OBJECTIVE_REF can be a plain number (e.g., "42"), P-prefixed ("P42"),
    or a GitHub issue URL (e.g., "https://github.com/owner/repo/issues/123").
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    repo_root = repo.root

    # Parse issue identifier
    issue_number = parse_issue_identifier(objective_ref)

    # Fetch issue from GitHub
    result = ctx.issues.get_issue(repo_root, issue_number)
    if isinstance(result, IssueNotFound):
        raise UserFacingCliError(f"Issue #{issue_number} not found")
    issue = result

    # Verify erk-objective label
    if "erk-objective" not in issue.labels:
        raise UserFacingCliError(
            f"Issue #{issue_number} is not an objective (missing erk-objective label)"
        )

    # Parse roadmap from issue body
    phases, _validation_errors = parse_roadmap(issue.body)

    # Compute summary statistics
    summary = compute_summary(phases)

    # Find next step
    next_step = find_next_step(phases)

    # Display objective details
    user_output("")
    user_output(_format_field("Title", click.style(issue.title, bold=True)))

    # Display metadata with clickable ID
    state_color = "green" if issue.state == "OPEN" else "red"
    user_output(_format_field("State", click.style(issue.state, fg=state_color)))

    # Make ID clickable using OSC 8
    id_text = f"#{issue_number}"
    colored_id = click.style(id_text, fg="cyan")
    clickable_id = f"\033]8;;{issue.url}\033\\{colored_id}\033]8;;\033\\"
    user_output(_format_field("ID", clickable_id))
    user_output(_format_field("URL", issue.url))

    # Display timestamps with relative time
    user_output(_format_timestamp(issue.created_at, label="Created"))
    user_output(_format_timestamp(issue.updated_at, label="Updated"))

    # Display roadmap if phases exist
    if phases:
        user_output("")
        user_output(click.style("─── Roadmap ───", bold=True))

        console = Console(stderr=True, force_terminal=True)

        # Pre-compute max column widths across all phases for global alignment
        max_id_width = 0
        max_status_width = 0
        max_desc_width = 0
        max_plan_width = 0
        max_pr_width = 0
        for phase in phases:
            for step in phase.steps:
                max_id_width = max(max_id_width, cell_len(step.id))
                status_markup = _format_step_status(step.status, plan=step.plan)
                max_status_width = max(
                    max_status_width,
                    cell_len(Text.from_markup(status_markup).plain),
                )
                max_desc_width = max(max_desc_width, cell_len(step.description))
                plan_text = "-" if step.plan is None else step.plan
                max_plan_width = max(max_plan_width, cell_len(plan_text))
                pr_text = "-" if step.pr is None else step.pr
                max_pr_width = max(max_pr_width, cell_len(pr_text))

        for phase in phases:
            # Count done steps in this phase
            done_count = sum(1 for step in phase.steps if step.status == "done")
            total_count = len(phase.steps)

            # Format phase identifier (e.g., "Phase 1A" or "Phase 1")
            phase_id = f"Phase {phase.number}{phase.suffix}"

            # Format phase header
            phase_header = f"{phase_id}: {phase.name} ({done_count}/{total_count} steps done)"
            user_output(click.style(phase_header, bold=True))

            # Display steps as a Rich table for proper alignment
            table = Table(
                show_header=False,
                box=None,
                pad_edge=False,
                padding=(0, 1),
            )
            table.add_column("step", style="cyan", no_wrap=True, min_width=max_id_width)
            table.add_column("status", no_wrap=True, min_width=max_status_width)
            table.add_column("description", min_width=max_desc_width)
            table.add_column("plan", no_wrap=True, min_width=max_plan_width)
            table.add_column("pr", no_wrap=True, min_width=max_pr_width)

            for step in phase.steps:
                table.add_row(
                    escape(step.id),
                    _format_step_status(step.status, plan=step.plan),
                    escape(step.description),
                    "-" if step.plan is None else escape(step.plan),
                    "-" if step.pr is None else escape(step.pr),
                )

            console.print(table)

            user_output("")

        # Display summary
        user_output(click.style("─── Summary ───", bold=True))

        # Format steps summary
        user_output(
            _format_field(
                "Steps",
                (
                    f"{summary['done']}/{summary['total_steps']} done,"
                    f" {summary['in_progress']} in progress,"
                    f" {summary['pending']} pending"
                ),
            )
        )

        # Display next step if available
        if next_step:
            user_output(
                _format_field(
                    "Next step",
                    f"{next_step['id']} - {next_step['description']} (Phase: {next_step['phase']})",
                )
            )
        else:
            user_output(_format_field("Next step", "None"))

    else:
        # No roadmap found
        user_output("")
        user_output(click.style("─── Roadmap ───", bold=True))
        user_output(click.style("No roadmap data found", dim=True))
