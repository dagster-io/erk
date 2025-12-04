"""Tests for agent documentation validation operations."""

from pathlib import Path

from dot_agent_kit.models.agent_doc import AgentDocFrontmatter
from dot_agent_kit.operations.agent_docs import (
    collect_valid_docs,
    discover_agent_docs,
    generate_category_index,
    generate_root_index,
    parse_frontmatter,
    sync_agent_docs,
    validate_agent_doc_file,
    validate_agent_doc_frontmatter,
    validate_agent_docs,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parse_valid_frontmatter(self) -> None:
        """Parse valid YAML frontmatter."""
        content = """---
title: Test Document
read_when:
  - "creating something"
  - "doing something else"
---

# Content here
"""
        parsed, error = parse_frontmatter(content)
        assert error is None
        assert parsed == {
            "title": "Test Document",
            "read_when": ["creating something", "doing something else"],
        }

    def test_parse_no_frontmatter(self) -> None:
        """Return error when no frontmatter found."""
        content = "# Just a markdown file"
        parsed, error = parse_frontmatter(content)
        assert parsed is None
        assert error is not None
        assert "No frontmatter found" in error

    def test_parse_invalid_yaml(self) -> None:
        """Return error for invalid YAML."""
        content = """---
title: [invalid yaml
---
"""
        parsed, error = parse_frontmatter(content)
        assert parsed is None
        assert error is not None
        assert "Invalid YAML" in error

    def test_parse_non_dict_frontmatter(self) -> None:
        """Return error when frontmatter is not a mapping."""
        content = """---
- just
- a
- list
---
"""
        parsed, error = parse_frontmatter(content)
        assert parsed is None
        assert error is not None
        assert "not a valid YAML mapping" in error


class TestValidateAgentDocFrontmatter:
    """Tests for validate_agent_doc_frontmatter function."""

    def test_validate_valid_frontmatter(self) -> None:
        """Validate correctly structured frontmatter."""
        data = {
            "title": "Test Document",
            "read_when": ["when creating", "when deleting"],
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert len(errors) == 0
        assert frontmatter is not None
        assert frontmatter.title == "Test Document"
        assert frontmatter.read_when == ["when creating", "when deleting"]

    def test_validate_missing_title(self) -> None:
        """Detect missing title field."""
        data = {
            "read_when": ["when creating"],
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert frontmatter is None
        assert any("Missing required field: title" in e for e in errors)

    def test_validate_missing_read_when(self) -> None:
        """Detect missing read_when field."""
        data = {
            "title": "Test Document",
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert frontmatter is None
        assert any("Missing required field: read_when" in e for e in errors)

    def test_validate_title_not_string(self) -> None:
        """Detect non-string title."""
        data = {
            "title": 123,
            "read_when": ["when creating"],
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert frontmatter is None
        assert any("must be a string" in e for e in errors)

    def test_validate_read_when_not_list(self) -> None:
        """Detect non-list read_when."""
        data = {
            "title": "Test Document",
            "read_when": "just a string",
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert frontmatter is None
        assert any("must be a list" in e for e in errors)

    def test_validate_read_when_empty(self) -> None:
        """Detect empty read_when list."""
        data = {
            "title": "Test Document",
            "read_when": [],
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert frontmatter is None
        assert any("must not be empty" in e for e in errors)

    def test_validate_read_when_item_not_string(self) -> None:
        """Detect non-string items in read_when."""
        data = {
            "title": "Test Document",
            "read_when": ["valid", 123, "also valid"],
        }
        frontmatter, errors = validate_agent_doc_frontmatter(data)
        assert frontmatter is None
        assert any("read_when[1]" in e and "must be a string" in e for e in errors)


class TestValidateAgentDocFile:
    """Tests for validate_agent_doc_file function."""

    def test_validate_valid_file(self, tmp_path: Path) -> None:
        """Validate a properly formatted file."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        doc_file = agent_docs / "test.md"
        doc_file.write_text(
            """---
title: Test Document
read_when:
  - "when testing"
---

# Test Content
""",
            encoding="utf-8",
        )

        result = validate_agent_doc_file(doc_file, agent_docs)
        assert result.is_valid is True
        assert result.file_path == "test.md"
        assert len(result.errors) == 0
        assert result.frontmatter is not None
        assert result.frontmatter.title == "Test Document"

    def test_validate_file_missing(self, tmp_path: Path) -> None:
        """Return error for non-existent file."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        doc_file = agent_docs / "missing.md"

        result = validate_agent_doc_file(doc_file, agent_docs)
        assert result.is_valid is False
        assert any("does not exist" in e for e in result.errors)

    def test_validate_file_no_frontmatter(self, tmp_path: Path) -> None:
        """Return error for file without frontmatter."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        doc_file = agent_docs / "no-frontmatter.md"
        doc_file.write_text("# Just content\n", encoding="utf-8")

        result = validate_agent_doc_file(doc_file, agent_docs)
        assert result.is_valid is False
        assert any("No frontmatter found" in e for e in result.errors)

    def test_validate_file_in_subdirectory(self, tmp_path: Path) -> None:
        """Validate file in a subdirectory."""
        agent_docs = tmp_path / "docs" / "agent"
        subdir = agent_docs / "planning"
        subdir.mkdir(parents=True)
        doc_file = subdir / "lifecycle.md"
        doc_file.write_text(
            """---
title: Plan Lifecycle
read_when:
  - "creating a plan"
---

# Content
""",
            encoding="utf-8",
        )

        result = validate_agent_doc_file(doc_file, agent_docs)
        assert result.is_valid is True
        assert result.file_path == "planning/lifecycle.md"


class TestDiscoverAgentDocs:
    """Tests for discover_agent_docs function."""

    def test_discover_no_directory(self, tmp_path: Path) -> None:
        """Return empty list when directory doesn't exist."""
        agent_docs = tmp_path / "docs" / "agent"
        files = discover_agent_docs(agent_docs)
        assert files == []

    def test_discover_files(self, tmp_path: Path) -> None:
        """Discover markdown files in docs/agent."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        (agent_docs / "one.md").write_text("content", encoding="utf-8")
        (agent_docs / "two.md").write_text("content", encoding="utf-8")

        files = discover_agent_docs(agent_docs)
        assert len(files) == 2
        assert any("one.md" in str(f) for f in files)
        assert any("two.md" in str(f) for f in files)

    def test_discover_skips_index_files(self, tmp_path: Path) -> None:
        """Skip index.md files (auto-generated)."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        (agent_docs / "index.md").write_text("auto-generated", encoding="utf-8")
        (agent_docs / "real-doc.md").write_text("content", encoding="utf-8")

        files = discover_agent_docs(agent_docs)
        assert len(files) == 1
        assert "real-doc.md" in str(files[0])

    def test_discover_includes_subdirectories(self, tmp_path: Path) -> None:
        """Include files in subdirectories."""
        agent_docs = tmp_path / "docs" / "agent"
        subdir = agent_docs / "cli"
        subdir.mkdir(parents=True)
        (subdir / "output-styling.md").write_text("content", encoding="utf-8")

        files = discover_agent_docs(agent_docs)
        assert len(files) == 1
        assert "cli" in str(files[0])


class TestValidateAgentDocs:
    """Tests for validate_agent_docs function."""

    def test_validate_no_docs_directory(self, tmp_path: Path) -> None:
        """Return empty list when docs/agent doesn't exist."""
        results = validate_agent_docs(tmp_path)
        assert results == []

    def test_validate_multiple_files(self, tmp_path: Path) -> None:
        """Validate multiple files and return results."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)

        # Valid file
        (agent_docs / "valid.md").write_text(
            """---
title: Valid Doc
read_when:
  - "when valid"
---
""",
            encoding="utf-8",
        )

        # Invalid file
        (agent_docs / "invalid.md").write_text(
            "# No frontmatter",
            encoding="utf-8",
        )

        results = validate_agent_docs(tmp_path)
        assert len(results) == 2

        valid_results = [r for r in results if r.is_valid]
        invalid_results = [r for r in results if not r.is_valid]

        assert len(valid_results) == 1
        assert len(invalid_results) == 1


class TestAgentDocFrontmatter:
    """Tests for AgentDocFrontmatter dataclass."""

    def test_is_valid_with_all_fields(self) -> None:
        """is_valid returns True when all fields present."""
        frontmatter = AgentDocFrontmatter(
            title="Test",
            read_when=["when testing"],
        )
        assert frontmatter.is_valid() is True

    def test_is_valid_empty_title(self) -> None:
        """is_valid returns False for empty title."""
        frontmatter = AgentDocFrontmatter(
            title="",
            read_when=["when testing"],
        )
        assert frontmatter.is_valid() is False

    def test_is_valid_empty_read_when(self) -> None:
        """is_valid returns False for empty read_when."""
        frontmatter = AgentDocFrontmatter(
            title="Test",
            read_when=[],
        )
        assert frontmatter.is_valid() is False


def _create_valid_doc(path: Path, title: str, read_when: list[str]) -> None:
    """Helper to create a valid doc file with frontmatter."""
    read_when_yaml = "\n".join(f'  - "{item}"' for item in read_when)
    content = f"""---
title: {title}
read_when:
{read_when_yaml}
---

# {title}
"""
    path.write_text(content, encoding="utf-8")


class TestCollectValidDocs:
    """Tests for collect_valid_docs function."""

    def test_collect_no_directory(self, tmp_path: Path) -> None:
        """Return empty when directory doesn't exist."""
        uncategorized, categories, invalid = collect_valid_docs(tmp_path)
        assert uncategorized == []
        assert categories == []
        assert invalid == 0

    def test_collect_uncategorized_docs(self, tmp_path: Path) -> None:
        """Collect docs at root level as uncategorized."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        _create_valid_doc(agent_docs / "glossary.md", "Glossary", ["understanding terms"])
        _create_valid_doc(agent_docs / "guide.md", "Guide", ["getting started"])

        uncategorized, categories, invalid = collect_valid_docs(tmp_path)
        assert len(uncategorized) == 2
        assert len(categories) == 0
        assert invalid == 0

    def test_collect_categorized_docs(self, tmp_path: Path) -> None:
        """Collect docs in subdirectories as categorized."""
        agent_docs = tmp_path / "docs" / "agent"
        planning = agent_docs / "planning"
        planning.mkdir(parents=True)
        _create_valid_doc(planning / "lifecycle.md", "Lifecycle", ["creating plans"])
        _create_valid_doc(planning / "enrichment.md", "Enrichment", ["enriching plans"])

        uncategorized, categories, invalid = collect_valid_docs(tmp_path)
        assert len(uncategorized) == 0
        assert len(categories) == 1
        assert categories[0].name == "planning"
        assert len(categories[0].docs) == 2

    def test_collect_skips_invalid_docs(self, tmp_path: Path) -> None:
        """Skip docs with invalid frontmatter."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        _create_valid_doc(agent_docs / "valid.md", "Valid", ["when valid"])
        (agent_docs / "invalid.md").write_text("# No frontmatter", encoding="utf-8")

        uncategorized, categories, invalid = collect_valid_docs(tmp_path)
        assert len(uncategorized) == 1
        assert invalid == 1


class TestGenerateRootIndex:
    """Tests for generate_root_index function."""

    def test_generate_empty_index(self) -> None:
        """Generate index when no docs."""
        content = generate_root_index([], [])
        assert "# Agent Documentation" in content
        assert "*No documentation files found.*" in content

    def test_generate_with_uncategorized(self) -> None:
        """Generate index with uncategorized docs using bullet list format."""
        from dot_agent_kit.operations.agent_docs import DocInfo

        docs = [
            DocInfo("glossary.md", AgentDocFrontmatter("Glossary", ["understanding terms"])),
        ]
        content = generate_root_index(docs, [])
        assert "## Uncategorized" in content
        # Bullet list format: - **[link](link)** — description
        assert "- **[glossary.md](glossary.md)** — understanding terms" in content
        # No table syntax
        assert "|" not in content

    def test_generate_with_categories(self) -> None:
        """Generate index with categories using bullet list format."""
        from dot_agent_kit.operations.agent_docs import CategoryInfo, DocInfo

        categories = [
            CategoryInfo(
                "planning",
                [DocInfo("planning/lifecycle.md", AgentDocFrontmatter("Lifecycle", ["creating"]))],
            ),
        ]
        content = generate_root_index([], categories)
        assert "## Categories" in content
        # Bullet list format: - **[link](link)** — doc names
        assert "- **[planning/](planning/)** — lifecycle" in content
        # No table syntax
        assert "|" not in content


class TestGenerateCategoryIndex:
    """Tests for generate_category_index function."""

    def test_generate_category_index(self) -> None:
        """Generate category index with docs using bullet list format."""
        from dot_agent_kit.operations.agent_docs import CategoryInfo, DocInfo

        category = CategoryInfo(
            "planning",
            [
                DocInfo(
                    "planning/lifecycle.md", AgentDocFrontmatter("Lifecycle", ["creating plans"])
                ),
                DocInfo(
                    "planning/enrichment.md",
                    AgentDocFrontmatter("Enrichment", ["enriching plans"]),
                ),
            ],
        )
        content = generate_category_index(category)
        assert "# Planning Documentation" in content
        # Bullet list format: - **[link](link)** — description
        assert "- **[lifecycle.md](lifecycle.md)** — creating plans" in content
        assert "- **[enrichment.md](enrichment.md)** — enriching plans" in content
        # No table syntax
        assert "|" not in content

    def test_title_formatting(self) -> None:
        """Format category name as title case."""
        from dot_agent_kit.operations.agent_docs import CategoryInfo, DocInfo

        category = CategoryInfo(
            "cli-patterns",
            [DocInfo("cli-patterns/a.md", AgentDocFrontmatter("A", ["x"]))],
        )
        content = generate_category_index(category)
        assert "# Cli Patterns Documentation" in content
        # Bullet list format
        assert "- **[a.md](a.md)** — x" in content
        # No table syntax
        assert "|" not in content


class TestSyncAgentDocs:
    """Tests for sync_agent_docs function."""

    def test_sync_no_directory(self, tmp_path: Path) -> None:
        """Return empty result when no docs directory."""
        result = sync_agent_docs(tmp_path)
        assert result.created == []
        assert result.updated == []
        assert result.unchanged == []

    def test_sync_creates_root_index(self, tmp_path: Path) -> None:
        """Create root index.md when it doesn't exist."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        _create_valid_doc(agent_docs / "glossary.md", "Glossary", ["terms"])

        result = sync_agent_docs(tmp_path)
        assert len(result.created) == 1
        assert "index.md" in result.created[0]

        # Verify file was created with bullet list format
        index_path = agent_docs / "index.md"
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "- **[glossary.md](glossary.md)** — terms" in content
        # No table syntax
        assert "|" not in content

    def test_sync_creates_category_index(self, tmp_path: Path) -> None:
        """Create category index when 2+ docs in subdirectory."""
        agent_docs = tmp_path / "docs" / "agent"
        planning = agent_docs / "planning"
        planning.mkdir(parents=True)
        _create_valid_doc(planning / "lifecycle.md", "Lifecycle", ["creating"])
        _create_valid_doc(planning / "enrichment.md", "Enrichment", ["enriching"])

        result = sync_agent_docs(tmp_path)
        # Should create root index and planning index
        assert len(result.created) == 2

        # Verify category index
        category_index = planning / "index.md"
        assert category_index.exists()

    def test_sync_skips_single_doc_category(self, tmp_path: Path) -> None:
        """Don't create category index for single doc."""
        agent_docs = tmp_path / "docs" / "agent"
        planning = agent_docs / "planning"
        planning.mkdir(parents=True)
        _create_valid_doc(planning / "lifecycle.md", "Lifecycle", ["creating"])

        result = sync_agent_docs(tmp_path)
        # Should only create root index
        assert len(result.created) == 1

        # No category index
        category_index = planning / "index.md"
        assert not category_index.exists()

    def test_sync_dry_run(self, tmp_path: Path) -> None:
        """Dry run doesn't write files."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        _create_valid_doc(agent_docs / "glossary.md", "Glossary", ["terms"])

        result = sync_agent_docs(tmp_path, dry_run=True)
        assert len(result.created) == 1

        # Verify file was NOT created
        index_path = agent_docs / "index.md"
        assert not index_path.exists()

    def test_sync_unchanged_index(self, tmp_path: Path) -> None:
        """Report unchanged when content matches."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        _create_valid_doc(agent_docs / "glossary.md", "Glossary", ["terms"])

        # First sync creates
        sync_agent_docs(tmp_path)

        # Second sync should find unchanged
        result = sync_agent_docs(tmp_path)
        assert len(result.unchanged) == 1
        assert len(result.created) == 0
        assert len(result.updated) == 0

    def test_sync_updated_index(self, tmp_path: Path) -> None:
        """Report updated when content changes."""
        agent_docs = tmp_path / "docs" / "agent"
        agent_docs.mkdir(parents=True)
        _create_valid_doc(agent_docs / "glossary.md", "Glossary", ["terms"])

        # First sync
        sync_agent_docs(tmp_path)

        # Add another doc
        _create_valid_doc(agent_docs / "guide.md", "Guide", ["getting started"])

        # Second sync should update
        result = sync_agent_docs(tmp_path)
        assert len(result.updated) == 1
        assert len(result.created) == 0
