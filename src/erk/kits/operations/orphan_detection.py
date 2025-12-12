"""Orphaned artifact detection operations.

Detects artifacts in .claude/ that appear to be kit-related but
don't correspond to any installed kit.
"""

from dataclasses import dataclass
from pathlib import Path

from erk.kits.models.config import ProjectConfig


@dataclass(frozen=True)
class OrphanedArtifact:
    """Represents an orphaned artifact directory.

    Attributes:
        path: Path relative to project root (e.g., ".claude/commands/old-kit/")
        reason: Human-readable explanation (e.g., "not declared by any installed kit")
    """

    path: Path
    reason: str


@dataclass(frozen=True)
class OrphanDetectionResult:
    """Result of orphan detection scan.

    Attributes:
        orphaned_directories: List of detected orphaned artifact directories
    """

    orphaned_directories: list[OrphanedArtifact]


# Directory names where orphan detection applies.
# NOTE: skills/ is intentionally excluded. Claude Code resolves skills by
# direct folder name, so there's no way to distinguish "local skill I created"
# from "orphaned kit skill". Commands, agents, and docs use folder namespacing
# that maps cleanly to kit ownership.
_TRACKED_ARTIFACT_DIRS = ["commands", "agents", "docs"]

# Reserved directory names that are never considered orphaned
_RESERVED_DIRS = {"local"}


def _build_declared_directories(config: ProjectConfig | None) -> set[Path]:
    """Build set of directories declared by installed kits.

    Each artifact path like ".claude/docs/erk/includes/file.md" contributes
    all its parent directories under .claude/<type>/ to the set:
    - ".claude/docs/erk/includes"
    - ".claude/docs/erk"

    This handles nested artifact structures where we want to mark the
    top-level kit directory as declared even if only nested files are listed.

    Args:
        config: Project configuration with installed kits

    Returns:
        Set of Path objects representing directories declared by kits
    """
    declared: set[Path] = set()
    if config is None:
        return declared

    # Artifact type directories we care about
    artifact_types = {"commands", "agents", "docs", "skills"}

    for kit in config.kits.values():
        for artifact_path_str in kit.artifacts:
            artifact_path = Path(artifact_path_str)

            # Walk up from artifact parent to .claude/<type>/
            # e.g., ".claude/docs/erk/includes/file.md"
            #   -> parent: ".claude/docs/erk/includes"
            #   -> then: ".claude/docs/erk"
            #   -> stop at: ".claude/docs" (artifact type dir)
            current = artifact_path.parent
            while current.parts:
                # Stop if we've reached .claude/<type>/
                if len(current.parts) >= 2 and current.parts[-2] == ".claude":
                    if current.parts[-1] in artifact_types:
                        break
                # Stop if we've gone past .claude
                if len(current.parts) < 3:
                    break
                declared.add(current)
                current = current.parent

    return declared


def detect_orphaned_artifacts(
    project_dir: Path,
    config: ProjectConfig | None,
) -> OrphanDetectionResult:
    """Detect orphaned artifacts in .claude/ directory.

    Scans .claude/commands/, .claude/agents/, .claude/docs/, and .claude/skills/
    for subdirectories that don't correspond to any artifact declared by
    installed kits.

    The detection works by:
    1. Building a set of parent directories from all declared artifact paths
    2. Checking if each subdirectory in .claude/ is covered by that set

    Args:
        project_dir: Project root directory
        config: Loaded ProjectConfig from kits.toml, or None if not found

    Returns:
        OrphanDetectionResult containing list of orphaned directories
    """
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        return OrphanDetectionResult(orphaned_directories=[])

    # Build set of directories declared by installed kits
    declared_dirs = _build_declared_directories(config)

    orphaned: list[OrphanedArtifact] = []

    # Check tracked artifact directories (excludes skills/)
    for dir_name in _TRACKED_ARTIFACT_DIRS:
        artifact_dir = claude_dir / dir_name
        if not artifact_dir.exists():
            continue

        for subdir in artifact_dir.iterdir():
            if not subdir.is_dir():
                continue

            dir_basename = subdir.name

            # Skip reserved directories
            if dir_basename in _RESERVED_DIRS:
                continue

            # Get path relative to project root for comparison
            relative_path = subdir.relative_to(project_dir)

            # Check if this directory is declared by any installed kit
            if relative_path not in declared_dirs:
                orphaned.append(
                    OrphanedArtifact(
                        path=relative_path,
                        reason="not declared by any installed kit",
                    )
                )

    return OrphanDetectionResult(orphaned_directories=orphaned)
