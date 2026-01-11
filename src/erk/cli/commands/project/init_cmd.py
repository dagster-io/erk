"""Project init command - initialize a project in the current directory."""

import click
import tomlkit

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


def _build_project_toml(project_name: str) -> str:
    """Build project.toml content using tomlkit.

    Args:
        project_name: Name of the project (typically the directory name)

    Returns:
        TOML content as a string
    """
    doc = tomlkit.document()
    doc.add(tomlkit.comment("Project configuration for erk"))
    doc.add(tomlkit.comment("This file identifies this directory as an erk project"))
    doc.add(tomlkit.comment("within a monorepo."))
    doc.add(tomlkit.nl())
    doc.add(tomlkit.comment("Optional: custom project name (defaults to directory name)"))
    doc.add(tomlkit.comment(f' name = "{project_name}"'))
    doc.add(tomlkit.nl())

    # [env] section
    env_table = tomlkit.table()
    env_table.add(tomlkit.comment("Project-specific environment variables"))
    env_table.add(tomlkit.comment("(merged with repo-level config)"))
    env_table.add(tomlkit.comment("These variables are available in .env files"))
    env_table.add(tomlkit.comment("created for worktrees"))
    env_table.add(tomlkit.comment("Example:"))
    env_table.add(tomlkit.comment(' DAGSTER_HOME = "{project_root}"'))
    doc["env"] = env_table

    doc.add(tomlkit.nl())

    # [post_create] section
    post_create_table = tomlkit.table()
    post_create_table.add(tomlkit.comment("Commands to run after worktree creation,"))
    post_create_table.add(tomlkit.comment("FROM the project directory"))
    post_create_table.add(tomlkit.comment("These run AFTER repo-level post_create commands"))
    post_create_table.add(tomlkit.comment(' shell = "bash"'))
    post_create_table.add(tomlkit.comment(" commands = ["))
    post_create_table.add(tomlkit.comment('   "source .venv/bin/activate",'))
    post_create_table.add(tomlkit.comment(" ]"))
    doc["post_create"] = post_create_table

    return tomlkit.dumps(doc)


@click.command("init")
@click.pass_obj
def init_project(ctx: ErkContext) -> None:
    """Initialize a project in the current directory.

    Creates a .erk/project.toml file that identifies this directory as
    a project within a monorepo. When worktrees are created from this
    project context, erk will:

    - Record the project path in worktrees.toml
    - Navigate to the project subdirectory on `erk wt co`
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
    content = _build_project_toml(project_name)
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
