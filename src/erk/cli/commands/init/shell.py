"""Shell integration subcommand for erk init.

This module provides the `erk init shell` subcommand which follows modern shell
tool patterns (starship, direnv, zoxide) for shell integration setup.

Usage patterns:
    # Standard eval pattern (one line in .zshrc)
    eval "$(erk init shell zsh)"

    # Auto-install with consent
    erk init shell --install

    # Verify it's working
    erk init shell --check

    # Remove from RC file
    erk init shell --uninstall
"""

import os
from functools import cache
from pathlib import Path

import click

from erk.core.capabilities.shell_integration import ShellIntegrationCapability
from erk.core.context import ErkContext
from erk.core.init_utils import get_full_shell_init_content
from erk_shared.output.output import machine_output, user_output

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


@cache
def _shell_integration_dir() -> Path:
    """Return path to shell integration templates (deferred, cached)."""
    return Path(__file__).parent.parent.parent / "shell_integration"


def _show_check_status(*, active: bool, shell: str | None, rc_file: Path | None) -> None:
    """Display shell integration status check results.

    Args:
        active: Whether shell integration is currently active in this session
        shell: Detected shell name, or None if not detected
        rc_file: Path to shell rc file, or None if not detected
    """
    if active:
        erk_shell = os.environ.get("ERK_SHELL", "unknown")
        msg = f" Shell integration active (ERK_SHELL={erk_shell})"
        user_output(click.style("✓", fg="green") + msg)
    else:
        user_output(click.style("✗", fg="red") + " Shell integration not active")
        user_output("")

        if shell is not None:
            user_output("To set up, add to your " + str(rc_file) + ":")
            user_output(f'  eval "$(erk init shell {shell})"')
            user_output("")
            user_output("Or auto-install:")
            user_output("  erk init shell --install")
        else:
            user_output("Could not detect shell. Supported shells: bash, zsh, fish")


def _validate_shell_name(shell_name: str) -> str | None:
    """Validate shell name and return error message if invalid.

    Args:
        shell_name: The shell name to validate

    Returns:
        Error message if invalid, None if valid
    """
    if shell_name not in SUPPORTED_SHELLS:
        return f"Unsupported shell: {shell_name}. Supported: {', '.join(SUPPORTED_SHELLS)}"
    return None


@click.command("shell")
@click.argument("shell_name", required=False)
@click.option("-i", "--install", "install_flag", is_flag=True, help="Auto-install to RC file.")
@click.option("-c", "--check", "check_flag", is_flag=True, help="Check if active.")
@click.option("-u", "--uninstall", is_flag=True, help="Remove from shell RC file.")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompts.")
@click.pass_obj
def shell_cmd(
    ctx: ErkContext,
    shell_name: str | None,
    *,
    install_flag: bool,
    check_flag: bool,
    uninstall: bool,
    force: bool,
) -> None:
    """Configure shell integration for erk.

    Without arguments, shows usage help. With a SHELL_NAME argument (bash, zsh,
    or fish), outputs shell code suitable for eval.

    \b
    Standard setup (add to your ~/.zshrc or ~/.bashrc):
        eval "$(erk init shell zsh)"

    \b
    Or use auto-install:
        erk init shell --install

    \b
    Check if active:
        erk init shell --check

    \b
    Remove integration:
        erk init shell --uninstall
    """
    # Count mutually exclusive flags
    flag_count = sum([install_flag, check_flag, uninstall])
    if flag_count > 1:
        err = "--install, --check, and --uninstall are mutually exclusive"
        user_output(click.style("Error: ", fg="red") + err)
        raise SystemExit(1)

    # Use context's shell and console for testability
    shell_ops = ctx.shell
    console = ctx.console
    shell_integration_dir = _shell_integration_dir()

    # Handle --check: verify ERK_SHELL env var
    if check_flag:
        active = os.environ.get("ERK_SHELL") is not None
        shell_info = shell_ops.detect_shell()
        detected_shell = shell_info[0] if shell_info else None
        detected_rc = shell_info[1] if shell_info else None
        _show_check_status(active=active, shell=detected_shell, rc_file=detected_rc)
        if not active:
            raise SystemExit(1)
        return

    # Handle --install: use ShellIntegrationCapability
    if install_flag:
        cap = ShellIntegrationCapability(
            shell=shell_ops,
            console=console,
            shell_integration_dir=shell_integration_dir,
        )

        # Check if already installed
        if cap.is_installed(repo_root=None):
            shell_info = shell_ops.detect_shell()
            if shell_info:
                _, rc_path = shell_info
                msg = f" Shell integration already configured in {rc_path}"
                user_output(click.style("✓", fg="green") + msg)
            else:
                user_output(click.style("✓", fg="green") + " Shell integration already configured")
            return

        # Detect shell
        shell_info = shell_ops.detect_shell()
        if shell_info is None:
            err = "Could not detect shell (bash, zsh, or fish required)"
            user_output(click.style("Error: ", fg="red") + err)
            raise SystemExit(1)

        detected_shell, rc_path = shell_info

        # Confirm unless --force
        if not force:
            prompt = f"Add shell integration to {rc_path}? (A backup will be created)"
            if not console.confirm(prompt, default=True):
                user_output("Skipped. You can use the eval pattern instead:")
                user_output(f'  eval "$(erk init shell {detected_shell})"')
                return

        # Install
        init_content = get_full_shell_init_content(shell_integration_dir, detected_shell)
        result = cap._auto_install(rc_path, init_content)
        if result.success:
            user_output(click.style("✓", fg="green") + f" Added shell integration to {rc_path}")
            user_output("  Restart your shell or run: source " + str(rc_path))
        else:
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return

    # Handle --uninstall: use ShellIntegrationCapability
    if uninstall:
        cap = ShellIntegrationCapability(
            shell=shell_ops,
            console=console,
            shell_integration_dir=shell_integration_dir,
        )

        # Check if installed
        if not cap.is_installed(repo_root=None):
            msg = " Shell integration not installed (nothing to remove)"
            user_output(click.style("✓", fg="green") + msg)
            return

        # Detect shell
        shell_info = shell_ops.detect_shell()
        if shell_info is None:
            user_output(click.style("Error: ", fg="red") + "Could not detect shell")
            raise SystemExit(1)

        _, rc_path = shell_info

        # Confirm unless --force
        if not force:
            prompt = f"Remove shell integration from {rc_path}? (A backup will be created)"
            if not console.confirm(prompt, default=True):
                user_output("Skipped.")
                return

        # Uninstall
        result = cap.uninstall(repo_root=None)
        if result.success:
            user_output(click.style("✓", fg="green") + " " + result.message)
            user_output("  Restart your shell or run: source " + str(rc_path))
        else:
            user_output(click.style("Error: ", fg="red") + result.message)
            raise SystemExit(1)
        return

    # Handle shell_name provided: output combined wrapper+completion to stdout
    if shell_name is not None:
        error = _validate_shell_name(shell_name)
        if error:
            user_output(click.style("Error: ", fg="red") + error)
            raise SystemExit(1)

        content = get_full_shell_init_content(shell_integration_dir, shell_name)
        machine_output(content, nl=False)
        return

    # No arguments and no flags: show help
    shell_info = shell_ops.detect_shell()
    detected_shell = shell_info[0] if shell_info else "zsh"

    user_output("Shell integration enables seamless worktree switching.")
    user_output("")
    user_output("Quick setup - add to your shell rc file:")
    user_output(f'  eval "$(erk init shell {detected_shell})"')
    user_output("")
    user_output("Or use auto-install:")
    user_output("  erk init shell --install")
    user_output("")
    user_output("For more options, run: erk init shell --help")
