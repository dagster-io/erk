"""Codex compatibility tests for skill frontmatter validation.

Layer 3 (Pure Unit Tests): Validates YAML frontmatter in skill files without
external dependencies. Ensures all skills maintain Codex-compatible format.
"""

from pathlib import Path

import pytest
import yaml

from erk.core.capabilities.codex_portable import (
    CLAUDE_ONLY_SKILLS,
    CODEX_PORTABLE_SKILLS,
)


def _get_claude_skills_dir() -> Path:
    """Get .claude/skills/ directory from repo root."""
    test_file = Path(__file__)
    repo_root = test_file.parent.parent.parent.parent
    claude_skills_dir = repo_root / ".claude" / "skills"
    if not claude_skills_dir.exists():
        raise ValueError(f"Skills directory not found: {claude_skills_dir}")
    return claude_skills_dir


def _get_all_skill_names() -> set[str]:
    """Get all skill directory names from .claude/skills/."""
    claude_skills_dir = _get_claude_skills_dir()
    skill_dirs = [d for d in claude_skills_dir.iterdir() if d.is_dir()]
    return {d.name for d in skill_dirs}


def _parse_skill_frontmatter(skill_path: Path) -> dict[str, str]:
    """Parse YAML frontmatter from SKILL.md file.

    Returns dict with 'name' and 'description' keys if valid.
    Raises ValueError if frontmatter is missing or invalid.
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise ValueError(f"SKILL.md not found in {skill_path}")

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError(f"Missing YAML frontmatter in {skill_md}")

    # Extract frontmatter between --- markers
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid YAML frontmatter format in {skill_md}")

    frontmatter_yaml = parts[1]
    frontmatter = yaml.safe_load(frontmatter_yaml)

    if not isinstance(frontmatter, dict):
        raise ValueError(f"Frontmatter is not a dict in {skill_md}")

    return frontmatter


def test_all_skills_have_codex_required_frontmatter() -> None:
    """Verify all skills have required Codex frontmatter fields.

    Required fields:
    - name: ≤64 chars
    - description: ≤1024 chars
    """
    claude_skills_dir = _get_claude_skills_dir()
    all_skills = _get_all_skill_names()

    failures = []

    for skill_name in sorted(all_skills):
        skill_path = claude_skills_dir / skill_name

        try:
            frontmatter = _parse_skill_frontmatter(skill_path)
        except ValueError as e:
            failures.append(f"{skill_name}: {e}")
            continue

        # Check required fields
        if "name" not in frontmatter:
            failures.append(f"{skill_name}: Missing 'name' field in frontmatter")
            continue

        if "description" not in frontmatter:
            failures.append(f"{skill_name}: Missing 'description' field in frontmatter")
            continue

        # Validate field constraints
        name = frontmatter["name"]
        if not isinstance(name, str):
            failures.append(f"{skill_name}: 'name' must be a string")
        elif len(name) > 64:
            failures.append(f"{skill_name}: 'name' exceeds 64 chars ({len(name)})")

        description = frontmatter["description"]
        if not isinstance(description, str):
            failures.append(f"{skill_name}: 'description' must be a string")
        elif len(description) > 1024:
            failures.append(f"{skill_name}: 'description' exceeds 1024 chars ({len(description)})")

        # Verify name matches directory name
        if name != skill_name:
            failures.append(f"{skill_name}: 'name' field '{name}' doesn't match directory name")

    if failures:
        failure_message = "\n".join(failures)
        pytest.fail(f"Codex frontmatter validation failed:\n{failure_message}")


def test_portable_skills_match_bundled() -> None:
    """Verify every skill in CODEX_PORTABLE_SKILLS exists in .claude/skills/."""
    claude_skills_dir = _get_claude_skills_dir()
    all_skills = _get_all_skill_names()

    missing_skills = CODEX_PORTABLE_SKILLS - all_skills

    if missing_skills:
        pytest.fail(
            f"Skills in CODEX_PORTABLE_SKILLS not found in .claude/skills/: "
            f"{sorted(missing_skills)}"
        )

    # Verify all portable skills have valid frontmatter
    for skill_name in CODEX_PORTABLE_SKILLS:
        skill_path = claude_skills_dir / skill_name
        try:
            _parse_skill_frontmatter(skill_path)
        except ValueError as e:
            pytest.fail(f"Portable skill {skill_name} has invalid frontmatter: {e}")


def test_codex_portable_and_claude_only_cover_all_skills() -> None:
    """Verify union of CODEX_PORTABLE_SKILLS and CLAUDE_ONLY_SKILLS equals all skills.

    No skills should be orphaned (missing from both registries).
    No skills should be duplicated (in both registries).
    """
    all_skills = _get_all_skill_names()

    # Check for duplicates
    duplicates = CODEX_PORTABLE_SKILLS & CLAUDE_ONLY_SKILLS
    if duplicates:
        pytest.fail(
            f"Skills in both CODEX_PORTABLE_SKILLS and CLAUDE_ONLY_SKILLS: {sorted(duplicates)}"
        )

    # Check for orphans
    registered_skills = CODEX_PORTABLE_SKILLS | CLAUDE_ONLY_SKILLS
    orphaned_skills = all_skills - registered_skills

    if orphaned_skills:
        pytest.fail(
            f"Skills not in CODEX_PORTABLE_SKILLS or CLAUDE_ONLY_SKILLS: "
            f"{sorted(orphaned_skills)}\n"
            f"Add these to src/erk/core/capabilities/codex_portable.py"
        )

    # Check for nonexistent skills in registries
    nonexistent_portable = CODEX_PORTABLE_SKILLS - all_skills
    nonexistent_claude = CLAUDE_ONLY_SKILLS - all_skills

    if nonexistent_portable or nonexistent_claude:
        failures = []
        if nonexistent_portable:
            failures.append(
                f"CODEX_PORTABLE_SKILLS contains nonexistent skills: {sorted(nonexistent_portable)}"
            )
        if nonexistent_claude:
            failures.append(
                f"CLAUDE_ONLY_SKILLS contains nonexistent skills: {sorted(nonexistent_claude)}"
            )
        pytest.fail("\n".join(failures))


def test_claude_only_skills_exist() -> None:
    """Verify all skills in CLAUDE_ONLY_SKILLS exist in .claude/skills/."""
    all_skills = _get_all_skill_names()

    missing_skills = CLAUDE_ONLY_SKILLS - all_skills

    if missing_skills:
        pytest.fail(
            f"Skills in CLAUDE_ONLY_SKILLS not found in .claude/skills/: {sorted(missing_skills)}"
        )
