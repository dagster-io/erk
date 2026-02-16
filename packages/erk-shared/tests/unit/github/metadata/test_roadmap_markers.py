"""Tests for roadmap table HTML comment markers."""

from erk_shared.gateway.github.metadata.roadmap import (
    extract_roadmap_table_section,
    wrap_roadmap_tables_with_markers,
)


def test_wrap_adds_markers_around_roadmap() -> None:
    """Markers wrap the entire roadmap section from first phase to last table row."""
    content = """# Objective

Some description.

## Roadmap

### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup infra | pending | - | - |
| 1.2 | Add tests | done | - | #100 |

### Phase 2: Core

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 2.1 | Build feature | pending | - | - |

## Notes

Some notes after roadmap.
"""
    result = wrap_roadmap_tables_with_markers(content)

    assert "<!-- erk:roadmap-table -->" in result
    assert "<!-- /erk:roadmap-table -->" in result
    # Markers should wrap the roadmap section
    start_idx = result.index("<!-- erk:roadmap-table -->")
    end_idx = result.index("<!-- /erk:roadmap-table -->")
    assert start_idx < end_idx
    # Phase headers should be inside markers
    section = result[start_idx:end_idx]
    assert "### Phase 1: Foundation" in section
    assert "### Phase 2: Core" in section
    assert "| 2.1 |" in section
    # Content after roadmap should be outside markers
    after = result[end_idx:]
    assert "Some notes after roadmap." in after


def test_wrap_no_phases_returns_unchanged() -> None:
    """Content without phase headers is returned unchanged."""
    content = "# Objective\n\nNo roadmap here.\n"
    result = wrap_roadmap_tables_with_markers(content)

    assert result == content
    assert "<!-- erk:roadmap-table -->" not in result


def test_wrap_replaces_existing_markers() -> None:
    """Existing markers are replaced, not duplicated."""
    content = """<!-- erk:roadmap-table -->
### Phase 1: Foundation

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Setup | pending | - | - |
<!-- /erk:roadmap-table -->
"""
    result = wrap_roadmap_tables_with_markers(content)

    # Should have exactly one pair of markers
    assert result.count("<!-- erk:roadmap-table -->") == 1
    assert result.count("<!-- /erk:roadmap-table -->") == 1


def test_extract_returns_section_when_markers_present() -> None:
    """Extract returns the section between markers."""
    text = """Some prefix.
<!-- erk:roadmap-table -->
### Phase 1: Test
| 1.1 | Step | pending | - | - |
<!-- /erk:roadmap-table -->
Some suffix."""

    result = extract_roadmap_table_section(text)

    assert result is not None
    section, start, end = result
    assert "### Phase 1: Test" in section
    assert "| 1.1 |" in section
    # Verify offsets
    assert text[start:].startswith("<!-- erk:roadmap-table -->")
    assert text[:end].endswith("<!-- /erk:roadmap-table -->")


def test_extract_returns_none_without_markers() -> None:
    """Extract returns None when no markers are present."""
    text = """### Phase 1: Test
| 1.1 | Step | pending | - | - |
"""
    result = extract_roadmap_table_section(text)

    assert result is None


def test_extract_returns_none_with_only_start_marker() -> None:
    """Extract returns None when only start marker is present."""
    text = """<!-- erk:roadmap-table -->
### Phase 1: Test
| 1.1 | Step | pending | - | - |
"""
    result = extract_roadmap_table_section(text)

    assert result is None


def test_wrap_single_phase() -> None:
    """Single phase is wrapped correctly."""
    content = """### Phase 1: Only Phase

| Step | Description | Status | Plan | PR |
|------|-------------|--------|------|-----|
| 1.1 | Step one | pending | - | - |
"""
    result = wrap_roadmap_tables_with_markers(content)

    assert "<!-- erk:roadmap-table -->" in result
    assert "<!-- /erk:roadmap-table -->" in result
    section = extract_roadmap_table_section(result)
    assert section is not None
    assert "### Phase 1: Only Phase" in section[0]
    assert "| 1.1 |" in section[0]
