"""Command to fetch and display a single plan."""

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.output.output import user_output


@click.command("get")
@click.argument("identifier", type=str)
@click.pass_obj
def get_plan(ctx: ErkContext, identifier: str) -> None:
    """Fetch and display a plan by identifier.

    Args:
        identifier: Plan identifier (e.g., "42" for GitHub)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    try:
        plan = ctx.plan_store.get_plan(repo_root, identifier)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Display plan details
    user_output("")
    user_output(click.style(plan.title, bold=True))
    user_output("")

    # Display metadata with clickable ID
    state_color = "green" if plan.state.value == "OPEN" else "red"

    # Make ID clickable using OSC 8 if URL is available
    id_text = f"#{identifier}"
    if plan.url:
        colored_id = click.style(id_text, fg="cyan")
        clickable_id = f"\033]8;;{plan.url}\033\\{colored_id}\033]8;;\033\\"
    else:
        clickable_id = click.style(id_text, fg="cyan")

    user_output(f"State: {click.style(plan.state.value, fg=state_color)} | ID: {clickable_id}")
    user_output(f"URL: {plan.url}")

    # Display labels
    if plan.labels:
        labels_str = ", ".join(
            click.style(f"[{label}]", fg="bright_magenta") for label in plan.labels
        )
        user_output(f"Labels: {labels_str}")

    # Display assignees
    if plan.assignees:
        assignees_str = ", ".join(plan.assignees)
        user_output(f"Assignees: {assignees_str}")

    # Display timestamps
    created = plan.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    updated = plan.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    user_output(f"Created: {created}")
    user_output(f"Updated: {updated}")

    # Display body if present
    if plan.body:
        user_output("")
        user_output(click.style("Description:", bold=True))
        user_output(plan.body)
