"""Direnv capability for erk init.

Capability for setting up direnv shell environment auto-loading with .envrc files.
"""

import os
import shutil
import subprocess
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.init_utils import build_envrc_content


class DirenvCapability(Capability):
    """Capability to configure direnv shell environment auto-loading.

    This capability creates a .envrc file with example configurations as
    comments for automatic shell environment setup when entering the
    project directory.

    This is an optional capability that users can install via:
        erk init capability add direnv
    """

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
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(path=".envrc", artifact_type="file"),
        ]

    @property
    def installation_check_description(self) -> str:
        return ".envrc file exists in repo root"

    def preflight(self, repo_root: Path | None) -> CapabilityResult:
        """Check if direnv is installed.

        For explicit `capability add`: fail if direnv not installed.
        Note: This is only called for explicit adds, not during erk init.
        """
        if shutil.which("direnv") is None:
            return CapabilityResult(
                success=False,
                message="direnv not installed. Install from https://direnv.net",
            )
        return CapabilityResult(success=True, message="")

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if .envrc exists in repo root."""
        if repo_root is None:
            return False
        return (repo_root / ".envrc").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install direnv capability by creating .envrc file.

        This method:
        1. Detects the user's shell
        2. Creates .envrc with example configurations as comments
        3. Runs `direnv allow` to authorize the .envrc

        Note: Users should add .envrc to .gitignore manually if desired.
        """
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="DirenvCapability requires repo_root",
            )

        envrc_path = repo_root / ".envrc"
        if envrc_path.exists():
            return CapabilityResult(success=True, message=".envrc already exists")

        # 1. Detect shell
        shell = _detect_shell()

        # 2. Create .envrc with examples as comments
        envrc_path.write_text(build_envrc_content(shell), encoding="utf-8")

        # 3. Run `direnv allow`
        subprocess.run(["direnv", "allow"], cwd=repo_root, check=False)

        return CapabilityResult(
            success=True,
            message="Created .envrc",
            created_files=(".envrc",),
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove .envrc file."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="DirenvCapability requires repo_root",
            )

        envrc_path = repo_root / ".envrc"

        if not envrc_path.exists():
            return CapabilityResult(success=True, message="No direnv files to remove")

        envrc_path.unlink()
        return CapabilityResult(
            success=True,
            message="Removed .envrc",
        )


def _detect_shell() -> str:
    """Detect user's shell from environment.

    Returns:
        Shell name ("zsh" or "bash"). Defaults to "bash" if unknown.
    """
    shell_path = os.environ.get("SHELL", "")
    if "zsh" in shell_path:
        return "zsh"
    if "bash" in shell_path:
        return "bash"
    return "bash"  # Default to bash
