"""Init command for creating .erk/kits.toml configuration."""

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
    help="Overwrite existing .erk/kits.toml if present",
)
def init(force: bool) -> None:
    """Initialize .erk/kits.toml configuration file.

    Creates a new kits.toml configuration file in .erk/ directory
    at the git repo root (or current directory if not in a git repo).
    Also creates .erk/ directory if it doesn't exist.

    Use --force to overwrite an existing configuration.
    """
    project_dir = resolve_project_dir(Path.cwd())
    config_path = project_dir / ".erk" / "kits.toml"
    erk_dir = project_dir / ".erk"

    # Check if config already exists
    if config_path.exists() and not force:
        user_output(f"Error: {config_path} already exists")
        user_output("Use --force to overwrite")
        raise SystemExit(1)

    # Create .erk directory if it doesn't exist
    if not erk_dir.exists():
        erk_dir.mkdir(parents=True)
        user_output(f"Created {erk_dir}/")

    # Create default config
    config = create_default_config()
    save_project_config(project_dir, config)

    user_output(f"Created {config_path}")
    user_output("\nYou can now install kits using:")
    user_output("  erk kit install <kit-name>")
