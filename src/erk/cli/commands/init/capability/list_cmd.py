"""List capabilities and their installation status."""

import itertools
from pathlib import Path

import click

from erk.cli.commands.init.capability.backend_utils import resolve_backend
from erk.core.capabilities.base import Capability, CapabilityArtifact
from erk.core.capabilities.registry import get_capability, list_optional_capabilities
from erk.core.context import ErkContext
from erk.core.repo_discovery import NoRepoSentinel, discover_repo_or_sentinel
from erk_shared.context.types import AgentBackend
from erk_shared.output.output import user_output

TAG_DISPLAY_NAMES: dict[str, str] = {
    "code-reviews": "Code Reviews",
    "devrun": "Devrun",
    "dignified-python": "Dignified Python",
    "documentation": "Documentation",
    "external-tools": "External Tools",
}


@click.command("list")
@click.argument("name", required=False)
@click.pass_obj
def list_cmd(ctx: ErkContext, name: str | None) -> None:
    """List capabilities and their installation status.

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

    backend = resolve_backend(ctx)

    if name is not None:
        _check_capability(name, repo_root, backend=backend)
    else:
        _check_all(repo_root, backend=backend)


def _check_capability(name: str, repo_root: Path | None, *, backend: AgentBackend) -> None:
    """Check a specific capability."""
    cap = get_capability(name)
    if cap is None:
        user_output(click.style("Error: ", fg="red") + f"Unknown capability: {name}")
        user_output("\nAvailable capabilities:")
        for c in list_optional_capabilities():
            user_output(f"  {c.name}")
        raise SystemExit(1)

    # For project-level capabilities, require repo_root
    if cap.scope == "project" and repo_root is None:
        user_output(
            click.style("Error: ", fg="red")
            + f"'{cap.name}' is a project-level capability - run from a git repository"
        )
        raise SystemExit(1)

    is_installed = cap.is_installed(repo_root if cap.scope == "project" else None, backend=backend)
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


def _render_capability_line(
    cap: Capability, repo_root: Path | None, *, backend: AgentBackend
) -> None:
    """Render a single capability line with install status indicator."""
    cap_line = f"{cap.name:35} {f'[{cap.scope}]':10} {cap.description}"
    check_line = click.style(f"    Checked: {cap.installation_check_description}", dim=True)

    if cap.scope == "project" and repo_root is None:
        user_output(click.style("  ? ", fg="yellow") + cap_line)
        user_output(check_line)
    else:
        if cap.is_installed(repo_root if cap.scope == "project" else None, backend=backend):
            user_output(click.style("  ✓ ", fg="green") + cap_line)
            user_output(check_line)
        else:
            user_output(click.style("  ○ ", fg="white") + cap_line)
            user_output(check_line)


def _check_all(repo_root: Path | None, *, backend: AgentBackend) -> None:
    """Check all capabilities, grouped by tag."""
    caps = list_optional_capabilities()

    if not caps:
        user_output("No capabilities registered.")
        return

    user_output("Erk capabilities:")

    # Sort: tagged capabilities first (alphabetically by tag, then name), ungrouped last
    sorted_caps = sorted(
        caps,
        key=lambda c: (0 if c.tag is not None else 1, c.tag or "", c.name),
    )

    for tag, group in itertools.groupby(sorted_caps, key=lambda c: c.tag):
        group_caps = list(group)
        if tag is not None:
            display_name = TAG_DISPLAY_NAMES.get(tag, tag)
            user_output(f"\n  [{display_name}]")
        else:
            user_output("\n  [Other]")
        for cap in group_caps:
            _render_capability_line(cap, repo_root, backend=backend)
