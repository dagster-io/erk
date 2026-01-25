"""Tests for promoting tripwire candidates to documentation frontmatter."""

from pathlib import Path

from erk_shared.learn.tripwire_promotion import PromotionResult, promote_tripwire_to_frontmatter


def _create_doc(tmp_path: Path, relative_path: str, content: str) -> Path:
    """Create a doc file under docs/learned/ in a temp project root."""
    full_path = tmp_path / "docs" / "learned" / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


def test_add_tripwire_to_doc_with_existing_tripwires(tmp_path: Path) -> None:
    """Add a tripwire to a doc that already has tripwires in frontmatter."""
    _create_doc(
        tmp_path,
        "architecture/foo.md",
        """\
---
title: Foo Patterns
tripwires:
  - action: "existing action"
    warning: "Existing warning."
---

# Foo Patterns

Content here.
""",
    )

    result = promote_tripwire_to_frontmatter(
        project_root=tmp_path,
        target_doc_path="architecture/foo.md",
        action="new action",
        warning="New warning message.",
    )

    assert result == PromotionResult(
        success=True, target_doc_path="architecture/foo.md", error=None
    )

    # Verify file was updated
    doc_path = tmp_path / "docs" / "learned" / "architecture" / "foo.md"
    content = doc_path.read_text(encoding="utf-8")
    assert "new action" in content
    assert "New warning message." in content
    assert "existing action" in content


def test_add_tripwire_to_doc_without_tripwires_key(tmp_path: Path) -> None:
    """Add a tripwire to a doc that has frontmatter but no tripwires key."""
    _create_doc(
        tmp_path,
        "architecture/bar.md",
        """\
---
title: Bar Patterns
read_when:
  - "doing bar things"
---

# Bar Patterns

Content here.
""",
    )

    result = promote_tripwire_to_frontmatter(
        project_root=tmp_path,
        target_doc_path="architecture/bar.md",
        action="calling bar without baz",
        warning="Always pass baz to bar().",
    )

    assert result.success is True

    content = (tmp_path / "docs" / "learned" / "architecture" / "bar.md").read_text(
        encoding="utf-8"
    )
    assert "calling bar without baz" in content
    assert "Always pass baz to bar()." in content


def test_duplicate_detection(tmp_path: Path) -> None:
    """Skip adding tripwire if same action already exists."""
    _create_doc(
        tmp_path,
        "architecture/dup.md",
        """\
---
title: Dup Test
tripwires:
  - action: "same action"
    warning: "Original warning."
---

# Content
""",
    )

    result = promote_tripwire_to_frontmatter(
        project_root=tmp_path,
        target_doc_path="architecture/dup.md",
        action="same action",
        warning="Different warning text.",
    )

    assert result.success is True

    # File should NOT be modified (original warning preserved)
    content = (tmp_path / "docs" / "learned" / "architecture" / "dup.md").read_text(
        encoding="utf-8"
    )
    assert "Original warning." in content
    assert "Different warning text." not in content


def test_file_not_found(tmp_path: Path) -> None:
    """Return error result when target doc does not exist."""
    result = promote_tripwire_to_frontmatter(
        project_root=tmp_path,
        target_doc_path="architecture/nonexistent.md",
        action="some action",
        warning="Some warning.",
    )

    assert result.success is False
    assert result.error is not None
    assert "File not found" in result.error


def test_no_frontmatter(tmp_path: Path) -> None:
    """Return error result when doc has no frontmatter."""
    _create_doc(
        tmp_path,
        "architecture/nofm.md",
        """\
# No Frontmatter

This doc has no YAML frontmatter.
""",
    )

    result = promote_tripwire_to_frontmatter(
        project_root=tmp_path,
        target_doc_path="architecture/nofm.md",
        action="some action",
        warning="Some warning.",
    )

    assert result.success is False
    assert result.error is not None
    assert "No frontmatter" in result.error


def test_preserves_existing_content(tmp_path: Path) -> None:
    """Verify that existing frontmatter fields and body content are preserved."""
    _create_doc(
        tmp_path,
        "architecture/preserve.md",
        """\
---
title: Preserve Test
read_when:
  - "testing preservation"
tripwires:
  - action: "old action"
    warning: "Old warning."
---

# Preserve Test

Important body content that must be preserved.
""",
    )

    result = promote_tripwire_to_frontmatter(
        project_root=tmp_path,
        target_doc_path="architecture/preserve.md",
        action="new action",
        warning="New warning.",
    )

    assert result.success is True

    content = (tmp_path / "docs" / "learned" / "architecture" / "preserve.md").read_text(
        encoding="utf-8"
    )
    assert "title: Preserve Test" in content
    assert "testing preservation" in content
    assert "old action" in content
    assert "Old warning." in content
    assert "new action" in content
    assert "New warning." in content
    assert "Important body content that must be preserved." in content
