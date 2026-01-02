"""Learn command hooks for capturing documentation gaps.

This module provides the CLI integration for the learn feature,
which hooks into `erk land` to capture documentation gaps from
implementation sessions.
"""

from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.learn.capture import capture_for_learn
from erk_shared.learn.types import LearnResult
from erk_shared.output.output import user_output


def _maybe_capture_learn(
    ctx: ErkContext,
    worktree_path: Path,
    branch_name: str,
    pr_number: int,
    learn_flag: bool | None,
) -> LearnResult | None:
    """Prompt and capture for learn if appropriate.

    This is the hook wrapper that handles the --learn/--no-learn flags
    and user prompting.

    Args:
        ctx: ErkContext with issues and prompt_executor
        worktree_path: Path to the worktree being landed
        branch_name: Git branch name
        pr_number: PR number that was merged
        learn_flag: --learn flag value:
            - True: Automatically capture
            - False: Skip capture
            - None: Prompt user

    Returns:
        LearnResult if capture was attempted, None if skipped
    """
    # Check if .impl/ folder exists (prerequisite for learn capture)
    impl_dir = worktree_path / ".impl"
    if not impl_dir.exists():
        return None

    # Handle explicit flags
    if learn_flag is False:
        return None

    # Prompt user if not explicitly set
    if learn_flag is None:
        if not click.confirm("Capture session for docs?", default=True, err=True):
            return None

    # Proceed with capture
    user_output("Capturing documentation gaps...")

    result = capture_for_learn(
        worktree_path=worktree_path,
        branch_name=branch_name,
        pr_number=pr_number,
        github_issues=ctx.issues,
        prompt_executor=ctx.prompt_executor,
    )

    # Report result
    if result is None:
        user_output(click.style("ℹ", fg="cyan") + " No session data found for learn capture")
        return None

    if result.success:
        user_output(click.style("✓", fg="green") + f" Created learn issue: {result.issue_url}")
    else:
        user_output(click.style("⚠", fg="yellow") + f" Learn capture failed: {result.error}")

    return result
