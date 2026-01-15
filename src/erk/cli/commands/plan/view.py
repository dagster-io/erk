"""Command to fetch and display a single plan."""

from datetime import datetime

import click

from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.metadata.core import find_metadata_block
from erk_shared.github.metadata.schemas import (
    CREATED_BY,
    CREATED_FROM_SESSION,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_AT,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_LOCAL_IMPL_SESSION,
    LAST_LOCAL_IMPL_USER,
    LAST_REMOTE_IMPL_AT,
    OBJECTIVE_ISSUE,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
)
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
    if CREATED_BY in header_info:
        lines.append(f"Created by: {header_info[CREATED_BY]}")

    if SCHEMA_VERSION in header_info:
        lines.append(f"Schema version: {header_info[SCHEMA_VERSION]}")

    if WORKTREE_NAME in header_info:
        lines.append(f"Worktree: {header_info[WORKTREE_NAME]}")

    if OBJECTIVE_ISSUE in header_info:
        lines.append(f"Objective: #{header_info[OBJECTIVE_ISSUE]}")

    if SOURCE_REPO in header_info:
        lines.append(f"Source repo: {header_info[SOURCE_REPO]}")

    # Local implementation info
    has_local_impl = any(
        k in header_info
        for k in [LAST_LOCAL_IMPL_AT, LAST_LOCAL_IMPL_EVENT, LAST_LOCAL_IMPL_SESSION]
    )
    if has_local_impl:
        lines.append("")
        lines.append(click.style("--- Local Implementation ---", bold=True))
        if LAST_LOCAL_IMPL_AT in header_info:
            event = header_info.get(LAST_LOCAL_IMPL_EVENT, "")
            event_str = f" ({event})" if event else ""
            timestamp = _format_value(header_info[LAST_LOCAL_IMPL_AT])
            lines.append(f"Last impl: {timestamp}{event_str}")
        if LAST_LOCAL_IMPL_SESSION in header_info:
            lines.append(f"Session: {header_info[LAST_LOCAL_IMPL_SESSION]}")
        if LAST_LOCAL_IMPL_USER in header_info:
            lines.append(f"User: {header_info[LAST_LOCAL_IMPL_USER]}")

    # Remote implementation info
    if LAST_REMOTE_IMPL_AT in header_info:
        lines.append("")
        lines.append(click.style("--- Remote Implementation ---", bold=True))
        lines.append(f"Last impl: {_format_value(header_info[LAST_REMOTE_IMPL_AT])}")

    # Remote dispatch info (GitHub Actions workflow triggers)
    has_dispatch = LAST_DISPATCHED_AT in header_info or LAST_DISPATCHED_RUN_ID in header_info
    if has_dispatch:
        lines.append("")
        lines.append(click.style("--- Remote Dispatch ---", bold=True))
        if LAST_DISPATCHED_AT in header_info:
            lines.append(f"Last dispatched: {_format_value(header_info[LAST_DISPATCHED_AT])}")
        if LAST_DISPATCHED_RUN_ID in header_info:
            lines.append(f"Run ID: {header_info[LAST_DISPATCHED_RUN_ID]}")

    # Learn info - always show this section
    lines.append("")
    lines.append(click.style("--- Learn ---", bold=True))
    if CREATED_FROM_SESSION in header_info:
        lines.append(f"Plan created from session: {header_info[CREATED_FROM_SESSION]}")
    has_learn_evaluation = LAST_LEARN_AT in header_info or LAST_LEARN_SESSION in header_info
    if has_learn_evaluation:
        if LAST_LEARN_AT in header_info:
            lines.append(f"Last learn: {_format_value(header_info[LAST_LEARN_AT])}")
        if LAST_LEARN_SESSION in header_info:
            lines.append(f"Learn session: {header_info[LAST_LEARN_SESSION]}")
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
