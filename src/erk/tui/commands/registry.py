"""Command registry for command palette.

This module defines all available commands and their availability predicates.
Commands are organized by category: Actions, Opens, Copies.
Plan commands appear only in Plans/Learn views; objective commands appear only in Objectives view.
Run commands appear only in Runs view.
"""

from collections.abc import Callable
from dataclasses import dataclass

from erk.tui.commands.types import (
    CommandCategory,
    CommandContext,
    CommandDefinition,
    RunCommandContext,
)
from erk.tui.views.types import ViewMode

CATEGORY_EMOJI: dict[CommandCategory, str] = {
    CommandCategory.ACTION: "⚡",
    CommandCategory.OPEN: "🔗",
    CommandCategory.COPY: "📋",
}


# === View Mode Predicates ===


def _is_plan_view(ctx: CommandContext) -> bool:
    """True when not in Objectives view (i.e., Plans or Learn)."""
    return ctx.view_mode != ViewMode.OBJECTIVES


def _is_objectives_view(ctx: CommandContext) -> bool:
    """True when in Objectives view."""
    return ctx.view_mode == ViewMode.OBJECTIVES


# === Display Name Generators (Plan Commands) ===


def _display_close_pr(ctx: CommandContext) -> str:
    """Display name for close_pr command."""
    return f"erk pr close {ctx.row.pr_number}"


def _display_dispatch_to_queue(ctx: CommandContext) -> str:
    """Display name for dispatch_to_queue command."""
    return f"erk pr dispatch {ctx.row.pr_number}"


def _display_land_pr(ctx: CommandContext) -> str:
    """Display name for land_pr command."""
    return f"erk land {ctx.row.pr_number}"


def _display_rebase_remote(ctx: CommandContext) -> str:
    """Display name for rebase_remote command."""
    return f"erk launch pr-rebase --pr {ctx.row.pr_number}"


def _display_address_remote(ctx: CommandContext) -> str:
    """Display name for address_remote command."""
    return f"erk launch pr-address --pr {ctx.row.pr_number}"


def _display_open_issue(ctx: CommandContext) -> str:
    """Display name for open_issue command."""
    if ctx.row.pr_url:
        return ctx.row.pr_url
    return "Issue"


def _display_open_pr(ctx: CommandContext) -> str:
    """Display name for open_pr command."""
    if ctx.row.pr_url:
        return ctx.row.pr_url
    return "PR"


def _display_open_run(ctx: CommandContext) -> str:
    """Display name for open_run command."""
    if ctx.row.run_url:
        return ctx.row.run_url
    return "Workflow Run"


def _display_copy_checkout(ctx: CommandContext) -> str:
    """Display name for copy_checkout command."""
    if ctx.row.worktree_branch:
        return f"erk slot co {ctx.row.worktree_branch}"
    if ctx.row.pr_number:
        return f"erk pr co {ctx.row.pr_number}"
    return "erk slot co <branch>"


def _display_copy_pr_checkout_script(ctx: CommandContext) -> str:
    """Display name for copy_pr_checkout_script command."""
    if ctx.row.pr_number:
        return f'source "$(erk pr checkout {ctx.row.pr_number} --script)"'
    return "checkout"


def _display_copy_pr_checkout_plain(ctx: CommandContext) -> str:
    """Display name for copy_pr_checkout_plain command."""
    if ctx.row.pr_number:
        return f"erk pr checkout {ctx.row.pr_number}"
    return "checkout"


def _display_copy_teleport(ctx: CommandContext) -> str:
    """Display name for copy_teleport command."""
    return f"erk pr teleport {ctx.row.pr_number}"


def _display_copy_teleport_new_slot(ctx: CommandContext) -> str:
    """Display name for copy_teleport_new_slot command."""
    return f"erk pr teleport {ctx.row.pr_number} --new-slot"


def _display_cmux_checkout(ctx: CommandContext) -> str:
    """Display name for cmux_checkout command."""
    return f"erk pr checkout {ctx.row.pr_number} --script"


def _display_cmux_teleport(ctx: CommandContext) -> str:
    """Display name for cmux_teleport command."""
    return f"erk pr teleport {ctx.row.pr_number} --new-slot --script --sync"


def _display_copy_implement_local(ctx: CommandContext) -> str:
    """Display name for copy_implement_local command."""
    return f'source "$(erk pr checkout {ctx.row.pr_number} --script)" && erk implement --dangerous'


def _display_copy_dispatch(ctx: CommandContext) -> str:
    """Display name for copy_dispatch command."""
    return f"erk pr dispatch {ctx.row.pr_number}"


def _display_copy_replan(ctx: CommandContext) -> str:
    """Display name for copy_replan command."""
    return f"erk pr replan {ctx.row.pr_number}"


def _display_copy_land(ctx: CommandContext) -> str:
    """Display name for copy_land command."""
    return f"erk land {ctx.row.pr_number}"


def _display_copy_close_pr(ctx: CommandContext) -> str:
    """Display name for copy_close_pr command."""
    return f"erk pr close {ctx.row.pr_number}"


def _display_copy_rebase_remote(ctx: CommandContext) -> str:
    """Display name for copy_rebase_remote command."""
    return f"erk launch pr-rebase --pr {ctx.row.pr_number}"


def _display_copy_address_remote(ctx: CommandContext) -> str:
    """Display name for copy_address_remote command."""
    return f"erk launch pr-address --pr {ctx.row.pr_number}"


def _display_rewrite_remote(ctx: CommandContext) -> str:
    """Display name for rewrite_remote command."""
    return f"erk launch pr-rewrite --pr {ctx.row.pr_number}"


def _display_copy_rewrite_remote(ctx: CommandContext) -> str:
    """Display name for copy_rewrite_remote command."""
    return f"erk launch pr-rewrite --pr {ctx.row.pr_number}"


def _display_incremental_dispatch(ctx: CommandContext) -> str:
    """Display name for incremental_dispatch command."""
    return f"erk exec incremental-dispatch --pr {ctx.row.pr_number}"


# === Display Name Generators (Objective Commands) ===


def _display_one_shot_plan(ctx: CommandContext) -> str:
    """Display name for one_shot_plan command."""
    return f"erk objective plan {ctx.row.pr_number} --one-shot"


def _display_check_objective(ctx: CommandContext) -> str:
    """Display name for check_objective command."""
    return f"erk objective check {ctx.row.pr_number}"


def _display_close_objective(ctx: CommandContext) -> str:
    """Display name for close_objective command."""
    return f"erk objective close {ctx.row.pr_number} --force"


def _display_codespace_run_plan(ctx: CommandContext) -> str:
    """Display name for codespace_run_plan command."""
    return f"erk codespace run objective plan {ctx.row.pr_number}"


def _display_open_objective(ctx: CommandContext) -> str:
    """Display name for open_objective command."""
    if ctx.row.objective_url is not None:
        return ctx.row.objective_url
    return "Objective"


def _display_copy_plan(ctx: CommandContext) -> str:
    """Display name for copy_plan command."""
    return f"erk objective plan {ctx.row.pr_number}"


def _display_copy_view(ctx: CommandContext) -> str:
    """Display name for copy_view command."""
    return f"erk objective view {ctx.row.pr_number}"


def get_all_commands() -> list[CommandDefinition]:
    """Return all command definitions.

    Commands are ordered by category:
    1. Actions (mutative operations)
    2. Opens (browser navigation)
    3. Copies (clipboard operations)

    Plan commands are filtered out in Objectives view; objective commands
    are filtered out in Plans/Learn views.

    Returns:
        List of all available command definitions
    """
    return [
        # === PLAN ACTIONS ===
        CommandDefinition(
            id="close_pr",
            name="Close Plan",
            description="close",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="c",
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_close_pr,
        ),
        CommandDefinition(
            id="dispatch_to_queue",
            name="Dispatch to Queue",
            description="dispatch",
            category=CommandCategory.ACTION,
            shortcut="d",
            launch_key="d",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_url is not None,
            get_display_name=_display_dispatch_to_queue,
        ),
        CommandDefinition(
            id="land_pr",
            name="Land PR",
            description="land",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="l",
            is_available=lambda ctx: (
                _is_plan_view(ctx) and ctx.row.pr_number is not None and ctx.row.pr_state == "OPEN"
            ),
            get_display_name=_display_land_pr,
        ),
        CommandDefinition(
            id="address_remote",
            name="Address Remote",
            description="address",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="a",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_address_remote,
        ),
        CommandDefinition(
            id="rebase_remote",
            name="Rebase Remote",
            description="rebase",
            category=CommandCategory.ACTION,
            shortcut="5",
            launch_key="r",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_rebase_remote,
        ),
        CommandDefinition(
            id="rewrite_remote",
            name="Rewrite Remote",
            description="rewrite",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="w",
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_rewrite_remote,
        ),
        CommandDefinition(
            id="cmux_checkout",
            name="cmux checkout",
            description="cmux checkout",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="n",
            is_available=lambda ctx: (
                _is_plan_view(ctx)
                and ctx.row.pr_number is not None
                and ctx.row.pr_head_branch is not None
                and ctx.cmux_integration
            ),
            get_display_name=_display_cmux_checkout,
        ),
        CommandDefinition(
            id="cmux_teleport",
            name="cmux teleport",
            description="cmux teleport",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="m",
            is_available=lambda ctx: (
                _is_plan_view(ctx)
                and ctx.row.pr_number is not None
                and ctx.row.pr_head_branch is not None
                and ctx.cmux_integration
            ),
            get_display_name=_display_cmux_teleport,
        ),
        CommandDefinition(
            id="incremental_dispatch",
            name="Incremental Dispatch",
            description="incremental dispatch",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="i",
            is_available=lambda ctx: (
                _is_plan_view(ctx) and ctx.row.pr_number is not None and ctx.row.pr_state == "OPEN"
            ),
            get_display_name=_display_incremental_dispatch,
        ),
        # === OBJECTIVE ACTIONS ===
        CommandDefinition(
            id="check_objective",
            name="Check Objective",
            description="check",
            category=CommandCategory.ACTION,
            shortcut="5",
            launch_key="k",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_check_objective,
        ),
        CommandDefinition(
            id="close_objective",
            name="Close Objective",
            description="close",
            category=CommandCategory.ACTION,
            shortcut=None,
            launch_key="c",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_close_objective,
        ),
        CommandDefinition(
            id="one_shot_plan",
            name="Plan (One-Shot)",
            description="plan (one-shot)",
            category=CommandCategory.ACTION,
            shortcut="s",
            launch_key="s",
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_one_shot_plan,
        ),
        # === PLAN OPENS ===
        CommandDefinition(
            id="open_issue",
            name="Issue",
            description="plan",
            category=CommandCategory.OPEN,
            shortcut="i",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_url is not None,
            get_display_name=_display_open_issue,
        ),
        CommandDefinition(
            id="open_pr",
            name="PR",
            description="pr",
            category=CommandCategory.OPEN,
            shortcut="p",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_url is not None,
            get_display_name=_display_open_pr,
        ),
        CommandDefinition(
            id="open_run",
            name="Workflow Run",
            description="run",
            category=CommandCategory.OPEN,
            shortcut="r",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.run_url is not None,
            get_display_name=_display_open_run,
        ),
        # === OBJECTIVE OPENS ===
        CommandDefinition(
            id="open_objective",
            name="Objective",
            description="objective",
            category=CommandCategory.OPEN,
            shortcut="p",
            launch_key=None,
            is_available=lambda ctx: _is_objectives_view(ctx) and ctx.row.objective_url is not None,
            get_display_name=_display_open_objective,
        ),
        # === PLAN COPIES ===
        CommandDefinition(
            id="copy_checkout",
            name="erk slot co <branch>",
            description="checkout",
            category=CommandCategory.COPY,
            shortcut="c",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.worktree_branch is not None,
            get_display_name=_display_copy_checkout,
        ),
        CommandDefinition(
            id="copy_pr_checkout_plain",
            name="erk pr checkout",
            description="checkout",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_pr_checkout_plain,
        ),
        CommandDefinition(
            id="copy_pr_checkout_script",
            name="erk pr checkout --script",
            description="checkout (cd)",
            category=CommandCategory.COPY,
            shortcut="e",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_pr_checkout_script,
        ),
        CommandDefinition(
            id="copy_teleport",
            name="erk pr teleport",
            description="teleport",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_teleport,
        ),
        CommandDefinition(
            id="copy_teleport_new_slot",
            name="erk pr teleport --new-slot",
            description="teleport (new slot)",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_teleport_new_slot,
        ),
        CommandDefinition(
            id="copy_close_pr",
            name="erk pr close",
            description="close",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_copy_close_pr,
        ),
        CommandDefinition(
            id="copy_cmux_checkout",
            name="cmux checkout",
            description="cmux checkout",
            category=CommandCategory.COPY,
            shortcut="w",
            launch_key=None,
            is_available=lambda ctx: (
                _is_plan_view(ctx)
                and ctx.row.pr_number is not None
                and ctx.row.pr_head_branch is not None
                and ctx.cmux_integration
            ),
            get_display_name=_display_cmux_checkout,
        ),
        CommandDefinition(
            id="copy_cmux_teleport",
            name="cmux teleport",
            description="cmux teleport",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: (
                _is_plan_view(ctx)
                and ctx.row.pr_number is not None
                and ctx.row.pr_head_branch is not None
                and ctx.cmux_integration
            ),
            get_display_name=_display_cmux_teleport,
        ),
        CommandDefinition(
            id="copy_dispatch",
            name="erk pr dispatch",
            description="dispatch",
            category=CommandCategory.COPY,
            shortcut="3",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx),
            get_display_name=_display_copy_dispatch,
        ),
        CommandDefinition(
            id="copy_implement_local",
            name="checkout && implement",
            description="implement",
            category=CommandCategory.COPY,
            shortcut="2",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_implement_local,
        ),
        CommandDefinition(
            id="copy_land",
            name="erk land",
            description="land",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_land,
        ),
        CommandDefinition(
            id="copy_replan",
            name="erk pr replan",
            description="replan",
            category=CommandCategory.COPY,
            shortcut="6",
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_url is not None,
            get_display_name=_display_copy_replan,
        ),
        CommandDefinition(
            id="copy_address_remote",
            name="erk launch pr-address",
            description="address",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_address_remote,
        ),
        CommandDefinition(
            id="copy_rebase_remote",
            name="erk launch pr-rebase",
            description="rebase",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_rebase_remote,
        ),
        CommandDefinition(
            id="copy_rewrite_remote",
            name="erk launch pr-rewrite",
            description="rewrite",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_plan_view(ctx) and ctx.row.pr_number is not None,
            get_display_name=_display_copy_rewrite_remote,
        ),
        # === OBJECTIVE COPIES ===
        CommandDefinition(
            id="codespace_run_plan",
            name="Codespace Run Plan",
            description="codespace",
            category=CommandCategory.COPY,
            shortcut=None,
            launch_key=None,
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_codespace_run_plan,
        ),
        CommandDefinition(
            id="copy_plan",
            name="erk objective plan",
            description="plan",
            category=CommandCategory.COPY,
            shortcut="1",
            launch_key=None,
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_copy_plan,
        ),
        CommandDefinition(
            id="copy_view",
            name="erk objective view",
            description="view",
            category=CommandCategory.COPY,
            shortcut="3",
            launch_key=None,
            is_available=lambda ctx: _is_objectives_view(ctx),
            get_display_name=_display_copy_view,
        ),
    ]


def get_available_commands(ctx: CommandContext) -> list[CommandDefinition]:
    """Return commands available in current context.

    Args:
        ctx: Command context containing the plan row data

    Returns:
        List of commands that are available for the given context
    """
    return [cmd for cmd in get_all_commands() if cmd.is_available(ctx)]


def get_display_name(cmd: CommandDefinition, ctx: CommandContext) -> str:
    """Get the display name for a command in the given context.

    Args:
        cmd: The command definition
        ctx: The command context

    Returns:
        The dynamic display name if get_display_name is set, otherwise the static name
    """
    if cmd.get_display_name is not None:
        return cmd.get_display_name(ctx)
    return cmd.name


def get_copy_text(command_id: str, ctx: CommandContext) -> str | None:
    """Get the text to copy to clipboard for a command.

    This function maps (command_id, ctx) to the clipboard text by
    finding the command and using its display name generator. This eliminates
    duplication across app.py and plan_detail_screen.py.

    Args:
        command_id: The command ID (e.g., "copy_pr_checkout_script")
        ctx: The command context (row, view_mode, cmux_integration)

    Returns:
        The text to copy, or None if the command is not found, not available,
        or has no display name
    """
    for cmd in get_all_commands():
        if cmd.id == command_id:
            if cmd.is_available(ctx) and cmd.get_display_name is not None:
                return cmd.get_display_name(ctx)
            break
    return None


# === Run Command Definitions ===
# Run commands use RunCommandContext instead of CommandContext.
# They share CommandCategory and display formatting but have their own
# availability predicates operating on RunRowData.


@dataclass(frozen=True)
class RunCommandDefinition:
    """Definition of a command for the Runs tab.

    Attributes:
        id: Unique identifier for the command
        name: Display name
        description: Brief description for palette display
        category: Command category for emoji prefix
        is_available: Predicate function to check if command is available
        get_display_name: Optional function to generate context-aware display name
    """

    id: str
    name: str
    description: str
    category: CommandCategory
    is_available: Callable[[RunCommandContext], bool]
    get_display_name: Callable[[RunCommandContext], str] | None


def _run_is_cancellable(ctx: RunCommandContext) -> bool:
    """True when run is queued or in_progress."""
    return ctx.row.status in ("queued", "in_progress")


def _run_is_retryable(ctx: RunCommandContext) -> bool:
    """True when run is completed with failure or cancelled conclusion."""
    return ctx.row.status == "completed" and ctx.row.conclusion in ("failure", "cancelled")


def _display_cancel_run(ctx: RunCommandContext) -> str:
    return f"erk workflow run cancel {ctx.row.run_id}"


def _display_retry_run(ctx: RunCommandContext) -> str:
    return f"erk workflow run retry {ctx.row.run_id}"


def _display_retry_failed_run(ctx: RunCommandContext) -> str:
    return f"erk workflow run retry {ctx.row.run_id} --failed"


def _display_open_run_url(ctx: RunCommandContext) -> str:
    return ctx.row.run_url or "Run"


def _display_open_run_pr(ctx: RunCommandContext) -> str:
    return ctx.row.pr_url or "PR"


def _display_copy_cancel_cmd(ctx: RunCommandContext) -> str:
    return f"erk workflow run cancel {ctx.row.run_id}"


def _display_copy_retry_cmd(ctx: RunCommandContext) -> str:
    return f"erk workflow run retry {ctx.row.run_id}"


def get_all_run_commands() -> list[RunCommandDefinition]:
    """Return all run command definitions.

    Returns:
        List of all run-specific command definitions
    """
    return [
        # === RUN ACTIONS ===
        RunCommandDefinition(
            id="cancel_run",
            name="Cancel Run",
            description="cancel",
            category=CommandCategory.ACTION,
            is_available=_run_is_cancellable,
            get_display_name=_display_cancel_run,
        ),
        RunCommandDefinition(
            id="retry_run",
            name="Retry Run",
            description="retry",
            category=CommandCategory.ACTION,
            is_available=_run_is_retryable,
            get_display_name=_display_retry_run,
        ),
        RunCommandDefinition(
            id="retry_failed_run",
            name="Retry Failed Jobs",
            description="retry failed",
            category=CommandCategory.ACTION,
            is_available=_run_is_retryable,
            get_display_name=_display_retry_failed_run,
        ),
        # === RUN OPENS ===
        RunCommandDefinition(
            id="open_run_url",
            name="Run",
            description="run",
            category=CommandCategory.OPEN,
            is_available=lambda ctx: ctx.row.run_url is not None,
            get_display_name=_display_open_run_url,
        ),
        RunCommandDefinition(
            id="open_run_pr",
            name="PR",
            description="pr",
            category=CommandCategory.OPEN,
            is_available=lambda ctx: ctx.row.pr_url is not None,
            get_display_name=_display_open_run_pr,
        ),
        # === RUN COPIES ===
        RunCommandDefinition(
            id="copy_cancel_cmd",
            name="erk workflow run cancel",
            description="cancel",
            category=CommandCategory.COPY,
            is_available=_run_is_cancellable,
            get_display_name=_display_copy_cancel_cmd,
        ),
        RunCommandDefinition(
            id="copy_retry_cmd",
            name="erk workflow run retry",
            description="retry",
            category=CommandCategory.COPY,
            is_available=_run_is_retryable,
            get_display_name=_display_copy_retry_cmd,
        ),
    ]


def get_available_run_commands(ctx: RunCommandContext) -> list[RunCommandDefinition]:
    """Return run commands available in current context.

    Args:
        ctx: Run command context containing the run row data

    Returns:
        List of run commands that are available for the given context
    """
    return [cmd for cmd in get_all_run_commands() if cmd.is_available(ctx)]


def get_run_display_name(cmd: RunCommandDefinition, ctx: RunCommandContext) -> str:
    """Get the display name for a run command in the given context.

    Args:
        cmd: The run command definition
        ctx: The run command context

    Returns:
        The dynamic display name if get_display_name is set, otherwise the static name
    """
    if cmd.get_display_name is not None:
        return cmd.get_display_name(ctx)
    return cmd.name
