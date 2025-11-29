"""Initialize GitHub Codespaces configuration for remote planning."""

import json
from pathlib import Path

import click
from erk_shared.output.output import user_output

DEVCONTAINER_CONFIG = {
    "name": "erk-planning",
    "image": "mcr.microsoft.com/devcontainers/python:3.13",
    "features": {
        "ghcr.io/devcontainers/features/node:1": {},
        "ghcr.io/devcontainers/features/github-cli:1": {},
    },
    "postCreateCommand": "npm install -g @anthropic-ai/claude-code && pip install uv && uv sync",
    "secrets": ["ANTHROPIC_API_KEY"],
}


@click.command("init")
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing devcontainer.json file.",
)
def init_codespace(force: bool) -> None:
    """Create .devcontainer/devcontainer.json for remote planning.

    This sets up a GitHub Codespace configuration with Claude Code
    pre-installed for remote AI-assisted planning workflows.
    """
    devcontainer_dir = Path.cwd() / ".devcontainer"
    devcontainer_file = devcontainer_dir / "devcontainer.json"

    # Check if file already exists
    if devcontainer_file.exists() and not force:
        user_output(
            click.style("Error: ", fg="red")
            + f"{devcontainer_file} already exists.\n\n"
            + "Use --force to overwrite the existing configuration."
        )
        raise SystemExit(1)

    # Create .devcontainer directory if needed
    if not devcontainer_dir.exists():
        devcontainer_dir.mkdir(parents=True)

    # Write devcontainer.json
    devcontainer_file.write_text(
        json.dumps(DEVCONTAINER_CONFIG, indent=2) + "\n",
        encoding="utf-8",
    )

    user_output(click.style("✓ ", fg="green") + f"Created {devcontainer_file}")
    user_output("")
    user_output("Next steps:")
    user_output("  1. Commit the .devcontainer/devcontainer.json file")
    user_output("  2. Set your ANTHROPIC_API_KEY as a GitHub Codespaces secret:")
    user_output("     gh secret set ANTHROPIC_API_KEY --user")
    user_output("  3. Ensure gh CLI has codespace scope:")
    user_output("     gh auth refresh -h github.com -s codespace")
    user_output("  4. Create a Codespace: erk codespace plan <description>")
