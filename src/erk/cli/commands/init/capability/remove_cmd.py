"""Remove capabilities from a repository."""

from pathlib import Path

import click

from erk.core.capabilities.registry import get_capability, list_capabilities
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.output.output import user_output


@click.command("remove")
@click.argument("names", nargs=-1, required=True)
@click.pass_obj
def remove_cmd(ctx: ErkContext, names: tuple[str, ...]) -> None:
    """Remove capabilities from the current repository or user settings.

    NAMES are the capability names to remove. Multiple can be
    specified at once.

    Required capabilities (like erk-hooks) cannot be removed.

    Examples:
        erk init capability remove dignified-python
        erk init capability remove learned-docs devrun-agent
        erk init capability remove statusline  # user-level
    """
    # Track success/failure for exit code
    any_failed = False

    # Lazy repo discovery - only done if needed
    repo_root: Path | None = None
    repo_checked = False

    for cap_name in names:
        cap = get_capability(cap_name)
        if cap is None:
            user_output(click.style("✗ ", fg="red") + f"Unknown capability: {cap_name}")
            user_output("  Available capabilities:")
            for c in list_capabilities():
                user_output(f"    {c.name}")
            any_failed = True
            continue

        # Check if capability is required
        if cap.required:
            user_output(
                click.style("✗ ", fg="red") + f"{cap_name}: Cannot remove required capability"
            )
            any_failed = True
            continue

        # Determine repo_root based on capability scope
        if cap.scope == "project":
            # Lazy repo discovery - only do it once
            if not repo_checked:
                erk_root = ctx.erk_installation.root()
                repo_or_sentinel = discover_repo_or_sentinel(ctx.cwd, erk_root, ctx.git)
                if isinstance(repo_or_sentinel, NoRepoSentinel):
                    repo_root = None
                else:
                    repo_root = repo_or_sentinel.root
                repo_checked = True

            if repo_root is None:
                user_output(
                    click.style("✗ ", fg="red")
                    + f"{cap_name}: Not in a git repository (required for project-level capability)"
                )
                any_failed = True
                continue

            uninstall_repo_root = repo_root
        else:
            # User-level capability - no repo needed
            uninstall_repo_root = None

        # Check if installed before trying to remove
        if not cap.is_installed(uninstall_repo_root):
            user_output(click.style("⚠ ", fg="yellow") + f"{cap_name}: Not installed, skipping")
            continue

        result = cap.uninstall(uninstall_repo_root)
        if result.success:
            user_output(click.style("✓ ", fg="green") + f"{cap_name}: {result.message}")
        else:
            user_output(click.style("✗ ", fg="red") + f"{cap_name}: {result.message}")
            any_failed = True

    if any_failed:
        raise SystemExit(1)
