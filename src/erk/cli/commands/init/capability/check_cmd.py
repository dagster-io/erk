"""Check capability installation status."""

from pathlib import Path

import click

from erk.core.capabilities import (
    expand_capability_names,
    get_capability,
    get_group,
    is_group,
    list_capabilities,
    list_groups,
)
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.output.output import user_output


@click.command("check")
@click.argument("name", required=False)
@click.pass_obj
def check_cmd(ctx: ErkContext, name: str | None) -> None:
    """Check capability installation status.

    Without NAME: shows all capabilities with installed status.
    With NAME: shows detailed status for that specific capability or group.

    Requires being in a git repository.
    """
    # Discover repo using context's cwd and git
    erk_root = ctx.erk_installation.root()
    repo_or_sentinel = discover_repo_or_sentinel(ctx.cwd, erk_root, ctx.git)

    if isinstance(repo_or_sentinel, NoRepoSentinel):
        user_output(click.style("Error: ", fg="red") + "Not in a git repository.")
        user_output("Run this command from within a git repository.")
        raise SystemExit(1)

    repo_root = repo_or_sentinel.root

    if name is not None:
        # Check if name is a group
        if is_group(name):
            _check_group(name, repo_root)
        else:
            _check_capability(name, repo_root)
    else:
        # Check all capabilities
        _check_all(repo_root)


def _check_capability(name: str, repo_root: Path) -> None:
    """Check a specific capability."""
    cap = get_capability(name)
    if cap is None:
        user_output(click.style("Error: ", fg="red") + f"Unknown capability: {name}")
        user_output("\nAvailable capabilities:")
        for c in list_capabilities():
            user_output(f"  {c.name}")
        user_output("\nAvailable groups:")
        for g in list_groups():
            user_output(f"  {g.name}")
        raise SystemExit(1)

    is_installed = cap.is_installed(repo_root)
    if is_installed:
        user_output(click.style("✓ ", fg="green") + f"{cap.name}: installed")
    else:
        user_output(click.style("○ ", fg="white") + f"{cap.name}: not installed")
    user_output(f"  {cap.description}")

    # Show what the check looks for
    user_output(f"\n  Checks for: {cap.installation_check_description}")

    # Show artifacts
    if is_installed:
        user_output("\n  Artifacts:")
    else:
        add_cmd = f"erk init capability add {cap.name}"
        user_output(f"\n  Artifacts (would be created by '{add_cmd}'):")

    for artifact in cap.artifacts:
        artifact_path = repo_root / artifact.path
        exists = artifact_path.exists()
        if exists:
            status = click.style("✓", fg="green")
        else:
            status = click.style("○", fg="white")
        user_output(f"    {status} {artifact.path:25} ({artifact.artifact_type})")


def _check_group(name: str, repo_root: Path) -> None:
    """Check a capability group - shows status of all member capabilities."""
    group = get_group(name)
    if group is None:
        user_output(click.style("Error: ", fg="red") + f"Unknown group: {name}")
        raise SystemExit(1)

    # Expand group to get member names
    member_names = expand_capability_names([name])

    # Count installed members
    installed_count = 0
    for member_name in member_names:
        cap = get_capability(member_name)
        if cap is not None and cap.is_installed(repo_root):
            installed_count += 1

    total = len(member_names)
    if installed_count == total:
        user_output(
            click.style("✓ ", fg="green") + f"Group '{name}': all {total} members installed"
        )
    elif installed_count == 0:
        user_output(
            click.style("○ ", fg="white") + f"Group '{name}': none of {total} members installed"
        )
    else:
        user_output(
            click.style("◐ ", fg="yellow")
            + f"Group '{name}': {installed_count}/{total} members installed"
        )

    user_output(f"  {group.description}")
    user_output("\n  Members:")

    for member_name in member_names:
        cap = get_capability(member_name)
        if cap is None:
            user_output(click.style("    ? ", fg="red") + f"{member_name:20} (not registered)")
        elif cap.is_installed(repo_root):
            user_output(click.style("    ✓ ", fg="green") + f"{cap.name:20} {cap.description}")
        else:
            user_output(click.style("    ○ ", fg="white") + f"{cap.name:20} {cap.description}")


def _check_all(repo_root: Path) -> None:
    """Check all capabilities and groups."""
    caps = list_capabilities()
    groups = list_groups()

    if not caps and not groups:
        user_output("No capabilities registered.")
        return

    user_output(f"Capabilities in {repo_root.name}:")
    for cap in caps:
        if cap.is_installed(repo_root):
            user_output(click.style("  ✓ ", fg="green") + f"{cap.name:25} {cap.description}")
        else:
            user_output(click.style("  ○ ", fg="white") + f"{cap.name:25} {cap.description}")

    if groups:
        user_output("\nGroups:")
        for group in groups:
            member_names = expand_capability_names([group.name])
            installed = sum(
                1
                for n in member_names
                if (cap := get_capability(n)) is not None and cap.is_installed(repo_root)
            )
            total = len(member_names)
            if installed == total:
                status = click.style("  ✓ ", fg="green")
                suffix = "all installed"
            elif installed == 0:
                status = click.style("  ○ ", fg="white")
                suffix = "none installed"
            else:
                status = click.style("  ◐ ", fg="yellow")
                suffix = f"{installed}/{total} installed"
            user_output(status + f"{group.name:25} {group.description} ({suffix})")
