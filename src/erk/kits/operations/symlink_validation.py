"""Symlink validation for managed skills.

This module validates the integrity of the two-layer skill management system:
- Stage 1: Kit sources → .erk/skills/{skill-name}/ (copy or symlink)
- Stage 2: .erk/skills/{skill-name}/ ← .claude/skills/{skill-name}/ (always symlink)

Validation rules:
1. Every managed skill in .erk/skills/ must have exactly one symlink in .claude/skills/
2. Orphaned symlinks (target doesn't exist) → ERROR
3. Missing symlinks (source exists, no symlink) → ERROR
4. Regular files in .claude/skills/ → IGNORED (user-created, not managed)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from erk.kits.models.config import ProjectConfig


@dataclass(frozen=True)
class SymlinkIssue:
    """A single symlink validation issue."""

    severity: Literal["error", "warning"]
    issue_type: Literal["orphaned", "missing", "broken", "wrong_target"]
    path: Path
    message: str


@dataclass(frozen=True)
class SymlinkValidationResult:
    """Result of symlink validation."""

    issues: list[SymlinkIssue]

    @property
    def is_valid(self) -> bool:
        """Return True if no error-level issues exist."""
        return not any(issue.severity == "error" for issue in self.issues)


def _get_managed_skill_names(config: ProjectConfig | None) -> set[str]:
    """Extract skill names from managed_skills paths in config.

    Args:
        config: Project configuration (can be None)

    Returns:
        Set of skill names (e.g., {"my-skill", "other-skill"})
    """
    if config is None:
        return set()

    skill_names: set[str] = set()
    for kit in config.kits.values():
        for managed_path in kit.managed_skills:
            # Path like ".erk/skills/my-skill"
            path = Path(managed_path)
            skill_names.add(path.name)

    return skill_names


def validate_skill_symlinks(
    project_dir: Path,
    config: ProjectConfig | None,
) -> SymlinkValidationResult:
    """Validate symlink integrity between .erk/skills/ and .claude/skills/.

    Checks:
    1. Every directory in .erk/skills/ has a corresponding symlink in .claude/skills/
    2. Every symlink in .claude/skills/ points to a valid target in .erk/skills/
    3. Symlinks point to the correct target (not a different skill)

    Args:
        project_dir: Project root directory
        config: Project configuration (can be None)

    Returns:
        SymlinkValidationResult with list of issues
    """
    issues: list[SymlinkIssue] = []

    erk_skills_dir = project_dir / ".erk" / "skills"
    claude_skills_dir = project_dir / ".claude" / "skills"

    # Get managed skill names from config
    managed_skill_names = _get_managed_skill_names(config)

    # If no managed skills and no .erk/skills directory, nothing to validate
    if not erk_skills_dir.exists() and not managed_skill_names:
        return SymlinkValidationResult(issues=[])

    # Collect .erk/skills directories
    erk_skills: set[str] = set()
    if erk_skills_dir.exists():
        for item in erk_skills_dir.iterdir():
            if item.is_dir() or item.is_symlink():
                erk_skills.add(item.name)

    # Collect .claude/skills symlinks and regular entries
    claude_symlinks: dict[str, Path] = {}  # name -> target
    claude_regular_files: set[str] = set()

    if claude_skills_dir.exists():
        for item in claude_skills_dir.iterdir():
            if item.is_symlink():
                claude_symlinks[item.name] = item
            elif item.is_dir() or item.is_file():
                claude_regular_files.add(item.name)

    # Check 1: Every .erk/skills/{name} that is managed should have a symlink
    for skill_name in erk_skills:
        if skill_name not in managed_skill_names:
            # Not a managed skill (orphaned in .erk/skills), warn
            issues.append(
                SymlinkIssue(
                    severity="warning",
                    issue_type="orphaned",
                    path=erk_skills_dir / skill_name,
                    message=f"Skill '{skill_name}' in .erk/skills/ is not tracked in config",
                )
            )
            continue

        if skill_name not in claude_symlinks:
            # Managed skill missing symlink in .claude/skills
            if skill_name in claude_regular_files:
                # There's a regular file/dir instead of a symlink
                issues.append(
                    SymlinkIssue(
                        severity="error",
                        issue_type="missing",
                        path=claude_skills_dir / skill_name,
                        message=(
                            f"Skill '{skill_name}' exists in .erk/skills/ but "
                            f".claude/skills/{skill_name} is a regular file/directory"
                        ),
                    )
                )
            else:
                # No entry at all in .claude/skills
                issues.append(
                    SymlinkIssue(
                        severity="error",
                        issue_type="missing",
                        path=claude_skills_dir / skill_name,
                        message=f"Skill '{skill_name}' in .erk/skills/ has no symlink",
                    )
                )

    # Check 2: Every symlink in .claude/skills should point to valid .erk/skills target
    for skill_name, symlink_path in claude_symlinks.items():
        # Check if symlink is broken
        if not symlink_path.exists():
            issues.append(
                SymlinkIssue(
                    severity="error",
                    issue_type="broken",
                    path=symlink_path,
                    message=f"Symlink .claude/skills/{skill_name} is broken",
                )
            )
            continue

        # Check if symlink points to the expected .erk/skills location
        resolved_target = symlink_path.resolve()
        expected_target = (erk_skills_dir / skill_name).resolve()

        # Only check wrong_target if .erk/skills/{name} exists
        if (erk_skills_dir / skill_name).exists():
            if resolved_target != expected_target:
                issues.append(
                    SymlinkIssue(
                        severity="warning",
                        issue_type="wrong_target",
                        path=symlink_path,
                        message=(
                            f"Symlink .claude/skills/{skill_name} points to wrong target: "
                            f"{resolved_target}"
                        ),
                    )
                )
        else:
            # Symlink exists but no corresponding .erk/skills entry
            # This could be a user-created symlink pointing elsewhere - just warn
            if skill_name in managed_skill_names:
                issues.append(
                    SymlinkIssue(
                        severity="error",
                        issue_type="orphaned",
                        path=symlink_path,
                        message=f"Symlink .claude/skills/{skill_name} has no .erk/skills/ source",
                    )
                )

    return SymlinkValidationResult(issues=issues)
