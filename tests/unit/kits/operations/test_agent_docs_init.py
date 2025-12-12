"""Tests for agent documentation initialization operations."""

from pathlib import Path

from erk.kits.operations.agent_docs import (
    AGENT_DOCS_DIR,
    DOCS_AGENT_TEMPLATE_FILES,
    InitResult,
    _load_docs_agent_templates,
    check_docs_agent_ready,
    init_docs_agent,
    parse_frontmatter,
    validate_agent_doc_frontmatter,
)


class TestDocsAgentTemplates:
    """Tests for .erk/docs/agent template files."""

    def test_templates_have_valid_frontmatter(self) -> None:
        """All templates must have valid frontmatter to pass validation."""
        templates = _load_docs_agent_templates()
        for filename, content in templates.items():
            parsed, parse_error = parse_frontmatter(content)
            assert parse_error is None, f"{filename}: {parse_error}"
            assert parsed is not None, f"{filename}: no frontmatter parsed"

            frontmatter, validation_errors = validate_agent_doc_frontmatter(parsed)
            assert len(validation_errors) == 0, f"{filename}: {validation_errors}"
            assert frontmatter is not None, f"{filename}: frontmatter is None"
            assert frontmatter.title, f"{filename}: empty title"
            assert frontmatter.read_when, f"{filename}: empty read_when"

    def test_templates_include_expected_files(self) -> None:
        """Templates include glossary, conventions, and guide."""
        assert "glossary.md" in DOCS_AGENT_TEMPLATE_FILES
        assert "conventions.md" in DOCS_AGENT_TEMPLATE_FILES
        assert "guide.md" in DOCS_AGENT_TEMPLATE_FILES


class TestInitDocsAgent:
    """Tests for init_docs_agent function."""

    def test_init_creates_directory_when_missing(self, tmp_path: Path) -> None:
        """Create .erk/docs/agent directory if it doesn't exist."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        assert not agent_docs.exists()

        result = init_docs_agent(tmp_path)

        assert agent_docs.exists()
        assert len(result.created) == len(DOCS_AGENT_TEMPLATE_FILES)
        assert result.skipped == []
        assert result.overwritten == []

    def test_init_creates_template_files(self, tmp_path: Path) -> None:
        """Create all template files with correct content."""
        result = init_docs_agent(tmp_path)
        agent_docs = tmp_path / AGENT_DOCS_DIR
        templates = _load_docs_agent_templates()

        for filename in DOCS_AGENT_TEMPLATE_FILES:
            file_path = agent_docs / filename
            assert file_path.exists(), f"{filename} was not created"

            expected_rel_path = f"{AGENT_DOCS_DIR}/{filename}"
            assert expected_rel_path in result.created

            content = file_path.read_text(encoding="utf-8")
            assert content == templates[filename]

    def test_init_skips_existing_files_without_force(self, tmp_path: Path) -> None:
        """Skip existing files when force=False."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        agent_docs.mkdir(parents=True)

        # Create one existing file with custom content
        glossary_path = agent_docs / "glossary.md"
        custom_content = "# My Custom Glossary\n"
        glossary_path.write_text(custom_content, encoding="utf-8")

        result = init_docs_agent(tmp_path, force=False)

        # glossary.md should be skipped
        assert f"{AGENT_DOCS_DIR}/glossary.md" in result.skipped
        assert f"{AGENT_DOCS_DIR}/glossary.md" not in result.created
        assert f"{AGENT_DOCS_DIR}/glossary.md" not in result.overwritten

        # Custom content should be preserved
        assert glossary_path.read_text(encoding="utf-8") == custom_content

        # Other templates should be created
        assert f"{AGENT_DOCS_DIR}/conventions.md" in result.created
        assert f"{AGENT_DOCS_DIR}/guide.md" in result.created

    def test_init_overwrites_existing_files_with_force(self, tmp_path: Path) -> None:
        """Overwrite existing files when force=True."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        agent_docs.mkdir(parents=True)

        # Create existing file with custom content
        glossary_path = agent_docs / "glossary.md"
        custom_content = "# My Custom Glossary\n"
        glossary_path.write_text(custom_content, encoding="utf-8")

        result = init_docs_agent(tmp_path, force=True)

        # glossary.md should be overwritten
        assert f"{AGENT_DOCS_DIR}/glossary.md" in result.overwritten
        assert f"{AGENT_DOCS_DIR}/glossary.md" not in result.created
        assert f"{AGENT_DOCS_DIR}/glossary.md" not in result.skipped

        # Content should be replaced with template
        templates = _load_docs_agent_templates()
        assert glossary_path.read_text(encoding="utf-8") == templates["glossary.md"]

    def test_init_returns_correct_result_type(self, tmp_path: Path) -> None:
        """Return InitResult dataclass with correct structure."""
        result = init_docs_agent(tmp_path)

        assert isinstance(result, InitResult)
        assert isinstance(result.created, list)
        assert isinstance(result.skipped, list)
        assert isinstance(result.overwritten, list)

    def test_init_idempotent_with_force(self, tmp_path: Path) -> None:
        """Running init twice with force produces same result."""
        # First run
        init_docs_agent(tmp_path, force=True)

        # Second run with force
        result = init_docs_agent(tmp_path, force=True)

        # All files should be overwritten (not created)
        assert len(result.overwritten) == len(DOCS_AGENT_TEMPLATE_FILES)
        assert len(result.created) == 0
        assert len(result.skipped) == 0


class TestCheckDocsAgentReady:
    """Tests for check_docs_agent_ready function."""

    def test_check_returns_false_when_directory_missing(self, tmp_path: Path) -> None:
        """Return False when .erk/docs/agent directory doesn't exist."""
        is_ready, warning = check_docs_agent_ready(tmp_path)

        assert is_ready is False
        assert warning is not None
        assert "does not exist" in warning

    def test_check_returns_false_when_directory_empty(self, tmp_path: Path) -> None:
        """Return False when .erk/docs/agent exists but has no .md files."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        agent_docs.mkdir(parents=True)

        is_ready, warning = check_docs_agent_ready(tmp_path)

        assert is_ready is False
        assert warning is not None
        assert "no documentation files" in warning

    def test_check_returns_false_when_only_index_exists(self, tmp_path: Path) -> None:
        """Return False when only index.md exists (auto-generated)."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        agent_docs.mkdir(parents=True)
        (agent_docs / "index.md").write_text("# Auto-generated", encoding="utf-8")

        is_ready, warning = check_docs_agent_ready(tmp_path)

        assert is_ready is False
        assert warning is not None
        assert "no documentation files" in warning

    def test_check_returns_true_when_has_md_files(self, tmp_path: Path) -> None:
        """Return True when .erk/docs/agent has at least one .md file."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        agent_docs.mkdir(parents=True)
        (agent_docs / "glossary.md").write_text("# Glossary", encoding="utf-8")

        is_ready, warning = check_docs_agent_ready(tmp_path)

        assert is_ready is True
        assert warning is None

    def test_check_returns_true_after_init(self, tmp_path: Path) -> None:
        """Return True after running init_docs_agent."""
        # First check - should fail
        is_ready, _ = check_docs_agent_ready(tmp_path)
        assert is_ready is False

        # Run init
        init_docs_agent(tmp_path)

        # Second check - should pass
        is_ready, warning = check_docs_agent_ready(tmp_path)
        assert is_ready is True
        assert warning is None

    def test_check_ignores_subdirectories_in_glob(self, tmp_path: Path) -> None:
        """Only check root-level .md files, not subdirectories."""
        agent_docs = tmp_path / AGENT_DOCS_DIR
        subdir = agent_docs / "planning"
        subdir.mkdir(parents=True)
        # File in subdirectory only
        (subdir / "lifecycle.md").write_text("# Lifecycle", encoding="utf-8")

        is_ready, warning = check_docs_agent_ready(tmp_path)

        # Should fail - no root-level .md files
        assert is_ready is False
        assert warning is not None
        assert "no documentation files" in warning


class TestInitResultDataclass:
    """Tests for InitResult dataclass."""

    def test_init_result_immutable(self) -> None:
        """InitResult is immutable (frozen)."""
        result = InitResult(created=["a"], skipped=["b"], overwritten=["c"])

        try:
            result.created = ["modified"]  # type: ignore
            msg = "Should have raised FrozenInstanceError"
            raise AssertionError(msg)
        except AttributeError:
            pass  # Expected - frozen dataclass

    def test_init_result_lists_are_shallow_copied(self) -> None:
        """Lists passed to InitResult are the same objects (not deep copied)."""
        created = ["a"]
        result = InitResult(created=created, skipped=[], overwritten=[])

        # Lists are the same objects (frozen doesn't deep copy)
        assert result.created is created
