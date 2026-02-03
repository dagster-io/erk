"""Tests for objective_header module."""

import pytest

from erk_shared.gateway.github.metadata.objective_header import (
    create_objective_header_block,
    extract_objective_content,
    extract_objective_parent,
    format_objective_header_body,
    format_objective_issue_body,
)
from erk_shared.gateway.github.metadata.schemas import ObjectiveHeaderSchema


class TestObjectiveHeaderSchema:
    """Tests for ObjectiveHeaderSchema validation."""

    def test_schema_accepts_valid_data_with_parent(self) -> None:
        """Schema accepts valid data with parent_objective."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1", "parent_objective": 123}
        schema.validate(data)  # Should not raise

    def test_schema_accepts_valid_data_without_parent(self) -> None:
        """Schema accepts valid data with parent_objective as None."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1", "parent_objective": None}
        schema.validate(data)  # Should not raise

    def test_schema_accepts_data_without_parent_field(self) -> None:
        """Schema accepts data without parent_objective field."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1"}
        schema.validate(data)  # Should not raise

    def test_schema_rejects_wrong_version(self) -> None:
        """Schema rejects wrong schema_version."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "2", "parent_objective": 123}
        with pytest.raises(ValueError, match="Invalid schema_version"):
            schema.validate(data)

    def test_schema_rejects_missing_version(self) -> None:
        """Schema rejects missing schema_version."""
        schema = ObjectiveHeaderSchema()
        data = {"parent_objective": 123}
        with pytest.raises(ValueError, match="Missing required fields"):
            schema.validate(data)

    def test_schema_rejects_non_integer_parent(self) -> None:
        """Schema rejects non-integer parent_objective."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1", "parent_objective": "123"}
        with pytest.raises(ValueError, match="parent_objective must be an integer"):
            schema.validate(data)

    def test_schema_rejects_zero_parent(self) -> None:
        """Schema rejects zero parent_objective."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1", "parent_objective": 0}
        with pytest.raises(ValueError, match="parent_objective must be positive"):
            schema.validate(data)

    def test_schema_rejects_negative_parent(self) -> None:
        """Schema rejects negative parent_objective."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1", "parent_objective": -1}
        with pytest.raises(ValueError, match="parent_objective must be positive"):
            schema.validate(data)

    def test_schema_rejects_unknown_fields(self) -> None:
        """Schema rejects unknown fields."""
        schema = ObjectiveHeaderSchema()
        data = {"schema_version": "1", "unknown_field": "value"}
        with pytest.raises(ValueError, match="Unknown fields"):
            schema.validate(data)

    def test_get_key_returns_correct_value(self) -> None:
        """get_key() returns 'objective-header'."""
        schema = ObjectiveHeaderSchema()
        assert schema.get_key() == "objective-header"


class TestCreateObjectiveHeaderBlock:
    """Tests for create_objective_header_block function."""

    def test_creates_block_with_parent(self) -> None:
        """Creates metadata block with parent_objective."""
        block = create_objective_header_block(parent_objective=456)

        assert block.key == "objective-header"
        assert block.data.get("schema_version") == "1"
        assert block.data.get("parent_objective") == 456

    def test_creates_block_without_parent(self) -> None:
        """Creates metadata block without parent_objective."""
        block = create_objective_header_block(parent_objective=None)

        assert block.key == "objective-header"
        assert block.data.get("schema_version") == "1"
        assert "parent_objective" not in block.data


class TestFormatObjectiveHeaderBody:
    """Tests for format_objective_header_body function."""

    def test_formats_metadata_with_parent(self) -> None:
        """Formats metadata block markdown with parent_objective."""
        body = format_objective_header_body(parent_objective=789)

        assert "```erk-metadata:objective-header" in body
        assert "schema_version: '1'" in body
        assert "parent_objective: 789" in body

    def test_formats_metadata_without_parent(self) -> None:
        """Formats metadata block markdown without parent_objective."""
        body = format_objective_header_body(parent_objective=None)

        assert "```erk-metadata:objective-header" in body
        assert "schema_version: '1'" in body
        # parent_objective should not appear in YAML when None
        assert "parent_objective" not in body


class TestFormatObjectiveIssueBody:
    """Tests for format_objective_issue_body function."""

    def test_returns_plain_content_when_no_parent(self) -> None:
        """Returns plain content without metadata when parent_objective is None."""
        content = "# My Objective\n\nRoadmap content..."
        body = format_objective_issue_body(
            plan_content=content,
            parent_objective=None,
        )

        assert body == content.strip()
        assert "```erk-metadata" not in body

    def test_prepends_metadata_when_parent_set(self) -> None:
        """Prepends metadata block when parent_objective is set."""
        content = "# Child Objective\n\nRoadmap content..."
        body = format_objective_issue_body(
            plan_content=content,
            parent_objective=999,
        )

        assert "```erk-metadata:objective-header" in body
        assert "parent_objective: 999" in body
        assert "# Child Objective" in body
        assert "Roadmap content..." in body

        # Verify metadata comes before content with blank line separator
        assert body.startswith("```erk-metadata:objective-header")

    def test_strips_leading_trailing_whitespace_from_content(self) -> None:
        """Strips leading and trailing whitespace from plan_content."""
        content = "\n\n  # Objective\n\nContent...  \n\n"
        body = format_objective_issue_body(
            plan_content=content,
            parent_objective=None,
        )

        assert body == "# Objective\n\nContent..."


class TestExtractObjectiveParent:
    """Tests for extract_objective_parent function."""

    def test_extracts_parent_from_issue_with_metadata(self) -> None:
        """Extracts parent_objective from issue body with objective-header."""
        issue_body = """```erk-metadata:objective-header
schema_version: '1'
parent_objective: 111
```

# Child Objective

Content..."""

        parent = extract_objective_parent(issue_body)
        assert parent == 111

    def test_returns_none_for_issue_without_metadata(self) -> None:
        """Returns None for issue body without objective-header."""
        issue_body = "# Standalone Objective\n\nContent..."

        parent = extract_objective_parent(issue_body)
        assert parent is None

    def test_returns_none_when_parent_field_is_none(self) -> None:
        """Returns None when parent_objective field is None."""
        issue_body = """```erk-metadata:objective-header
schema_version: '1'
parent_objective: null
```

# Objective

Content..."""

        parent = extract_objective_parent(issue_body)
        assert parent is None

    def test_returns_none_when_parent_field_missing(self) -> None:
        """Returns None when parent_objective field is missing."""
        issue_body = """```erk-metadata:objective-header
schema_version: '1'
```

# Objective

Content..."""

        parent = extract_objective_parent(issue_body)
        assert parent is None


class TestExtractObjectiveContent:
    """Tests for extract_objective_content function."""

    def test_returns_full_body_when_no_metadata(self) -> None:
        """Returns full body when no metadata block present."""
        issue_body = "# Standalone Objective\n\nFull content..."

        content = extract_objective_content(issue_body)
        assert content == issue_body

    def test_strips_metadata_block_from_body(self) -> None:
        """Strips objective-header metadata block from body."""
        issue_body = """```erk-metadata:objective-header
schema_version: '1'
parent_objective: 222
```

# Child Objective

Roadmap content..."""

        content = extract_objective_content(issue_body)

        assert "```erk-metadata" not in content
        assert "schema_version" not in content
        assert content.startswith("# Child Objective")

    def test_strips_leading_whitespace_after_metadata(self) -> None:
        """Strips leading whitespace after removing metadata block."""
        issue_body = """```erk-metadata:objective-header
schema_version: '1'
```

# Objective

Content..."""

        content = extract_objective_content(issue_body)
        assert content.startswith("# Objective")


class TestRoundtrip:
    """Test round-trip operations: create body with parent, extract parent back."""

    def test_roundtrip_with_parent(self) -> None:
        """Create body with parent_objective, extract parent back."""
        original_content = "# Test Objective\n\nTest content..."
        parent_num = 555

        # Create issue body with parent
        body = format_objective_issue_body(
            plan_content=original_content,
            parent_objective=parent_num,
        )

        # Extract parent back
        extracted_parent = extract_objective_parent(body)
        assert extracted_parent == parent_num

        # Extract content back
        extracted_content = extract_objective_content(body)
        assert extracted_content.strip() == original_content.strip()

    def test_roundtrip_without_parent(self) -> None:
        """Create body without parent_objective, verify plain content."""
        original_content = "# Standalone Objective\n\nStandalone content..."

        # Create issue body without parent
        body = format_objective_issue_body(
            plan_content=original_content,
            parent_objective=None,
        )

        # Extract parent (should be None)
        extracted_parent = extract_objective_parent(body)
        assert extracted_parent is None

        # Body should be exactly the original content (backward compatible)
        assert body == original_content.strip()
