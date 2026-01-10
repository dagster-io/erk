"""Check capability installation status."""

from pathlib import Path

import click

from erk.core.capabilities.base import Capability, CapabilityArtifact
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

    Project-level capabilities require being in a git repository.
    User-level capabilities can be checked from anywhere.
    """
    # Lazy repo discovery - only done if needed
    erk_root = ctx.erk_installation.root()
    repo_or_sentinel = discover_repo_or_sentinel(ctx.cwd, erk_root, ctx.git)

    if isinstance(repo_or_sentinel, NoRepoSentinel):
        repo_root = None
    else:
        repo_root = repo_or_sentinel.root

    if name is not None:
        _check_capability(name, repo_root)
    else:
        _check_all(repo_root)


def _check_capability(name: str, repo_root: Path | None) -> None:
    """Check a specific capability."""
    cap = get_capability(name)
    if cap is None:
        user_output(click.style("Error: ", fg="red") + f"Unknown capability: {name}")
        user_output("\nAvailable capabilities:")
        for c in list_capabilities():
            user_output(f"  {c.name}")
        raise SystemExit(1)

    # For project-level capabilities, require repo_root
    if cap.scope == "project" and repo_root is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"'{cap.name}' is a project-level capability - run from a git repository"
        )
        raise SystemExit(1)

    check_repo_root = repo_root if cap.scope == "project" else None
    is_installed = cap.is_installed(check_repo_root)
    scope_label = f"[{cap.scope}]"

    if is_installed:
        user_output(click.style("✓ ", fg="green") + f"{cap.name} {scope_label}: installed")
    else:
        user_output(click.style("○ ", fg="white") + f"{cap.name} {scope_label}: not installed")
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
        _show_artifact_status(cap, artifact, repo_root)


def _show_artifact_status(
    cap: Capability,
    artifact: CapabilityArtifact,
    repo_root: Path | None,
) -> None:
    """Show status of a single artifact."""
    # For user-level capabilities, artifacts might use ~ paths
    if cap.scope == "user":
        # Expand ~ in paths
        artifact_path = Path(artifact.path).expanduser()
        exists = artifact_path.exists()
    else:
        # Project-level - relative to repo_root
        if repo_root is None:
            exists = False
        else:
            artifact_path = repo_root / artifact.path
            exists = artifact_path.exists()

    if exists:
        status = click.style("✓", fg="green")
    else:
        status = click.style("○", fg="white")
    user_output(f"    {status} {artifact.path:25} ({artifact.artifact_type})")


def _check_all(repo_root: Path | None) -> None:
    """Check all capabilities."""
    caps = list_capabilities()

    if not caps:
        user_output("No capabilities registered.")
        return

    user_output("Erk capabilities:")
    for cap in sorted(caps, key=lambda c: (c.scope, c.name)):
        scope_label = f"[{cap.scope}]"
        check_desc = f"({cap.installation_check_description})"
        cap_line = f"{cap.name:25} {scope_label:10} {cap.description}"

        # Determine if we can check this capability
        if cap.scope == "project" and repo_root is None:
            # Can't check project capability without repo
            user_output(click.style("  ? ", fg="yellow") + cap_line)
        else:
            check_repo_root = repo_root if cap.scope == "project" else None
            if cap.is_installed(check_repo_root):
                user_output(click.style("  ✓ ", fg="green") + cap_line + "  " + check_desc)
            else:
                user_output(click.style("  ○ ", fg="white") + cap_line + "  " + check_desc)
