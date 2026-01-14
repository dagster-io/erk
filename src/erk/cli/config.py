import tomllib
from dataclasses import dataclass
from pathlib import Path

# Re-export LoadedConfig from erk_shared for backwards compatibility
from erk_shared.context.types import LoadedConfig as LoadedConfig


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


@dataclass(frozen=True)
class LegacyConfigLocation:
    """Information about a detected legacy config location."""

    path: Path
    description: str


def _parse_config_file(cfg_path: Path) -> LoadedConfig:
    """Parse a config.toml file into a LoadedConfig.

    Args:
        cfg_path: Path to the config.toml file (must exist)

    Returns:
        LoadedConfig with parsed values
    """
    data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    env = {str(k): str(v) for k, v in data.get("env", {}).items()}
    post = data.get("post_create", {})
    commands = [str(x) for x in post.get("commands", [])]
    shell = post.get("shell")
    if shell is not None:
        shell = str(shell)

    # Parse [plans] section
    plans = data.get("plans", {})
    plans_repo = plans.get("repo")
    if plans_repo is not None:
        plans_repo = str(plans_repo)

    # Parse [pool] section
    pool = data.get("pool", {})
    pool_size = pool.get("max_slots")
    if pool_size is not None:
        pool_size = int(pool_size)

    # Parse [pool.checkout] section
    pool_checkout = pool.get("checkout", {})
    pool_checkout_commands = [str(x) for x in pool_checkout.get("commands", [])]
    pool_checkout_shell = pool_checkout.get("shell")
    if pool_checkout_shell is not None:
        pool_checkout_shell = str(pool_checkout_shell)

    return LoadedConfig(
        env=env,
        post_create_commands=commands,
        post_create_shell=shell,
        plans_repo=plans_repo,
        pool_size=pool_size,
        pool_checkout_commands=pool_checkout_commands,
        pool_checkout_shell=pool_checkout_shell,
    )


def detect_legacy_config_locations(
    repo_root: Path, legacy_metadata_dir: Path | None
) -> list[LegacyConfigLocation]:
    """Detect legacy config.toml files that should be migrated.

    Legacy locations:
    1. <repo-root>/config.toml (created by 'erk init --repo')
    2. ~/.erk/repos/<repo>/config.toml (created by 'erk init' without --repo)

    Args:
        repo_root: Path to the repository root
        legacy_metadata_dir: Path to ~/.erk/repos/<repo>/ directory (or None)

    Returns:
        List of detected legacy config locations
    """
    legacy_locations: list[LegacyConfigLocation] = []

    # Check for config at repo root (created by 'erk init --repo')
    repo_root_config = repo_root / "config.toml"
    if repo_root_config.exists():
        legacy_locations.append(
            LegacyConfigLocation(
                path=repo_root_config,
                description="repo root (created by 'erk init --repo')",
            )
        )

    # Check for config in ~/.erk/repos/<repo>/ (created by 'erk init')
    if legacy_metadata_dir is not None:
        metadata_dir_config = legacy_metadata_dir / "config.toml"
        if metadata_dir_config.exists():
            legacy_locations.append(
                LegacyConfigLocation(
                    path=metadata_dir_config,
                    description=f"~/.erk/repos/ metadata dir ({legacy_metadata_dir})",
                )
            )

    return legacy_locations


def load_config(repo_root: Path) -> LoadedConfig:
    """Load config.toml for a repository.

    Location: <repo-root>/.erk/config.toml

    Example config:
      [env]
      DAGSTER_GIT_REPO_DIR = "{worktree_path}"

      [post_create]
      shell = "bash"
      commands = [
        "uv venv",
        "uv run make dev_install",
      ]

    Note: Legacy config locations (repo root, ~/.erk/repos/) are NOT supported here.
    Run 'erk doctor' to detect legacy configs that need migration.

    Args:
        repo_root: Path to the repository root

    Returns:
        LoadedConfig with parsed values or defaults if no config found
    """
    config_path = repo_root / ".erk" / "config.toml"
    if config_path.exists():
        return _parse_config_file(config_path)

    # No config found
    return LoadedConfig(
        env={},
        post_create_commands=[],
        post_create_shell=None,
        plans_repo=None,
        pool_size=None,
        pool_checkout_commands=[],
        pool_checkout_shell=None,
    )


def load_local_config(repo_root: Path) -> LoadedConfig:
    """Load config.local.toml for per-user configuration.

    Location: <repo-root>/.erk/config.local.toml

    This file is gitignored and contains per-user settings that
    override repo-level config values.

    Args:
        repo_root: Path to the repository root

    Returns:
        LoadedConfig with parsed values or defaults if no config found
    """
    config_path = repo_root / ".erk" / "config.local.toml"
    if config_path.exists():
        return _parse_config_file(config_path)

    return LoadedConfig(
        env={},
        post_create_commands=[],
        post_create_shell=None,
        plans_repo=None,
        pool_size=None,
        pool_checkout_commands=[],
        pool_checkout_shell=None,
    )


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
        plans_repo=repo_config.plans_repo,
        pool_size=repo_config.pool_size,  # Pool is repo-level only, no project override
        pool_checkout_commands=repo_config.pool_checkout_commands,
        pool_checkout_shell=repo_config.pool_checkout_shell,
    )


def merge_configs_with_local(
    *,
    base_config: LoadedConfig,
    local_config: LoadedConfig,
) -> LoadedConfig:
    """Merge base config with per-user local config.

    Merge rules:
    - env: Local values override base values (dict merge)
    - post_create_commands: Base commands run first, then local (list concat)
    - post_create_shell: Local shell overrides base if set
    - plans_repo: Local overrides base if set
    - pool_size: Local overrides base if set
    - pool_checkout_commands: Base first, then local (list concat)
    - pool_checkout_shell: Local overrides base if set

    Args:
        base_config: Repository-level configuration
        local_config: Per-user local configuration

    Returns:
        Merged LoadedConfig
    """
    return LoadedConfig(
        env={**base_config.env, **local_config.env},
        post_create_commands=base_config.post_create_commands + local_config.post_create_commands,
        post_create_shell=(
            local_config.post_create_shell
            if local_config.post_create_shell is not None
            else base_config.post_create_shell
        ),
        plans_repo=(
            local_config.plans_repo
            if local_config.plans_repo is not None
            else base_config.plans_repo
        ),
        pool_size=(
            local_config.pool_size if local_config.pool_size is not None else base_config.pool_size
        ),
        pool_checkout_commands=(
            base_config.pool_checkout_commands + local_config.pool_checkout_commands
        ),
        pool_checkout_shell=(
            local_config.pool_checkout_shell
            if local_config.pool_checkout_shell is not None
            else base_config.pool_checkout_shell
        ),
    )
