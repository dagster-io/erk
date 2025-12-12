"""Project init command - initialize a project in the current directory."""

import click

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.output.output import user_output

# Template for project.toml
PROJECT_TOML_TEMPLATE = """\
# Project configuration for erk
# This file identifies this directory as an erk project within a monorepo.

# Optional: custom project name (defaults to directory name)
# name = "{project_name}"

[env]
# Project-specific environment variables (merged with repo-level config)
# These variables are available in .env files created for worktrees
# Example:
# DAGSTER_HOME = "{{project_root}}"

[post_create]
# Commands to run after worktree creation, FROM the project directory
# These run AFTER repo-level post_create commands
# shell = "bash"
# commands = [
#   "source .venv/bin/activate",
# ]
"""


@click.command("init")
@click.pass_obj
def init_project(ctx: ErkContext) -> None:
    """Initialize a project in the current directory.

    Creates a .erk/project.toml file that identifies this directory as
    a project within a monorepo. When worktrees are created from this
    project context, erk will:

    - Record the project path in worktrees.toml
    - Navigate to the project subdirectory on `erk goto`
    - Merge project-level config with repo-level config
    - Run project-specific post_create commands

    Example:
        cd /code/internal/python_modules/my-project
        erk project init
    """
    # Validate we're in a git repo
    repo = discover_repo_context(ctx, ctx.cwd)

    # Don't allow init at repo root (check before project.toml to give clearer error)
    if ctx.cwd.resolve() == repo.root.resolve():
        user_output(
            click.style("Error: ", fg="red") + "Cannot initialize project at repository root.\n"
            "Projects are subdirectories within a repo. "
            "Use `erk init` for repository-level configuration."
        )
        raise SystemExit(1)

    # Check if project.toml already exists
    project_toml_path = ctx.cwd / ".erk" / "project.toml"
    if ctx.git.path_exists(project_toml_path):
        user_output(
            click.style("Error: ", fg="red") + f"Project already initialized: {project_toml_path}"
        )
        raise SystemExit(1)

    # Create .erk directory and project.toml
    erk_dir = ctx.cwd / ".erk"
    erk_dir.mkdir(parents=True, exist_ok=True)

    project_name = ctx.cwd.name
    content = PROJECT_TOML_TEMPLATE.format(project_name=project_name)
    project_toml_path.write_text(content, encoding="utf-8")

    # Calculate path from repo root for display
    path_from_repo = ctx.cwd.relative_to(repo.root)

    user_output(
        click.style("✓ ", fg="green")
        + f"Initialized project: {click.style(project_name, fg='cyan', bold=True)}"
    )
    user_output(f"  Location: {path_from_repo}")
    user_output(f"  Config: {project_toml_path}")
    user_output("")
    user_output("Next steps:")
    user_output(f"  1. Edit {project_toml_path} to configure project settings")
    user_output("  2. Create a worktree from this project: erk wt create <name>")
