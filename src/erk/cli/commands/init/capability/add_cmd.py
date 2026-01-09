"""Add capabilities to a repository."""

import click

from erk.core.capabilities import (
    expand_capability_names,
    get_capability,
    is_group,
    list_capabilities,
    list_groups,
)
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.output.output import user_output


@click.command("add")
@click.argument("names", nargs=-1, required=True)
@click.pass_obj
def add_cmd(ctx: ErkContext, names: tuple[str, ...]) -> None:
    """Install capabilities in the current repository.

    NAMES are the capability or group names to install. Multiple can be
    specified at once. Groups expand to their member capabilities.

    Requires being in a git repository.

    Examples:
        erk init capability add learned-docs
        erk init capability add python-dev  # Installs group members
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

    # Expand groups to individual capabilities
    expanded_names = expand_capability_names(list(names))

    # Track which names were groups for reporting
    group_expansions: dict[str, list[str]] = {}
    for name in names:
        if is_group(name):
            group_expansions[name] = [
                n for n in expanded_names if n in expand_capability_names([name])
            ]

    # Report group expansions
    for group_name, members in group_expansions.items():
        user_output(click.style("◆ ", fg="cyan") + f"Group '{group_name}' → {', '.join(members)}")

    # Track success/failure for exit code
    any_failed = False

    for cap_name in expanded_names:
        cap = get_capability(cap_name)
        if cap is None:
            user_output(click.style("✗ ", fg="red") + f"Unknown capability: {cap_name}")
            user_output("  Available capabilities:")
            for c in list_capabilities():
                user_output(f"    {c.name}")
            user_output("  Available groups:")
            for g in list_groups():
                user_output(f"    {g.name}")
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
