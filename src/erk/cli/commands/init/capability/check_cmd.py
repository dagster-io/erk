"""Check capability installation status."""

from pathlib import Path

import click

from erk.core.capabilities.registry import get_capability, list_capabilities
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.output.output import user_output


@click.command("check")
@click.argument("name", required=False)
@click.pass_obj
def check_cmd(ctx: ErkContext, name: str | None) -> None:
    """Check capability installation status.

    Without NAME: shows all capabilities with installed status.
    With NAME: shows detailed status for that specific capability.

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
        _check_capability(name, repo_root)
    else:
        _check_all(repo_root)


def _check_capability(name: str, repo_root: Path) -> None:
    """Check a specific capability."""
    cap = get_capability(name)
    if cap is None:
        user_output(click.style("Error: ", fg="red") + f"Unknown capability: {name}")
        user_output("\nAvailable capabilities:")
        for c in list_capabilities():
            user_output(f"  {c.name}")
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


def _check_all(repo_root: Path) -> None:
    """Check all capabilities."""
    caps = list_capabilities()

    if not caps:
        user_output("No capabilities registered.")
        return

    user_output("Erk project capabilities:")
    for cap in sorted(caps, key=lambda c: c.name):
        if cap.is_installed(repo_root):
            user_output(click.style("  ✓ ", fg="green") + f"{cap.name:25} {cap.description}")
        else:
            user_output(click.style("  ○ ", fg="white") + f"{cap.name:25} {cap.description}")
