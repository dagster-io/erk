import subprocess
from collections.abc import MutableMapping
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Any, cast

import click
import tomlkit

from erk.cli.commands.slot.common import DEFAULT_POOL_SIZE
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext, write_trunk_to_pyproject
from erk_shared.context.types import GlobalConfig
from erk_shared.output.output import machine_output, user_output


@cache
def get_global_config_keys() -> dict[str, str]:
    """Get user-exposed global config keys with descriptions.

    Order determines display order in 'erk config list'.
    shell_setup_complete is internal and not exposed.
    """
    return {
        "erk_root": "Root directory for erk data (~/.erk by default)",
        "use_graphite": "Enable Graphite integration for stack management",
        "github_planning": "Enable GitHub issues integration for planning",
        "fix_conflicts_require_dangerous_flag": "Require --dangerous flag for fix-conflicts",
        "show_hidden_commands": "Show deprecated/hidden commands in help output",
        "prompt_learn_on_land": "Prompt about running learn before landing plan PRs",
        "shell_integration": "Enable auto-navigation shell integration (opt-in)",
    }


@cache
def get_overridable_global_keys() -> set[str]:
    """Get keys that can be set at global, repo, or local level.

    These keys can be overridden per-repo or per-user:
    - Global: `erk config set <key> <value>`
    - Repo: `erk config set --repo <key> <value>`
    - Local: `erk config set --local <key> <value>`

    Override chain: Global < Repo < Local
    """
    return {
        "prompt_learn_on_land",
        "fix_conflicts_require_dangerous_flag",
        "show_hidden_commands",
        "use_graphite",
        "github_planning",
        "shell_integration",
    }


@cache
def get_global_only_keys() -> set[str]:
    """Get keys that can ONLY be set at global level.

    These keys don't make sense at repo or local level.
    """
    return {
        "erk_root",
    }


def _get_env_value(cfg: LoadedConfig, parts: list[str], key: str) -> None:
    """Handle env.* configuration keys.

    Prints the value or exits with error if key not found.
    """
    Ensure.invariant(len(parts) == 2, f"Invalid key: {key}")
    Ensure.invariant(parts[1] in cfg.env, f"Key not found: {key}")

    machine_output(cfg.env[parts[1]])


def _get_post_create_value(cfg: LoadedConfig, parts: list[str], key: str) -> None:
    """Handle post_create.* configuration keys.

    Prints the value or exits with error if key not found.
    """
    Ensure.invariant(len(parts) == 2, f"Invalid key: {key}")

    # Handle shell subkey
    if parts[1] == "shell":
        Ensure.truthy(cfg.post_create_shell, f"Key not found: {key}")
        machine_output(cfg.post_create_shell)
        return

    # Handle commands subkey
    if parts[1] == "commands":
        for cmd in cfg.post_create_commands:
            machine_output(cmd)
        return

    # Unknown subkey
    Ensure.invariant(False, f"Key not found: {key}")


def _write_to_repo_config(
    *,
    repo_root: Path,
    key: str,
    value: object,
    local: bool,
) -> None:
    """Write a value to repo config (config.toml or config.local.toml).

    Handles nested keys like "pool.max_slots", "env.MY_VAR", "post_create.shell".
    Creates file if doesn't exist. Preserves existing formatting with tomlkit.

    Args:
        repo_root: Path to the repository root directory
        key: Dot-separated key path (e.g., "pool.max_slots", "env.FOO")
        value: Value to write (int, str, list, etc.)
        local: If True, write to config.local.toml; otherwise config.toml
    """
    config_dir = repo_root / ".erk"
    config_filename = "config.local.toml" if local else "config.toml"
    config_path = config_dir / config_filename

    # Ensure .erk directory exists
    if not config_dir.exists():
        config_dir.mkdir(parents=True)

    # Load existing file or create new document
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    # Parse key into parts (e.g., "pool.max_slots" -> ["pool", "max_slots"])
    parts = key.split(".")

    # Navigate/create sections for nested keys
    current: MutableMapping[str, Any] = cast(MutableMapping[str, Any], doc)
    for section_key in parts[:-1]:
        if section_key not in current:
            assert isinstance(current, MutableMapping), type(current)
            current[section_key] = tomlkit.table()
        section = current[section_key]
        assert isinstance(section, MutableMapping), type(section)
        current = section

    # Set the final value
    final_key = parts[-1]
    current[final_key] = value

    # Write back to file
    with config_path.open("w", encoding="utf-8") as f:
        tomlkit.dump(doc, f)


@click.group("config")
def config_group() -> None:
    """Manage erk configuration."""


@config_group.command("keys")
def config_keys() -> None:
    """List all available configuration keys with descriptions."""
    formatter = click.HelpFormatter()

    # Global config section
    user_output(click.style("Global configuration keys:", bold=True))
    rows = list(get_global_config_keys().items())
    formatter.write_dl(rows)
    user_output(formatter.getvalue().rstrip())

    user_output("")

    # Repository config section
    user_output(click.style("Repository configuration keys:", bold=True))
    formatter = click.HelpFormatter()
    repo_keys = [
        ("trunk-branch", "The main/master branch name for the repository"),
        ("pool.max_slots", "Maximum number of pool slots for worktree pool"),
        ("pool.checkout.shell", "Shell to use for pool checkout commands"),
        ("pool.checkout.commands", "Commands to run after checking out a worktree from pool"),
        ("env.<name>", "Environment variables to set in worktrees"),
        ("post_create.shell", "Shell to use for post-create commands"),
        ("post_create.commands", "Commands to run after creating a worktree"),
        ("plans.repo", "Repository for storing plan issues (owner/repo format)"),
    ]
    formatter.write_dl(repo_keys)
    user_output(formatter.getvalue().rstrip())


def _format_config_value(value: object) -> str:
    """Format a config value for display."""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _get_overridable_key_source(
    key: str,
    *,
    repo_config: LoadedConfig,
    local_config: LoadedConfig,
) -> str:
    """Determine source annotation for an overridable global key.

    Returns empty string for global, ' (repo)' for repo, ' (local)' for local.
    """
    local_value = getattr(local_config, key, None)
    repo_value = getattr(repo_config, key, None)

    if local_value is not None:
        return " (local)"
    if repo_value is not None:
        return " (repo)"
    return ""


def _get_effective_value_for_overridable_key(
    key: str,
    *,
    global_config: GlobalConfig | None,
    merged_config: LoadedConfig,
) -> object:
    """Get effective value for an overridable key from the override chain."""
    merged_value = getattr(merged_config, key, None)
    if merged_value is not None:
        return merged_value
    if global_config is not None:
        return getattr(global_config, key, None)
    return None


@config_group.command("list")
@click.pass_obj
def config_list(ctx: ErkContext) -> None:
    """Print a list of configuration keys and values."""
    from erk.cli.config import load_config, load_local_config
    from erk.core.repo_discovery import NoRepoSentinel

    # Load repo and local configs separately for source detection
    repo_only_config: LoadedConfig | None = None
    local_only_config: LoadedConfig | None = None
    if not isinstance(ctx.repo, NoRepoSentinel):
        repo_only_config = load_config(ctx.repo.root)
        local_only_config = load_local_config(ctx.repo.root)

    # Display global config
    user_output(click.style("Global configuration:", bold=True))
    if ctx.global_config:
        overridable_keys = get_overridable_global_keys()
        for key in get_global_config_keys():
            # For overridable keys, show effective value with source annotation
            if key in overridable_keys and repo_only_config and local_only_config:
                effective_value = _get_effective_value_for_overridable_key(
                    key,
                    global_config=ctx.global_config,
                    merged_config=ctx.local_config,
                )
                source = _get_overridable_key_source(
                    key,
                    repo_config=repo_only_config,
                    local_config=local_only_config,
                )
                user_output(f"  {key}={_format_config_value(effective_value)}{source}")
            else:
                # Non-overridable key or not in repo - show global value
                value = getattr(ctx.global_config, key)
                user_output(f"  {key}={_format_config_value(value)}")

        # Interactive Claude configuration
        ic = ctx.global_config.interactive_claude
        user_output(click.style("\nInteractive Claude configuration:", bold=True))
        if ic.model:
            user_output(f"  interactive_claude.model={ic.model}")
        user_output(f"  interactive_claude.verbose={_format_config_value(ic.verbose)}")
        user_output(f"  interactive_claude.permission_mode={ic.permission_mode}")
        user_output(f"  interactive_claude.dangerous={_format_config_value(ic.dangerous)}")
        user_output(
            f"  interactive_claude.allow_dangerous={_format_config_value(ic.allow_dangerous)}"
        )
    else:
        user_output("  (not configured - run 'erk init' to create)")

    # Display local config
    user_output(click.style("\nRepository configuration:", bold=True))

    if isinstance(ctx.repo, NoRepoSentinel):
        user_output("  (not in a git repository)")
    else:
        assert repo_only_config is not None
        assert local_only_config is not None

        trunk_branch = ctx.trunk_branch
        cfg = ctx.local_config
        if trunk_branch:
            user_output(f"  trunk-branch={trunk_branch}")

        # pool.max_slots with source annotation
        if cfg.pool_size is not None:
            pool_source = (
                " (local)"
                if local_only_config.pool_size is not None
                else (" (repo)" if repo_only_config.pool_size is not None else "")
            )
            user_output(f"  pool.max_slots={cfg.pool_size}{pool_source}")
        else:
            user_output(f"  pool.max_slots={DEFAULT_POOL_SIZE} (default)")

        # env with source annotations
        if cfg.env:
            for env_key, value in cfg.env.items():
                source = " (local)" if env_key in local_only_config.env else ""
                user_output(f"  env.{env_key}={value}{source}")

        # post_create.shell with source annotation
        if cfg.post_create_shell:
            shell_source = " (local)" if local_only_config.post_create_shell is not None else ""
            user_output(f"  post_create.shell={cfg.post_create_shell}{shell_source}")

        # post_create.commands with source annotation
        if cfg.post_create_commands:
            # Commands are concatenated, so source detection is more complex
            # Just show if there are any local commands
            has_local_commands = bool(local_only_config.post_create_commands)
            cmds_source = " (includes local)" if has_local_commands else ""
            user_output(f"  post_create.commands={cfg.post_create_commands}{cmds_source}")

        # pool.checkout.shell with source annotation
        if cfg.pool_checkout_shell:
            checkout_shell_source = (
                " (local)" if local_only_config.pool_checkout_shell is not None else ""
            )
            user_output(f"  pool.checkout.shell={cfg.pool_checkout_shell}{checkout_shell_source}")

        # pool.checkout.commands with source annotation
        if cfg.pool_checkout_commands:
            has_local_checkout_commands = bool(local_only_config.pool_checkout_commands)
            checkout_cmds_source = " (includes local)" if has_local_checkout_commands else ""
            user_output(
                f"  pool.checkout.commands={cfg.pool_checkout_commands}{checkout_cmds_source}"
            )

        # plans.repo with source annotation
        if cfg.plans_repo:
            plans_repo_source = " (local)" if local_only_config.plans_repo is not None else ""
            user_output(f"  plans.repo={cfg.plans_repo}{plans_repo_source}")

        has_no_custom_config = (
            not trunk_branch
            and cfg.pool_size is None
            and not cfg.env
            and not cfg.post_create_shell
            and not cfg.post_create_commands
            and not cfg.pool_checkout_shell
            and not cfg.pool_checkout_commands
            and not cfg.plans_repo
        )
        if has_no_custom_config:
            user_output("  (no custom configuration - run 'erk init' to create)")


@config_group.command("get")
@click.argument("key", metavar="KEY")
@click.pass_obj
def config_get(ctx: ErkContext, key: str) -> None:
    """Print the value of a given configuration key."""
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in get_global_config_keys():
        global_config = Ensure.not_none(
            ctx.global_config, f"Global config not found at {ctx.erk_installation.config_path()}"
        )
        value = getattr(global_config, parts[0])
        machine_output(_format_config_value(value))
        return

    # Handle repo config keys
    from erk.core.repo_discovery import NoRepoSentinel

    Ensure.invariant(
        not isinstance(ctx.repo, NoRepoSentinel),
        "Not in a git repository",
    )

    if parts[0] == "trunk-branch":
        trunk_branch = ctx.trunk_branch
        if trunk_branch:
            machine_output(trunk_branch)
        else:
            user_output("not configured (will auto-detect)")
        return

    cfg = ctx.local_config

    if parts[0] == "env":
        _get_env_value(cfg, parts, key)
        return

    if parts[0] == "post_create":
        _get_post_create_value(cfg, parts, key)
        return

    if parts[0] == "pool" and len(parts) == 2 and parts[1] == "max_slots":
        if cfg.pool_size is not None:
            machine_output(str(cfg.pool_size))
        else:
            machine_output(f"{DEFAULT_POOL_SIZE} (default)")
        return

    user_output(f"Invalid key: {key}")
    raise SystemExit(1)


def _parse_config_value(key: str, value: str, current_type: type) -> object:
    """Parse a string value to the appropriate type for a config key."""
    if current_type is bool:
        Ensure.invariant(
            value.lower() in ("true", "false"),
            f"Invalid boolean value: {value}",
        )
        return value.lower() == "true"
    if current_type is Path or key == "erk_root":
        return Path(value).expanduser().resolve()
    return value


@config_group.command("set")
@click.option("-l", "--local", is_flag=True, help="Write to .erk/config.local.toml instead")
@click.option(
    "-r", "--repo", "repo_flag", is_flag=True, help="Write to .erk/config.toml (repo level)"
)
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
@click.pass_obj
def config_set(ctx: ErkContext, local: bool, repo_flag: bool, key: str, value: str) -> None:
    """Update configuration with a value for the given key."""
    # Validate mutually exclusive flags
    Ensure.invariant(
        not (local and repo_flag),
        "Cannot use both --local and --repo flags",
    )

    # Parse key into parts
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in get_global_config_keys():
        # Check if this key is overridable at repo/local level
        is_overridable = parts[0] in get_overridable_global_keys()

        if local or repo_flag:
            Ensure.invariant(
                is_overridable,
                f"Global key '{key}' cannot be written to local or repo config",
            )

            # Write overridable key to repo or local config
            repo = discover_repo_context(ctx, Path.cwd())

            # Parse as boolean for known boolean keys
            Ensure.invariant(
                value.lower() in ("true", "false"),
                f"Invalid boolean value: {value}",
            )
            parsed_bool = value.lower() == "true"

            _write_to_repo_config(
                repo_root=repo.main_repo_root or repo.root, key=key, value=parsed_bool, local=local
            )
            level_suffix = " (local)" if local else " (repo)"
            user_output(f"Set {key}={value}{level_suffix}")
            return

        # Write to global config (default behavior for global keys)
        config_path = ctx.erk_installation.config_path()
        global_config = Ensure.not_none(
            ctx.global_config,
            f"Global config not found at {config_path}. Run 'erk init' to create it.",
        )

        # Get current value's type and parse new value
        current_value = getattr(global_config, parts[0])
        parsed_value = _parse_config_value(parts[0], value, type(current_value))

        # Create new config with updated value using dataclasses.replace
        new_config = replace(global_config, **{parts[0]: parsed_value})

        ctx.erk_installation.save_config(new_config)
        user_output(f"Set {key}={value}")
        return

    # Handle repo config keys
    if parts[0] == "trunk-branch":
        # trunk-branch lives in pyproject.toml, not erk config
        Ensure.invariant(
            not (local or repo_flag),
            "trunk-branch lives in pyproject.toml. Cannot use --local or --repo flag.",
        )

        # discover_repo_context checks for git repository and raises FileNotFoundError
        repo = discover_repo_context(ctx, Path.cwd())

        # Validate that the branch exists before writing
        result = subprocess.run(
            ["git", "rev-parse", "--verify", value],
            cwd=repo.root,
            capture_output=True,
            text=True,
            check=False,
        )
        Ensure.invariant(
            result.returncode == 0,
            f"Branch '{value}' doesn't exist in repository.\n"
            f"Create the branch first before configuring it as trunk.",
        )

        # Write configuration
        write_trunk_to_pyproject(repo.root, value)
        user_output(f"Set trunk-branch={value}")
        return

    # Handle repo config keys with match
    transformed: object
    match parts:
        case (
            ["env", _]
            | ["post_create", "shell"]
            | ["pool", "checkout", "shell"]
            | ["plans", "repo"]
        ):
            transformed = value
        case ["post_create", "commands"] | ["pool", "checkout", "commands"]:
            transformed = [cmd.strip() for cmd in value.split(",") if cmd.strip()]
        case ["pool", "max_slots"]:
            Ensure.invariant(
                value.isdigit() and int(value) >= 1,
                f"Invalid value: {value}. pool.max_slots must be a positive integer.",
            )
            transformed = int(value)
        case _:
            user_output(f"Invalid key: {key}")
            raise SystemExit(1)

    repo = discover_repo_context(ctx, Path.cwd())
    _write_to_repo_config(
        repo_root=repo.main_repo_root or repo.root, key=key, value=transformed, local=local
    )
    level_suffix = " (local)" if local else (" (repo)" if repo_flag else "")
    user_output(f"Set {key}={transformed}{level_suffix}")
