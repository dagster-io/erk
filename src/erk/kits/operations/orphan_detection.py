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


# Directory names within .claude/ where orphan detection applies.
# NOTE: skills/ is intentionally excluded. Claude Code resolves skills by
# direct folder name, so there's no way to distinguish "local skill I created"
# from "orphaned kit skill". Commands and agents use folder namespacing
# that maps cleanly to kit ownership.
# NOTE: docs/ is excluded from .claude/ scanning because kit docs now live in
# .erk/docs/kits/ (scanned separately). Non-kit docs in .claude/docs/ are local.
_TRACKED_ARTIFACT_DIRS = ["commands", "agents"]

# Reserved directory names that are never considered orphaned
_RESERVED_DIRS = {"local"}


def _build_declared_directories(config: ProjectConfig | None) -> set[Path]:
    """Build set of directories declared by installed kits.

    Each artifact path like ".claude/agents/erk/plan-extractor.md" contributes
    all its parent directories under .claude/<type>/ to the set:
    - ".claude/agents/erk"

    For kit docs at ".erk/docs/kits/<kit>/...", we track:
    - ".erk/docs/kits/<kit>/..."

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

    # Artifact type directories we care about for .claude/
    claude_artifact_types = {"commands", "agents", "skills"}

    for kit in config.kits.values():
        for artifact_path_str in kit.artifacts:
            artifact_path = Path(artifact_path_str)

            # Handle .erk/docs/kits/ paths
            if artifact_path.parts[:3] == (".erk", "docs", "kits"):
                # Walk up from artifact parent to .erk/docs/kits/
                current = artifact_path.parent
                while current.parts:
                    # Stop at .erk/docs/kits
                    if current.parts == (".erk", "docs", "kits"):
                        break
                    if len(current.parts) < 4:
                        break
                    declared.add(current)
                    current = current.parent
            # Handle .claude/ paths
            elif artifact_path.parts[:1] == (".claude",):
                # Walk up from artifact parent to .claude/<type>/
                current = artifact_path.parent
                while current.parts:
                    # Stop if we've reached .claude/<type>/
                    if len(current.parts) >= 2 and current.parts[-2] == ".claude":
                        if current.parts[-1] in claude_artifact_types:
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
    """Detect orphaned artifacts in .claude/ and .erk/docs/kits/ directories.

    Scans .claude/commands/ and .claude/agents/ for subdirectories that don't
    correspond to any artifact declared by installed kits. Also scans
    .erk/docs/kits/ for orphaned kit documentation directories.

    The detection works by:
    1. Building a set of parent directories from all declared artifact paths
    2. Checking if each subdirectory is covered by that set

    Args:
        project_dir: Project root directory
        config: Loaded ProjectConfig from kits.toml, or None if not found

    Returns:
        OrphanDetectionResult containing list of orphaned directories
    """
    # Build set of directories declared by installed kits
    declared_dirs = _build_declared_directories(config)

    orphaned: list[OrphanedArtifact] = []

    # Check .claude/ tracked artifact directories (excludes skills/ and docs/)
    claude_dir = project_dir / ".claude"
    if claude_dir.exists():
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

    # Check .erk/docs/kits/ for orphaned kit doc directories
    erk_docs_kits_dir = project_dir / ".erk" / "docs" / "kits"
    if erk_docs_kits_dir.exists():
        for subdir in erk_docs_kits_dir.iterdir():
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
