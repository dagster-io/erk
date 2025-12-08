"""Init command for creating .agent/dot-agent.toml configuration."""

from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io.git import resolve_project_dir
from dot_agent_kit.io.state import create_default_config, save_project_config


@click.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing .agent/dot-agent.toml if present",
)
def init(force: bool) -> None:
    """Initialize .agent/dot-agent.toml configuration file.

    Creates a new dot-agent.toml configuration file in .agent/ directory
    at the git repo root (or current directory if not in a git repo).
    Also creates .agent/ directory if it doesn't exist.

    Use --force to overwrite an existing configuration.
    """
    project_dir = resolve_project_dir(Path.cwd())
    config_path = project_dir / ".agent" / "dot-agent.toml"
    agent_dir = project_dir / ".agent"

    # Check if config already exists
    if config_path.exists() and not force:
        user_output(f"Error: {config_path} already exists")
        user_output("Use --force to overwrite")
        raise SystemExit(1)

    # Create .agent directory if it doesn't exist
    if not agent_dir.exists():
        agent_dir.mkdir(parents=True)
        user_output(f"Created {agent_dir}/")

    # Create default config
    config = create_default_config()
    save_project_config(project_dir, config)

    user_output(f"Created {config_path}")
    user_output("\nYou can now install kits using:")
    user_output("  dot-agent kit install <kit-name>")
