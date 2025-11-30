"""List registered codespaces with live GitHub status."""

import datetime

import click
from erk_shared.output.output import user_output
from rich.console import Console
from rich.table import Table

from erk.core.codespace.types import GitHubCodespaceInfo, RegisteredCodespace
from erk.core.context import ErkContext


def _format_gh_status(gh_info: GitHubCodespaceInfo | None) -> str:
    """Format GitHub status with color coding.

    Args:
        gh_info: GitHub codespace info, or None if not found

    Returns:
        Colored status string
    """
    if gh_info is None:
        return "[red]deleted[/red]"

    status_styles = {
        "Available": "[green]available[/green]",
        "Shutdown": "[yellow]shutdown[/yellow]",
        "Starting": "[yellow]starting[/yellow]",
        "Pending": "[yellow]pending[/yellow]",
        "Failed": "[red]failed[/red]",
    }
    return status_styles.get(gh_info.state, f"[dim]{gh_info.state.lower()}[/dim]")


def _format_config_status(configured: bool) -> str:
    """Format configuration status.

    Args:
        configured: Whether the codespace has been configured

    Returns:
        Status string with color
    """
    if configured:
        return "[green]ready[/green]"
    return "[dim]pending[/dim]"


def _format_relative_time(last_connected: datetime.datetime | None) -> str:
    """Format last connected time as relative time.

    Args:
        last_connected: Last connected datetime, or None

    Returns:
        Relative time string
    """
    if last_connected is None:
        return "[dim]never[/dim]"

    now = datetime.datetime.now(datetime.UTC)
    # Ensure last_connected has timezone info
    if last_connected.tzinfo is None:
        last_connected = last_connected.replace(tzinfo=datetime.UTC)

    delta = now - last_connected

    if delta.days > 30:
        return f"{delta.days // 30}mo ago"
    elif delta.days > 0:
        return f"{delta.days}d ago"
    elif delta.seconds >= 3600:
        return f"{delta.seconds // 3600}h ago"
    elif delta.seconds >= 60:
        return f"{delta.seconds // 60}m ago"
    else:
        return "just now"


def _list_codespaces_table(
    codespaces: list[RegisteredCodespace],
    gh_status: dict[str, GitHubCodespaceInfo],
) -> None:
    """Display codespaces as a Rich table.

    Args:
        codespaces: List of registered codespaces
        gh_status: Dict mapping gh_name to live GitHub status
    """
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("name", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("config", no_wrap=True)
    table.add_column("repository", style="dim", no_wrap=True)
    table.add_column("last used", style="dim", no_wrap=True)

    for cs in codespaces:
        gh_info = gh_status.get(cs.gh_name)
        status = _format_gh_status(gh_info)
        config = _format_config_status(cs.configured)
        last_used = _format_relative_time(cs.last_connected_at)

        # Truncate repository if too long
        repo = cs.repository
        if len(repo) > 25:
            repo = repo[:22] + "..."

        table.add_row(
            cs.friendly_name,
            status,
            config,
            repo,
            last_used,
        )

    console = Console(stderr=True, force_terminal=True)
    console.print(table)


@click.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.pass_obj
def list_codespaces(ctx: ErkContext, output_json: bool) -> None:
    """Show registered codespaces with their status.

    Displays codespaces from the local registry along with their
    current GitHub status (Available, Shutdown, etc.).

    Examples:

        erk codespace list

        erk codespace list --json
    """
    import json

    registry = ctx.codespace_registry
    github = ctx.codespace_github

    codespaces = registry.list_codespaces()

    if not codespaces:
        user_output("No codespaces registered.")
        user_output("")
        user_output("To register an existing codespace:")
        user_output("  erk codespace register <friendly-name>")
        return

    # Fetch live status from GitHub
    gh_codespaces = github.list_codespaces()
    gh_status: dict[str, GitHubCodespaceInfo] = {cs.name: cs for cs in gh_codespaces}

    if output_json:
        # JSON output for scripting
        data = []
        for cs in codespaces:
            gh_info = gh_status.get(cs.gh_name)
            entry = {
                "friendly_name": cs.friendly_name,
                "gh_name": cs.gh_name,
                "repository": cs.repository,
                "branch": cs.branch,
                "machine_type": cs.machine_type,
                "configured": cs.configured,
                "gh_status": gh_info.state if gh_info else "deleted",
                "registered_at": cs.registered_at.isoformat(),
                "last_connected_at": (
                    cs.last_connected_at.isoformat() if cs.last_connected_at else None
                ),
                "notes": cs.notes,
            }
            data.append(entry)

        user_output(json.dumps(data, indent=2))
        return

    # Rich table output
    _list_codespaces_table(codespaces, gh_status)
