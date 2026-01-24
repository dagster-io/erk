"""Command registry for command palette.

This module defines all available commands and their availability predicates.
Commands are organized by category: Actions, Opens, Copies.
"""

from erk.tui.commands.types import CommandContext, CommandDefinition


def get_all_commands() -> list[CommandDefinition]:
    """Return all command definitions.

    Commands are ordered by category:
    1. Actions (mutative operations)
    2. Opens (browser navigation)
    3. Copies (clipboard operations)

    Returns:
        List of all available command definitions
    """
    return [
        # === ACTIONS ===
        CommandDefinition(
            id="close_plan",
            name="Action: Close Plan",
            description="Close issue and linked PRs",
            shortcut=None,
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="submit_to_queue",
            name="Action: Submit to Queue",
            description="Submit plan for remote AI implementation",
            shortcut="s",
            is_available=lambda ctx: ctx.row.issue_url is not None,
        ),
        CommandDefinition(
            id="land_pr",
            name="Action: Land PR",
            description="Merge PR and delete remote branch",
            shortcut=None,
            is_available=lambda ctx: (
                ctx.row.pr_number is not None
                and ctx.row.pr_state == "OPEN"
                and ctx.row.run_url is not None
            ),
        ),
        CommandDefinition(
            id="fix_conflicts_remote",
            name="Action: Fix Conflicts Remote",
            description="Launch remote conflict resolution workflow",
            shortcut="5",
            is_available=lambda ctx: ctx.row.pr_number is not None,
        ),
        # === OPENS ===
        CommandDefinition(
            id="open_browser",
            name="Open: In Browser",
            description="Open PR (or issue if no PR)",
            shortcut="o",
            is_available=lambda ctx: bool(ctx.row.pr_url or ctx.row.issue_url),
        ),
        CommandDefinition(
            id="open_issue",
            name="Open: Issue",
            description="Open issue in browser",
            shortcut="i",
            is_available=lambda ctx: ctx.row.issue_url is not None,
        ),
        CommandDefinition(
            id="open_pr",
            name="Open: PR",
            description="Open PR in browser",
            shortcut="p",
            is_available=lambda ctx: ctx.row.pr_url is not None,
        ),
        CommandDefinition(
            id="open_run",
            name="Open: Workflow Run",
            description="Open GitHub Actions run",
            shortcut="r",
            is_available=lambda ctx: ctx.row.run_url is not None,
        ),
        # === COPIES ===
        CommandDefinition(
            id="copy_checkout",
            name="Copy: erk br co <branch_name>",
            description="Copy checkout command",
            shortcut="c",
            is_available=lambda ctx: ctx.row.worktree_branch is not None,
        ),
        CommandDefinition(
            id="copy_pr_checkout",
            name="Copy: PR checkout && sync",
            description="Copy PR checkout command (activates worktree)",
            shortcut="e",
            is_available=lambda ctx: ctx.row.pr_number is not None,
        ),
        CommandDefinition(
            id="copy_prepare",
            name="Copy: erk prepare",
            description="Copy prepare command",
            shortcut="1",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_prepare_dangerous",
            name="Copy: erk prepare --dangerous",
            description="Copy dangerous prepare command",
            shortcut="2",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_prepare_activate",
            name="Copy: source prepare && implement",
            description="Copy one-liner to prepare worktree and start implementation",
            shortcut="4",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_submit",
            name="Copy: erk plan submit",
            description="Copy submit command",
            shortcut="3",
            is_available=lambda _: True,
        ),
        CommandDefinition(
            id="copy_replan",
            name="Copy: erk plan replan",
            description="Copy replan command to re-evaluate plan against current codebase",
            shortcut="6",
            is_available=lambda ctx: ctx.row.issue_url is not None,
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
