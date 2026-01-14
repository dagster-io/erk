"""Command to fetch and display a single plan."""

from datetime import datetime

import click

from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.metadata.core import find_metadata_block
from erk_shared.output.output import user_output


def _format_value(value: object) -> str:
    """Format a value for display, handling datetime conversion.

    YAML parsing converts ISO 8601 timestamps to datetime objects.
    This function converts them back to ISO format strings for display.

    Args:
        value: Any value from metadata

    Returns:
        String representation suitable for display
    """
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _extract_plan_header_info(issue_body: str) -> dict[str, object]:
    """Extract all fields from plan-header metadata block.

    Args:
        issue_body: Raw issue body containing metadata blocks

    Returns:
        Dictionary of header fields, empty if no plan-header found
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return {}
    return dict(block.data)


def _format_header_section(header_info: dict[str, object]) -> list[str]:
    """Format the header info section for display.

    Args:
        header_info: Dictionary of header fields from plan-header block

    Returns:
        List of formatted lines for display
    """
    lines: list[str] = []

    # Skip if no header info
    if not header_info:
        return lines

    lines.append("")
    lines.append(click.style("--- Header Info ---", bold=True))

    # Basic metadata
    if "created_by" in header_info:
        lines.append(f"Created by: {header_info['created_by']}")

    if "schema_version" in header_info:
        lines.append(f"Schema version: {header_info['schema_version']}")

    if "worktree_name" in header_info:
        lines.append(f"Worktree: {header_info['worktree_name']}")

    if "objective_issue" in header_info:
        lines.append(f"Objective: #{header_info['objective_issue']}")

    if "source_repo" in header_info:
        lines.append(f"Source repo: {header_info['source_repo']}")

    # Local implementation info
    has_local_impl = any(
        k in header_info
        for k in ["last_local_impl_at", "last_local_impl_event", "last_local_impl_session"]
    )
    if has_local_impl:
        lines.append("")
        lines.append(click.style("--- Local Implementation ---", bold=True))
        if "last_local_impl_at" in header_info:
            event = header_info.get("last_local_impl_event", "")
            event_str = f" ({event})" if event else ""
            timestamp = _format_value(header_info["last_local_impl_at"])
            lines.append(f"Last impl: {timestamp}{event_str}")
        if "last_local_impl_session" in header_info:
            lines.append(f"Session: {header_info['last_local_impl_session']}")
        if "last_local_impl_user" in header_info:
            lines.append(f"User: {header_info['last_local_impl_user']}")

    # Remote implementation info
    if "last_remote_impl_at" in header_info:
        lines.append("")
        lines.append(click.style("--- Remote Implementation ---", bold=True))
        lines.append(f"Last impl: {_format_value(header_info['last_remote_impl_at'])}")

    # Remote dispatch info (GitHub Actions workflow triggers)
    has_dispatch = "last_dispatched_at" in header_info or "last_dispatched_run_id" in header_info
    if has_dispatch:
        lines.append("")
        lines.append(click.style("--- Remote Dispatch ---", bold=True))
        if "last_dispatched_at" in header_info:
            lines.append(f"Last dispatched: {_format_value(header_info['last_dispatched_at'])}")
        if "last_dispatched_run_id" in header_info:
            lines.append(f"Run ID: {header_info['last_dispatched_run_id']}")

    # Learn info - always show this section
    lines.append("")
    lines.append(click.style("--- Learn ---", bold=True))
    if "created_from_session" in header_info:
        lines.append(f"Plan created from session: {header_info['created_from_session']}")
    has_learn_evaluation = "last_learn_at" in header_info or "last_learn_session" in header_info
    if has_learn_evaluation:
        if "last_learn_at" in header_info:
            lines.append(f"Last learn: {_format_value(header_info['last_learn_at'])}")
        if "last_learn_session" in header_info:
            lines.append(f"Learn session: {header_info['last_learn_session']}")
    else:
        lines.append("No learn evaluation")

    return lines


@click.command("view")
@click.argument("identifier", type=str)
@click.option("--full", "-f", is_flag=True, help="Show full plan body")
@click.pass_obj
def view_plan(ctx: ErkContext, identifier: str, *, full: bool) -> None:
    """Fetch and display a plan by identifier.

    IDENTIFIER can be a plain number (e.g., "42") or a GitHub issue URL
    (e.g., "https://github.com/owner/repo/issues/123").

    By default, shows only header information. Use --full to display
    the complete plan body.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Parse identifier (handles both numbers and URLs)
    issue_number = parse_issue_identifier(identifier)

    try:
        plan = ctx.plan_store.get_plan(repo_root, str(issue_number))
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
    id_text = f"#{issue_number}"
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

    # Extract and display header info from metadata
    issue_body = plan.metadata.get("issue_body")
    if isinstance(issue_body, str):
        header_info = _extract_plan_header_info(issue_body)
        header_lines = _format_header_section(header_info)
        for line in header_lines:
            user_output(line)

    # Display body only with --full flag
    if full and plan.body:
        user_output("")
        user_output(click.style("--- Plan ---", bold=True))
        user_output(plan.body)
