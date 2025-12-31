"""Sync artifacts from erk package to project's .claude/ directory."""

import shutil
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from erk.artifacts.detection import is_in_erk_repo
from erk.artifacts.models import ArtifactState
from erk.artifacts.state import save_artifact_state
from erk.core.release_notes import get_current_version


@dataclass(frozen=True)
class SyncResult:
    """Result of artifact sync operation."""

    success: bool
    artifacts_installed: int
    message: str


@cache
def get_bundled_claude_dir() -> Path:
    """Get path to bundled .claude/ directory in installed erk package.

    The .claude/ directory from the erk repo is bundled as package data
    at erk/data/claude/ via pyproject.toml force-include.
    """
    import erk

    return Path(erk.__file__).parent / "data" / "claude"


def _copy_directory_contents(source_dir: Path, target_dir: Path) -> int:
    """Copy directory contents recursively, returning count of files copied."""
    if not source_dir.exists():
        return 0

    count = 0
    for source_path in source_dir.rglob("*"):
        if source_path.is_file():
            relative = source_path.relative_to(source_dir)
            target_path = target_dir / relative
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            count += 1
    return count


def sync_artifacts(project_dir: Path, force: bool) -> SyncResult:
    """Sync artifacts from erk package to project's .claude/ directory.

    When running in the erk repo itself, skips sync since artifacts
    are read directly from source.
    """
    # Skip sync in erk repo - artifacts are already at source
    if is_in_erk_repo(project_dir):
        return SyncResult(
            success=True,
            artifacts_installed=0,
            message="Skipped: running in erk repo (artifacts read from source)",
        )

    bundled_dir = get_bundled_claude_dir()
    if not bundled_dir.exists():
        return SyncResult(
            success=False,
            artifacts_installed=0,
            message=f"Bundled .claude/ not found at {bundled_dir}",
        )

    target_claude_dir = project_dir / ".claude"
    target_claude_dir.mkdir(parents=True, exist_ok=True)

    total_copied = 0

    # Sync artifact folders (commands, skills, agents)
    for subdir in ["commands", "skills", "agents"]:
        source = bundled_dir / subdir
        target = target_claude_dir / subdir
        total_copied += _copy_directory_contents(source, target)

    # Save state with current version
    save_artifact_state(project_dir, ArtifactState(version=get_current_version()))

    return SyncResult(
        success=True,
        artifacts_installed=total_copied,
        message=f"Synced {total_copied} artifact files",
    )
