import subprocess
from pathlib import Path

import click
from erk_shared.output.output import machine_output, user_output

from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext, write_trunk_to_pyproject


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


@click.group("config")
def config_group() -> None:
    """Manage erk configuration."""


@config_group.command("list")
@click.pass_obj
def config_list(ctx: ErkContext) -> None:
    """Print a list of configuration keys and values."""
    # Display global config
    user_output(click.style("Global configuration:", bold=True))
    if ctx.global_config:
        user_output(f"  erk_root={ctx.global_config.erk_root}")
        user_output(f"  use_graphite={str(ctx.global_config.use_graphite).lower()}")
        user_output(f"  show_pr_info={str(ctx.global_config.show_pr_info).lower()}")
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
        if cfg.env:
            for key, value in cfg.env.items():
                user_output(f"  env.{key}={value}")
        if cfg.post_create_shell:
            user_output(f"  post_create.shell={cfg.post_create_shell}")
        if cfg.post_create_commands:
            user_output(f"  post_create.commands={cfg.post_create_commands}")

        has_no_config = (
            not trunk_branch
            and not cfg.env
            and not cfg.post_create_shell
            and not cfg.post_create_commands
        )
        if has_no_config:
            user_output("  (no configuration - run 'erk init --repo' to create)")


@config_group.command("get")
@click.argument("key", metavar="KEY")
@click.pass_obj
def config_get(ctx: ErkContext, key: str) -> None:
    """Print the value of a given configuration key."""
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in ("erk_root", "use_graphite", "show_pr_info"):
        global_config = Ensure.not_none(
            ctx.global_config, f"Global config not found at {ctx.config_store.path()}"
        )

        if parts[0] == "erk_root":
            machine_output(str(global_config.erk_root))
        elif parts[0] == "use_graphite":
            machine_output(str(global_config.use_graphite).lower())
        elif parts[0] == "show_pr_info":
            machine_output(str(global_config.show_pr_info).lower())
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

    user_output(f"Invalid key: {key}")
    raise SystemExit(1)


@config_group.command("set")
@click.argument("key", metavar="KEY")
@click.argument("value", metavar="VALUE")
@click.pass_obj
def config_set(ctx: ErkContext, key: str, value: str) -> None:
    """Update configuration with a value for the given key."""
    # Parse key into parts
    parts = key.split(".")

    # Handle global config keys
    if parts[0] in ("erk_root", "use_graphite", "show_pr_info"):
        global_config = Ensure.not_none(
            ctx.global_config,
            f"Global config not found at {ctx.config_store.path()}. Run 'erk init' to create it.",
        )

        # Create new config with updated value
        if parts[0] == "erk_root":
            new_config = GlobalConfig(
                erk_root=Path(value).expanduser().resolve(),
                use_graphite=global_config.use_graphite,
                shell_setup_complete=global_config.shell_setup_complete,
                show_pr_info=global_config.show_pr_info,
            )
        elif parts[0] == "use_graphite":
            if value.lower() not in ("true", "false"):
                user_output(f"Invalid boolean value: {value}")
                raise SystemExit(1)
            new_config = GlobalConfig(
                erk_root=global_config.erk_root,
                use_graphite=value.lower() == "true",
                shell_setup_complete=global_config.shell_setup_complete,
                show_pr_info=global_config.show_pr_info,
            )
        elif parts[0] == "show_pr_info":
            if value.lower() not in ("true", "false"):
                user_output(f"Invalid boolean value: {value}")
                raise SystemExit(1)
            new_config = GlobalConfig(
                erk_root=global_config.erk_root,
                use_graphite=global_config.use_graphite,
                shell_setup_complete=global_config.shell_setup_complete,
                show_pr_info=value.lower() == "true",
            )
        else:
            user_output(f"Invalid key: {key}")
            raise SystemExit(1)

        ctx.config_store.save(new_config)
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
        if result.returncode != 0:
            user_output(
                f"Error: Branch '{value}' does not exist in repository.\n"
                f"Create the branch first before configuring it as trunk."
            )
            raise SystemExit(1)

        # Write configuration
        write_trunk_to_pyproject(repo.root, value)
        user_output(f"Set trunk-branch={value}")
        return

    # Other repo config keys not implemented yet
    user_output("Setting repo config keys not yet implemented")
    raise SystemExit(1)
