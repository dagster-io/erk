"""Register an existing GitHub codespace with a friendly name."""

import click
from erk_shared.output.output import user_output

from erk.core.codespace.types import GitHubCodespaceInfo, RegisteredCodespace
from erk.core.context import ErkContext


def _format_gh_status(state: str) -> str:
    """Format GitHub state with styling for interactive display."""
    status_styles = {
        "Available": "[green]available[/green]",
        "Shutdown": "[yellow]shutdown[/yellow]",
        "Starting": "[yellow]starting[/yellow]",
        "Pending": "[yellow]pending[/yellow]",
        "Failed": "[red]failed[/red]",
    }
    return status_styles.get(state, state.lower())


def _select_codespace_interactive(
    codespaces: list[GitHubCodespaceInfo],
) -> GitHubCodespaceInfo:
    """Show available codespaces and let user select one.

    Args:
        codespaces: List of available GitHub codespaces

    Returns:
        Selected codespace info

    Raises:
        SystemExit: If user cancels or invalid selection
    """
    from rich.console import Console
    from rich.table import Table

    console = Console(stderr=True, force_terminal=True)

    user_output("Available codespaces:\n")

    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("name", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("repository", style="dim")
    table.add_column("branch", style="dim")

    for i, cs in enumerate(codespaces, 1):
        status = _format_gh_status(cs.state)
        table.add_row(str(i), cs.name, status, cs.repository, cs.branch)

    console.print(table)
    user_output("")

    try:
        selection = click.prompt(
            "Select codespace number",
            type=click.IntRange(1, len(codespaces)),
        )
        return codespaces[selection - 1]
    except (KeyboardInterrupt, click.Abort):
        user_output("\nCancelled.")
        raise SystemExit(1) from None


@click.command("register")
@click.argument("friendly_name")
@click.option(
    "--gh-name",
    help="GitHub codespace name (from 'gh codespace list'). "
    "If not provided, shows available codespaces to select from.",
)
@click.option(
    "--notes",
    help="Optional notes about this codespace.",
)
@click.pass_obj
def register_codespace(
    ctx: ErkContext,
    friendly_name: str,
    gh_name: str | None,
    notes: str | None,
) -> None:
    """Register an existing GitHub codespace with a friendly name.

    This registers a codespace that was created outside of erk
    (e.g., through github.com or gh CLI) so it can be managed
    with erk codespace commands.

    Examples:

        # Interactive selection (shows available codespaces to choose from)
        erk codespace register my-planning-space

        # Direct registration (if you know the GitHub codespace name)
        erk codespace register my-space --gh-name "schrockn-curly-rotary-abc123"
    """
    registry = ctx.codespace_registry
    github = ctx.codespace_github

    # Check friendly_name not already registered
    existing = registry.get(friendly_name)
    if existing is not None:
        user_output(
            click.style("Error: ", fg="red")
            + f"Name '{friendly_name}' is already registered.\n\n"
            + "Choose a different name or unregister the existing one:\n"
            + f"  erk codespace unregister {friendly_name}"
        )
        raise SystemExit(1)

    # Get or select GitHub codespace
    if gh_name is None:
        # Interactive selection
        codespaces = github.list_codespaces()
        if not codespaces:
            user_output(
                click.style("Error: ", fg="red")
                + "No codespaces found on GitHub.\n\n"
                + "Create one first:\n"
                + "  erk codespace create <friendly-name>"
            )
            raise SystemExit(1)

        selected = _select_codespace_interactive(codespaces)
        gh_name = selected.name
        gh_info = selected
    else:
        # Validate GitHub codespace exists
        gh_info = github.get_codespace(gh_name)
        if gh_info is None:
            user_output(
                click.style("Error: ", fg="red")
                + f"Codespace '{gh_name}' not found on GitHub.\n\n"
                + "List available codespaces with:\n"
                + "  gh codespace list"
            )
            raise SystemExit(1)

    # Create registry entry
    codespace = RegisteredCodespace(
        friendly_name=friendly_name,
        gh_name=gh_name,
        repository=gh_info.repository,
        branch=gh_info.branch,
        machine_type=gh_info.machine_type,
        configured=False,
        registered_at=ctx.time.now(),
        last_connected_at=None,
        notes=notes,
    )

    registry.register(codespace)

    user_output(click.style("", fg="green") + f"Registered '{friendly_name}'")
    user_output(f"  GitHub name: {gh_name}")
    user_output(f"  Repository: {gh_info.repository}")
    user_output(f"  Branch: {gh_info.branch}")
    user_output("\nNext step: Configure the codespace for development:")
    user_output(f"  erk codespace configure {friendly_name}")
