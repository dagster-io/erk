import dataclasses
from pathlib import Path

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.init_utils import (
    add_gitignore_entry,
    discover_presets,
    get_shell_wrapper_content,
    is_repo_named,
    render_config_template,
)
from erk.core.kit_installer import install_erk_kits
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.shell import Shell
from erk.core.version_check import check_and_sync_kits


def detect_graphite(shell_ops: Shell) -> bool:
    """Detect if Graphite (gt) is installed and available in PATH."""
    return shell_ops.get_installed_tool_path("gt") is not None


def create_and_save_global_config(
    ctx: ErkContext,
    erk_root: Path,
    shell_setup_complete: bool,
) -> GlobalConfig:
    """Create and save global config, returning the created config."""
    use_graphite = detect_graphite(ctx.shell)
    config = GlobalConfig(
        erk_root=erk_root,
        use_graphite=use_graphite,
        shell_setup_complete=shell_setup_complete,
        show_pr_info=True,
    )
    ctx.config_store.save(config)
    return config


def _add_gitignore_entry_with_prompt(
    content: str, entry: str, prompt_message: str
) -> tuple[str, bool]:
    """Add an entry to gitignore content if not present and user confirms.

    This wrapper adds user interaction to the pure add_gitignore_entry function.

    Args:
        content: Current gitignore content
        entry: Entry to add (e.g., ".env")
        prompt_message: Message to show user when confirming

    Returns:
        Tuple of (updated_content, was_modified)
    """
    # Entry already present
    if entry in content:
        return (content, False)

    # User declined
    if not click.confirm(prompt_message, default=True):
        return (content, False)

    # Use pure function to add entry
    new_content = add_gitignore_entry(content, entry)
    return (new_content, True)


def print_shell_setup_instructions(
    shell: str, rc_file: Path, completion_line: str, wrapper_content: str
) -> None:
    """Print formatted shell integration setup instructions for manual installation.

    Args:
        shell: The shell type (e.g., "zsh", "bash", "fish")
        rc_file: Path to the shell's rc file (e.g., ~/.zshrc)
        completion_line: The completion command to add (e.g., "source <(erk completion zsh)")
        wrapper_content: The full wrapper function content to add
    """
    user_output("\n" + "━" * 60)
    user_output("Shell Integration Setup")
    user_output("━" * 60)
    user_output(f"\nDetected shell: {shell} ({rc_file})")
    user_output("\nAdd the following to your rc file:\n")
    user_output("# Erk completion")
    user_output(f"{completion_line}\n")
    user_output("# Erk shell integration")
    user_output(wrapper_content)
    user_output("\nThen reload your shell:")
    user_output(f"  source {rc_file}")
    user_output("━" * 60)


def perform_shell_setup(shell_ops: Shell) -> bool:
    """Print shell integration setup instructions for manual installation.

    Returns True if instructions were printed, False if setup was skipped.
    """
    shell_info = shell_ops.detect_shell()
    if not shell_info:
        user_output("Unable to detect shell. Skipping shell integration setup.")
        return False

    shell, rc_file = shell_info

    # Resolve symlinks to show the real file path in instructions
    if rc_file.exists():
        rc_file = rc_file.resolve()

    user_output(f"\nDetected shell: {shell}")
    user_output("Shell integration provides:")
    user_output("  - Tab completion for erk commands")
    user_output("  - Automatic worktree activation on 'erk checkout'")

    if not click.confirm("\nShow shell integration setup instructions?", default=True):
        user_output("Skipping shell integration. You can run 'erk init --shell' later.")
        return False

    # Generate the instructions
    completion_line = f"source <(erk completion {shell})"
    shell_integration_dir = Path(__file__).parent.parent / "shell_integration"
    wrapper_content = get_shell_wrapper_content(shell_integration_dir, shell)

    # Print the formatted instructions
    print_shell_setup_instructions(shell, rc_file, completion_line, wrapper_content)

    return True


def _get_presets_dir() -> Path:
    """Get the path to the presets directory."""
    return Path(__file__).parent.parent / "presets"


@click.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing repo config if present.")
@click.option(
    "--preset",
    type=str,
    default="auto",
    help=(
        "Config template to use. 'auto' detects preset based on repo characteristics. "
        f"Available: auto, {', '.join(discover_presets(_get_presets_dir()))}."
    ),
)
@click.option(
    "--list-presets",
    is_flag=True,
    help="List available presets and exit.",
)
@click.option(
    "--repo",
    is_flag=True,
    help="Initialize repository-level config only (skip global config setup).",
)
@click.option(
    "--shell",
    is_flag=True,
    help="Show shell integration setup instructions (completion + auto-activation wrapper).",
)
@click.pass_obj
def init_cmd(
    ctx: ErkContext, force: bool, preset: str, list_presets: bool, repo: bool, shell: bool
) -> None:
    """Initialize erk for this repo and scaffold config.toml."""

    # Handle --shell flag: only do shell setup
    if shell:
        if ctx.global_config is None:
            config_path = ctx.config_store.path()
            user_output(f"Global config not found at {config_path}")
            user_output("Run 'erk init' without --shell to create global config first.")
            raise SystemExit(1)

        setup_complete = perform_shell_setup(ctx.shell)
        if setup_complete:
            # Show what we're about to write
            config_path = ctx.config_store.path()
            user_output("\nTo remember that shell setup is complete, erk needs to update:")
            user_output(f"  {config_path}")

            if not click.confirm("Proceed with updating global config?", default=True):
                user_output("\nShell integration instructions were displayed above.")
                user_output("Run 'erk init --shell' again to save this preference.")
                return

            # Update global config with shell_setup_complete=True
            new_config = GlobalConfig(
                erk_root=ctx.global_config.erk_root,
                use_graphite=ctx.global_config.use_graphite,
                shell_setup_complete=True,
                show_pr_info=ctx.global_config.show_pr_info,
            )
            try:
                ctx.config_store.save(new_config)
                user_output(click.style("✓", fg="green") + " Global config updated")
            except PermissionError as e:
                user_output(click.style("\n❌ Error: ", fg="red") + "Could not save global config")
                user_output(str(e))
                user_output("\nShell integration instructions were displayed above.")
                user_output("You can use them now - erk just couldn't save this preference.")
                raise SystemExit(1) from e
        return

    # Discover available presets on demand
    presets_dir = _get_presets_dir()
    available_presets = discover_presets(presets_dir)
    valid_choices = ["auto"] + available_presets

    # Handle --list-presets flag
    if list_presets:
        user_output("Available presets:")
        for p in available_presets:
            user_output(f"  - {p}")
        return

    # Validate preset choice
    if preset not in valid_choices:
        user_output(f"Invalid preset '{preset}'. Available options: {', '.join(valid_choices)}")
        raise SystemExit(1)

    # Track if this is the first time init is run
    first_time_init = False

    # Check for global config first (unless --repo flag is set)
    if not repo and not ctx.config_store.exists():
        first_time_init = True
        config_path = ctx.config_store.path()
        user_output(f"Global config not found at {config_path}")
        user_output("Please provide the path where you want to store all worktrees.")
        user_output("(This directory will contain subdirectories for each repository)")
        erk_root = click.prompt("Worktrees root directory", type=Path)
        erk_root = erk_root.expanduser().resolve()
        config = create_and_save_global_config(ctx, erk_root, shell_setup_complete=False)
        # Update context with newly created config
        ctx = dataclasses.replace(ctx, global_config=config)
        user_output(f"Created global config at {config_path}")
        # Show graphite status on first init
        has_graphite = detect_graphite(ctx.shell)
        if has_graphite:
            user_output("Graphite (gt) detected - will use 'gt create' for new branches")
        else:
            user_output("Graphite (gt) not detected - will use 'git' for branch creation")

    # Check for version changes and sync kits if needed (for existing repos)
    if not first_time_init:
        # Discover repo context to get repo root
        repo_context = discover_repo_context(ctx, ctx.cwd)
        check_and_sync_kits(repo_context.root)

    # When --repo is set, verify that global config exists
    if repo and not ctx.config_store.exists():
        config_path = ctx.config_store.path()
        user_output(f"Global config not found at {config_path}")
        user_output("Run 'erk init' without --repo to create global config first.")
        raise SystemExit(1)

    # Now proceed with repo-specific setup
    repo_context = discover_repo_context(ctx, ctx.cwd)

    # Determine config path based on --repo flag
    if repo:
        # Repository-level config goes in repo root
        cfg_path = repo_context.root / "config.toml"
    else:
        # Worktree-level config goes in erks_dir
        repo_dir = ensure_erk_metadata_dir(repo_context)
        cfg_path = repo_dir / "config.toml"

    if cfg_path.exists() and not force:
        user_output(f"Config already exists: {cfg_path}. Use --force to overwrite.")
        raise SystemExit(1)

    effective_preset: str | None
    choice = preset.lower()
    if choice == "auto":
        effective_preset = "dagster" if is_repo_named(repo_context.root, "dagster") else "generic"
    else:
        effective_preset = choice

    content = render_config_template(presets_dir, effective_preset)
    cfg_path.write_text(content, encoding="utf-8")
    user_output(f"Wrote {cfg_path}")

    # Install Claude Code kits (first-time init only)
    if first_time_init and ctx.global_config is not None:
        has_graphite = ctx.global_config.use_graphite
        install_erk_kits(repo_context.root, use_graphite=has_graphite)

    # Check for .gitignore and add .env
    gitignore_path = repo_context.root / ".gitignore"
    if not gitignore_path.exists():
        # Early return: no gitignore file
        pass
    else:
        gitignore_content = gitignore_path.read_text(encoding="utf-8")

        # Add .env
        gitignore_content, env_added = _add_gitignore_entry_with_prompt(
            gitignore_content,
            ".env",
            "Add .env to .gitignore?",
        )

        # Write if modified
        if env_added:
            gitignore_path.write_text(gitignore_content, encoding="utf-8")
            user_output(f"Updated {gitignore_path}")

    # On first-time init, offer shell setup if not already completed
    if first_time_init:
        # Reload global config after creating it
        fresh_config = ctx.config_store.load()
        if not fresh_config.shell_setup_complete:
            setup_complete = perform_shell_setup(ctx.shell)
            if setup_complete:
                # Show what we're about to write
                config_path = ctx.config_store.path()
                user_output("\nTo remember that shell setup is complete, erk needs to update:")
                user_output(f"  {config_path}")

                if not click.confirm("Proceed with updating global config?", default=True):
                    user_output("\nShell integration instructions were displayed above.")
                    user_output("Run 'erk init --shell' again to save this preference.")
                else:
                    # Update global config with shell_setup_complete=True
                    new_config = GlobalConfig(
                        erk_root=fresh_config.erk_root,
                        use_graphite=fresh_config.use_graphite,
                        shell_setup_complete=True,
                        show_pr_info=fresh_config.show_pr_info,
                    )
                    try:
                        ctx.config_store.save(new_config)
                        user_output(click.style("✓", fg="green") + " Global config updated")
                    except PermissionError as e:
                        error_msg = "Could not save global config"
                        user_output(click.style("\n❌ Error: ", fg="red") + error_msg)
                        user_output(str(e))
                        user_output("\nShell integration instructions were displayed above.")
                        msg = "You can use them now - erk just couldn't save this preference."
                        user_output(msg)
