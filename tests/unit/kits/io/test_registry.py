"""Tests for registry operations."""

from pathlib import Path

from erk.kits.io.registry import (
    add_kit_to_registry,
    create_kit_registry_file,
    generate_registry_entry,
    rebuild_registry,
    remove_kit_from_registry,
)
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.models.kit import KitManifest


def test_generate_registry_entry() -> None:
    """Test registry entry generation from kit manifest."""
    manifest = KitManifest(
        name="test-kit",
        version="1.0.0",
        description="Test kit for registry generation",
        artifacts={
            "agent": ["agents/test-agent/test.md"],
            "command": ["commands/test-cmd/test.md"],
            "doc": ["docs/test/reference.md"],
        },
    )

    installed_kit = InstalledKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/agents/test-agent/test.md"],
    )

    entry = generate_registry_entry("test-kit", "1.0.0", manifest, installed_kit)

    # Verify required fields present
    assert "### test-kit (v1.0.0)" in entry
    assert "**Purpose**: Test kit for registry generation" in entry
    assert "**Usage**:" in entry

    # Verify artifacts listed
    assert "agent: agents/test-agent/test.md" in entry
    assert "command: commands/test-cmd/test.md" in entry

    # Verify usage examples generated
    assert 'Use Task tool with subagent_type="test-agent"' in entry
    assert "Run `/test-cmd` command" in entry


def test_generate_registry_entry_minimal() -> None:
    """Test registry entry with minimal artifacts (doc only)."""
    manifest = KitManifest(
        name="doc-kit",
        version="1.0.0",
        description="Documentation only kit",
        artifacts={
            "doc": ["docs/reference.md"],
        },
    )

    installed_kit = InstalledKit(
        kit_id="doc-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/docs/reference.md"],
    )

    entry = generate_registry_entry("doc-kit", "1.0.0", manifest, installed_kit)

    # Should have fallback usage text
    assert "Reference documentation loaded automatically" in entry


def test_create_kit_registry_file(tmp_path: Path) -> None:
    """Test creating registry entry file."""
    entry_content = "### test-kit (v1.0.0)\n\n**Purpose**: Test\n\n**Usage**: Test usage\n"

    result_path = create_kit_registry_file("test-kit", entry_content, tmp_path)

    # Verify file created
    assert result_path.exists()
    assert result_path == tmp_path / ".erk" / "kits" / "test-kit" / "registry-entry.md"

    # Verify content matches
    assert result_path.read_text(encoding="utf-8") == entry_content


def test_add_kit_to_registry_new_file(tmp_path: Path) -> None:
    """Test adding kit to new registry with structured format."""
    add_kit_to_registry("test-kit", tmp_path, "1.0.0", "bundled")

    registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"

    # Verify registry created
    assert registry_path.exists()

    content = registry_path.read_text(encoding="utf-8")

    # Verify header present
    assert "# Kit Documentation Registry" in content
    assert "AUTO-GENERATED" in content
    assert "BEGIN_ENTRIES" in content
    assert "END_ENTRIES" in content

    # Verify structured entry added
    assert 'ENTRY_START kit_id="test-kit"' in content
    assert "@.erk/kits/test-kit/registry-entry.md" in content


def test_add_kit_to_registry_existing_file(tmp_path: Path) -> None:
    """Test adding kit to existing registry (new structured format)."""
    # First add creates registry
    add_kit_to_registry("existing-kit", tmp_path, "1.0.0", "bundled")

    # Add new kit to existing registry
    add_kit_to_registry("new-kit", tmp_path, "2.0.0", "bundled")

    registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"
    content = registry_path.read_text(encoding="utf-8")

    # Verify structured format
    assert "BEGIN_ENTRIES" in content
    assert "END_ENTRIES" in content

    # Verify both kits present with metadata
    assert 'ENTRY_START kit_id="existing-kit"' in content
    assert 'ENTRY_START kit_id="new-kit"' in content
    assert "@.erk/kits/existing-kit/registry-entry.md" in content
    assert "@.erk/kits/new-kit/registry-entry.md" in content


def test_add_kit_to_registry_duplicate(tmp_path: Path) -> None:
    """Test adding same kit twice (should be idempotent)."""
    # Add kit once
    add_kit_to_registry("test-kit", tmp_path, "1.0.0", "bundled")

    registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"
    content_after_first = registry_path.read_text(encoding="utf-8")

    # Add same kit again
    add_kit_to_registry("test-kit", tmp_path, "1.0.0", "bundled")

    content_after_second = registry_path.read_text(encoding="utf-8")

    # Content should be unchanged
    assert content_after_first == content_after_second

    # Should only appear once
    assert content_after_second.count('kit_id="test-kit"') == 1


def test_remove_kit_from_registry(tmp_path: Path) -> None:
    """Test removing kit from registry."""
    # Create registry with kit
    registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        "# Kit Documentation Registry\n\n"
        "@.erk/kits/kit1/registry-entry.md\n\n"
        "@.erk/kits/kit2/registry-entry.md\n\n"
        "@.erk/kits/kit3/registry-entry.md\n",
        encoding="utf-8",
    )

    # Create kit registry directory
    kit_dir = tmp_path / ".erk" / "kits" / "kit2"
    kit_dir.mkdir(parents=True, exist_ok=True)
    (kit_dir / "registry-entry.md").write_text("content", encoding="utf-8")

    # Remove kit2
    remove_kit_from_registry("kit2", tmp_path)

    content = registry_path.read_text(encoding="utf-8")

    # Verify kit2 removed
    assert "@.erk/kits/kit2/registry-entry.md" not in content

    # Verify other kits still present
    assert "@.erk/kits/kit1/registry-entry.md" in content
    assert "@.erk/kits/kit3/registry-entry.md" in content

    # Verify directory deleted
    assert not kit_dir.exists()


def test_remove_kit_from_registry_nonexistent(tmp_path: Path) -> None:
    """Test removing nonexistent kit (should not error)."""
    # Create empty registry
    registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("# Kit Documentation Registry\n\n", encoding="utf-8")

    # Should not raise
    remove_kit_from_registry("nonexistent-kit", tmp_path)


def test_rebuild_registry(tmp_path: Path) -> None:
    """Test rebuilding entire registry from installed kits."""
    # Note: This test requires actual kit manifests to be resolvable
    # For now, we test with empty config (no kits installed)

    config = ProjectConfig(version="1", kits={})

    rebuild_registry(tmp_path, config)

    registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"

    # Verify registry created
    assert registry_path.exists()

    content = registry_path.read_text(encoding="utf-8")

    # Verify header present
    assert "# Kit Documentation Registry" in content
    assert "AUTO-GENERATED" in content


def test_generate_registry_entry_with_skill() -> None:
    """Test registry entry with skill artifact."""
    manifest = KitManifest(
        name="skill-kit",
        version="1.0.0",
        description="Kit with skill",
        artifacts={
            "skill": ["skills/test-skill/SKILL.md"],
        },
    )

    installed_kit = InstalledKit(
        kit_id="skill-kit",
        source_type="bundled",
        version="1.0.0",
        artifacts=[".claude/skills/test-skill/SKILL.md"],
    )

    entry = generate_registry_entry("skill-kit", "1.0.0", manifest, installed_kit)

    # Verify skill usage example
    assert "Load `test-skill` skill" in entry


def test_parse_doc_registry_entries() -> None:
    """Test parsing structured registry entries."""
    from erk.kits.io.registry import parse_doc_registry_entries

    content = """# Kit Documentation Registry

<!-- BEGIN_ENTRIES -->

<!-- ENTRY_START kit_id="devrun" version="0.1.0" source="bundled" -->
@.erk/kits/devrun/registry-entry.md
<!-- ENTRY_END -->

<!-- ENTRY_START kit_id="gt" version="0.2.0" source="standalone" -->
@.erk/kits/gt/registry-entry.md
<!-- ENTRY_END -->

<!-- END_ENTRIES -->
"""

    entries = parse_doc_registry_entries(content)

    # Should parse both entries
    assert len(entries) == 2

    # Check first entry
    assert entries[0].kit_id == "devrun"
    assert entries[0].version == "0.1.0"
    assert entries[0].source_type == "bundled"
    assert entries[0].include_path == ".erk/kits/devrun/registry-entry.md"

    # Check second entry
    assert entries[1].kit_id == "gt"
    assert entries[1].version == "0.2.0"
    assert entries[1].source_type == "standalone"


def test_generate_doc_registry_content() -> None:
    """Test generating registry content from entries."""
    from erk.kits.io.registry import DocRegistryEntry, generate_doc_registry_content

    entries = [
        DocRegistryEntry(
            kit_id="kit-b",
            version="2.0.0",
            source_type="bundled",
            include_path=".erk/kits/kit-b/registry-entry.md",
        ),
        DocRegistryEntry(
            kit_id="kit-a",
            version="1.0.0",
            source_type="standalone",
            include_path=".erk/kits/kit-a/registry-entry.md",
        ),
    ]

    content = generate_doc_registry_content(entries)

    # Should have structured format
    assert "BEGIN_ENTRIES" in content
    assert "END_ENTRIES" in content
    assert "REGISTRY_VERSION: 1" in content

    # Should be sorted alphabetically (kit-a before kit-b)
    kit_a_pos = content.find('kit_id="kit-a"')
    kit_b_pos = content.find('kit_id="kit-b"')
    assert kit_a_pos < kit_b_pos  # kit-a should come before kit-b

    # Should have metadata
    assert 'version="1.0.0"' in content
    assert 'source="standalone"' in content


def test_old_format_migration() -> None:
    """Test migration from old format to new format."""
    from erk.kits.io.state import save_project_config
    from erk.kits.models.config import ProjectConfig

    tmp_path = Path("/tmp/test_migration")
    tmp_path.mkdir(exist_ok=True)

    try:
        # Create old format registry
        registry_path = tmp_path / ".erk" / "kits" / "kit-registry.md"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(
            "# Kit Documentation Registry\n\n@.erk/kits/old-kit/registry-entry.md\n",
            encoding="utf-8",
        )

        # Create kits.toml with kit info
        config = ProjectConfig(
            version="1",
            kits={
                "old-kit": InstalledKit(
                    kit_id="old-kit",
                    source_type="bundled",
                    version="1.0.0",
                    artifacts=[],
                )
            },
        )
        save_project_config(tmp_path, config)

        # Add another kit - should trigger migration
        add_kit_to_registry("new-kit", tmp_path, "2.0.0", "bundled")

        content = registry_path.read_text(encoding="utf-8")

        # Should have migrated to new format
        assert "BEGIN_ENTRIES" in content
        assert "END_ENTRIES" in content
        assert 'kit_id="old-kit"' in content
        assert 'kit_id="new-kit"' in content
    finally:
        # Cleanup
        if tmp_path.exists():
            import shutil

            shutil.rmtree(tmp_path)
