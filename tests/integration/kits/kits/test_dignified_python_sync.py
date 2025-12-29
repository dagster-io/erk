from pathlib import Path

import pytest


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

    # Check unified skill directory exists
    unified_skill_dir = unified_kit_dir / "skills" / "dignified-python"
    if not unified_skill_dir.exists():
        pytest.fail("Unified skill directory missing: skills/dignified-python/")

    # Check required root-level documentation files
    required_docs = [
        "SKILL.md",
        "dignified-python-core.md",
        "cli-patterns.md",
        "subprocess.md",
    ]

    for doc in required_docs:
        doc_path = unified_skill_dir / doc
        if not doc_path.exists():
            pytest.fail(f"Unified skill missing {doc}")

    # Check version-specific files in versions/ subdirectory
    versions_dir = unified_skill_dir / "versions"
    if not versions_dir.exists():
        pytest.fail("Unified skill missing versions/ subdirectory")

    python_versions = ["python-3.10.md", "python-3.11.md", "python-3.12.md", "python-3.13.md"]
    for version_file in python_versions:
        version_path = versions_dir / version_file
        if not version_path.exists():
            pytest.fail(f"Unified skill missing {version_file} in versions/")


def test_skill_md_has_valid_references():
    """Verify SKILL.md uses relative references (not absolute paths)."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"

    skill_md = kits_dir / "dignified-python" / "skills" / "dignified-python" / "SKILL.md"
    if not skill_md.exists():
        pytest.fail("SKILL.md not found")

    content = skill_md.read_text(encoding="utf-8")

    # Check that SKILL.md uses relative references
    # and does NOT use absolute paths
    forbidden_patterns = [
        "@.erk/docs/",
        "@.erk/docs/kits/dignified-python/",
        "@.claude/skills/",
    ]

    for pattern in forbidden_patterns:
        if pattern in content:
            pytest.fail(
                f"SKILL.md uses absolute path reference: '{pattern}'\n"
                "SKILL.md should use relative references "
                "(e.g., @dignified-python-core.md or @versions/python-3.13.md)"
            )


def test_package_and_project_in_sync():
    """Verify package skill files match project .claude/skills/ files."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent

    package_kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"
    project_skills_dir = project_root / ".claude" / "skills"

    package_skill_dir = package_kits_dir / "dignified-python" / "skills" / "dignified-python"
    project_skill_dir = project_skills_dir / "dignified-python"

    if not project_skill_dir.exists():
        pytest.fail(
            f"Project skill directory missing: .claude/skills/dignified-python/\n"
            f"Expected at: {project_skill_dir}"
        )

    # Get all files from package (including subdirectories like versions/)
    package_files = set(
        f.relative_to(package_skill_dir) for f in package_skill_dir.rglob("*") if f.is_file()
    )
    project_files = set(
        f.relative_to(project_skill_dir) for f in project_skill_dir.rglob("*") if f.is_file()
    )

    # Check package files exist in project
    missing_in_project = package_files - project_files
    if missing_in_project:
        pytest.fail(
            f"Skill has files in package but missing in project:\n"
            f"  {sorted(missing_in_project)}\n"
            f"Run 'erk dev kit-build' to sync."
        )

    # Check project files exist in package (extra files)
    extra_in_project = project_files - package_files
    if extra_in_project:
        pytest.fail(
            f"Skill has extra files in project not in package:\n"
            f"  {sorted(extra_in_project)}\n"
            f"These files should be in the package source."
        )

    # Verify file contents match (only for .md files)
    for rel_path in package_files:
        if rel_path.suffix == ".md":
            package_content = (package_skill_dir / rel_path).read_text(encoding="utf-8")
            project_content = (project_skill_dir / rel_path).read_text(encoding="utf-8")

            if package_content != project_content:
                pytest.fail(
                    f"Skill/{rel_path} content mismatch between package and project.\n"
                    f"Run 'erk dev kit-build' to sync."
                )


def test_all_doc_files_have_frontmatter():
    """Verify all documentation files have required erk frontmatter."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"

    skill_dir = kits_dir / "dignified-python" / "skills" / "dignified-python"

    # Get all .md files (including versions/ subdirectory)
    md_files = list(skill_dir.rglob("*.md"))

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")

        # Check for frontmatter (must start with ---)
        if not content.strip().startswith("---"):
            pytest.fail(
                f"File missing frontmatter: {md_file.relative_to(project_root)}\n"
                f"All doc files must have 'erk: kit: dignified-python' frontmatter."
            )

        # Check for erk: kit: dignified-python in frontmatter
        # Find the end of frontmatter
        if content.count("---") < 2:
            pytest.fail(
                f"Invalid frontmatter in: {md_file.relative_to(project_root)}\n"
                f"Frontmatter must be enclosed with --- delimiters."
            )

        frontmatter_end = content.find("---", 3)  # Skip first ---
        frontmatter = content[3:frontmatter_end]

        if "kit: dignified-python" not in frontmatter:
            pytest.fail(
                f"File missing kit identifier in frontmatter: "
                f"{md_file.relative_to(project_root)}\n"
                f"Frontmatter must include 'erk: kit: dignified-python'."
            )


def test_no_docs_in_erk_docs_kits():
    """Verify dignified-python docs have been removed from .erk/docs/kits/."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    obsolete_docs_dir = project_root / ".erk" / "docs" / "kits" / "dignified-python"

    if obsolete_docs_dir.exists():
        pytest.fail(
            "Obsolete documentation directory still exists: "
            ".erk/docs/kits/dignified-python/\n"
            "Documentation is now embedded in the unified skill directory.\n"
            "Delete this directory: rm -rf .erk/docs/kits/dignified-python/"
        )
