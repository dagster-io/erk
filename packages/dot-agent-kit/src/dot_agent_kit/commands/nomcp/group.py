"""nomcp command group - MCP-hidden CLI wrapper pattern."""

import click


@click.group(name="nomcp")
def nomcp_group() -> None:
    """MCP-hidden CLI wrapper pattern.

    Use MCP servers without MCP. Turn any MCP server into a kit with CLI commands + skill.

    Commands:
      inspect  - Discover tools from an MCP server
      init     - Create a kit that wraps an MCP server
      skill    - Generate or update skill from kit
    """
