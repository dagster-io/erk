import dataclasses
import json
from pathlib import Path

import click

from erk.artifacts.sync import sync_artifacts
from erk.cli.core import discover_repo_context
from erk.core.claude_settings import (
    ERK_PERMISSION,
    NoBackupCreated,
    StatuslineNotConfigured,
    add_erk_hooks,
    add_erk_permission,
    add_erk_statusline,
    get_erk_statusline_command,
    get_global_claude_settings_path,
    get_repo_claude_settings_path,
    get_statusline_config,
    has_erk_permission,
    has_erk_statusline,
    has_exit_plan_hook,
    has_user_prompt_hook,
    read_claude_settings,
    write_claude_settings,
)
from erk.core.context import ErkContext
from erk.core.init_utils import (
    add_gitignore_entry,
    discover_presets,
    get_shell_wrapper_content,
    has_shell_integration_in_rc,
    is_repo_erk_ified,
    is_repo_named,
    render_config_template,
)
from erk.core.repo_discovery import (
    NoRepoSentinel,
    discover_repo_or_sentinel,
    ensure_erk_metadata_dir,
)
from erk.core.shell import Shell
from erk_shared.context.types import GlobalConfig
from erk_shared.git.real import RealGit
from erk_shared.output.output import user_confirm, user_output


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
    ctx.erk_installation.save_config(config)
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


def _create_prompt_hooks_directory(repo_root: Path) -> None:
    """Create .erk/prompt-hooks/ directory and install README.

    Args:
        repo_root: Path to the repository root
    """
    prompt_hooks_dir = repo_root / ".erk" / "prompt-hooks"
    prompt_hooks_dir.mkdir(parents=True, exist_ok=True)

    # Install README template
    template_path = Path(__file__).parent.parent / "prompt_hooks_templates" / "README.md"
    readme_path = prompt_hooks_dir / "README.md"

    if template_path.exists():
        readme_content = template_path.read_text(encoding="utf-8")
        readme_path.write_text(readme_content, encoding="utf-8")
        user_output(click.style("✓", fg="green") + " Created prompt hooks directory")
        user_output("  See .erk/prompt-hooks/README.md for available hooks")
    else:
        # Fallback: create directory but warn about missing template
        user_output(
            click.style("⚠️", fg="yellow") + " Created .erk/prompt-hooks/ (template not found)"
        )


def _run_gitignore_prompts(repo_root: Path) -> None:
    """Run interactive prompts for .gitignore entries.

    Offers to add .env, .erk/scratch/, and .impl/ to .gitignore.

    Args:
        repo_root: Path to the repository root
    """
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return

    gitignore_content = gitignore_path.read_text(encoding="utf-8")

    # Add .env
    gitignore_content, env_added = _add_gitignore_entry_with_prompt(
        gitignore_content,
        ".env",
        "Add .env to .gitignore?",
    )

    # Add .erk/scratch/
    gitignore_content, scratch_added = _add_gitignore_entry_with_prompt(
        gitignore_content,
        ".erk/scratch/",
        "Add .erk/scratch/ to .gitignore (session-specific working files)?",
    )

    # Add .impl/
    gitignore_content, impl_added = _add_gitignore_entry_with_prompt(
        gitignore_content,
        ".impl/",
        "Add .impl/ to .gitignore (temporary implementation plans)?",
    )

    # Write if any entry was modified
    if env_added or scratch_added or impl_added:
        gitignore_path.write_text(gitignore_content, encoding="utf-8")
        user_output(f"Updated {gitignore_path}")


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


def _get_presets_dir() -> Path:
    """Get the path to the presets directory."""
    return Path(__file__).parent.parent / "presets"


def offer_claude_permission_setup(repo_root: Path) -> Path | NoBackupCreated:
    """Offer to add erk permission to repo's Claude Code settings.

    This checks if the repo's .claude/settings.json exists and whether the erk
    permission is already configured. If the file exists but permission is missing,
    it prompts the user to add it.

    Args:
        repo_root: Path to the repository root

    Returns:
        Path to backup file if one was created, NoBackupCreated sentinel otherwise.
    """
    settings_path = get_repo_claude_settings_path(repo_root)

    try:
        settings = read_claude_settings(settings_path)
    except json.JSONDecodeError as e:
        warning = click.style("⚠️  Warning: ", fg="yellow")
        user_output(warning + "Invalid JSON in .claude/settings.json")
        user_output(f"   {e}")
        return NoBackupCreated()

    # No settings file - skip silently (repo may not have Claude settings)
    if settings is None:
        return NoBackupCreated()

    # Permission already exists - skip silently
    if has_erk_permission(settings):
        return NoBackupCreated()

    # Offer to add permission
    user_output("\nClaude settings found. The erk permission allows Claude to run")
    user_output("erk commands without prompting for approval each time.")

    if not user_confirm(f"Add {ERK_PERMISSION} to .claude/settings.json?", default=False):
        user_output("Skipped. You can add the permission manually to .claude/settings.json")
        return NoBackupCreated()

    # Add permission
    new_settings = add_erk_permission(settings)

    # Confirm before overwriting
    user_output(f"\nThis will update: {settings_path}")
    if not user_confirm("Proceed with writing changes?", default=False):
        user_output("Skipped. No changes made to settings.json")
        return NoBackupCreated()

    backup_result = write_claude_settings(settings_path, new_settings)
    user_output(click.style("✓", fg="green") + f" Added {ERK_PERMISSION} to {settings_path}")

    # If backup was created, inform user (deletion offered at end of init)
    if not isinstance(backup_result, NoBackupCreated):
        user_output(f"\n📁 Backup created: {backup_result}")
        user_output(f"   To restore: cp {backup_result} {settings_path}")

    return backup_result


def offer_backup_cleanup(backup_path: Path) -> None:
    """Offer to delete a backup file.

    Args:
        backup_path: Path to the backup file to potentially delete
    """
    if click.confirm("Delete backup?", default=True):
        backup_path.unlink()
        user_output(click.style("✓", fg="green") + " Backup deleted")


def offer_claude_hook_setup(repo_root: Path) -> None:
    """Offer to add erk hooks to repo's Claude Code settings.

    This checks if the repo's .claude/settings.json exists and whether the erk
    hooks are already configured. If the file exists but hooks are missing,
    it prompts the user to add them.

    Args:
        repo_root: Path to the repository root
    """
    settings_path = get_repo_claude_settings_path(repo_root)

    try:
        settings = read_claude_settings(settings_path)
    except json.JSONDecodeError as e:
        warning = click.style("⚠️  Warning: ", fg="yellow")
        user_output(warning + "Invalid JSON in .claude/settings.json")
        user_output(f"   {e}")
        return

    # No settings file - will create one
    creating_new_file = settings is None
    if creating_new_file:
        settings = {}
        user_output(f"\nNo .claude/settings.json found. Will create: {settings_path}")

    if has_user_prompt_hook(settings) and has_exit_plan_hook(settings):  # type: ignore[invalid-argument-type]
        user_output(click.style("✓", fg="green") + " Hooks already configured")
        return

    # Explain what hooks do
    user_output("\nErk uses Claude Code hooks for session management and plan tracking.")

    if not user_confirm("Add erk hooks to .claude/settings.json?", default=False):
        user_output("Skipped. You can add hooks later with: erk init --hooks")
        return

    new_settings = add_erk_hooks(settings)  # type: ignore[invalid-argument-type]
    write_claude_settings(settings_path, new_settings)
    user_output(click.style("✓", fg="green") + " Added erk hooks")


def perform_statusline_setup(settings_path: Path | None) -> bool:
    """Configure erk-statusline in global Claude Code settings.

    Reads ~/.claude/settings.json, adds statusLine configuration if not present
    or different, and writes back. Handles edge cases:
    - File doesn't exist: creates it with just statusLine config
    - Already configured with same command: skips
    - Different statusLine command: warns and prompts to overwrite

    Args:
        settings_path: Path to settings.json. If None, uses ~/.claude/settings.json.

    Returns:
        True if status line was configured, False otherwise.
    """
    if settings_path is None:
        settings_path = get_global_claude_settings_path()

    user_output("\n  Configuring Claude Code status line...")

    # Read existing settings (or None if file doesn't exist)
    try:
        settings = read_claude_settings(settings_path)
    except json.JSONDecodeError as e:
        warning = click.style("⚠️  Warning: ", fg="yellow")
        user_output(warning + "Invalid JSON in ~/.claude/settings.json")
        user_output(f"   {e}")
        return False

    # No settings file - will create one
    if settings is None:
        settings = {}
        user_output(f"  Creating: {settings_path}")

    # Check current statusline config
    current_config = get_statusline_config(settings)

    # Already configured with erk-statusline
    if has_erk_statusline(settings):
        user_output(click.style("  ✓", fg="green") + " Statusline already configured")
        return True

    # Different statusline configured - warn and prompt
    if not isinstance(current_config, StatuslineNotConfigured):
        user_output(f"\n  Existing statusLine found: {current_config.command}")
        if not user_confirm(f"  Replace with {get_erk_statusline_command()}?", default=False):
            user_output("  Skipped. Keeping existing statusLine configuration.")
            return False

    # Add statusline config
    new_settings = add_erk_statusline(settings)
    write_claude_settings(settings_path, new_settings)
    statusline_msg = " Status line configured in ~/.claude/settings.json"
    user_output(click.style("  ✓", fg="green") + statusline_msg)
    user_output("  Note: Install erk-statusline with: uv tool install erk-statusline")

    return True


@click.command("init")
@click.option("-f", "--force", is_flag=True, help="Overwrite existing repo config if present.")
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
    "--shell",
    is_flag=True,
    help="Show shell integration setup instructions (completion + auto-activation wrapper).",
)
@click.option(
    "--hooks",
    "hooks_only",
    is_flag=True,
    help="Only set up Claude Code hooks.",
)
@click.option(
    "--statusline",
    "statusline_only",
    is_flag=True,
    help="Only configure erk-statusline in Claude Code.",
)
@click.option(
    "--no-interactive",
    "no_interactive",
    is_flag=True,
    help="Skip all interactive prompts (gitignore, permissions, hooks, shell setup).",
)
@click.option(
    "--with-dignified-review",
    "with_dignified_review",
    is_flag=True,
    help="Install dignified-python skill and review workflow.",
)
@click.pass_obj
def init_cmd(
    ctx: ErkContext,
    force: bool,
    preset: str,
    list_presets: bool,
    shell: bool,
    hooks_only: bool,
    statusline_only: bool,
    no_interactive: bool,
    with_dignified_review: bool,
) -> None:
    """Initialize erk for this repo and scaffold config.toml.

    Runs in three sequential steps:
    1. Repo verification - checks that you're in a git repository
    2. Project setup - erk-ifies the repo (if not already)
    3. User setup - configures shell integration and Claude Code status line
    """
    # Discover available presets on demand (needed for --list-presets)
    presets_dir = _get_presets_dir()
    available_presets = discover_presets(presets_dir)
    valid_choices = ["auto"] + available_presets

    # Handle --list-presets flag (doesn't require repo)
    if list_presets:
        user_output("Available presets:")
        for p in available_presets:
            user_output(f"  - {p}")
        return

    # Handle --shell flag: only do shell setup (doesn't require repo)
    if shell:
        if ctx.global_config is None:
            config_path = ctx.erk_installation.config_path()
            user_output(f"Global config not found at {config_path}")
            user_output("Run 'erk init' without --shell to create global config first.")
            raise SystemExit(1)

        setup_complete = perform_shell_setup(ctx.shell)
        if setup_complete:
            # Show what we're about to write
            config_path = ctx.erk_installation.config_path()
            user_output("\nTo remember that shell setup is complete, erk needs to update:")
            user_output(f"  {config_path}")

            if not user_confirm("Proceed with updating global config?", default=False):
                user_output("\nShell integration instructions shown above.")
                user_output("Run 'erk init --shell' to save this preference.")
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
                ctx.erk_installation.save_config(new_config)
                user_output(click.style("✓", fg="green") + " Global config updated")
            except PermissionError as e:
                user_output(click.style("\n❌ Error: ", fg="red") + "Could not save global config")
                user_output(str(e))
                user_output("\nShell integration instructions shown above.")
                user_output("You can use them now - erk just couldn't save.")
                raise SystemExit(1) from e
        return

    # =========================================================================
    # STEP 1: Repo Verification
    # =========================================================================
    user_output("\nStep 1: Checking repository...")

    # Check if we're in a git repo (before any other setup)
    # Use a temporary erk_root for discovery - will be replaced after global config setup
    temp_erk_root = Path.home() / ".erk"
    repo_or_sentinel = discover_repo_or_sentinel(ctx.cwd, temp_erk_root, RealGit())

    if isinstance(repo_or_sentinel, NoRepoSentinel):
        user_output(click.style("Error: ", fg="red") + "Not in a git repository.")
        user_output("Run 'erk init' from within a git repository.")
        raise SystemExit(1)

    # We have a valid repo - extract the root for display
    repo_root = repo_or_sentinel.root
    user_output(click.style("✓", fg="green") + f" Git repository detected: {repo_root.name}")

    # Handle --hooks flag: only do hook setup
    if hooks_only:
        offer_claude_hook_setup(repo_root)
        return

    # Handle --statusline flag: only do statusline setup
    if statusline_only:
        perform_statusline_setup(settings_path=None)
        return

    # Validate preset choice
    if preset not in valid_choices:
        user_output(f"Invalid preset '{preset}'. Available options: {', '.join(valid_choices)}")
        raise SystemExit(1)

    # =========================================================================
    # STEP 2: Project Configuration
    # =========================================================================
    user_output("\nStep 2: Project configuration...")

    # Check if repo is already erk-ified
    already_erkified = is_repo_erk_ified(repo_root)

    if already_erkified and not force:
        user_output(click.style("✓", fg="green") + " Repository already configured for erk")
    else:
        # Check for global config first
        if not ctx.erk_installation.config_exists():
            config_path = ctx.erk_installation.config_path()
            user_output(f"  Global config not found at {config_path}")
            user_output("  Please provide the path for your .erk folder.")
            user_output("  (This directory will contain worktrees for each repository)")
            default_erk_root = Path.home() / ".erk"
            erk_root = click.prompt("  .erk folder", type=Path, default=str(default_erk_root))
            erk_root = erk_root.expanduser().resolve()
            config = create_and_save_global_config(ctx, erk_root, shell_setup_complete=False)
            # Update context with newly created config
            ctx = dataclasses.replace(ctx, global_config=config)
            user_output(f"  Created global config at {config_path}")
            # Show graphite status on first init
            has_graphite = detect_graphite(ctx.shell)
            if has_graphite:
                user_output("  Graphite (gt) detected - will use 'gt create' for new branches")
            else:
                user_output("  Graphite (gt) not detected - will use 'git' for branch creation")

        # Now re-discover repo with correct erk_root
        if ctx.global_config is not None:
            repo_context = discover_repo_context(ctx, ctx.cwd)
        else:
            # Fallback (shouldn't happen, but defensive)
            repo_context = repo_or_sentinel

        # Ensure .erk directory exists
        erk_dir = repo_context.root / ".erk"
        erk_dir.mkdir(parents=True, exist_ok=True)

        # All repo config now goes to .erk/config.toml (consolidated location)
        cfg_path = erk_dir / "config.toml"

        # Also ensure metadata directory exists (needed for worktrees dir)
        ensure_erk_metadata_dir(repo_context)

        effective_preset: str | None
        choice = preset.lower()
        if choice == "auto":
            is_dagster = is_repo_named(repo_context.root, "dagster")
            effective_preset = "dagster" if is_dagster else "generic"
        else:
            effective_preset = choice

        content = render_config_template(presets_dir, effective_preset)
        cfg_path.write_text(content, encoding="utf-8")
        user_output(f"  Wrote {cfg_path}")

        # Sync artifacts (skills, commands, agents, workflows, actions)
        sync_result = sync_artifacts(repo_context.root, force=False)
        if sync_result.success:
            user_output(click.style("  ✓ ", fg="green") + sync_result.message)
        else:
            # Non-fatal: warn but continue init
            warn_msg = f"Artifact sync failed: {sync_result.message}"
            user_output(click.style("  ⚠ ", fg="yellow") + warn_msg)
            user_output("    Run 'erk artifact sync' to retry")

        # Sync optional dignified-review feature if requested
        if with_dignified_review:
            from erk.artifacts.sync import sync_dignified_review

            dr_result = sync_dignified_review(repo_context.root)
            if dr_result.success:
                user_output(click.style("  ✓ ", fg="green") + dr_result.message)
            else:
                warn_msg = f"dignified-review sync failed: {dr_result.message}"
                user_output(click.style("  ⚠ ", fg="yellow") + warn_msg)

        # Create prompt hooks directory with README
        _create_prompt_hooks_directory(repo_root=repo_context.root)

        # Skip interactive prompts if requested
        interactive = not no_interactive

        # Track backup files for cleanup at end
        pending_backup: Path | NoBackupCreated = NoBackupCreated()

        if interactive:
            _run_gitignore_prompts(repo_context.root)
            pending_backup = offer_claude_permission_setup(repo_context.root)
            offer_claude_hook_setup(repo_context.root)

        # Offer to clean up any pending backup files (at end of project setup)
        if not isinstance(pending_backup, NoBackupCreated):
            offer_backup_cleanup(pending_backup)

    # =========================================================================
    # STEP 3: User Configuration (always runs)
    # =========================================================================
    user_output("\nStep 3: User configuration...")

    # Skip interactive prompts if requested
    interactive = not no_interactive

    # 3a. Global config (if not exists) - already handled in step 2 if needed

    # 3b. Shell integration
    if interactive:
        # Only check if global config exists
        if ctx.global_config is not None or ctx.erk_installation.config_exists():
            config_exists = ctx.erk_installation.config_exists()
            fresh_config = ctx.erk_installation.load_config() if config_exists else None
            if fresh_config is not None and not fresh_config.shell_setup_complete:
                # Check if shell integration is already in the RC file
                shell_info = ctx.shell.detect_shell()
                already_in_rc = False
                if shell_info is not None:
                    shell_name, rc_path = shell_info
                    already_in_rc = has_shell_integration_in_rc(rc_path)
                    if already_in_rc:
                        # Already configured - just show message and update config flag
                        msg = f" Shell integration already configured ({shell_name})"
                        user_output(click.style("✓", fg="green") + msg)
                        # Update global config to remember this
                        new_config = GlobalConfig(
                            erk_root=fresh_config.erk_root,
                            use_graphite=fresh_config.use_graphite,
                            shell_setup_complete=True,
                            show_pr_info=fresh_config.show_pr_info,
                            github_planning=fresh_config.github_planning,
                        )
                        ctx.erk_installation.save_config(new_config)

                if not already_in_rc:
                    setup_complete = perform_shell_setup(ctx.shell)
                    if setup_complete:
                        # Show what we're about to write
                        config_path = ctx.erk_installation.config_path()
                        shell_msg = "To remember that shell setup is complete, erk needs to update:"
                        user_output(f"\n  {shell_msg}")
                        user_output(f"    {config_path}")

                        prompt = "  Proceed with updating global config?"
                        if not user_confirm(prompt, default=False):
                            user_output("\n  Shell integration instructions shown above.")
                            user_output("  Run 'erk init --shell' to save this preference.")
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
                                ctx.erk_installation.save_config(new_config)
                                msg = click.style("  ✓", fg="green") + " Global config updated"
                                user_output(msg)
                            except PermissionError as e:
                                error_msg = "Could not save global config"
                                user_output(click.style("\n  ❌ Error: ", fg="red") + error_msg)
                                user_output(f"  {e}")
                                user_output("\n  Shell integration instructions shown above.")
                                user_output("  You can use them now - erk just couldn't save.")

    # 3c. Status line configuration
    if interactive:
        perform_statusline_setup(settings_path=None)

    user_output(click.style("\n✓", fg="green") + " Initialization complete!")
