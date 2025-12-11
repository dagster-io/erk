"""Orphaned artifact detection operations.

Detects artifacts in .claude/ that appear to be kit-related but
don't correspond to any installed kit.
"""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.models.config import ProjectConfig


@dataclass(frozen=True)
class OrphanedArtifact:
    """Represents an orphaned artifact directory.

    Attributes:
        path: Path relative to project root (e.g., ".claude/commands/old-kit/")
        reason: Human-readable explanation (e.g., "kit 'old-kit' not installed")
        kit_id: Inferred kit ID from the directory name
    """

    path: Path
    reason: str
    kit_id: str


@dataclass(frozen=True)
class OrphanDetectionResult:
    """Result of orphan detection scan.

    Attributes:
        orphaned_directories: List of detected orphaned artifact directories
    """

    orphaned_directories: list[OrphanedArtifact]


# Directory names to check for kit-organized artifacts
# These directories use kit IDs as subdirectory names
_KIT_ORGANIZED_DIRS = ["commands", "agents", "docs"]

# Skills use skill names (not kit IDs) as subdirectory names
_SKILL_DIR = "skills"

# Reserved directory names that are never considered orphaned
_RESERVED_DIRS = {"local"}


def _extract_kit_prefix_from_skill(skill_name: str) -> str:
    """Extract kit ID prefix from a skill name.

    Skills are named with the pattern "<kit-id>-<variant>" where the kit ID
    may contain hyphens. We assume the last hyphen-separated part is the
    variant if it looks like a version identifier (e.g., "313", "v2").

    Examples:
        "dignified-python-313" -> "dignified-python"
        "gt-graphite" -> "gt"
        "simple" -> "simple"
    """
    parts = skill_name.rsplit("-", 1)
    if len(parts) == 1:
        return skill_name

    prefix, suffix = parts
    # If suffix looks like a version number (digits only), it's a variant
    if suffix.isdigit():
        return prefix
    # Otherwise, return the full name as the kit ID
    return skill_name


def detect_orphaned_artifacts(
    project_dir: Path,
    config: ProjectConfig | None,
) -> OrphanDetectionResult:
    """Detect orphaned artifacts in .claude/ directory.

    Scans .claude/commands/, .claude/agents/, .claude/docs/, and .claude/skills/
    for subdirectories that don't correspond to any installed kit.

    Args:
        project_dir: Project root directory
        config: Loaded ProjectConfig from kits.toml, or None if not found

    Returns:
        OrphanDetectionResult containing list of orphaned directories
    """
    claude_dir = project_dir / ".claude"
    if not claude_dir.exists():
        return OrphanDetectionResult(orphaned_directories=[])

    # Build set of installed kit IDs
    installed_kit_ids: set[str] = set()
    if config is not None:
        installed_kit_ids = set(config.kits.keys())

    orphaned: list[OrphanedArtifact] = []

    # Check kit-organized directories (commands/, agents/, docs/)
    for dir_name in _KIT_ORGANIZED_DIRS:
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

            # Check if this kit is installed
            if dir_basename not in installed_kit_ids:
                relative_path = subdir.relative_to(project_dir)
                orphaned.append(
                    OrphanedArtifact(
                        path=relative_path,
                        reason=f"kit '{dir_basename}' not installed",
                        kit_id=dir_basename,
                    )
                )

    # Check skills directory separately (uses kit prefix matching)
    skills_dir = claude_dir / _SKILL_DIR
    if skills_dir.exists():
        for skill_subdir in skills_dir.iterdir():
            if not skill_subdir.is_dir():
                continue

            skill_name = skill_subdir.name
            kit_prefix = _extract_kit_prefix_from_skill(skill_name)

            # Check if the inferred kit is installed
            if kit_prefix not in installed_kit_ids:
                relative_path = skill_subdir.relative_to(project_dir)
                orphaned.append(
                    OrphanedArtifact(
                        path=relative_path,
                        reason=f"kit '{kit_prefix}' not installed",
                        kit_id=kit_prefix,
                    )
                )

    return OrphanDetectionResult(orphaned_directories=orphaned)
