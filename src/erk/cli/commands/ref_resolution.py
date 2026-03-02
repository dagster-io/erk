"""Shared helper for resolving dispatch ref across multiple commands.

This module provides a single point for handling --ref and --ref-current flag
resolution, ensuring consistent validation and error handling across all
dispatch commands (launch, one-shot, pr dispatch, workflow smoke-test, objective plan).
"""

import click

from erk.core.context import ErkContext


def resolve_dispatch_ref(
    ctx: ErkContext, *, dispatch_ref: str | None, ref_current: bool
) -> str | None:
    """Resolve dispatch ref from flags and config.

    Handles mutual exclusivity check and falls back to config default.

    Args:
        ctx: ErkContext with git and local_config
        dispatch_ref: Value from --ref flag (None if not provided)
        ref_current: Value from --ref-current flag

    Returns:
        The resolved ref (branch name) or None if using default

    Raises:
        click.UsageError: If both --ref and --ref-current are provided,
            or if --ref-current is used with detached HEAD
    """
    if ref_current and dispatch_ref is not None:
        raise click.UsageError("--ref and --ref-current are mutually exclusive")

    if ref_current:
        branch = ctx.git.branch.get_current_branch(ctx.cwd)
        if branch is None:
            raise click.UsageError("--ref-current requires being on a branch (not detached HEAD)")
        return branch

    return dispatch_ref if dispatch_ref is not None else ctx.local_config.dispatch_ref
