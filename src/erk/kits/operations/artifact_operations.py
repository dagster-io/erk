"""Artifact installation and cleanup strategies.

This module provides abstract interfaces and concrete strategies for installing
and cleaning up kit artifacts. It separates production behavior (copy/delete) from
dev-mode behavior (symlink-based with special cleanup).
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from erk.kits.io.state import load_project_config
from erk.kits.sources.resolver import ResolvedKit


class ArtifactOperations(ABC):
    """Strategy for installing and cleaning up artifacts."""

    @abstractmethod
    def install_artifact(self, source: Path, target: Path) -> str:
        """Install artifact from source to target.

        Args:
            source: Source file path
            target: Target file path

        Returns:
            Status message suffix for logging (e.g., "" or " -> source")
        """
        pass

    @abstractmethod
    def remove_artifacts(self, artifact_paths: list[str], project_dir: Path) -> list[str]:
        """Remove old artifacts.

        Args:
            artifact_paths: List of artifact paths relative to project_dir
            project_dir: Project root directory

        Returns:
            List of artifact paths that were skipped (not removed)
        """
        pass


class ProdOperations(ArtifactOperations):
    """Production strategy: copy artifacts and delete all on cleanup."""

    def install_artifact(self, source: Path, target: Path) -> str:
        """Copy artifact from source to target."""
        # Ensure parent directories exist
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)

        content = source.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        return ""

    def remove_artifacts(self, artifact_paths: list[str], project_dir: Path) -> list[str]:
        """Remove all artifacts unconditionally."""
        for artifact_path in artifact_paths:
            full_path = project_dir / artifact_path
            if not full_path.exists():
                continue

            if full_path.is_file() or full_path.is_symlink():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)

        return []


class DevModeOperations(ArtifactOperations):
    """Dev-mode strategy: create symlinks (no fallback) and skip symlinks on cleanup."""

    def install_artifact(self, source: Path, target: Path) -> str:
        """Create symlink to source. Raises error if symlink creation fails."""
        # Ensure parent directories exist
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)

        # Calculate relative path from target to source
        source_abs = source.resolve()
        target_abs = target.resolve() if target.exists() else target.parent.resolve() / target.name

        # Get relative path from target to source
        relative_source = os.path.relpath(source_abs, target_abs.parent)

        # Create symlink or raise error (no fallback to copy in dev mode)
        target.symlink_to(relative_source)
        return " -> source"

    def remove_artifacts(self, artifact_paths: list[str], project_dir: Path) -> list[str]:
        """Remove artifacts, skipping symlinks (dev mode preserves symlinked artifacts)."""
        skipped: list[str] = []

        for artifact_path in artifact_paths:
            full_path = project_dir / artifact_path
            if not full_path.exists():
                continue

            # Skip symlinks in dev mode
            if full_path.is_symlink():
                skipped.append(artifact_path)
                continue

            # Remove regular files or directories
            if full_path.is_file():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)

        return skipped


def _validate_dev_mode_invariants(project_dir: Path, resolved: ResolvedKit) -> None:
    """Validate all dev mode invariants. Raises error if any invariant fails.

    Dev mode requires:
    1. Kit source exists
    2. Source is within same git repository (not cross-worktree)

    Args:
        project_dir: Project root directory
        resolved: Resolved kit information

    Raises:
        RuntimeError: If any dev mode invariant is violated
    """
    artifacts_base = resolved.artifacts_base

    # Invariant 1: Source must exist
    if not artifacts_base.exists():
        msg = (
            f"Dev mode enabled but kit source does not exist: {artifacts_base}\n"
            "Dev mode requires bundled kit sources in packages/"
        )
        raise RuntimeError(msg)

    # Invariant 2: Must be same git repository (not cross-worktree)
    source_git = _find_git_root(artifacts_base)
    project_git = _find_git_root(project_dir)

    if source_git is None or project_git is None:
        msg = "Dev mode enabled but could not determine git repository roots"
        raise RuntimeError(msg)

    if source_git != project_git:
        msg = (
            f"Dev mode enabled but kit source is in different git repository:\n"
            f"  Project: {project_git}\n"
            f"  Kit source: {source_git}\n"
            "Dev mode does not support cross-worktree installations"
        )
        raise RuntimeError(msg)


def _find_git_root(start_path: Path) -> Path | None:
    """Find the root of the git repository containing the given path.

    Args:
        start_path: Path to start searching from

    Returns:
        Path to git root, or None if not in a git repository
    """
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def create_artifact_operations(project_dir: Path, resolved: ResolvedKit) -> ArtifactOperations:
    """Factory that creates appropriate artifact operation strategies.

    Checks dev_mode and validates invariants if enabled.

    Args:
        project_dir: Project root directory
        resolved: Resolved kit information

    Returns:
        DevModeOperations if dev_mode enabled, ProdOperations otherwise

    Raises:
        RuntimeError: If dev_mode is enabled but invariants are violated
    """
    # Load configuration to check dev_mode
    config = load_project_config(project_dir)
    if config is not None and config.dev_mode:
        # Validate all dev mode invariants (raises if any fail)
        _validate_dev_mode_invariants(project_dir, resolved)
        return DevModeOperations()

    # Production mode: copy files, delete all on cleanup
    return ProdOperations()
