"""Local init command - set up local developer environment.

This command performs local developer setup:
- Checks if repo is erk-ified (prompts to run `erk project init` if not)
- Checks version compatibility and prompts for upgrade if needed
- Sets up global config if needed
- Optionally sets up shell integration
- Saves local init state
"""

import dataclasses
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.init_utils import get_shell_wrapper_content
from erk.core.local_state import create_local_init_state, load_local_state, save_local_state
from erk.core.release_notes import get_current_version
from erk.core.shell import Shell
from erk.core.version_check import get_required_version, is_version_mismatch
from erk_shared.output.output import user_output


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
        github_planning=True,
    )
    ctx.config_store.save(config)
    return config


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
    user_output("  - Automatic worktree activation on 'erk br co'")

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


def _check_version_compatibility(
    repo_root: Path, installed_version: str
) -> tuple[bool, str | None]:
    """Check if installed version is compatible with required version.

    Args:
        repo_root: Path to the repository root
        installed_version: Currently installed erk version

    Returns:
        Tuple of (compatible, required_version)
        - compatible: True if versions match or no version file exists
        - required_version: Required version string or None if no file
    """
    required_version = get_required_version(repo_root)
    if required_version is None:
        return (True, None)

    if is_version_mismatch(installed_version, required_version):
        return (False, required_version)

    return (True, required_version)


@click.command("init")
@click.option(
    "--shell",
    is_flag=True,
    help="Show shell integration setup instructions (completion + auto-activation wrapper).",
)
@click.pass_obj
def init_cmd(
    ctx: ErkContext,
    shell: bool,
) -> None:
    """Set up local erk development environment.

    This command performs local developer setup for an erk-ified repository:

    1. Checks if the repository has been initialized with 'erk project init'
    2. Verifies version compatibility with the repository's required version
    3. Sets up global configuration (erk root, graphite detection)
    4. Optionally configures shell integration

    For repo admins setting up erk in a new project, use 'erk project init' instead.

    Example:
        cd /path/to/erk-ified-repo
        erk init
    """
    installed_version = get_current_version()

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
                github_planning=ctx.global_config.github_planning,
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

    # Track if this is the first time init is run (for shell setup offer)
    first_time_init = False

    # Check for global config first
    if not ctx.config_store.exists():
        first_time_init = True
        config_path = ctx.config_store.path()
        user_output(f"Global config not found at {config_path}")
        user_output("Please provide the path for your .erk folder.")
        user_output("(This directory will contain worktrees for each repository)")
        default_erk_root = Path.home() / ".erk"
        erk_root = click.prompt(".erk folder", type=Path, default=str(default_erk_root))
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

    # Discover repo context
    repo_context = discover_repo_context(ctx, ctx.cwd)

    # Check if repo is erk-ified
    erk_dir = repo_context.root / ".erk"
    if not erk_dir.exists():
        user_output("")
        user_output(click.style("⚠️  Repository not erk-ified", fg="yellow"))
        user_output("")
        user_output("This repository hasn't been set up for erk yet.")
        user_output("For repo admins: run 'erk project init' to erk-ify this repository.")
        user_output("")
        user_output("If you're a developer on an already erk-ified repo, make sure you're")
        user_output("in the correct directory and have pulled the latest changes.")
        raise SystemExit(1)

    # Check version compatibility
    compatible, required_version = _check_version_compatibility(
        repo_context.root, installed_version
    )

    if not compatible and required_version is not None:
        user_output("")
        user_output(click.style("⚠️  Version mismatch", fg="yellow"))
        user_output(f"   Installed: {installed_version}")
        user_output(f"   Required:  {required_version}")
        user_output("")

        from packaging.version import Version

        installed_v = Version(installed_version)
        required_v = Version(required_version)

        if installed_v < required_v:
            # User needs to upgrade their local erk
            user_output("Your erk is older than the project requires.")
            user_output("Run: uv tool upgrade erk")
        else:
            # User has newer erk - project may need upgrading
            user_output("Your erk is newer than the project requires.")
            user_output("If you're the project maintainer, run: erk project upgrade")
            user_output(
                "Otherwise, you may need to downgrade: uv tool install erk@{required_version}"
            )

        raise SystemExit(1)

    # Check local init state
    local_state = load_local_state(repo_context.root)
    if local_state is not None:
        # Already initialized
        if local_state.initialized_version == installed_version:
            user_output(click.style("✓ ", fg="green") + "Local environment already initialized")
            user_output(f"  Version: {installed_version}")
            return
        else:
            old_ver = local_state.initialized_version
            user_output(f"Updating local init state from {old_ver} to {installed_version}")

    # Save local init state
    new_state = create_local_init_state(installed_version)
    save_local_state(repo_context.root, new_state)
    user_output(
        click.style("✓ ", fg="green") + f"Local environment initialized (v{installed_version})"
    )

    # On first-time init, offer shell setup if not already completed
    if first_time_init:
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
                        github_planning=fresh_config.github_planning,
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
