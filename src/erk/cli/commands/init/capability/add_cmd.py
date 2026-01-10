"""Add capabilities to a repository."""

from pathlib import Path

import click

from erk.core.capabilities.registry import get_capability, list_capabilities
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.output.output import user_output


@click.command("add")
@click.argument("names", nargs=-1, required=True)
@click.pass_obj
def add_cmd(ctx: ErkContext, names: tuple[str, ...]) -> None:
    """Install capabilities in the current repository or user settings.

    NAMES are the capability names to install. Multiple can be
    specified at once.

    Project-level capabilities require being in a git repository.
    User-level capabilities can be installed from anywhere.

    Examples:
        erk init capability add learned-docs
        erk init capability add learned-docs dignified-python
        erk init capability add statusline  # user-level, works outside repos
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

            install_repo_root = repo_root
        else:
            # User-level capability - no repo needed
            install_repo_root = None

        # Run preflight checks before installation
        preflight_result = cap.preflight(install_repo_root)
        if not preflight_result.success:
            user_output(click.style("✗ ", fg="red") + f"{cap_name}: {preflight_result.message}")
            any_failed = True
            continue

        result = cap.install(install_repo_root)
        if result.success:
            user_output(click.style("✓ ", fg="green") + f"{cap_name}: {result.message}")
            for created_file in result.created_files:
                user_output(f"    {created_file}")
        else:
            user_output(click.style("⚠ ", fg="yellow") + f"{cap_name}: {result.message}")
            any_failed = True

    if any_failed:
        raise SystemExit(1)
