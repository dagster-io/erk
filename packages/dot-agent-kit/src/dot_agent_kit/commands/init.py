"""Init command for creating .erk/installed.toml configuration."""

from pathlib import Path

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.io.git import resolve_project_dir
from dot_agent_kit.io.state import create_default_config, save_project_config
from dot_agent_kit.operations.agent_docs import init_docs_agent


@click.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing .erk/installed.toml if present",
)
def init(force: bool) -> None:
    """Initialize .erk/installed.toml configuration file.

    Creates a new installed.toml configuration file in .erk/ directory
    at the git repo root (or current directory if not in a git repo).
    Also creates .erk/ directory if it doesn't exist.

    Additionally initializes docs/agent/ with template files for agent
    documentation (glossary, conventions, guide).

    Use --force to overwrite an existing configuration.
    """
    project_dir = resolve_project_dir(Path.cwd())
    config_path = project_dir / ".erk" / "installed.toml"
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

    # Initialize docs/agent with template files
    docs_result = init_docs_agent(project_dir, force=force)
    if docs_result.created:
        user_output()
        for path in docs_result.created:
            user_output(f"Created {path}")

    user_output("\nYou can now install kits using:")
    user_output("  erk kit install <kit-name>")
