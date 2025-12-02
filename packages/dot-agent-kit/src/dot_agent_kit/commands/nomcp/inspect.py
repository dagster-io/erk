"""nomcp inspect command - discover tools from an MCP server."""

import asyncio
import shlex

import click
from rich.console import Console
from rich.table import Table

from dot_agent_kit.commands.nomcp.group import nomcp_group


@nomcp_group.command(name="inspect")
@click.argument("mcp_command", nargs=-1, required=True)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def inspect(mcp_command: tuple[str, ...], output_json: bool) -> None:
    """Discover tools from an MCP server.

    MCP_COMMAND is the command to start the MCP server.

    Examples:

        dot-agent nomcp inspect uvx mcp-server-github

        dot-agent nomcp inspect python -m my_mcp_server

        dot-agent nomcp inspect -- uvx mcp-server-fetch --verbose
    """
    command_list = list(mcp_command)

    if not command_list:
        raise click.ClickException("MCP command is required")

    asyncio.run(_inspect_async(command_list, output_json))


async def _inspect_async(command: list[str], output_json: bool) -> None:
    """Async implementation of inspect command."""
    from dot_agent_kit.nomcp.wrapper import MCPWrapper, MCPWrapperError

    try:
        wrapper = MCPWrapper(command=command)
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    console = Console()

    try:
        async with wrapper:
            tools = await wrapper.list_tools()
    except MCPWrapperError as e:
        raise click.ClickException(f"Failed to connect to MCP server: {e}") from e
    except Exception as e:
        raise click.ClickException(f"Error connecting to MCP server: {e}") from e

    if output_json:
        import json

        tools_data = [
            {
                "name": t.name,
                "description": t.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                    }
                    for p in t.parameters
                ],
            }
            for t in tools
        ]
        click.echo(json.dumps({"tools": tools_data}, indent=2))
        return

    # Pretty print with Rich
    command_str = shlex.join(command)
    console.print(f"\n[bold]Tools available from:[/bold] {command_str}\n")

    if not tools:
        console.print("[yellow]No tools found.[/yellow]")
        return

    for tool in tools:
        console.print(f"[bold cyan]{tool.name}[/bold cyan]")
        if tool.description:
            console.print(f"  {tool.description}")

        if tool.parameters:
            table = Table(show_header=True, header_style="dim", padding=(0, 1))
            table.add_column("Parameter")
            table.add_column("Type")
            table.add_column("Required")
            table.add_column("Description")

            for param in tool.parameters:
                required_str = "[green]yes[/green]" if param.required else "no"
                table.add_row(
                    param.name,
                    param.type,
                    required_str,
                    param.description or "",
                )

            console.print(table)

        console.print()
