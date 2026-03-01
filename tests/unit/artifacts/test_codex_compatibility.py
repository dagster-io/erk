"""Codex compatibility tests for skill frontmatter validation.

Layer 3 (Pure Unit Tests): Validates YAML frontmatter in skill files without
external dependencies. Ensures all skills maintain Codex-compatible format.
"""

import tomllib
from pathlib import Path

import pytest
import yaml

from erk.core.capabilities.codex_portable import (
    claude_only_skills,
    codex_portable_skills,
)


def _get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent.parent


def _get_claude_skills_dir() -> Path:
    """Get .claude/skills/ directory from repo root."""
    claude_skills_dir = _get_repo_root() / ".claude" / "skills"
    if not claude_skills_dir.exists():
        raise ValueError(f"Skills directory not found: {claude_skills_dir}")
    return claude_skills_dir


def _get_all_skill_names() -> set[str]:
    """Get all skill directory names from .claude/skills/."""
    claude_skills_dir = _get_claude_skills_dir()
    skill_dirs = [d for d in claude_skills_dir.iterdir() if d.is_dir()]
    return {d.name for d in skill_dirs}


def _get_force_included_skill_names() -> set[str]:
    """Get skill names from pyproject.toml force-include entries."""
    pyproject_path = _get_repo_root() / "pyproject.toml"
    if not pyproject_path.exists():
        raise ValueError(f"pyproject.toml not found: {pyproject_path}")

    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    force_include = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )

    skill_names: set[str] = set()
    prefix = ".claude/skills/"
    for source_path in force_include:
        if source_path.startswith(prefix):
            # Extract skill name: ".claude/skills/foo" -> "foo"
            skill_name = source_path[len(prefix) :]
            if "/" not in skill_name:
                skill_names.add(skill_name)

    return skill_names


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
    """Verify every skill in codex_portable_skills() exists in .claude/skills/."""
    claude_skills_dir = _get_claude_skills_dir()
    all_skills = _get_all_skill_names()

    missing_skills = codex_portable_skills() - all_skills

    if missing_skills:
        pytest.fail(
            f"Skills in codex_portable_skills() not found in .claude/skills/: "
            f"{sorted(missing_skills)}"
        )

    # Verify all portable skills have valid frontmatter
    for skill_name in codex_portable_skills():
        skill_path = claude_skills_dir / skill_name
        try:
            _parse_skill_frontmatter(skill_path)
        except ValueError as e:
            pytest.fail(f"Portable skill {skill_name} has invalid frontmatter: {e}")


def test_codex_portable_and_claude_only_cover_all_skills() -> None:
    """Verify union of codex_portable_skills() and claude_only_skills() equals all skills.

    No skills should be orphaned (missing from both registries).
    No skills should be duplicated (in both registries).
    """
    all_skills = _get_all_skill_names()

    # Check for duplicates
    duplicates = codex_portable_skills() & claude_only_skills()
    if duplicates:
        pytest.fail(
            f"Skills in both codex_portable_skills() and claude_only_skills(): {sorted(duplicates)}"
        )

    # Check for orphans
    registered_skills = codex_portable_skills() | claude_only_skills()
    orphaned_skills = all_skills - registered_skills

    if orphaned_skills:
        pytest.fail(
            f"Skills not in codex_portable_skills() or claude_only_skills(): "
            f"{sorted(orphaned_skills)}\n"
            f"Add these to src/erk/core/capabilities/codex_portable.py"
        )

    # Check for nonexistent skills in registries
    nonexistent_portable = codex_portable_skills() - all_skills
    nonexistent_claude = claude_only_skills() - all_skills

    if nonexistent_portable or nonexistent_claude:
        failures = []
        if nonexistent_portable:
            failures.append(
                f"codex_portable_skills() contains nonexistent skills: "
                f"{sorted(nonexistent_portable)}"
            )
        if nonexistent_claude:
            failures.append(
                f"claude_only_skills() contains nonexistent skills: {sorted(nonexistent_claude)}"
            )
        pytest.fail("\n".join(failures))


def test_claude_only_skills_exist() -> None:
    """Verify all skills in claude_only_skills() exist in .claude/skills/."""
    all_skills = _get_all_skill_names()

    missing_skills = claude_only_skills() - all_skills

    if missing_skills:
        pytest.fail(
            f"Skills in claude_only_skills() not found in .claude/skills/: {sorted(missing_skills)}"
        )


def test_codex_portable_skills_match_force_include() -> None:
    """Verify pyproject.toml force-include entries match codex_portable_skills() exactly.

    If someone adds a skill to codex_portable_skills() but forgets the pyproject.toml
    force-include entry, the wheel won't contain the skill. If someone removes a skill
    from the portable list but leaves the force-include entry, the wheel will contain
    a skill that shouldn't be distributed.
    """
    portable = codex_portable_skills()
    force_included = _get_force_included_skill_names()

    missing_from_pyproject = portable - force_included
    extra_in_pyproject = force_included - portable

    failures = []
    if missing_from_pyproject:
        failures.append(
            f"Skills in codex_portable_skills() missing from pyproject.toml "
            f"[tool.hatch.build.targets.wheel.force-include]: {sorted(missing_from_pyproject)}\n"
            f"Add force-include entries for these skills in pyproject.toml"
        )
    if extra_in_pyproject:
        failures.append(
            f"Skills in pyproject.toml force-include not in codex_portable_skills(): "
            f"{sorted(extra_in_pyproject)}\n"
            f"Add these to codex_portable_skills() in "
            f"src/erk/core/capabilities/codex_portable.py, or remove the "
            f"force-include entries from pyproject.toml"
        )

    if failures:
        pytest.fail("\n".join(failures))
