"""Artifact synchronization from erk package to project."""

from dataclasses import dataclass
from pathlib import Path

from erk.artifacts.models import ArtifactState
from erk.artifacts.staleness import get_current_version
from erk.artifacts.state import save_artifact_state
from erk.kits.io.frontmatter import parse_artifact_frontmatter
from erk.kits.models.artifact import ARTIFACT_TARGET_DIRS, ArtifactType
from erk.kits.operations.artifact_operations import create_artifact_operations
from erk_kits import get_kits_dir


@dataclass(frozen=True)
class SyncResult:
    """Result of artifact sync operation."""

    success: bool
    artifacts_installed: int
    error: str | None = None


def _discover_kit_artifacts(kit_path: Path, kit_name: str) -> dict[ArtifactType, list[str]]:
    """Discover artifacts in kit by scanning files for erk.kit frontmatter.

    Args:
        kit_path: Path to kit directory
        kit_name: Expected kit name in frontmatter

    Returns:
        Dict mapping artifact type to list of relative paths
    """
    artifacts: dict[ArtifactType, list[str]] = {}

    # Scan known artifact directories
    artifact_dirs: list[tuple[str, ArtifactType]] = [
        ("commands", "command"),
        ("skills", "skill"),
        ("agents", "agent"),
        ("docs", "doc"),
    ]

    for dir_name, artifact_type in artifact_dirs:
        artifact_dir = kit_path / dir_name
        if not artifact_dir.exists():
            continue

        for md_file in artifact_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            frontmatter = parse_artifact_frontmatter(content)

            if frontmatter is not None and frontmatter.kit == kit_name:
                rel_path = str(md_file.relative_to(kit_path))
                if artifact_type not in artifacts:
                    artifacts[artifact_type] = []
                artifacts[artifact_type].append(rel_path)

    return artifacts


def sync_artifacts(project_dir: Path) -> SyncResult:
    """Sync artifacts from erk package to project.

    This function copies artifacts from the bundled erk kit to the project
    directory. Artifacts are discovered by scanning for files with erk.kit
    frontmatter.

    Args:
        project_dir: Project root directory

    Returns:
        SyncResult with counts of installed artifacts
    """
    erk_kit_path = get_kits_dir() / "erk"
    artifacts = _discover_kit_artifacts(erk_kit_path, "erk")

    operations = create_artifact_operations()
    artifacts_installed = 0

    # Copy artifacts
    for artifact_type, paths in artifacts.items():
        for artifact_path in paths:
            source = erk_kit_path / artifact_path
            if not source.exists():
                continue

            # Transform path to target location
            target = _get_target_path(project_dir, artifact_type, artifact_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            operations.install_artifact(source, target)
            artifacts_installed += 1

    # Save state with current version
    save_artifact_state(project_dir, ArtifactState(version=get_current_version()))

    return SyncResult(
        success=True,
        artifacts_installed=artifacts_installed,
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
