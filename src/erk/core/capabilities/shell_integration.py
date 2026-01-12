"""ShellIntegrationCapability - user-level capability for shell integration."""

from functools import cache
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.init_utils import (
    ERK_SHELL_INTEGRATION_MARKER,
    get_shell_wrapper_content,
    has_shell_integration_in_rc,
    remove_shell_integration_from_content,
)
from erk_shared.gateway.console.abc import Console
from erk_shared.gateway.console.real import InteractiveConsole
from erk_shared.gateway.shell.abc import Shell
from erk_shared.gateway.shell.real import RealShell


@cache
def _shell_integration_dir() -> Path:
    """Return path to shell integration templates (deferred, cached)."""
    return Path(__file__).parent.parent.parent / "cli" / "shell_integration"


class ShellIntegrationCapability(Capability):
    """Capability for configuring shell integration (erk function wrapper).

    This is a user-level capability that modifies the user's shell RC file
    (e.g., ~/.zshrc, ~/.bashrc) to add the erk shell wrapper function.

    Shell integration enables seamless worktree switching by wrapping the
    erk command so that directory changes happen in the current shell.
    """

    def __init__(
        self,
        *,
        shell: Shell | None,
        console: Console | None,
        shell_integration_dir: Path | None,
    ) -> None:
        """Initialize ShellIntegrationCapability.

        Args:
            shell: Shell gateway for detecting shell type. If None, uses RealShell.
            console: Console gateway for user prompts. If None, uses InteractiveConsole.
            shell_integration_dir: Path to shell integration templates.
                If None, uses the bundled templates in src/erk/cli/shell_integration/.
        """
        self._shell = shell or RealShell()
        self._console = console or InteractiveConsole()
        self._shell_integration_dir = shell_integration_dir or _shell_integration_dir()

    @property
    def name(self) -> str:
        return "shell-integration"

    @property
    def description(self) -> str:
        return "Shell wrapper for seamless worktree switching"

    @property
    def scope(self) -> CapabilityScope:
        return "user"

    @property
    def installation_check_description(self) -> str:
        return "erk shell integration marker in shell RC file"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # RC file is user's existing file, not an artifact we own
        return []

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if shell integration is already installed.

        Detects the user's shell and checks if the marker comment exists
        in the corresponding RC file.
        """
        # User-level capability ignores repo_root
        _ = repo_root

        shell_info = self._shell.detect_shell()
        if shell_info is None:
            return False

        _, rc_path = shell_info
        return has_shell_integration_in_rc(rc_path)

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install shell integration by modifying the user's RC file.

        Prompts the user to choose between auto-modification (with backup)
        or manual installation instructions.
        """
        # User-level capability ignores repo_root
        _ = repo_root

        # Step 1: Detect shell
        shell_info = self._shell.detect_shell()
        if shell_info is None:
            return CapabilityResult(
                success=False,
                message="Could not detect shell (bash, zsh, or fish required)",
            )

        shell_name, rc_path = shell_info

        # Step 2: Check if already installed
        if has_shell_integration_in_rc(rc_path):
            return CapabilityResult(
                success=True,
                message=f"Shell integration already configured in {rc_path}",
            )

        # Step 3: Get wrapper content
        wrapper_content = get_shell_wrapper_content(self._shell_integration_dir, shell_name)

        # Step 4: Ask user how to proceed
        auto_install = self._console.confirm(
            f"Automatically modify {rc_path}? (A backup will be created)",
            default=True,
        )

        if auto_install:
            return self._auto_install(rc_path, wrapper_content)
        return self._manual_install(rc_path, shell_name, wrapper_content)

    def _auto_install(self, rc_path: Path, wrapper_content: str) -> CapabilityResult:
        """Automatically modify RC file with backup."""
        # Create backup
        backup_path = rc_path.with_suffix(rc_path.suffix + ".erk-backup")

        # Read existing content
        existing_content = ""
        if rc_path.exists():
            existing_content = rc_path.read_text(encoding="utf-8")
            backup_path.write_text(existing_content, encoding="utf-8")

        # Append wrapper with marker
        new_content = existing_content
        if not new_content.endswith("\n"):
            new_content += "\n"

        new_content += f"\n{ERK_SHELL_INTEGRATION_MARKER}\n"
        new_content += wrapper_content

        rc_path.write_text(new_content, encoding="utf-8")

        return CapabilityResult(
            success=True,
            message=f"Installed shell integration in {rc_path} (backup at {backup_path})",
            created_files=(str(rc_path),),
        )

    def _manual_install(
        self, rc_path: Path, shell_name: str, wrapper_content: str
    ) -> CapabilityResult:
        """Show manual installation instructions."""
        instructions = f"""
To install shell integration manually, add the following to {rc_path}:

{ERK_SHELL_INTEGRATION_MARKER}
{wrapper_content}

Then restart your shell or run: source {rc_path}
"""
        self._console.info(instructions)

        return CapabilityResult(
            success=True,
            message=f"Manual installation instructions shown for {shell_name}",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove shell integration from the user's RC file."""
        # User-level capability ignores repo_root
        _ = repo_root

        # Detect shell
        shell_info = self._shell.detect_shell()
        if shell_info is None:
            return CapabilityResult(
                success=True,
                message="shell-integration not installed (could not detect shell)",
            )

        _, rc_path = shell_info

        if not has_shell_integration_in_rc(rc_path):
            return CapabilityResult(
                success=True,
                message="shell-integration not installed",
            )

        # Read current content
        content = rc_path.read_text(encoding="utf-8")

        # Remove shell integration
        new_content = remove_shell_integration_from_content(content)
        if new_content is None:
            return CapabilityResult(
                success=True,
                message="shell-integration not installed",
            )

        # Create backup
        backup_path = rc_path.with_suffix(rc_path.suffix + ".erk-uninstall-backup")
        backup_path.write_text(content, encoding="utf-8")

        # Write new content
        rc_path.write_text(new_content, encoding="utf-8")

        return CapabilityResult(
            success=True,
            message=f"Removed shell integration from {rc_path} (backup at {backup_path})",
        )
