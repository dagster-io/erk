"""Upgrade command for erk tool installation.

Upgrades the user's local erk installation to match the repo's required version.
"""

import click
from packaging.version import Version

from erk.cli.core import discover_repo_context
from erk.cli.subprocess_utils import run_with_error_reporting
from erk.core.context import ErkContext
from erk.core.release_notes import get_current_version
from erk.core.version_check import get_required_version


@click.command("upgrade")
@click.pass_obj
def upgrade_cmd(ctx: ErkContext) -> None:
    """Upgrade local erk installation to match repo requirement.

    Reads the required version from .erk/required-erk-uv-tool-version
    and upgrades if the installed version is older.

    Examples:

    \b
      # Upgrade erk to match repo requirement
      erk upgrade
    """
    # Find repo context to get repo root
    repo = discover_repo_context(ctx, ctx.cwd)

    # Read required version from repo
    required = get_required_version(repo.root)
    if required is None:
        click.echo(
            click.style("Error: ", fg="red")
            + "No version requirement found in this repo (.erk/required-erk-uv-tool-version)"
        )
        raise SystemExit(1)

    # Get installed version
    installed = get_current_version()
    installed_ver = Version(installed)
    required_ver = Version(required)

    # Check if upgrade is needed
    if installed_ver == required_ver:
        click.echo(click.style(f"Already up to date ({installed})", fg="green"))
        return

    if installed_ver > required_ver:
        click.echo(
            click.style(f"Already at {installed}", fg="green") + f" (repo requires {required})"
        )
        return

    # Upgrade needed: installed < required
    click.echo(f"Upgrade available: {installed} → {required}")
    click.echo(click.style("Command: ", dim=True) + "uv tool upgrade erk")
    click.echo()

    if not click.confirm("Proceed with upgrade?"):
        click.echo()
        click.echo(click.style("Manual remediation required:", bold=True))
        click.echo("  Run: uv tool upgrade erk")
        click.echo(f"  Or:  uv tool install erk=={required}")
        raise SystemExit(1)

    click.echo()
    click.echo("Running uv tool upgrade erk...")
    run_with_error_reporting(
        ["uv", "tool", "upgrade", "erk"],
        error_prefix="Upgrade failed",
        troubleshooting=[
            "Ensure uv is installed: curl -LsSf https://astral.sh/uv/install.sh | sh",
            "Try manual upgrade: uv tool upgrade erk",
            f"Or install specific version: uv tool install erk=={required}",
        ],
    )

    click.echo(click.style(f"Successfully upgraded erk to {required}", fg="green"))
