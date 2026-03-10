"""Command to fetch and display a single plan.

Human-facing command with Click options and rich terminal output.
Machine-readable JSON equivalent lives in pr/view/json_cli.py.
"""

from datetime import datetime

import click

from erk.cli.commands.pr.view.operation import PrViewRequest, PrViewResult, run_pr_view
from erk.cli.repo_resolution import resolved_repo_option
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError
from erk_shared.core.typing_utils import narrow_to_literal
from erk_shared.gateway.github.metadata.schemas import (
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
    LEARN_RUN_ID,
    LEARN_STATUS,
    OBJECTIVE_ISSUE,
    SCHEMA_VERSION,
    SOURCE_REPO,
    WORKTREE_NAME,
    LearnStatusValue,
)
from erk_shared.gateway.github.parsing import (
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.gateway.github.types import GitHubRepoId
from erk_shared.output.output import user_output


def _format_value(value: object) -> str:
    """Format a value for display, handling datetime conversion."""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _format_field(label: str, value: str) -> str:
    """Format a field with dimmed label and consistent width."""
    label_width = 12
    styled_label = click.style(f"{label}:".ljust(label_width), dim=True)
    return f"{styled_label} {value}"


def _format_learn_state(
    learn_status: LearnStatusValue | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
) -> str:
    """Format learn status for CLI display."""
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


def _format_header_section(header_info: dict[str, object], *, pr_url: str | None) -> list[str]:
    """Format the header info section for display."""
    lines: list[str] = []

    if not header_info:
        return lines

    lines.append("")
    lines.append(click.style("\u2500\u2500\u2500 Header \u2500\u2500\u2500", bold=True))

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

    has_local_impl = any(
        k in header_info
        for k in [LAST_LOCAL_IMPL_AT, LAST_LOCAL_IMPL_EVENT, LAST_LOCAL_IMPL_SESSION]
    )
    if has_local_impl:
        lines.append("")
        lines.append(
            click.style("\u2500\u2500\u2500 Local Implementation \u2500\u2500\u2500", bold=True)
        )
        if LAST_LOCAL_IMPL_AT in header_info:
            event = header_info.get(LAST_LOCAL_IMPL_EVENT, "")
            event_str = f" ({event})" if event else ""
            timestamp = _format_value(header_info[LAST_LOCAL_IMPL_AT])
            lines.append(_format_field("Last impl", f"{timestamp}{event_str}"))
        if LAST_LOCAL_IMPL_SESSION in header_info:
            lines.append(_format_field("Session", str(header_info[LAST_LOCAL_IMPL_SESSION])))
        if LAST_LOCAL_IMPL_USER in header_info:
            lines.append(_format_field("User", str(header_info[LAST_LOCAL_IMPL_USER])))

    if LAST_REMOTE_IMPL_AT in header_info:
        lines.append("")
        lines.append(
            click.style("\u2500\u2500\u2500 Remote Implementation \u2500\u2500\u2500", bold=True)
        )
        lines.append(_format_field("Last impl", _format_value(header_info[LAST_REMOTE_IMPL_AT])))

    has_dispatch = LAST_DISPATCHED_AT in header_info or LAST_DISPATCHED_RUN_ID in header_info
    if has_dispatch:
        lines.append("")
        lines.append(
            click.style("\u2500\u2500\u2500 Remote Dispatch \u2500\u2500\u2500", bold=True)
        )
        if LAST_DISPATCHED_AT in header_info:
            lines.append(
                _format_field("Last dispatched", _format_value(header_info[LAST_DISPATCHED_AT]))
            )
        if LAST_DISPATCHED_RUN_ID in header_info:
            lines.append(_format_field("Run ID", str(header_info[LAST_DISPATCHED_RUN_ID])))

    lines.append("")
    lines.append(click.style("\u2500\u2500\u2500 Learn \u2500\u2500\u2500", bold=True))

    learn_status_raw = header_info.get(LEARN_STATUS)
    learn_plan_issue_raw = header_info.get(LEARN_PLAN_ISSUE)
    learn_plan_pr_raw = header_info.get(LEARN_PLAN_PR)

    learn_status_str = learn_status_raw if isinstance(learn_status_raw, str) else None
    learn_status_val = narrow_to_literal(learn_status_str, LearnStatusValue)

    learn_plan_issue_int: int | None = None
    if isinstance(learn_plan_issue_raw, int):
        learn_plan_issue_int = learn_plan_issue_raw

    learn_plan_pr_int: int | None = None
    if isinstance(learn_plan_pr_raw, int):
        learn_plan_pr_int = learn_plan_pr_raw

    learn_display = _format_learn_state(learn_status_val, learn_plan_issue_int, learn_plan_pr_int)
    lines.append(_format_field("Status", learn_display))

    if learn_status_val == "pending":
        learn_run_id_raw = header_info.get(LEARN_RUN_ID)
        if learn_run_id_raw is not None and pr_url is not None:
            owner_repo = extract_owner_repo_from_github_url(pr_url)
            if owner_repo is not None:
                workflow_url = construct_workflow_run_url(
                    owner_repo[0], owner_repo[1], str(learn_run_id_raw)
                )
                lines.append(_format_field("Workflow", workflow_url))

    if CREATED_FROM_SESSION in header_info:
        lines.append(_format_field("PR session", str(header_info[CREATED_FROM_SESSION])))
    if LAST_LEARN_SESSION in header_info:
        lines.append(_format_field("Learn session", str(header_info[LAST_LEARN_SESSION])))

    return lines


def _display_plan(result: PrViewResult) -> None:
    """Display plan details with consistent formatting."""
    user_output("")
    user_output(_format_field("Title", click.style(result.title, bold=True)))

    state_color = "green" if result.state == "OPEN" else "red"
    user_output(_format_field("State", click.style(result.state, fg=state_color)))

    id_text = f"#{result.pr_id}"
    if result.url:
        colored_id = click.style(id_text, fg="cyan")
        clickable_id = f"\033]8;;{result.url}\033\\{colored_id}\033]8;;\033\\"
    else:
        clickable_id = click.style(id_text, fg="cyan")
    user_output(_format_field("ID", clickable_id))
    user_output(_format_field("URL", result.url or "-"))

    if result.branch:
        user_output(_format_field("Branch", result.branch))

    if result.labels:
        labels_str = ", ".join(
            click.style(f"[{label}]", fg="bright_magenta") for label in result.labels
        )
        user_output(_format_field("Labels", labels_str))

    if result.assignees:
        assignees_str = ", ".join(result.assignees)
        user_output(_format_field("Assignees", assignees_str))

    created = datetime.fromisoformat(result.created_at).strftime("%Y-%m-%d %H:%M:%S UTC")
    updated = datetime.fromisoformat(result.updated_at).strftime("%Y-%m-%d %H:%M:%S UTC")
    user_output(_format_field("Created", created))
    user_output(_format_field("Updated", updated))

    header_lines = _format_header_section(result.header_fields, pr_url=result.url)
    for line in header_lines:
        user_output(line)

    if result.body:
        user_output("")
        user_output(click.style("\u2500\u2500\u2500 Plan \u2500\u2500\u2500", bold=True))
        user_output(result.body)


@click.command("view")
@click.argument("identifier", type=str, required=False, default=None)
@click.option("--full", "-f", is_flag=True, help="Show full plan body")
@resolved_repo_option
@click.pass_obj
def pr_view(
    ctx: ErkContext,
    identifier: str | None,
    *,
    full: bool,
    repo_id: GitHubRepoId,
) -> None:
    """Fetch and display a plan by identifier.

    IDENTIFIER can be a plain number (e.g., "42") or a GitHub issue URL
    (e.g., "https://github.com/owner/repo/issues/123").

    If not provided, infers the plan number from the current branch name.

    By default, shows only header information. Use --full to display
    the complete plan body.

    Examples:
        erk pr view 42
        erk pr view 42 --full
        erk pr view 42 --repo owner/repo
    """
    request = PrViewRequest(identifier=identifier, full=full)
    result = run_pr_view(ctx, request, repo_id=repo_id)

    if isinstance(result, MachineCommandError):
        user_output(click.style("Error: ", fg="red") + result.message)
        if result.error_type == "missing_identifier":
            user_output("Usage: erk pr view <identifier>")
            user_output("Or run from a plan branch with a plan reference file")
        raise SystemExit(1)

    _display_plan(result)
