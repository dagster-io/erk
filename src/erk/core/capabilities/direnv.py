"""DirenvCapability - auto-loading shell environment with direnv.

This capability creates .envrc and .envrc.example files for direnv integration,
enabling automatic shell environment loading (venv activation, erk completions)
when entering the project directory.
"""

from pathlib import Path
from typing import Literal

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.init_utils import (
    add_gitignore_entry,
    build_envrc_content,
    build_envrc_example_content,
)
from erk_shared.gateway.shell.abc import Shell
from erk_shared.gateway.shell.real import RealShell


class DirenvCapability(Capability):
    """Capability for setting up direnv integration.

    Creates .envrc and .envrc.example files for automatic shell environment
    loading. The .envrc file is gitignored (user-specific), while .envrc.example
    is committed as a template.

    Graceful degradation:
    - During `erk init`: Skips silently if direnv not installed
    - During `erk init capability add direnv`: Fails with install instructions
    """

    def __init__(self, *, shell: Shell | None) -> None:
        """Initialize DirenvCapability.

        Args:
            shell: Shell gateway for detecting shell type and direnv availability.
                If None, uses RealShell.
        """
        self._shell = shell or RealShell()

    @property
    def name(self) -> str:
        return "direnv"

    @property
    def description(self) -> str:
        return "Shell environment auto-loading with direnv (.envrc files)"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def required(self) -> bool:
        return False  # Optional - users can install with `erk init capability add direnv`

    @property
    def installation_check_description(self) -> str:
        return ".envrc file exists in repo root"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(path=".envrc", artifact_type="file"),
            CapabilityArtifact(path=".envrc.example", artifact_type="file"),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if .envrc exists in repo root."""
        if repo_root is None:
            return False
        return (repo_root / ".envrc").exists()

    def _get_direnv_install_instructions(self) -> str:
        """Return platform-appropriate direnv installation instructions."""
        return (
            "direnv is not installed. Install it via:\n"
            "  - macOS:  brew install direnv\n"
            "  - Linux:  apt-get install direnv or pacman -S direnv\n"
            "  - nix:    nix-env -iA nixpkgs.direnv\n"
            "\n"
            "After installation, add to your shell:\n"
            "  - bash:   echo 'eval \"$(direnv hook bash)\"' >> ~/.bashrc\n"
            "  - zsh:    echo 'eval \"$(direnv hook zsh)\"' >> ~/.zshrc\n"
            "\n"
            "See: https://direnv.net/docs/installation.html"
        )

    def preflight(self, repo_root: Path | None) -> CapabilityResult:
        """Check if direnv is installed (for explicit capability add).

        This is only called for explicit `erk init capability add direnv`,
        not during auto-install. Returns failure with install instructions
        if direnv is not installed.
        """
        if self._shell.get_installed_tool_path("direnv") is None:
            return CapabilityResult(
                success=False,
                message=self._get_direnv_install_instructions(),
            )
        return CapabilityResult(success=True, message="")

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install direnv capability by creating .envrc and .envrc.example.

        During auto-install (erk init), gracefully skips if direnv is not installed.
        Creates shell-specific .envrc with completions for the detected shell.
        """
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="DirenvCapability requires repo_root",
            )

        # Step 1: Check if direnv is installed
        if self._shell.get_installed_tool_path("direnv") is None:
            # Graceful degradation for auto-install during erk init
            return CapabilityResult(
                success=True,
                message="Skipped: direnv not installed",
            )

        # Step 2: Check if already installed
        envrc_path = repo_root / ".envrc"
        if envrc_path.exists():
            return CapabilityResult(
                success=True,
                message=".envrc already exists",
            )

        # Step 3: Detect shell for completions
        shell_info = self._shell.detect_shell()
        shell_name: Literal["bash", "zsh"] = "zsh"  # Default to zsh
        if shell_info is not None:
            detected_shell = shell_info[0]
            if detected_shell == "bash":
                shell_name = "bash"
            elif detected_shell == "zsh":
                shell_name = "zsh"

        # Step 4: Create .envrc.example (template, committed to git)
        envrc_example_path = repo_root / ".envrc.example"
        envrc_example_path.write_text(build_envrc_example_content(), encoding="utf-8")

        # Step 5: Create .envrc (user-specific, gitignored)
        envrc_path.write_text(build_envrc_content(shell=shell_name), encoding="utf-8")

        # Step 6: Add .envrc to .gitignore
        gitignore_path = repo_root / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
        else:
            content = ""
        new_content = add_gitignore_entry(content, ".envrc")
        if new_content != content:
            gitignore_path.write_text(new_content, encoding="utf-8")

        # Step 7: Run direnv allow (non-blocking, best-effort)
        # We don't fail if this doesn't work - user can run manually
        import subprocess

        try:
            subprocess.run(
                ["direnv", "allow"],
                cwd=repo_root,
                check=False,
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass  # Non-critical, user can run direnv allow manually

        created_files = [".envrc", ".envrc.example"]
        if new_content != content:
            created_files.append(".gitignore")

        return CapabilityResult(
            success=True,
            message=f"Created .envrc ({shell_name}) and .envrc.example",
            created_files=tuple(created_files),
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Uninstall direnv capability by removing .envrc files.

        Note: Does not remove .envrc from .gitignore to avoid git noise.
        """
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="DirenvCapability requires repo_root",
            )

        removed_files: list[str] = []

        envrc_path = repo_root / ".envrc"
        if envrc_path.exists():
            envrc_path.unlink()
            removed_files.append(".envrc")

        envrc_example_path = repo_root / ".envrc.example"
        if envrc_example_path.exists():
            envrc_example_path.unlink()
            removed_files.append(".envrc.example")

        if not removed_files:
            return CapabilityResult(
                success=True,
                message="direnv already uninstalled (no .envrc files found)",
            )

        return CapabilityResult(
            success=True,
            message=f"Removed {', '.join(removed_files)}",
        )
