"""Tests for objective metadata extraction: slug, comment_id, and content."""

from erk_shared.gateway.github.metadata.core import (
    extract_objective_from_comment,
    extract_objective_header_comment_id,
    extract_objective_slug,
    format_objective_content_comment,
)


def test_extract_objective_header_comment_id_found() -> None:
    """Extract objective_comment_id from objective-header block when present."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-15T10:30:00Z'
created_by: user123
objective_comment_id: 42

```

</details>
<!-- /erk:metadata-block:objective-header -->"""

    result = extract_objective_header_comment_id(issue_body)
    assert result == 42


def test_extract_objective_header_comment_id_missing_block() -> None:
    """Return None when objective-header block is missing."""
    issue_body = "This is a plain issue body without any metadata blocks."

    result = extract_objective_header_comment_id(issue_body)
    assert result is None


def test_extract_objective_header_comment_id_null() -> None:
    """Return None when objective_comment_id is null."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-15T10:30:00Z'
created_by: user123
objective_comment_id: null

```

</details>
<!-- /erk:metadata-block:objective-header -->"""

    result = extract_objective_header_comment_id(issue_body)
    assert result is None


def test_extract_objective_from_comment_new_format() -> None:
    """Extract objective content from objective-body metadata block."""
    comment_body = format_objective_content_comment("# My Objective\n\n1. Step one\n2. Step two")

    result = extract_objective_from_comment(comment_body)
    assert result is not None
    assert "# My Objective" in result
    assert "1. Step one" in result
    assert "2. Step two" in result


def test_extract_objective_from_comment_no_block() -> None:
    """Return None when no objective-body block found."""
    comment_body = "Just a plain comment without metadata blocks."

    result = extract_objective_from_comment(comment_body)
    assert result is None


def test_extract_objective_from_comment_details_open() -> None:
    """Extract content from <details open> variant."""
    comment_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-body -->
<details open>
<summary><strong>Objective</strong></summary>

# Objective Content

- Item A
- Item B

</details>
<!-- /erk:metadata-block:objective-body -->"""

    result = extract_objective_from_comment(comment_body)
    assert result is not None
    assert "# Objective Content" in result
    assert "- Item A" in result


def test_extract_objective_slug_found() -> None:
    """Extract slug from objective-header block when present."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-15T10:30:00Z'
created_by: user123
slug: tui-redesign

```

</details>
<!-- /erk:metadata-block:objective-header -->"""

    result = extract_objective_slug(issue_body)
    assert result == "tui-redesign"


def test_extract_objective_slug_missing_block() -> None:
    """Return None when objective-header block is missing."""
    issue_body = "This is a plain issue body without any metadata blocks."

    result = extract_objective_slug(issue_body)
    assert result is None


def test_extract_objective_slug_missing_field() -> None:
    """Return None when slug field is not in objective-header block."""
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:objective-header -->
<details>
<summary><code>objective-header</code></summary>

```yaml

created_at: '2025-01-15T10:30:00Z'
created_by: user123
objective_comment_id: 42

```

</details>
<!-- /erk:metadata-block:objective-header -->"""

    result = extract_objective_slug(issue_body)
    assert result is None
