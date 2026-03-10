"""Command to fetch and display a single plan."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import click

from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import get_remote_github, resolved_repo_option
from erk.core.context import ErkContext
from erk_shared.agentclick.json_command import json_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed
from erk_shared.context.types import NoRepoSentinel
from erk_shared.core.typing_utils import narrow_to_literal
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.schemas import (
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
from erk_shared.plan_store.conversion import github_issue_to_plan
from erk_shared.plan_store.types import Plan, PlanNotFound


@dataclass(frozen=True)
class PrViewResult:
    """JSON result for erk pr view."""

    plan_id: str
    title: str
    state: str
    url: str | None
    labels: list[str]
    assignees: list[str]
    created_at: str
    updated_at: str
    objective_id: int | None
    branch: str | None
    header_fields: dict[str, object]
    body: str | None

    def to_json_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "plan_id": self.plan_id,
            "title": self.title,
            "state": self.state,
            "url": self.url,
            "labels": self.labels,
            "assignees": self.assignees,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "objective_id": self.objective_id,
            "branch": self.branch,
            "header_fields": _serialize_header_fields(self.header_fields),
        }
        if self.body is not None:
            result["body"] = self.body
        return result


def _serialize_header_fields(fields: dict[str, object]) -> dict[str, object]:
    """Serialize header fields, converting datetime values to ISO 8601 strings."""
    result: dict[str, object] = {}
    for key, value in fields.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


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
    learn_status: LearnStatusValue | None,
    learn_plan_issue: int | None,
    learn_plan_pr: int | None,
) -> str:
    """Format learn status for CLI display.

    Args:
        learn_status: Learn status value (see LearnStatusValue for valid values)
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


def _format_header_section(header_info: dict[str, object], *, plan_url: str | None) -> list[str]:
    """Format the header info section for display.

    Args:
        header_info: Dictionary of header fields from plan-header block
        plan_url: GitHub issue URL for constructing workflow URLs

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
    learn_status_raw = header_info.get(LEARN_STATUS)
    learn_plan_issue_raw = header_info.get(LEARN_PLAN_ISSUE)
    learn_plan_pr_raw = header_info.get(LEARN_PLAN_PR)

    # Cast to correct types (LBYL)
    # Narrow learn_status to LearnStatusValue if valid
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

    # Show workflow URL when learn is in progress
    if learn_status_val == "pending":
        learn_run_id_raw = header_info.get(LEARN_RUN_ID)
        if learn_run_id_raw is not None and plan_url is not None:
            owner_repo = extract_owner_repo_from_github_url(plan_url)
            if owner_repo is not None:
                workflow_url = construct_workflow_run_url(
                    owner_repo[0], owner_repo[1], str(learn_run_id_raw)
                )
                lines.append(_format_field("Workflow", workflow_url))

    if CREATED_FROM_SESSION in header_info:
        lines.append(_format_field("Plan session", str(header_info[CREATED_FROM_SESSION])))
    if LAST_LEARN_SESSION in header_info:
        lines.append(_format_field("Learn session", str(header_info[LAST_LEARN_SESSION])))

    return lines


@mcp_exposed(
    name="pr_view",
    description=(
        "View a specific plan's metadata, header info, and body content."
        " Returns plan title, state, labels, timestamps, and header metadata."
    ),
)
@json_command(exclude_json_input=frozenset({"repo_id"}), output_types=(PrViewResult,))
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
    json_stdout: bool,
) -> PrViewResult | None:
    """Fetch and display a plan by identifier.

    IDENTIFIER can be a plain number (e.g., "42") or a GitHub issue URL
    (e.g., "https://github.com/owner/repo/issues/123").

    If not provided, infers the plan number from the current branch name
    (e.g., via plan-ref.json in the resolved implementation directory).

    By default, shows only header information. Use --full to display
    the complete plan body.

    Examples:
        erk pr view 42
        erk pr view 42 --full
        erk pr view 42 --repo owner/repo
    """
    repo_root = None if isinstance(ctx.repo, NoRepoSentinel) else ctx.repo.root
    plan_id: str | None = None

    # If no identifier, infer from branch (local only)
    if identifier is None:
        if isinstance(ctx.repo, NoRepoSentinel):
            user_output(
                click.style("Error: ", fg="red")
                + "A plan identifier is required in remote mode (cannot infer from branch).\n"
                "Usage: erk pr view <number> --repo owner/repo"
            )
            raise SystemExit(1)

        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            user_output(
                click.style("Error: ", fg="red")
                + "No identifier specified and could not infer from branch name"
            )
            user_output("Usage: erk pr view <identifier>")
            user_output("Or run from a plan branch with a plan reference file")
            raise SystemExit(1)

        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(ctx.repo.root, branch)
        if plan_id is None:
            user_output(
                click.style("Error: ", fg="red")
                + "No identifier specified and could not infer from branch name"
            )
            user_output("Usage: erk pr view <identifier>")
            user_output("Or run from a plan branch with a plan reference file")
            raise SystemExit(1)

        identifier = plan_id

    plan_number = parse_issue_identifier(identifier)
    if plan_id is None:
        plan_id = str(plan_number)

    remote = get_remote_github(ctx)

    issue = remote.get_issue(owner=repo_id.owner, repo=repo_id.repo, number=plan_number)
    if isinstance(issue, IssueNotFound):
        user_output(click.style("Error: ", fg="red") + f"Plan #{plan_id} not found")
        raise SystemExit(1)

    plan = github_issue_to_plan(issue)

    # Optional local enrichment for richer header metadata
    if repo_root is not None:
        all_meta = ctx.plan_backend.get_all_metadata_fields(repo_root, plan_id)
        if isinstance(all_meta, PlanNotFound):
            header_info: dict[str, object] = plan.header_fields
        else:
            header_info = all_meta
    else:
        header_info = plan.header_fields

    if json_stdout:
        return PrViewResult(
            plan_id=plan_id,
            title=plan.title,
            state=plan.state.value,
            url=plan.url,
            labels=plan.labels,
            assignees=plan.assignees,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
            objective_id=plan.objective_id,
            branch=str(header_info[BRANCH_NAME]) if BRANCH_NAME in header_info else None,
            header_fields=header_info,
            body=plan.body if full else None,
        )

    _display_plan(plan, plan_id=plan_id, header_info=header_info, full=full)
    return None


def _display_plan(
    plan: Plan,
    *,
    plan_id: str,
    header_info: dict[str, object],
    full: bool,
) -> None:
    """Display plan details with consistent formatting.

    Shared display logic used by both local and remote paths.
    """
    user_output("")
    user_output(_format_field("Title", click.style(plan.title, bold=True)))

    # Display metadata with clickable ID
    state_color = "green" if plan.state.value == "OPEN" else "red"
    user_output(_format_field("State", click.style(plan.state.value, fg=state_color)))

    # Make ID clickable using OSC 8 if URL is available
    id_text = f"#{plan_id}"
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
    header_lines = _format_header_section(header_info, plan_url=plan.url)
    for line in header_lines:
        user_output(line)

    # Display body only with --full flag
    if full and plan.body:
        user_output("")
        user_output(click.style("─── Plan ───", bold=True))
        user_output(plan.body)
