from pathlib import Path

import pytest


def test_shared_files_exist():
    """Verify all universal files exist in .claude/docs/dignified-python/ directory."""
    # Documentation now lives in .claude/docs/dignified-python/ (project-level)
    # This test verifies the installed documentation structure
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    docs_dir = repo_root / ".claude" / "docs" / "dignified-python"

    # Check universal reference files at root level
    # Note: Core standards have been consolidated into dignified-python-core.md
    # to reduce duplication and improve maintainability
    universal_files = [
        "dignified-python-core.md",
        "cli-patterns.md",
        "subprocess.md",
        "type-annotations-common.md",
    ]

    for filename in universal_files:
        file_path = docs_dir / filename
        if not file_path.exists():
            pytest.fail(f"Documentation file missing: .claude/docs/dignified-python/{filename}")


def test_type_annotations_files_exist():
    """Verify all version-specific type annotation files exist."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    docs_dir = repo_root / ".claude" / "docs" / "dignified-python"
    version_specific_dir = docs_dir / "version-specific"

    if not version_specific_dir.exists():
        pytest.fail(
            "Version-specific directory missing: .claude/docs/dignified-python/version-specific/"
        )

    # Check version-specific files for each version
    versions = ["310", "311", "312", "313"]
    version_files = [
        "type-annotations.md",
        "pattern-table.md",
        "checklist.md",
    ]

    for version in versions:
        version_dir = version_specific_dir / version
        if not version_dir.exists():
            pytest.fail(
                f"Version directory missing: "
                f".claude/docs/dignified-python/version-specific/{version}/"
            )

        for filename in version_files:
            file_path = version_dir / filename
            if not file_path.exists():
                pytest.fail(
                    f"Version-specific file missing: "
                    f".claude/docs/dignified-python/version-specific/{version}/{filename}"
                )


def test_unified_kit_structure():
    """Verify unified kit has required files and structure."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"
    unified_kit_dir = kits_dir / "dignified-python"

    # Check kit.yaml
    kit_yaml = unified_kit_dir / "kit.yaml"
    if not kit_yaml.exists():
        pytest.fail("Unified kit missing kit.yaml")

    # Check version-aware hook file
    hook_file = unified_kit_dir / "scripts" / "dignified-python" / "version_aware_reminder_hook.py"
    if not hook_file.exists():
        pytest.fail("Unified kit missing hook file version_aware_reminder_hook.py")

    # Check each version-specific skill exists
    versions = ["310", "311", "312", "313"]
    for version in versions:
        skill_dir = unified_kit_dir / "skills" / f"dignified-python-{version}"

        # Check SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            pytest.fail(f"Unified kit missing SKILL.md for version {version}")

        # Check VERSION-CONTEXT.md
        version_context = skill_dir / "VERSION-CONTEXT.md"
        if not version_context.exists():
            pytest.fail(f"Unified kit missing VERSION-CONTEXT.md for version {version}")


def test_skill_references_correct_types():
    """Verify each SKILL.md references correct documentation paths."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"

    versions = ["310", "311", "312", "313"]

    for version in versions:
        skill_md = (
            kits_dir / "dignified-python" / "skills" / f"dignified-python-{version}" / "SKILL.md"
        )
        if not skill_md.exists():
            continue  # Skip if file doesn't exist (caught by other test)

        content = skill_md.read_text(encoding="utf-8")

        # Check that SKILL.md references .claude/docs/dignified-python/ paths
        expected_docs_path = "@.claude/docs/dignified-python/"
        expected_version_specific = f"@.claude/docs/dignified-python/version-specific/{version}/"

        has_docs_reference = expected_docs_path in content
        has_version_specific_reference = expected_version_specific in content

        if not (has_docs_reference and has_version_specific_reference):
            pytest.fail(
                f"Skill {version} SKILL.md does not properly reference documentation paths.\n"
                f"Expected to find both:\n"
                f"  - {expected_docs_path}\n"
                f"  - {expected_version_specific}"
            )


def test_skill_components_exist():
    """Verify core documentation file exists (skill components consolidated)."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    docs_dir = repo_root / ".claude" / "docs" / "dignified-python"

    # Core components have been consolidated into dignified-python-core.md
    core_file = docs_dir / "dignified-python-core.md"
    if not core_file.exists():
        pytest.fail(
            "Core documentation file missing: "
            ".claude/docs/dignified-python/dignified-python-core.md"
        )


def test_no_version_specific_language_in_universal():
    """Verify universal documentation files don't contain version-specific language."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    docs_dir = repo_root / ".claude" / "docs" / "dignified-python"

    # Patterns that should NOT appear in universal files
    prohibited_patterns = [
        "Python 3.13+",
        "3.13 and above",
        "3.13 or higher",
        "Python 3.13 only",
        "Python 3.10+",
        "3.10 and above",
        "3.10 or higher",
        "Python 3.10 only",
    ]

    # Get all markdown files at root level
    # (excluding version-specific and skill-components subdirectories)
    universal_files = [f for f in docs_dir.glob("*.md") if f.is_file() and f.parent == docs_dir]

    for file_path in universal_files:
        content = file_path.read_text(encoding="utf-8")

        for pattern in prohibited_patterns:
            if pattern in content:
                pytest.fail(
                    f"Universal documentation file {file_path.name} contains version-specific "
                    f"language: '{pattern}'\n"
                    f"Universal files must be version-neutral."
                )
