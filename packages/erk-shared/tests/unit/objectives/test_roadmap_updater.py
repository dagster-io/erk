"""Unit tests for the roadmap_updater module.

Tests cover:
- Successful PR column update via LLM
- Error handling (step not found, PR column not empty)
- Multiple tables (original bug case)
- LLM failure handling
"""

from erk_shared.objectives.roadmap_updater import update_roadmap_with_plan
from erk_shared.prompt_executor.fake import FakePromptExecutor

BASIC_ROADMAP = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | pending | |
| 2.2 | Add tests | pending | |
| 2.3 | Update CLI | pending | |
"""

BASIC_ROADMAP_UPDATED_2_1 = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | pending | plan #5999 |
| 2.2 | Add tests | pending | |
| 2.3 | Update CLI | pending | |
"""

BASIC_ROADMAP_UPDATED_2_2 = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | pending | |
| 2.2 | Add tests | pending | plan #6001 |
| 2.3 | Update CLI | pending | |
"""

BASIC_ROADMAP_UPDATED_2_3 = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | pending | |
| 2.2 | Add tests | pending | |
| 2.3 | Update CLI | pending | plan #6002 |
"""

ROADMAP_WITH_EXISTING_PR = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | done | #5892 |
| 2.2 | Add tests | pending | |
"""

ROADMAP_WITH_EXISTING_PR_UPDATED_2_2 = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | done | #5892 |
| 2.2 | Add tests | pending | plan #5999 |
"""

MULTI_TABLE_OBJECTIVE = """# Objective

## Phase 1A - Foundation

| Step | Description | PR |
| ---- | ----------- | -- |
| 1A.1 | Setup base | #5800 |
| 1A.2 | Add config | #5810 |

## Phase 1B - Core Features

| Step | Description | PR |
| ---- | ----------- | -- |
| 1B.1 | Feature one | #5820 |
| 1B.2 | Feature two | |

## Phase 1C - Integration

| Step | Description | PR |
| ---- | ----------- | -- |
| 1C.1 | Integrate all | |
| 1C.2 | Final tests | |
"""

MULTI_TABLE_OBJECTIVE_UPDATED_1C_1 = """# Objective

## Phase 1A - Foundation

| Step | Description | PR |
| ---- | ----------- | -- |
| 1A.1 | Setup base | #5800 |
| 1A.2 | Add config | #5810 |

## Phase 1B - Core Features

| Step | Description | PR |
| ---- | ----------- | -- |
| 1B.1 | Feature one | #5820 |
| 1B.2 | Feature two | |

## Phase 1C - Integration

| Step | Description | PR |
| ---- | ----------- | -- |
| 1C.1 | Integrate all | plan #6000 |
| 1C.2 | Final tests | |
"""

DOCUMENT_WITH_TABLE = """# Objective Title

Some introductory text.

## Roadmap

| Step | Description | PR |
| ---- | ----------- | -- |
| 1.1 | First step | |

## Additional Section

More content here.
"""

DOCUMENT_WITH_TABLE_UPDATED = """# Objective Title

Some introductory text.

## Roadmap

| Step | Description | PR |
| ---- | ----------- | -- |
| 1.1 | First step | plan #100 |

## Additional Section

More content here.
"""


def test_update_roadmap_with_plan_success() -> None:
    """Test updating a roadmap step's PR column."""
    fake_executor = FakePromptExecutor(output=BASIC_ROADMAP_UPDATED_2_1)

    result = update_roadmap_with_plan(
        fake_executor,
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
    fake_executor = FakePromptExecutor(output=BASIC_ROADMAP_UPDATED_2_2)

    result = update_roadmap_with_plan(
        fake_executor,
        BASIC_ROADMAP,
        step_id="2.2",
        plan_issue_number=6001,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #6001" in result.updated_body


def test_update_roadmap_last_step() -> None:
    """Test updating the last step in the table."""
    fake_executor = FakePromptExecutor(output=BASIC_ROADMAP_UPDATED_2_3)

    result = update_roadmap_with_plan(
        fake_executor,
        BASIC_ROADMAP,
        step_id="2.3",
        plan_issue_number=6002,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #6002" in result.updated_body


def test_update_roadmap_step_not_found() -> None:
    """Test error when step_id doesn't match any row."""
    fake_executor = FakePromptExecutor(output="ERROR: Step '9.9' not found in roadmap")

    result = update_roadmap_with_plan(
        fake_executor,
        BASIC_ROADMAP,
        step_id="9.9",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "not found" in result.error


def test_update_roadmap_pr_column_already_has_value() -> None:
    """Test error when PR column already has a value."""
    fake_executor = FakePromptExecutor(output="ERROR: Step 2.1 PR column already has value: #5892")

    result = update_roadmap_with_plan(
        fake_executor,
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
    roadmap_with_plan = """# Objective

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1 | Create type | in_progress | plan #5935 |
| 2.2 | Add tests | pending | |
"""
    fake_executor = FakePromptExecutor(
        output="ERROR: Step 2.1 PR column already has value: plan #5935"
    )

    result = update_roadmap_with_plan(
        fake_executor,
        roadmap_with_plan,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "already has value" in result.error
    assert "plan #5935" in result.error


def test_update_roadmap_llm_failure() -> None:
    """Test error when LLM execution fails."""
    fake_executor = FakePromptExecutor(should_fail=True, error="API rate limited")

    result = update_roadmap_with_plan(
        fake_executor,
        BASIC_ROADMAP,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "API rate limited" in result.error


def test_update_roadmap_preserves_rest_of_document() -> None:
    """Test that update preserves content before and after the table."""
    fake_executor = FakePromptExecutor(output=DOCUMENT_WITH_TABLE_UPDATED)

    result = update_roadmap_with_plan(
        fake_executor,
        DOCUMENT_WITH_TABLE,
        step_id="1.1",
        plan_issue_number=100,
    )

    assert result.success
    assert result.updated_body is not None
    # Verify surrounding content is preserved
    assert "# Objective Title" in result.updated_body
    assert "Some introductory text." in result.updated_body
    assert "## Additional Section" in result.updated_body
    assert "More content here." in result.updated_body
    assert "plan #100" in result.updated_body


def test_update_roadmap_step_in_later_table() -> None:
    """Test finding step in Phase 1C table (not first table).

    This is the original bug case: objectives with multiple phase tables
    where the target step is not in the first table.
    """
    fake_executor = FakePromptExecutor(output=MULTI_TABLE_OBJECTIVE_UPDATED_1C_1)

    result = update_roadmap_with_plan(
        fake_executor,
        MULTI_TABLE_OBJECTIVE,
        step_id="1C.1",
        plan_issue_number=6000,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #6000" in result.updated_body
    # Verify other tables are preserved
    assert "#5800" in result.updated_body  # Phase 1A
    assert "#5820" in result.updated_body  # Phase 1B


def test_update_roadmap_update_empty_cell_in_second_step() -> None:
    """Test updating when first step is done but second is empty."""
    fake_executor = FakePromptExecutor(output=ROADMAP_WITH_EXISTING_PR_UPDATED_2_2)

    result = update_roadmap_with_plan(
        fake_executor,
        ROADMAP_WITH_EXISTING_PR,
        step_id="2.2",
        plan_issue_number=5999,
    )

    assert result.success
    assert result.updated_body is not None
    assert "plan #5999" in result.updated_body
    # First row should be unchanged
    assert "#5892" in result.updated_body


def test_update_roadmap_prompt_contains_required_fields() -> None:
    """Test that the prompt sent to LLM contains required information."""
    fake_executor = FakePromptExecutor(output=BASIC_ROADMAP_UPDATED_2_1)

    update_roadmap_with_plan(
        fake_executor,
        BASIC_ROADMAP,
        step_id="2.1",
        plan_issue_number=5999,
    )

    # Verify the prompt was sent correctly
    assert len(fake_executor.prompt_calls) == 1
    call = fake_executor.prompt_calls[0]
    assert "2.1" in call.prompt  # step_id
    assert "5999" in call.prompt  # plan_issue_number
    assert "# Objective" in call.prompt  # objective_body content
    assert call.model == "haiku"


def test_update_roadmap_invalid_llm_response() -> None:
    """Test error when LLM response doesn't contain expected marker."""
    fake_executor = FakePromptExecutor(output="Some random invalid response")

    result = update_roadmap_with_plan(
        fake_executor,
        BASIC_ROADMAP,
        step_id="2.1",
        plan_issue_number=5999,
    )

    assert not result.success
    assert result.updated_body is None
    assert "missing expected" in result.error
