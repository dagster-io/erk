"""Unit tests for the roadmap_updater module.

Tests cover:
- Successful PR column update
- Various table formats
- Error handling for missing tables, columns, steps
- Edge cases (already filled PR column, malformed tables)
"""

from erk_shared.objectives.roadmap_updater import update_roadmap_with_plan

BASIC_ROADMAP = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | pending | |
| 2.2 | Add tests | pending | |
| 2.3 | Update CLI | pending | |
"""

ROADMAP_WITH_EXISTING_PR = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | done | #5892 |
| 2.2 | Add tests | pending | |
"""

ROADMAP_WITH_PLAN_IN_PROGRESS = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | in_progress | plan #5935 |
| 2.2 | Add tests | pending | |
"""

ROADMAP_NO_PR_COLUMN = """# Objective

## Roadmap

| Step | Description | Status |
| ---- | ----------- | ------ |
| 2.1 | Create type | pending |
"""

ROADMAP_NO_STEP_COLUMN = """# Objective

## Roadmap

| ID | Description | PR |
| -- | ----------- | -- |
| 2.1 | Create type | |
"""

NO_TABLE = """# Objective

This objective has no roadmap table.

Just some text.
"""


def test_update_roadmap_with_plan_success() -> None:
    """Test updating a roadmap step's PR column."""
    result = update_roadmap_with_plan(
        BASIC_ROADMAP,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert result.success
    assert result.error is None
    assert result.updated_body is not None
    assert "plan #5999" in result.updated_body
    # Other rows should be unchanged
    assert "| 2.2 |" in result.updated_body
    assert "| 2.3 |" in result.updated_body


def test_update_roadmap_middle_step() -> None:
    """Test updating a step in the middle of the table."""
    result = update_roadmap_with_plan(
        BASIC_ROADMAP,
        step_id="2.2",
        plan_issue_number=6001,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #6001" in result.updated_body


def test_update_roadmap_last_step() -> None:
    """Test updating the last step in the table."""
    result = update_roadmap_with_plan(
        BASIC_ROADMAP,
        step_id="2.3",
        plan_issue_number=6002,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #6002" in result.updated_body


def test_update_roadmap_step_not_found() -> None:
    """Test error when step_id doesn't match any row."""
    result = update_roadmap_with_plan(
        BASIC_ROADMAP,
        step_id="9.9",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "not found" in result.error


def test_update_roadmap_pr_column_already_has_value() -> None:
    """Test error when PR column already has a value."""
    result = update_roadmap_with_plan(
        ROADMAP_WITH_EXISTING_PR,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "already has value" in result.error
    assert "#5892" in result.error


def test_update_roadmap_pr_column_has_plan() -> None:
    """Test error when PR column already has a plan reference."""
    result = update_roadmap_with_plan(
        ROADMAP_WITH_PLAN_IN_PROGRESS,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "already has value" in result.error
    assert "plan #5935" in result.error


def test_update_roadmap_no_table() -> None:
    """Test error when no roadmap table exists."""
    result = update_roadmap_with_plan(
        NO_TABLE,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "No roadmap table found" in result.error


def test_update_roadmap_missing_pr_column() -> None:
    """Test error when table is missing PR column."""
    result = update_roadmap_with_plan(
        ROADMAP_NO_PR_COLUMN,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "missing 'PR' column" in result.error


def test_update_roadmap_missing_step_column() -> None:
    """Test error when table is missing Step column."""
    result = update_roadmap_with_plan(
        ROADMAP_NO_STEP_COLUMN,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "missing 'Step' column" in result.error


def test_update_roadmap_preserves_rest_of_document() -> None:
    """Test that update preserves content before and after the table."""
    body = """# Objective Title

Some introductory text.

## Roadmap

| Step | Description | PR |
| ---- | ----------- | -- |
| 1.1 | First step | |

## Additional Section

More content here.
"""
    result = update_roadmap_with_plan(body, step_id="1.1", plan_issue_number=100)

    assert result.success
    assert result.updated_body is not None
    # Verify surrounding content is preserved
    assert "# Objective Title" in result.updated_body
    assert "Some introductory text." in result.updated_body
    assert "## Additional Section" in result.updated_body
    assert "More content here." in result.updated_body
    assert "plan #100" in result.updated_body


def test_update_roadmap_case_sensitive_step_id() -> None:
    """Test that step ID matching is case-sensitive."""
    body = """| Step | PR |
| ---- | -- |
| 2.1 | |
| 2.1a | |
"""
    # Should match exact step ID "2.1", not "2.1a"
    result = update_roadmap_with_plan(body, step_id="2.1", plan_issue_number=200)

    assert result.success
    assert result.updated_body is not None
    # Verify only the exact match was updated
    lines = result.updated_body.split("\n")
    updated_row = [line for line in lines if "2.1 " in line and "plan #200" in line]
    assert len(updated_row) == 1


def test_update_roadmap_alphanumeric_step_id() -> None:
    """Test handling of alphanumeric step IDs like '2A.1'."""
    body = """| Step | Description | PR |
| ---- | ----------- | -- |
| 2A.1 | Special step | |
"""
    result = update_roadmap_with_plan(body, step_id="2A.1", plan_issue_number=300)

    assert result.success
    assert result.updated_body is not None
    assert "plan #300" in result.updated_body


def test_update_roadmap_with_alignment_colons() -> None:
    """Test handling of tables with alignment colons in separator."""
    body = """| Step | Description | PR |
| :--- | :---------: | --: |
| 1.1 | Centered | |
"""
    result = update_roadmap_with_plan(body, step_id="1.1", plan_issue_number=400)

    assert result.success
    assert result.updated_body is not None
    assert "plan #400" in result.updated_body


def test_update_roadmap_update_empty_cell_in_second_step() -> None:
    """Test updating when first step is done but second is empty."""
    result = update_roadmap_with_plan(
        ROADMAP_WITH_EXISTING_PR,
        step_id="2.2",
        plan_issue_number=5999,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #5999" in result.updated_body
    # First row should be unchanged
    assert "#5892" in result.updated_body
