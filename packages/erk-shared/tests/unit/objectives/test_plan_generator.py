"""Unit tests for the plan_generator module.

Tests cover:
- Successful plan generation from step context
- Error handling for LLM failures
- Title extraction from generated plan
- Fallback title generation when H1 is missing
"""

from erk_shared.objectives.plan_generator import (
    GeneratedPlan,
    PlanGenerationError,
    generate_plan_for_step,
)
from erk_shared.prompt_executor.fake import FakePromptExecutor

SAMPLE_OBJECTIVE = """# Test Objective

## Goal

Enable the objective reconciler to automatically create plan issues.

## Design Decisions

1. Keep reconciler logic pure
2. Reuse existing infrastructure

## Roadmap

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 4.1 | Generate plan content | pending | |
| 4.2 | Create plan issue | pending | |
"""

SAMPLE_PLAN_OUTPUT = """# Step 4.1: Generate Plan Content

**Part of Objective #5934, Step 4.1**

## Goal

Generate plan markdown from objective step context.

## Implementation Approach

### Design Decisions

1. Use Haiku for generation (cost-effective)
2. Extract context from objective body

---

## Phase 1: Implement Plan Generator

### Files to Create/Modify

**New file**: `plan_generator.py`

### Tests

Add unit tests with FakePromptExecutor.

---

## Verification

Run pytest tests.

---

## Dependencies

- Requires: `dignified-python` skill
- Requires: `fake-driven-testing` skill
"""


def test_generate_plan_for_step_success() -> None:
    """Test successful plan generation from step context."""
    executor = FakePromptExecutor(output=SAMPLE_PLAN_OUTPUT)

    result = generate_plan_for_step(
        executor,
        objective_body=SAMPLE_OBJECTIVE,
        objective_number=5934,
        step_id="4.1",
        step_description="Generate plan content",
        phase_name="Phase 4: Plan Generation",
    )

    assert isinstance(result, GeneratedPlan)
    assert "# Step 4.1" in result.content
    assert "Part of Objective #5934" in result.content
    assert "Step 4.1: Generate Plan Content" in result.title


def test_generate_plan_for_step_extracts_title_from_h1() -> None:
    """Test that title is extracted from the H1 heading."""
    plan_with_custom_title = """# Custom Plan Title

## Goal

Some goal.
"""
    executor = FakePromptExecutor(output=plan_with_custom_title)

    result = generate_plan_for_step(
        executor,
        objective_body=SAMPLE_OBJECTIVE,
        objective_number=5934,
        step_id="4.1",
        step_description="Generate plan content",
        phase_name="Phase 4",
    )

    assert isinstance(result, GeneratedPlan)
    assert result.title == "Custom Plan Title"


def test_generate_plan_for_step_fallback_title_when_no_h1() -> None:
    """Test fallback title generation when H1 is missing."""
    plan_without_h1 = """## Goal

No H1 in this plan.

## Implementation

Some content.
"""
    executor = FakePromptExecutor(output=plan_without_h1)

    result = generate_plan_for_step(
        executor,
        objective_body=SAMPLE_OBJECTIVE,
        objective_number=5934,
        step_id="2.1",
        step_description="Create ReconcileAction type",
        phase_name="Phase 2",
    )

    assert isinstance(result, GeneratedPlan)
    assert result.title == "Step 2.1: Create ReconcileAction type"


def test_generate_plan_for_step_llm_failure() -> None:
    """Test plan generation handles LLM errors gracefully."""
    executor = FakePromptExecutor(
        should_fail=True,
        error="Rate limited",
    )

    result = generate_plan_for_step(
        executor,
        objective_body=SAMPLE_OBJECTIVE,
        objective_number=5934,
        step_id="4.1",
        step_description="Generate plan content",
        phase_name="Phase 4",
    )

    assert isinstance(result, PlanGenerationError)
    assert "Rate limited" in result.message


def test_generate_plan_for_step_passes_context_to_prompt() -> None:
    """Verify the objective body and step info are passed through to prompt."""
    executor = FakePromptExecutor(output="# Plan\n\nContent")

    generate_plan_for_step(
        executor,
        objective_body="My unique objective content",
        objective_number=1234,
        step_id="X.Y",
        step_description="My step description",
        phase_name="My Phase Name",
    )

    assert len(executor.prompt_calls) == 1
    prompt = executor.prompt_calls[0].prompt

    # Verify all context is in the prompt
    assert "My unique objective content" in prompt
    assert "#1234" in prompt
    assert "X.Y" in prompt
    assert "My step description" in prompt
    assert "My Phase Name" in prompt


def test_generate_plan_for_step_uses_haiku_model() -> None:
    """Verify Haiku model is used for cost-effectiveness."""
    executor = FakePromptExecutor(output="# Plan\n\nContent")

    generate_plan_for_step(
        executor,
        objective_body=SAMPLE_OBJECTIVE,
        objective_number=5934,
        step_id="4.1",
        step_description="Generate plan content",
        phase_name="Phase 4",
    )

    assert len(executor.prompt_calls) == 1
    assert executor.prompt_calls[0].model == "haiku"


def test_generate_plan_for_step_handles_empty_output() -> None:
    """Test handling of empty LLM output."""
    executor = FakePromptExecutor(output="")

    result = generate_plan_for_step(
        executor,
        objective_body=SAMPLE_OBJECTIVE,
        objective_number=5934,
        step_id="4.1",
        step_description="Generate plan content",
        phase_name="Phase 4",
    )

    # Empty output still returns a GeneratedPlan with fallback title
    assert isinstance(result, GeneratedPlan)
    assert result.content == ""
    assert result.title == "Step 4.1: Generate plan content"
