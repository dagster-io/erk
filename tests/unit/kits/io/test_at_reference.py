"""Tests for @ reference parsing module."""

from erk.kits.io.at_reference import AtReference, parse_at_references


class TestParseAtReferences:
    """Tests for parse_at_references function."""

    def test_parse_simple_reference(self) -> None:
        """Test parsing a simple @AGENTS.md reference."""
        content = "@AGENTS.md"
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "AGENTS.md"
        assert refs[0].fragment is None
        assert refs[0].line_number == 1
        assert refs[0].raw_text == "@AGENTS.md"

    def test_parse_reference_with_fragment(self) -> None:
        """Test parsing @file.md#section reference."""
        content = "@docs/guide.md#installation"
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "docs/guide.md"
        assert refs[0].fragment == "installation"
        assert refs[0].line_number == 1
        assert refs[0].raw_text == "@docs/guide.md#installation"

    def test_parse_relative_path(self) -> None:
        """Test parsing @../other.md relative path reference."""
        content = "@../other.md"
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "../other.md"
        assert refs[0].fragment is None

    def test_parse_dotpath(self) -> None:
        """Test parsing @.agent/kits/registry.md dotpath reference."""
        content = "@.agent/kits/registry.md"
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == ".agent/kits/registry.md"

    def test_parse_home_directory_path(self) -> None:
        """Test parsing @~/.claude/settings.md home directory reference."""
        content = "@~/.claude/settings.md"
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "~/.claude/settings.md"

    def test_ignores_code_blocks(self) -> None:
        """Test that @ references inside fenced code blocks are not matched."""
        content = """Some text

```markdown
@AGENTS.md
@other.md
```

@valid.md
"""
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "valid.md"

    def test_ignores_inline_code(self) -> None:
        """Test that @click.command() and similar inline code are not matched."""
        content = """`@click.command()`
@valid.md
Some text with `@property` decorator
"""
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "valid.md"

    def test_multiple_references(self) -> None:
        """Test parsing multiple @ references in one file."""
        content = """@AGENTS.md

Some text here.

@docs/guide.md#setup

More text.

@.claude/skills/my-skill.md
"""
        refs = parse_at_references(content)

        assert len(refs) == 3
        assert refs[0].file_path == "AGENTS.md"
        assert refs[0].line_number == 1
        assert refs[1].file_path == "docs/guide.md"
        assert refs[1].fragment == "setup"
        assert refs[1].line_number == 5
        assert refs[2].file_path == ".claude/skills/my-skill.md"
        assert refs[2].line_number == 9

    def test_ignores_inline_text_with_at(self) -> None:
        """Test that inline text containing @ is not matched."""
        content = """See @AGENTS.md for more info
@valid.md
Contact us at support@example.com
"""
        refs = parse_at_references(content)

        # Only standalone @valid.md should be matched
        assert len(refs) == 1
        assert refs[0].file_path == "valid.md"

    def test_preserves_line_numbers(self) -> None:
        """Test that line numbers are correctly tracked."""
        content = """Line 1
Line 2
@first.md
Line 4
Line 5
@second.md
"""
        refs = parse_at_references(content)

        assert len(refs) == 2
        assert refs[0].line_number == 3
        assert refs[1].line_number == 6

    def test_empty_content(self) -> None:
        """Test parsing empty content returns empty list."""
        refs = parse_at_references("")
        assert refs == []

    def test_no_references(self) -> None:
        """Test parsing content with no @ references."""
        content = """# Header

Some regular markdown content.

- List item
- Another item
"""
        refs = parse_at_references(content)
        assert refs == []

    def test_ignores_double_backtick_code(self) -> None:
        """Test that ``@example`` double backtick code is ignored."""
        content = """``@decorator``
@valid.md
"""
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "valid.md"

    def test_code_block_toggle(self) -> None:
        """Test that code blocks properly toggle on and off."""
        content = """@first.md
```
@inside-code.md
```
@second.md
```python
@more-code.md
```
@third.md
"""
        refs = parse_at_references(content)

        assert len(refs) == 3
        file_paths = [r.file_path for r in refs]
        assert "first.md" in file_paths
        assert "second.md" in file_paths
        assert "third.md" in file_paths
        assert "inside-code.md" not in file_paths
        assert "more-code.md" not in file_paths

    def test_reference_with_whitespace(self) -> None:
        """Test that references with leading/trailing whitespace are parsed."""
        content = "  @AGENTS.md  "
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].file_path == "AGENTS.md"

    def test_fragment_with_hyphens(self) -> None:
        """Test fragment with hyphens (like anchors)."""
        content = "@docs/guide.md#my-section-name"
        refs = parse_at_references(content)

        assert len(refs) == 1
        assert refs[0].fragment == "my-section-name"


class TestAtReferenceDataclass:
    """Tests for AtReference dataclass."""

    def test_frozen_immutable(self) -> None:
        """Test that AtReference is immutable (frozen)."""
        ref = AtReference(
            raw_text="@AGENTS.md",
            file_path="AGENTS.md",
            fragment=None,
            line_number=1,
        )

        # Should raise FrozenInstanceError when trying to mutate
        try:
            ref.file_path = "other.md"  # type: ignore[misc]
            raise AssertionError("Should have raised an error")
        except AttributeError:
            pass  # Expected behavior for frozen dataclass
