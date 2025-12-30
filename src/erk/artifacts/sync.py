"""Artifact synchronization from erk package to project."""

from dataclasses import dataclass
from pathlib import Path

from erk.artifacts.models import ArtifactState
from erk.artifacts.staleness import get_current_version
from erk.artifacts.state import save_artifact_state
from erk.kits.hooks.installer import install_hooks
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.artifact import ARTIFACT_TARGET_DIRS, ArtifactType
from erk.kits.operations.artifact_operations import create_artifact_operations
from erk_kits import get_kits_dir


@dataclass(frozen=True)
class SyncResult:
    """Result of artifact sync operation."""

    success: bool
    artifacts_installed: int
    hooks_installed: int
    error: str | None = None


def sync_artifacts(project_dir: Path) -> SyncResult:
    """Sync artifacts from erk package to project.

    This function copies artifacts from the bundled erk kit to the project
    directory and installs any associated hooks.

    Args:
        project_dir: Project root directory

    Returns:
        SyncResult with counts of installed artifacts and hooks
    """
    erk_kit_path = get_kits_dir() / "erk"
    manifest = load_kit_manifest(erk_kit_path / "kit.yaml")

    operations = create_artifact_operations()
    artifacts_installed = 0

    # Copy artifacts (reuse existing logic from kit install)
    for artifact_type_str, paths in manifest.artifacts.items():
        artifact_type: ArtifactType = artifact_type_str  # type: ignore[assignment]

        for artifact_path in paths:
            source = erk_kit_path / artifact_path
            if not source.exists():
                continue

            # Transform path to target location
            target = _get_target_path(project_dir, artifact_type, artifact_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            operations.install_artifact(source, target)
            artifacts_installed += 1

    # Install hooks
    hooks_installed = 0
    if manifest.hooks:
        hooks_installed = install_hooks(
            kit_id=manifest.name,
            hooks=manifest.hooks,
            project_root=project_dir,
        )

    # Save state with current version
    save_artifact_state(project_dir, ArtifactState(version=get_current_version()))

    return SyncResult(
        success=True,
        artifacts_installed=artifacts_installed,
        hooks_installed=hooks_installed,
    )


def _get_target_path(project_dir: Path, artifact_type: ArtifactType, artifact_path: str) -> Path:
    """Transform manifest path to installed path.

    Args:
        project_dir: Project root directory
        artifact_type: Type of artifact (skill, command, agent, etc.)
        artifact_path: Path from manifest (e.g., "commands/erk/foo.md")

    Returns:
        Full target path for the artifact
    """
    # Get base directory for this artifact type
    base_dir_name = ARTIFACT_TARGET_DIRS.get(artifact_type, ".claude")
    base_dir = project_dir / base_dir_name

    # Artifact paths are like "commands/erk/foo.md" or "skills/gt-graphite/SKILL.md"
    artifact_rel_path = Path(artifact_path)
    type_prefix = f"{artifact_type}s"

    # Doc type skips plural suffix since target dir (.erk/docs/kits) is complete
    if artifact_type == "doc":
        target_dir = base_dir
    else:
        target_dir = base_dir / type_prefix

    # Strip the type prefix if present (e.g., "commands/erk/foo.md" -> "erk/foo.md")
    if artifact_rel_path.parts[0] == type_prefix:
        relative_parts = artifact_rel_path.parts[1:]
        if relative_parts:
            return target_dir / Path(*relative_parts)
        return target_dir / artifact_rel_path.name

    # Fallback: use the whole path if prefix doesn't match
    return target_dir / artifact_rel_path
