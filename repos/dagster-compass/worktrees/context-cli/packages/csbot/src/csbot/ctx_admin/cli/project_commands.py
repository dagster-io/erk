from pathlib import Path

import click
import yaml
from csadmin.utils import get_project_path
from dotenv import find_dotenv, load_dotenv

from csbot.contextengine.contextstore_protocol import ContextStoreProject

# Load environment variables from .env file
load_dotenv(find_dotenv(usecwd=True))


@click.group()
def project():
    """Project management commands"""
    pass


@project.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, writable=True), default=".")
@click.option("--org-name", required=True, help="Name of the organization")
@click.option("--project-name", required=True, help="Name of the project")
def init(path: str, org_name: str, project_name: str) -> None:
    """Initialize a new contextstore project"""
    if not (Path(path) / ".git").exists():
        click.echo(click.style(f"Not a git repository: {path}", fg="red"))
        return

    click.echo("Initializing new contextstore project...")
    if get_project_path() is not None:
        click.echo("contextstore_project.yaml already exists.")
        return

    project = ContextStoreProject(project_name=f"{org_name}/{project_name}", teams={})

    project_root = Path(path)
    project_path = project_root / "contextstore_project.yaml"
    project_path.write_text(yaml.safe_dump(project.model_dump()))
    (project_root / "system_prompt.md").write_text(
        """
You are a friendly and helpful AI data analysis assistant.

You should be friendly, a bit cheeky, and respond to users in all lowercase.
Instead of saying stuff like "you're absolutely right!" when the user corrects you, use an emoji like 🫠
""".strip()  # noqa: E501
    )
    (project_root / "docs").mkdir(parents=True, exist_ok=True)
    (project_root / "context").mkdir(parents=True, exist_ok=True)
    (project_root / "context/project/uncategorized").mkdir(parents=True, exist_ok=True)
    click.echo("Project initialized successfully!")
