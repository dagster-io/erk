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


def _write_pool_max_slots(repo_root: Path, max_slots: int) -> None:
    """Write pool.max_slots to .erk/config.toml.

    Creates or updates the [pool] section with max_slots setting.
    Preserves existing formatting and comments using tomlkit.

    Args:
        repo_root: Path to the repository root directory
        max_slots: Maximum number of pool slots to configure
    """
    config_dir = repo_root / ".erk"
    config_path = config_dir / "config.toml"

    # Ensure .erk directory exists
    if not config_dir.exists():
        config_dir.mkdir(parents=True)

    # Load existing file or create new document
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    # Ensure [pool] section exists
    if "pool" not in doc:
        assert isinstance(doc, MutableMapping), f"Expected MutableMapping, got {type(doc)}"
        cast(dict[str, Any], doc)["pool"] = tomlkit.table()

    # Set max_slots value
    pool_section = doc["pool"]
    assert isinstance(pool_section, MutableMapping), type(pool_section)
    cast(dict[str, Any], pool_section)["max_slots"] = max_slots

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
        ("env.<name>", "Environment variables to set in worktrees"),
        ("post_create.shell", "Shell to use for post-create commands"),
        ("post_create.commands", "Commands to run after creating a worktree"),
    ]
    formatter.write_dl(repo_keys)
    user_output(formatter.getvalue().rstrip())


def _format_config_value(value: object) -> str:
    """Format a config value for display."""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


@config_group.command("list")
@click.pass_obj
def config_list(ctx: ErkContext) -> None:
    """Print a list of configuration keys and values."""
    # Display global config
    user_output(click.style("Global configuration:", bold=True))
    if ctx.global_config:
        for key in get_global_config_keys():
            value = getattr(ctx.global_config, key)
            user_output(f"  {key}={_format_config_value(value)}")
    else:
        user_output("  (not configured - run 'erk init' to create)")

    # Display local config
    user_output(click.style("\nRepository configuration:", bold=True))
    from erk.core.repo_discovery import NoRepoSentinel

    if isinstance(ctx.repo, NoRepoSentinel):
        user_output("  (not in a git repository)")
    else:
        trunk_branch = ctx.trunk_branch
        cfg = ctx.local_config
        if trunk_branch:
            user_output(f"  trunk-branch={trunk_branch}")
        if cfg.pool_size is not None:
            user_output(f"  pool.max_slots={cfg.pool_size}")
        else:
            user_output(f"  pool.max_slots={DEFAULT_POOL_SIZE} (default)")
        if cfg.env:
            for key, value in cfg.env.items():
                user_output(f"  env.{key}={value}")
        if cfg.post_create_shell:
            user_output(f"  post_create.shell={cfg.post_create_shell}")
        if cfg.post_create_commands:
            user_output(f"  post_create.commands={cfg.post_create_commands}")

        has_no_custom_config = (
            not trunk_branch
            and cfg.pool_size is None
            and not cfg.env
            and not cfg.post_create_shell
            and not cfg.post_create_commands
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

    if isinstance(ctx.repo, NoRepoSentinel):
        user_output("Not in a git repository")
        raise SystemExit(1)

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
        if value.lower() not in ("true", "false"):
            user_output(f"Invalid boolean value: {value}")
            raise SystemExit(1)
        return value.lower() == "true"
    if current_type is Path or key == "erk_root":
        return Path(value).expanduser().resolve()
    return value


@config_group.command("set")
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
@click.pass_obj
def config_set(ctx: ErkContext, key: str, value: str) -> None:
    """Update configuration with a value for the given key."""
    # Parse key into parts
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in get_global_config_keys():
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

    # Handle pool.max_slots
    if parts[0] == "pool" and len(parts) == 2 and parts[1] == "max_slots":
        repo = discover_repo_context(ctx, Path.cwd())

        # Validate value is a positive integer
        if not value.isdigit() or int(value) < 1:
            user_output(f"Invalid value: {value}. pool.max_slots must be a positive integer.")
            raise SystemExit(1)

        pool_size = int(value)
        _write_pool_max_slots(repo.root, pool_size)
        user_output(f"Set pool.max_slots={pool_size}")
        return

    # Other repo config keys not implemented yet
    user_output(f"Invalid key: {key}")
    raise SystemExit(1)
