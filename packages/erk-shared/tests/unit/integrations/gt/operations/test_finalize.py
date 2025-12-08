"""Unit tests for is_extraction_plan function.

Tests extraction plan detection for PR bodies.

Note: build_pr_body_footer tests are in tests/unit/github/test_pr_footer.py
"""

from pathlib import Path

from erk_shared.integrations.gt.operations.finalize import is_extraction_plan


class TestIsExtractionPlan:
    """Tests for is_extraction_plan function."""

    def test_returns_false_when_plan_md_does_not_exist(self, tmp_path: Path) -> None:
        """Test that function returns False when plan.md doesn't exist."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()

        result = is_extraction_plan(impl_dir)

        assert result is False

    def test_returns_false_when_impl_dir_does_not_exist(self, tmp_path: Path) -> None:
        """Test that function returns False when .impl/ doesn't exist."""
        impl_dir = tmp_path / ".impl"

        result = is_extraction_plan(impl_dir)

        assert result is False

    def test_returns_false_when_no_plan_header_block(self, tmp_path: Path) -> None:
        """Test returns False when plan.md has no plan-header metadata block."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_file = impl_dir / "plan.md"
        plan_file.write_text("# Plan\n\nJust a regular plan.", encoding="utf-8")

        result = is_extraction_plan(impl_dir)

        assert result is False

    def test_returns_false_when_plan_type_is_standard(self, tmp_path: Path) -> None:
        """Test returns False when plan_type is 'standard'."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_file = impl_dir / "plan.md"
        plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: "2"
created_at: "2025-01-01T00:00:00Z"
created_by: "testuser"
plan_type: standard
last_dispatched_run_id: null
last_dispatched_node_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan

Standard plan content.
"""
        plan_file.write_text(plan_content, encoding="utf-8")

        result = is_extraction_plan(impl_dir)

        assert result is False

    def test_returns_false_when_plan_type_is_missing(self, tmp_path: Path) -> None:
        """Test returns False when plan_type field is not present."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_file = impl_dir / "plan.md"
        plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: "2"
created_at: "2025-01-01T00:00:00Z"
created_by: "testuser"
last_dispatched_run_id: null
last_dispatched_node_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Plan

Plan without plan_type field.
"""
        plan_file.write_text(plan_content, encoding="utf-8")

        result = is_extraction_plan(impl_dir)

        assert result is False

    def test_returns_true_when_plan_type_is_extraction(self, tmp_path: Path) -> None:
        """Test returns True when plan_type is 'extraction'."""
        impl_dir = tmp_path / ".impl"
        impl_dir.mkdir()
        plan_file = impl_dir / "plan.md"
        plan_content = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: "2"
created_at: "2025-01-01T00:00:00Z"
created_by: "testuser"
plan_type: extraction
source_plan_issues:
- 123
extraction_session_ids:
- "abc123"
last_dispatched_run_id: null
last_dispatched_node_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

# Extraction Plan

Plan for extracting documentation.
"""
        plan_file.write_text(plan_content, encoding="utf-8")

        result = is_extraction_plan(impl_dir)

        assert result is True
