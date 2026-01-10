"""Add capabilities to a repository."""

import click

from erk.core.capabilities.registry import get_capability, list_capabilities
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.output.output import user_output


@click.command("add")
@click.argument("names", nargs=-1, required=True)
@click.pass_obj
def add_cmd(ctx: ErkContext, names: tuple[str, ...]) -> None:
    """Install capabilities in the current repository.

    NAMES are the capability names to install. Multiple can be
    specified at once.

    Requires being in a git repository.

    Examples:
        erk init capability add learned-docs
        erk init capability add learned-docs dignified-python
    """
    # Discover repo using context's cwd and git
    erk_root = ctx.erk_installation.root()
    repo_or_sentinel = discover_repo_or_sentinel(ctx.cwd, erk_root, ctx.git)

    if isinstance(repo_or_sentinel, NoRepoSentinel):
        user_output(click.style("Error: ", fg="red") + "Not in a git repository.")
        user_output("Run this command from within a git repository.")
        raise SystemExit(1)

    repo_root = repo_or_sentinel.root

    # Track success/failure for exit code
    any_failed = False

    for cap_name in names:
        cap = get_capability(cap_name)
        if cap is None:
            user_output(click.style("✗ ", fg="red") + f"Unknown capability: {cap_name}")
            user_output("  Available capabilities:")
            for c in list_capabilities():
                user_output(f"    {c.name}")
            any_failed = True
            continue

        result = cap.install(repo_root)
        if result.success:
            user_output(click.style("✓ ", fg="green") + f"{cap_name}: {result.message}")
            for created_file in result.created_files:
                user_output(f"    {created_file}")
        else:
            user_output(click.style("⚠ ", fg="yellow") + f"{cap_name}: {result.message}")
            any_failed = True

    if any_failed:
        raise SystemExit(1)
