"""nomcp init command - create a kit that wraps an MCP server."""

import asyncio
import re
import shlex
from pathlib import Path

import click
import yaml

from dot_agent_kit.commands.nomcp.group import nomcp_group


def _sanitize_name(name: str) -> str:
    """Convert name to valid kit/command name (lowercase, hyphens)."""
    # Replace underscores with hyphens
    name = name.replace("_", "-")
    # Remove any characters that aren't alphanumeric or hyphens
    name = re.sub(r"[^a-z0-9-]", "", name.lower())
    # Remove leading hyphens or numbers
    name = re.sub(r"^[^a-z]+", "", name)
    return name


def _tool_name_to_command_name(tool_name: str) -> str:
    """Convert MCP tool name to CLI command name."""
    return _sanitize_name(tool_name)


def _tool_name_to_function_name(tool_name: str) -> str:
    """Convert MCP tool name to Python function name."""
    # Replace hyphens with underscores
    name = tool_name.replace("-", "_")
    # Remove any non-alphanumeric characters except underscores
    name = re.sub(r"[^a-z0-9_]", "", name.lower())
    # Ensure it starts with a letter
    if name and not name[0].isalpha():
        name = "cmd_" + name
    return name


@nomcp_group.command(name="init")
@click.argument("kit_name")
@click.option(
    "--mcp",
    "mcp_command",
    required=True,
    help="MCP server command (e.g., 'uvx mcp-server-github')",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(),
    help="Output directory (default: ./<kit-name>)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing directory",
)
def init(kit_name: str, mcp_command: str, output_dir: str | None, force: bool) -> None:
    """Create a kit that wraps an MCP server.

    KIT_NAME is the name for the new kit (e.g., 'github-kit').

    Examples:

        dot-agent nomcp init github-kit --mcp "uvx mcp-server-github"

        dot-agent nomcp init fetch-kit --mcp "uvx mcp-server-fetch" -o ./my-kits/fetch
    """
    # Sanitize kit name
    kit_name = _sanitize_name(kit_name)
    if not kit_name:
        raise click.ClickException("Invalid kit name")

    # Parse MCP command
    command_list = shlex.split(mcp_command)
    if not command_list:
        raise click.ClickException("MCP command is required")

    # Determine output directory
    output_path = Path(output_dir) if output_dir else Path(kit_name)

    if output_path.exists() and not force:
        raise click.ClickException(
            f"Directory '{output_path}' already exists. Use --force to overwrite."
        )

    asyncio.run(_init_async(kit_name, command_list, output_path))


async def _init_async(kit_name: str, command: list[str], output_path: Path) -> None:
    """Async implementation of init command."""
    from rich.console import Console

    from dot_agent_kit.nomcp.wrapper import MCPWrapper, MCPWrapperError

    console = Console()

    # Connect to MCP server and discover tools
    console.print("[dim]Connecting to MCP server...[/dim]")

    try:
        wrapper = MCPWrapper(command=command)
        async with wrapper:
            tools = await wrapper.list_tools()
    except MCPWrapperError as e:
        raise click.ClickException(f"Failed to connect to MCP server: {e}") from e
    except Exception as e:
        raise click.ClickException(f"Error connecting to MCP server: {e}") from e

    if not tools:
        console.print("[yellow]Warning: No tools found from MCP server.[/yellow]")

    console.print(f"[green]Found {len(tools)} tools[/green]")

    # Create kit directory structure
    _create_kit_structure(kit_name, command, tools, output_path, console)

    console.print("\n[bold green]Kit created successfully![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Review and customize the generated wrappers in:")
    console.print(f"     {output_path}/kit_cli_commands/{kit_name}/")
    console.print("  2. Install the kit:")
    console.print(f"     dot-agent kit install {output_path}")
    console.print("  3. Test the commands:")
    console.print(f"     dot-agent run {kit_name} --help")


def _create_kit_structure(
    kit_name: str,
    command: list[str],
    tools: list,
    output_path: Path,
    console,
) -> None:
    """Create the kit directory structure with all files."""

    # Create directories
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "kit_cli_commands" / kit_name).mkdir(parents=True, exist_ok=True)
    (output_path / "skills" / kit_name).mkdir(parents=True, exist_ok=True)
    (output_path / "docs" / kit_name).mkdir(parents=True, exist_ok=True)

    # Create nomcp.yaml (MCP server configuration)
    nomcp_config = {
        "command": command,
    }
    (output_path / "nomcp.yaml").write_text(
        yaml.dump(nomcp_config, default_flow_style=False),
        encoding="utf-8",
    )
    console.print("  Created: nomcp.yaml")

    # Create kit_cli_commands/__init__.py files
    (output_path / "kit_cli_commands" / "__init__.py").write_text(
        f'"""Kit CLI commands for {kit_name}."""\n',
        encoding="utf-8",
    )
    (output_path / "kit_cli_commands" / kit_name / "__init__.py").write_text(
        f'"""CLI commands for {kit_name} kit."""\n',
        encoding="utf-8",
    )

    # Generate wrapper for each tool
    kit_cli_commands = []
    for tool in tools:
        command_name = _tool_name_to_command_name(tool.name)
        function_name = _tool_name_to_function_name(tool.name)
        file_name = f"{function_name}.py"

        wrapper_code = _generate_wrapper_code(kit_name, tool, function_name)
        wrapper_path = output_path / "kit_cli_commands" / kit_name / file_name
        wrapper_path.write_text(wrapper_code, encoding="utf-8")

        kit_cli_commands.append(
            {
                "name": command_name,
                "path": f"kit_cli_commands/{kit_name}/{file_name}",
                "description": tool.description or f"Call {tool.name} tool",
            }
        )
        console.print(f"  Created: kit_cli_commands/{kit_name}/{file_name}")

    # Create kit.yaml
    kit_manifest = {
        "name": kit_name,
        "version": "0.1.0",
        "description": f"MCP wrapper kit for {shlex.join(command)}",
        "license": "MIT",
        "artifacts": {
            "skill": [f"skills/{kit_name}/SKILL.md"],
            "doc": [f"docs/{kit_name}/REFERENCE.md"],
        },
        "kit_cli_commands": kit_cli_commands,
    }
    (output_path / "kit.yaml").write_text(
        yaml.dump(kit_manifest, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    console.print("  Created: kit.yaml")

    # Generate SKILL.md
    skill_content = _generate_skill_md(kit_name, tools)
    (output_path / "skills" / kit_name / "SKILL.md").write_text(
        skill_content,
        encoding="utf-8",
    )
    console.print(f"  Created: skills/{kit_name}/SKILL.md")

    # Generate REFERENCE.md
    reference_content = _generate_reference_md(kit_name, tools, command)
    (output_path / "docs" / kit_name / "REFERENCE.md").write_text(
        reference_content,
        encoding="utf-8",
    )
    console.print(f"  Created: docs/{kit_name}/REFERENCE.md")


def _generate_wrapper_code(kit_name: str, tool, function_name: str) -> str:
    """Generate Python wrapper code for an MCP tool."""
    # Build parameter definitions
    params = []
    param_docs = []
    param_kwargs = []

    for param in tool.parameters:
        param_name = param.name.replace("-", "_")
        param_type = _mcp_type_to_python_type(param.type)
        click_type = _mcp_type_to_click_type(param.type)

        if param.required:
            params.append(
                f'@click.option("--{param.name}", "{param_name}", '
                f"required=True, type={click_type}, help={repr(param.description or param.name)})"
            )
        else:
            params.append(
                f'@click.option("--{param.name}", "{param_name}", '
                f"type={click_type}, help={repr(param.description or param.name)})"
            )

        param_docs.append(f"        {param_name}: {param.description or param.name}")
        param_kwargs.append(f'"{param.name}": {param_name}')

    params_str = "\n".join(params)
    param_docs_str = "\n".join(param_docs) if param_docs else "        None"
    param_kwargs_str = ", ".join(param_kwargs)

    # Build function signature
    func_params = []
    for param in tool.parameters:
        param_name = param.name.replace("-", "_")
        param_type = _mcp_type_to_python_type(param.type)
        if param.required:
            func_params.append(f"{param_name}: {param_type}")
        else:
            func_params.append(f"{param_name}: {param_type} | None")

    func_params_str = ", ".join(func_params)

    code = f'''"""Wrapper for {tool.name} MCP tool."""

import asyncio
import json

import click

from dot_agent_kit.nomcp import MCPWrapper


@click.command()
{params_str}
def {function_name}({func_params_str}) -> None:
    """
    {tool.description or f"Call {tool.name} tool."}

    Args:
{param_docs_str}
    """
    asyncio.run(_call_tool({param_kwargs_str}))


async def _call_tool(**kwargs: object) -> None:
    """Call the MCP tool and output result."""
    # Filter out None values
    args = {{k: v for k, v in kwargs.items() if v is not None}}

    wrapper = MCPWrapper.from_kit()
    async with wrapper:
        result = await wrapper.call("{tool.name}", **args)

    if result.is_error:
        raise click.ClickException(f"Tool error: {{result.error_message}}")

    # Output result as JSON
    click.echo(json.dumps(result.data, indent=2, default=str))


if __name__ == "__main__":
    {function_name}()
'''
    return code


def _mcp_type_to_python_type(mcp_type: str) -> str:
    """Convert MCP type to Python type annotation."""
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }
    return type_map.get(mcp_type, "str")


def _mcp_type_to_click_type(mcp_type: str) -> str:
    """Convert MCP type to Click type."""
    type_map = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
    }
    return type_map.get(mcp_type, "str")


def _generate_skill_md(kit_name: str, tools: list) -> str:
    """Generate SKILL.md content."""
    tool_list = []
    for tool in tools:
        command_name = _tool_name_to_command_name(tool.name)
        tool_list.append(
            f"- `dot-agent run {kit_name} {command_name}` - {tool.description or tool.name}"
        )

    tools_str = "\n".join(tool_list) if tool_list else "No commands available."

    return f"""# {kit_name} Skill

This skill provides commands for interacting with the {kit_name} MCP server.

## When to Use

Use this skill when the user wants to:
- Access {kit_name} functionality
- Use any of the commands listed below

## Available Commands

{tools_str}

## Usage Pattern

When the user requests {kit_name} functionality, run the appropriate command:

```bash
dot-agent run {kit_name} <command> [options]
```

## Getting Help

For detailed options on any command:

```bash
dot-agent run {kit_name} <command> --help
```
"""


def _generate_reference_md(kit_name: str, tools: list, command: list[str]) -> str:
    """Generate REFERENCE.md content."""
    command_docs = []

    for tool in tools:
        command_name = _tool_name_to_command_name(tool.name)
        params_doc = []

        for param in tool.parameters:
            required = " (required)" if param.required else ""
            params_doc.append(
                f"  - `--{param.name}` ({param.type}){required}: {param.description or ''}"
            )

        params_str = "\n".join(params_doc) if params_doc else "  No parameters."

        command_docs.append(f"""### {command_name}

{tool.description or "No description available."}

**Parameters:**
{params_str}

**Example:**
```bash
dot-agent run {kit_name} {command_name} --help
```
""")

    commands_str = "\n".join(command_docs)
    command_str = shlex.join(command)

    return f"""# {kit_name} Reference

This kit wraps the MCP server: `{command_str}`

## Commands

{commands_str}

## Configuration

The MCP server configuration is stored in `nomcp.yaml`:

```yaml
command: {command}
```

## Customization

You can customize the wrappers in `kit_cli_commands/{kit_name}/` to:

- Add argument validation
- Transform inputs/outputs
- Add caching or retry logic
- Combine multiple MCP tools into one command
"""
