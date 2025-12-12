"""Artifact validation operations."""

from dataclasses import dataclass
from pathlib import Path

from erk.kits.io.state import load_project_config
from erk.kits.models.artifact import ARTIFACT_TARGET_DIRS


@dataclass(frozen=True)
class ValidationResult:
    """Result of artifact validation."""

    artifact_path: Path
    is_valid: bool
    errors: list[str]


def validate_artifact(artifact_path: Path) -> ValidationResult:
    """Validate a single artifact file exists."""
    if not artifact_path.exists():
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=False,
            errors=["File does not exist"],
        )

    # Simple validation: just check that the file exists and is readable
    try:
        _ = artifact_path.read_text(encoding="utf-8")
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=True,
            errors=[],
        )
    except Exception as e:
        return ValidationResult(
            artifact_path=artifact_path,
            is_valid=False,
            errors=[f"Cannot read file: {e}"],
        )


def validate_project(project_dir: Path) -> list[ValidationResult]:
    """Validate only managed artifacts (installed from kits) in project."""
    results: list[ValidationResult] = []

    # Load config to get list of managed artifacts
    config = load_project_config(project_dir)
    if not config:
        return results

    # Collect all managed artifact paths from all installed kits
    # Artifact paths are stored relative to project root (e.g., ".claude/commands/...")
    # or just the relative path within the base directory (e.g., "commands/...")
    managed_paths: set[str] = set()
    for kit in config.kits.values():
        for artifact_path in kit.artifacts:
            managed_paths.add(artifact_path)

    # Validate all managed artifacts
    for managed_path in managed_paths:
        # Artifact paths can be stored with or without base directory prefix
        # Check if path already starts with a known base directory
        full_path: Path | None = None
        for base_dir in ARTIFACT_TARGET_DIRS.values():
            if managed_path.startswith(f"{base_dir}/"):
                # Path already includes base directory
                full_path = project_dir / managed_path
                break

        if full_path is None:
            # Path doesn't start with a known base - assume .claude/ (legacy behavior)
            full_path = project_dir / ".claude" / managed_path

        result = validate_artifact(full_path)
        results.append(result)

    return results
