"""Autolearn helper for automatically running learn after landing PRs.

This module provides the logic to automatically run the learn workflow
when landing a PR from a plan branch, if autolearn is enabled in config.

Autolearn is essentially `erk learn -i` triggered automatically at land time.
"""

from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_output


def maybe_run_autolearn(
    ctx: ErkContext,
    *,
    repo_root: Path,
    branch: str,
) -> None:
    """Run learn workflow if autolearn is enabled and conditions are met.

    This is equivalent to running `erk learn -i` automatically.
    The learn workflow extracts insights from sessions and produces
    documentation in docs/learned/.

    Args:
        ctx: ErkContext with configuration and gateways
        repo_root: Repository root path
        branch: Branch name that was landed
    """
    # Check if autolearn is enabled
    if ctx.global_config is None or not ctx.global_config.autolearn:
        return

    # Extract plan issue number from branch name
    plan_issue_number = extract_leading_issue_number(branch)
    if plan_issue_number is None:
        # Branch doesn't have a plan prefix - nothing to do
        return

    user_output(
        click.style("📚 ", fg="cyan") + f"Running autolearn for plan #{plan_issue_number}..."
    )

    # Run the learn workflow (same as `erk learn -i`)
    ctx.claude_executor.execute_interactive(
        worktree_path=repo_root,
        dangerous=False,
        command=f"/erk:learn {plan_issue_number}",
        target_subpath=None,
    )
