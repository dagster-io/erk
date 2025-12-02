"""nomcp skill command - generate or update skill from kit."""

from pathlib import Path

import click
import yaml

from dot_agent_kit.commands.nomcp.group import nomcp_group


@nomcp_group.group(name="skill")
def skill_group() -> None:
    """Skill management commands."""


@skill_group.command(name="generate")
@click.argument("kit_path", type=click.Path(exists=True), default=".")
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(),
    help="Output path for SKILL.md (default: <kit>/skills/<kit-name>/SKILL.md)",
)
def generate(kit_path: str, output_path: str | None) -> None:
    """Regenerate SKILL.md from kit CLI commands.

    KIT_PATH is the path to the kit directory (default: current directory).

    This command reads the kit.yaml and regenerates the SKILL.md file
    based on the defined kit_cli_commands.

    Examples:

        dot-agent nomcp skill generate ./my-kit

        dot-agent nomcp skill generate . -o ./custom/SKILL.md
    """
    kit_dir = Path(kit_path)
    kit_yaml_path = kit_dir / "kit.yaml"

    if not kit_yaml_path.exists():
        raise click.ClickException(f"kit.yaml not found in {kit_dir}")

    # Load kit manifest
    manifest = yaml.safe_load(kit_yaml_path.read_text(encoding="utf-8"))
    kit_name = manifest.get("name")

    if not kit_name:
        raise click.ClickException("kit.yaml missing 'name' field")

    kit_cli_commands = manifest.get("kit_cli_commands", [])

    if not kit_cli_commands:
        click.echo("Warning: No kit_cli_commands found in kit.yaml")

    # Determine output path
    if output_path:
        skill_path = Path(output_path)
    else:
        skill_path = kit_dir / "skills" / kit_name / "SKILL.md"

    # Ensure parent directory exists
    skill_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate skill content
    skill_content = _generate_skill_content(kit_name, kit_cli_commands)
    skill_path.write_text(skill_content, encoding="utf-8")

    click.echo(f"Generated: {skill_path}")


def _generate_skill_content(kit_name: str, commands: list[dict]) -> str:
    """Generate SKILL.md content from kit CLI commands."""
    command_list = []
    for cmd in commands:
        name = cmd.get("name", "unknown")
        description = cmd.get("description", name)
        command_list.append(f"- `dot-agent run {kit_name} {name}` - {description}")

    commands_str = "\n".join(command_list) if command_list else "No commands available."

    return f"""# {kit_name} Skill

This skill provides commands for interacting with the {kit_name} kit.

## When to Use

Use this skill when the user wants to:
- Access {kit_name} functionality
- Use any of the commands listed below

## Available Commands

{commands_str}

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
