from pathlib import Path

import pytest


def test_skill_directories_self_contained():
    """Verify each skill directory contains all required documentation files."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"

    versions = ["310", "311", "312", "313"]

    for version in versions:
        skill_dir = kits_dir / "dignified-python" / "skills" / f"dignified-python-{version}"

        # Required files for all versions
        required_files = [
            "SKILL.md",
            "VERSION-CONTEXT.md",
            "dignified-python-core.md",
            "checklist.md",
            "cli-patterns.md",
            "subprocess.md",
            "pattern-table.md",
        ]

        # Version-specific type annotation files
        if version == "313":
            required_files.extend(["type-annotations-common.md", "type-annotations-delta.md"])
        else:
            required_files.append("type-annotations.md")

        for filename in required_files:
            file_path = skill_dir / filename
            if not file_path.exists():
                pytest.fail(
                    f"Self-contained skill {version} missing file: {filename}\n"
                    f"Expected at: {file_path}"
                )


def test_skill_references_use_relative_paths():
    """Verify SKILL.md files use relative references (not absolute paths)."""
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

        # Check that SKILL.md uses relative references (e.g., @dignified-python-core.md)
        # and does NOT use absolute paths (e.g., @.erk/docs/kits/dignified-python/)
        forbidden_patterns = [
            "@.erk/docs/",
            "@.erk/docs/kits/dignified-python/",
            "@.claude/skills/",
        ]

        for pattern in forbidden_patterns:
            if pattern in content:
                pytest.fail(
                    f"Skill {version} SKILL.md uses absolute path reference: '{pattern}'\n"
                    f"SKILL.md should use relative references (e.g., @dignified-python-core.md)"
                )

        # Verify relative references exist
        expected_relative_refs = ["@dignified-python-core.md", "@checklist.md"]

        for ref in expected_relative_refs:
            if ref not in content:
                pytest.fail(f"Skill {version} SKILL.md missing expected relative reference: {ref}")


def test_package_and_project_in_sync():
    """Verify package skill files match project .claude/skills/ files."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent

    package_kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"
    project_skills_dir = project_root / ".claude" / "skills"

    versions = ["310", "311", "312", "313"]

    for version in versions:
        package_skill_dir = (
            package_kits_dir / "dignified-python" / "skills" / f"dignified-python-{version}"
        )
        project_skill_dir = project_skills_dir / f"dignified-python-{version}"

        if not project_skill_dir.exists():
            pytest.fail(
                f"Project skill directory missing: .claude/skills/dignified-python-{version}/"
            )

        # Get all .md files from package
        package_files = set(f.name for f in package_skill_dir.glob("*.md"))
        project_files = set(f.name for f in project_skill_dir.glob("*.md"))

        # Check package files exist in project
        missing_in_project = package_files - project_files
        if missing_in_project:
            pytest.fail(
                f"Skill {version} has files in package but missing in project:\n"
                f"  {missing_in_project}\n"
                f"Run 'erk dev kit-build' to sync."
            )

        # Check project files exist in package (extra files)
        extra_in_project = project_files - package_files
        if extra_in_project:
            pytest.fail(
                f"Skill {version} has extra files in project not in package:\n"
                f"  {extra_in_project}\n"
                f"These files should be in the package source."
            )

        # Verify file contents match
        for filename in package_files:
            package_content = (package_skill_dir / filename).read_text(encoding="utf-8")
            project_content = (project_skill_dir / filename).read_text(encoding="utf-8")

            if package_content != project_content:
                pytest.fail(
                    f"Skill {version}/{filename} content mismatch between package and project.\n"
                    f"Run 'erk dev kit-build' to sync."
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
            "Documentation is now embedded in each skill directory.\n"
            "Delete this directory: rm -rf .erk/docs/kits/dignified-python/"
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

    # Check each version-specific skill exists with full documentation
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

        # Check dignified-python-core.md (embedded in each skill)
        core_md = skill_dir / "dignified-python-core.md"
        if not core_md.exists():
            pytest.fail(f"Unified kit missing dignified-python-core.md for version {version}")


def test_all_doc_files_have_frontmatter():
    """Verify all documentation files have required erk frontmatter."""
    # From tests/integration/kits/kits/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    kits_dir = project_root / "packages" / "erk-kits" / "src" / "erk_kits" / "data" / "kits"

    versions = ["310", "311", "312", "313"]

    for version in versions:
        skill_dir = kits_dir / "dignified-python" / "skills" / f"dignified-python-{version}"

        # Get all .md files
        md_files = list(skill_dir.glob("*.md"))

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
