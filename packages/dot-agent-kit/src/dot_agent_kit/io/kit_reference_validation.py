"""Validation logic for @ references within kit artifacts.

This module validates that @ references in kit artifacts (skills, docs, etc.)
point to files that will be installed when the kit is installed. This catches
issues like a skill referencing a doc that isn't declared in kit.yaml.
"""

from dataclasses import dataclass
from pathlib import Path

from dot_agent_kit.io.at_reference import parse_at_references
from dot_agent_kit.io.manifest import load_kit_manifest
from dot_agent_kit.models.kit import KitManifest


@dataclass(frozen=True)
class KitReferenceError:
    """An @ reference in a kit artifact that won't resolve when installed.

    Attributes:
        source_artifact: Path relative to kit root (e.g., "skills/my-skill/SKILL.md")
        reference: The @ reference path from the artifact
        error_type: Type of error ("missing_in_manifest")
        suggested_fix: Suggested action to fix the error
    """

    source_artifact: str
    reference: str
    error_type: str
    suggested_fix: str | None


def _get_artifact_install_path(artifact_type: str, artifact_path: str) -> str:
    """Map kit artifact path to installed path in .claude/.

    Args:
        artifact_type: Type from manifest (e.g., "skill", "doc")
        artifact_path: Path relative to kit root (e.g., "skills/foo/SKILL.md")

    Returns:
        Installed path (e.g., ".claude/skills/foo/SKILL.md")
    """
    # Kit artifacts install to .claude/<type>s/<path>
    # But artifact_path already starts with the plural form (skills/, docs/)
    return f".claude/{artifact_path}"


def _build_installed_paths(manifest: KitManifest) -> set[str]:
    """Build set of all paths that will be installed from a kit.

    Args:
        manifest: Kit manifest

    Returns:
        Set of installed paths (e.g., {".claude/skills/foo/SKILL.md", ...})
    """
    installed: set[str] = set()

    for artifact_type, paths in manifest.artifacts.items():
        for path in paths:
            installed_path = _get_artifact_install_path(artifact_type, path)
            installed.add(installed_path)

    return installed


def validate_kit_references(manifest_path: Path) -> list[KitReferenceError]:
    """Validate all @ references in kit artifacts resolve to installed files.

    For each markdown artifact in the kit, parse @ references and check if
    they point to paths that will be installed (either from this kit or
    from the installed location).

    Args:
        manifest_path: Path to kit.yaml

    Returns:
        List of KitReferenceError for references that won't resolve
    """
    if not manifest_path.exists():
        return []

    manifest = load_kit_manifest(manifest_path)
    kit_root = manifest_path.parent

    # Build set of paths that will be installed
    installed_paths = _build_installed_paths(manifest)

    errors: list[KitReferenceError] = []

    # Check each markdown artifact
    for _artifact_type, paths in manifest.artifacts.items():
        for artifact_path in paths:
            if not artifact_path.endswith(".md"):
                continue

            full_path = kit_root / artifact_path
            if not full_path.exists():
                # Missing artifact is a different error (manifest integrity)
                continue

            content = full_path.read_text(encoding="utf-8")
            references = parse_at_references(content)

            for ref in references:
                # Only check .claude/ references - those are what we install
                if not ref.file_path.startswith(".claude/"):
                    continue

                # Check if this reference will be installed
                if ref.file_path not in installed_paths:
                    # Build suggested fix
                    # Extract the relative path from .claude/
                    relative_path = ref.file_path.removeprefix(".claude/")

                    # Determine artifact type from path
                    ref_type = "doc"  # Default
                    if relative_path.startswith("skills/"):
                        ref_type = "skill"
                    elif relative_path.startswith("docs/"):
                        ref_type = "doc"
                    elif relative_path.startswith("commands/"):
                        ref_type = "command"
                    elif relative_path.startswith("agents/"):
                        ref_type = "agent"
                    elif relative_path.startswith("hooks/"):
                        ref_type = "hook"

                    suggested_fix = f"Add '{relative_path}' to artifacts.{ref_type} in kit.yaml"

                    errors.append(
                        KitReferenceError(
                            source_artifact=artifact_path,
                            reference=ref.file_path,
                            error_type="missing_in_manifest",
                            suggested_fix=suggested_fix,
                        )
                    )

    return errors
