"""Command to fetch and display a single plan."""

from datetime import datetime

import click

from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.github.metadata.core import find_metadata_block
from erk_shared.github.metadata.schemas import (
    BRANCH_NAME,
    CREATED_BY,
    CREATED_FROM_SESSION,
    LAST_DISPATCHED_AT,
    LAST_DISPATCHED_RUN_ID,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_AT,
    LAST_LOCAL_IMPL_EVENT,
    LAST_LOCAL_IMPL_SESSION,
    LAST_LOCAL_IMPL_USER,
    LAST_REMOTE_IMPL_AT,
    LEARN_PLAN_ISSUE,
    LEARN_PLAN_PR,
    LEARN_STATUS,
    OBJECTIVE_ISSUE,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
)
from erk_shared.naming import extract_leading_issue_number
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


def _format_field(label: str, value: str) -> str:
    """Format a field with dimmed label and consistent width.

    Uses a fixed width of 12 characters for label alignment across all
    plan view output fields.

    Args:
        label: The field label (e.g., "State", "ID")
        value: The value to display

    Returns:
        Formatted string with styled label and value
    """
    label_width = 12
    styled_label = click.style(f"{label}:".ljust(label_width), dim=True)
    return f"{styled_label} {value}"


def _format_learn_state(
    learn_status: str | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
) -> str:
    """Format learn status for CLI display.

    Args:
        learn_status: Raw status value from plan header
        learn_plan_issue: Issue number of generated learn plan
        learn_plan_pr: PR number that implemented the learn plan

    Returns:
        Formatted display string based on status
    """
    if learn_status is None or learn_status == "not_started":
        return "- not started"
    if learn_status == "pending":
        return "in progress"
    if learn_status == "completed_no_plan":
        return "no insights"
    if learn_status == "completed_with_plan" and learn_plan_issue is not None:
        return f"#{learn_plan_issue}"
    if learn_status == "pending_review" and learn_plan_pr is not None:
        return f"draft PR #{learn_plan_pr}"
    if learn_status == "plan_completed" and learn_plan_pr is not None:
        return f"completed #{learn_plan_pr}"
    return "- not started"


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
    lines.append(click.style("─── Header ───", bold=True))

    # Basic metadata
    if CREATED_BY in header_info:
        lines.append(_format_field("Created by", str(header_info[CREATED_BY])))

    if SCHEMA_VERSION in header_info:
        lines.append(_format_field("Schema version", str(header_info[SCHEMA_VERSION])))

    if WORKTREE_NAME in header_info:
        lines.append(_format_field("Worktree", str(header_info[WORKTREE_NAME])))

    if OBJECTIVE_ISSUE in header_info:
        lines.append(_format_field("Objective", f"#{header_info[OBJECTIVE_ISSUE]}"))

    if SOURCE_REPO in header_info:
        lines.append(_format_field("Source repo", str(header_info[SOURCE_REPO])))

    # Local implementation info
    has_local_impl = any(
        k in header_info
        for k in [LAST_LOCAL_IMPL_AT, LAST_LOCAL_IMPL_EVENT, LAST_LOCAL_IMPL_SESSION]
    )
    if has_local_impl:
        lines.append("")
        lines.append(click.style("─── Local Implementation ───", bold=True))
        if LAST_LOCAL_IMPL_AT in header_info:
            event = header_info.get(LAST_LOCAL_IMPL_EVENT, "")
            event_str = f" ({event})" if event else ""
            timestamp = _format_value(header_info[LAST_LOCAL_IMPL_AT])
            lines.append(_format_field("Last impl", f"{timestamp}{event_str}"))
        if LAST_LOCAL_IMPL_SESSION in header_info:
            lines.append(_format_field("Session", str(header_info[LAST_LOCAL_IMPL_SESSION])))
        if LAST_LOCAL_IMPL_USER in header_info:
            lines.append(_format_field("User", str(header_info[LAST_LOCAL_IMPL_USER])))

    # Remote implementation info
    if LAST_REMOTE_IMPL_AT in header_info:
        lines.append("")
        lines.append(click.style("─── Remote Implementation ───", bold=True))
        lines.append(_format_field("Last impl", _format_value(header_info[LAST_REMOTE_IMPL_AT])))

    # Remote dispatch info (GitHub Actions workflow triggers)
    has_dispatch = LAST_DISPATCHED_AT in header_info or LAST_DISPATCHED_RUN_ID in header_info
    if has_dispatch:
        lines.append("")
        lines.append(click.style("─── Remote Dispatch ───", bold=True))
        if LAST_DISPATCHED_AT in header_info:
            lines.append(
                _format_field("Last dispatched", _format_value(header_info[LAST_DISPATCHED_AT]))
            )
        if LAST_DISPATCHED_RUN_ID in header_info:
            lines.append(_format_field("Run ID", str(header_info[LAST_DISPATCHED_RUN_ID])))

    # Learn info - always show this section
    lines.append("")
    lines.append(click.style("─── Learn ───", bold=True))

    # Display learn state (status, plan issue, PR)
    learn_status = header_info.get(LEARN_STATUS)
    learn_plan_issue = header_info.get(LEARN_PLAN_ISSUE)
    learn_plan_pr = header_info.get(LEARN_PLAN_PR)

    # Cast to correct types (LBYL)
    learn_status_str: str | None = None
    if isinstance(learn_status, str):
        learn_status_str = learn_status

    learn_plan_issue_int: int | None = None
    if isinstance(learn_plan_issue, int):
        learn_plan_issue_int = learn_plan_issue

    learn_plan_pr_int: int | None = None
    if isinstance(learn_plan_pr, int):
        learn_plan_pr_int = learn_plan_pr

    learn_display = _format_learn_state(learn_status_str, learn_plan_issue_int, learn_plan_pr_int)
    lines.append(_format_field("Status", learn_display))

    if CREATED_FROM_SESSION in header_info:
        lines.append(_format_field("Plan session", str(header_info[CREATED_FROM_SESSION])))
    if LAST_LEARN_SESSION in header_info:
        lines.append(_format_field("Learn session", str(header_info[LAST_LEARN_SESSION])))

    return lines


@click.command("view")
@click.argument("identifier", type=str, required=False, default=None)
@click.option("--full", "-f", is_flag=True, help="Show full plan body")
@click.pass_obj
def view_plan(ctx: ErkContext, identifier: str | None, *, full: bool) -> None:
    """Fetch and display a plan by identifier.

    IDENTIFIER can be a plain number (e.g., "42") or a GitHub issue URL
    (e.g., "https://github.com/owner/repo/issues/123").

    If not provided, infers the plan number from the current branch name
    (e.g., branch "P123-foo-bar" will view plan #123).

    By default, shows only header information. Use --full to display
    the complete plan body.
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Resolve issue number: explicit argument or infer from branch
    issue_number: int | None = None
    if identifier is not None:
        issue_number = parse_issue_identifier(identifier)
    else:
        # Try to infer from current branch
        branch = ctx.git.get_current_branch(ctx.cwd)
        if branch is not None:
            issue_number = extract_leading_issue_number(branch)

    if issue_number is None:
        user_output(
            click.style("Error: ", fg="red")
            + "No identifier specified and could not infer from branch name"
        )
        user_output("Usage: erk plan view <identifier>")
        user_output("Or run from a branch named P{issue}-...")
        raise SystemExit(1)

    try:
        plan = ctx.plan_store.get_plan(repo_root, str(issue_number))
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    # Extract header info from issue body for branch display and later header section
    issue_body = plan.metadata.get("issue_body")
    header_info: dict[str, object] = {}
    if isinstance(issue_body, str):
        header_info = _extract_plan_header_info(issue_body)

    # Display plan details with consistent formatting
    user_output("")
    user_output(_format_field("Title", click.style(plan.title, bold=True)))

    # Display metadata with clickable ID
    state_color = "green" if plan.state.value == "OPEN" else "red"
    user_output(_format_field("State", click.style(plan.state.value, fg=state_color)))

    # Make ID clickable using OSC 8 if URL is available
    id_text = f"#{issue_number}"
    if plan.url:
        colored_id = click.style(id_text, fg="cyan")
        clickable_id = f"\033]8;;{plan.url}\033\\{colored_id}\033]8;;\033\\"
    else:
        clickable_id = click.style(id_text, fg="cyan")
    user_output(_format_field("ID", clickable_id))
    user_output(_format_field("URL", plan.url or "-"))

    # Display branch if available from plan-header
    branch_name = header_info.get(BRANCH_NAME)
    if branch_name:
        user_output(_format_field("Branch", str(branch_name)))

    # Display labels
    if plan.labels:
        labels_str = ", ".join(
            click.style(f"[{label}]", fg="bright_magenta") for label in plan.labels
        )
        user_output(_format_field("Labels", labels_str))

    # Display assignees
    if plan.assignees:
        assignees_str = ", ".join(plan.assignees)
        user_output(_format_field("Assignees", assignees_str))

    # Display timestamps
    created = plan.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    updated = plan.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    user_output(_format_field("Created", created))
    user_output(_format_field("Updated", updated))

    # Display header info section
    header_lines = _format_header_section(header_info)
    for line in header_lines:
        user_output(line)

    # Display body only with --full flag
    if full and plan.body:
        user_output("")
        user_output(click.style("─── Plan ───", bold=True))
        user_output(plan.body)
