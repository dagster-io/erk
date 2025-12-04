import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadedConfig:
    """In-memory representation of merged repo + project config."""

    env: dict[str, str]
    post_create_commands: list[str]
    post_create_shell: str | None


@dataclass(frozen=True)
class ProjectConfig:
    """In-memory representation of `.erk/project.toml`.

    Example project.toml:
      # Optional: custom name (defaults to directory name)
      # name = "dagster-open-platform"

      [env]
      # Project-specific env vars (merged with repo-level)
      DAGSTER_HOME = "{project_root}"

      [post_create]
      # Runs AFTER repo-level commands, FROM project directory
      shell = "bash"
      commands = [
        "source .venv/bin/activate",
      ]
    """

    name: str | None  # Custom project name (None = use directory name)
    env: dict[str, str]
    post_create_commands: list[str]
    post_create_shell: str | None


def load_config(config_dir: Path) -> LoadedConfig:
    """Load config.toml from the given directory if present; otherwise return defaults.

    Example config:
      [env]
      DAGSTER_GIT_REPO_DIR = "{worktree_path}"

      [post_create]
      shell = "bash"
      commands = [
        "uv venv",
        "uv run make dev_install",
      ]
    """

    cfg_path = config_dir / "config.toml"
    if not cfg_path.exists():
        return LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    env = {str(k): str(v) for k, v in data.get("env", {}).items()}
    post = data.get("post_create", {})
    commands = [str(x) for x in post.get("commands", [])]
    shell = post.get("shell")
    if shell is not None:
        shell = str(shell)
    return LoadedConfig(env=env, post_create_commands=commands, post_create_shell=shell)


def load_project_config(project_root: Path) -> ProjectConfig:
    """Load project.toml from the project's .erk directory.

    Args:
        project_root: Path to the project root directory

    Returns:
        ProjectConfig with parsed values, or defaults if file doesn't exist
    """
    cfg_path = project_root / ".erk" / "project.toml"
    if not cfg_path.exists():
        return ProjectConfig(name=None, env={}, post_create_commands=[], post_create_shell=None)

    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    # Optional name field
    name = data.get("name")
    if name is not None:
        name = str(name)

    # Env vars
    env = {str(k): str(v) for k, v in data.get("env", {}).items()}

    # Post-create commands
    post = data.get("post_create", {})
    commands = [str(x) for x in post.get("commands", [])]
    shell = post.get("shell")
    if shell is not None:
        shell = str(shell)

    return ProjectConfig(name=name, env=env, post_create_commands=commands, post_create_shell=shell)


def merge_configs(repo_config: LoadedConfig, project_config: ProjectConfig) -> LoadedConfig:
    """Merge repo-level and project-level configs.

    Merge rules:
    - env: Project values override repo values (dict merge)
    - post_create_commands: Repo commands run first, then project commands (list concat)
    - post_create_shell: Project shell overrides repo shell if set

    Args:
        repo_config: Repository-level configuration
        project_config: Project-level configuration

    Returns:
        Merged LoadedConfig
    """
    # Merge env: project overrides repo
    merged_env = {**repo_config.env, **project_config.env}

    # Concat commands: repo first, then project
    merged_commands = repo_config.post_create_commands + project_config.post_create_commands

    # Shell: project overrides if set
    merged_shell = (
        project_config.post_create_shell
        if project_config.post_create_shell is not None
        else repo_config.post_create_shell
    )

    return LoadedConfig(
        env=merged_env,
        post_create_commands=merged_commands,
        post_create_shell=merged_shell,
    )
