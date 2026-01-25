"""Unit tests for LLM-based next step inference.

Tests cover:
- Parsing successful inference responses with next step
- Parsing successful inference responses without next step
- Handling LLM errors (e.g., rate limiting)
- Edge cases in response parsing
"""

from erk_shared.objectives.next_step_inference import (
    _extract_fields,
    _normalize_optional,
    _parse_inference_response,
    infer_next_step,
)
from erk_shared.objectives.types import InferenceError, NextStepResult
from erk_shared.prompt_executor.fake import FakePromptExecutor


class TestInferNextStep:
    """Tests for the main infer_next_step function."""

    def test_parses_next_step_response(self) -> None:
        """Successfully parses response indicating a next step exists."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: yes
STEP_ID: 2.1
DESCRIPTION: Create ReconcileAction type
PHASE: Phase 2: Reconciler Core
REASON: Phase 1 steps are done (#5936), Phase 2 is pending"""
        )

        result = infer_next_step(fake_executor, "test objective body")

        assert isinstance(result, NextStepResult)
        assert result.has_next_step is True
        assert result.step_id == "2.1"
        assert result.step_description == "Create ReconcileAction type"
        assert result.phase_name == "Phase 2: Reconciler Core"
        assert "Phase 1 steps are done" in result.reason

    def test_handles_no_next_step(self) -> None:
        """Parses response indicating no step is available."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: All steps have plans in progress or are complete"""
        )

        result = infer_next_step(fake_executor, "test objective body")

        assert isinstance(result, NextStepResult)
        assert result.has_next_step is False
        assert result.step_id is None
        assert result.step_description is None
        assert result.phase_name is None
        assert "All steps" in result.reason

    def test_handles_inference_error(self) -> None:
        """Returns InferenceError when LLM call fails."""
        fake_executor = FakePromptExecutor(
            should_fail=True,
            error="Rate limited",
        )

        result = infer_next_step(fake_executor, "test objective body")

        assert isinstance(result, InferenceError)
        assert result.message == "Rate limited"

    def test_handles_inference_error_default_message(self) -> None:
        """Returns InferenceError with fake's default message when no error specified."""
        fake_executor = FakePromptExecutor(
            should_fail=True,
        )

        result = infer_next_step(fake_executor, "test objective body")

        assert isinstance(result, InferenceError)
        # FakePromptExecutor defaults to "Simulated failure" when no error is specified
        assert result.message == "Simulated failure"

    def test_uses_haiku_model(self) -> None:
        """Verifies the prompt is sent with haiku model."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: Test"""
        )

        infer_next_step(fake_executor, "test objective body")

        assert len(fake_executor.prompt_calls) == 1
        assert fake_executor.prompt_calls[0].model == "haiku"

    def test_prompt_includes_objective_body(self) -> None:
        """Verifies the objective body is included in the prompt."""
        fake_executor = FakePromptExecutor(
            output="""NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: Test"""
        )

        infer_next_step(fake_executor, "My custom objective content")

        assert len(fake_executor.prompt_calls) == 1
        assert "My custom objective content" in fake_executor.prompt_calls[0].prompt


class TestParseInferenceResponse:
    """Tests for _parse_inference_response function."""

    def test_parses_complete_response(self) -> None:
        """Parses a complete well-formed response."""
        output = """NEXT_STEP: yes
STEP_ID: 1.2
DESCRIPTION: Implement roadmap parsing
PHASE: Phase 1: Foundation
REASON: Step 1.1 is complete"""

        result = _parse_inference_response(output)

        assert result.has_next_step is True
        assert result.step_id == "1.2"
        assert result.step_description == "Implement roadmap parsing"
        assert result.phase_name == "Phase 1: Foundation"
        assert result.reason == "Step 1.1 is complete"

    def test_handles_missing_fields(self) -> None:
        """Provides defaults for missing fields."""
        output = """NEXT_STEP: no"""

        result = _parse_inference_response(output)

        assert result.has_next_step is False
        assert result.step_id is None
        assert result.step_description is None
        assert result.phase_name is None
        assert result.reason == "No reason provided"

    def test_normalizes_none_values(self) -> None:
        """Converts 'none' string to None."""
        output = """NEXT_STEP: no
STEP_ID: none
DESCRIPTION: NONE
PHASE: None
REASON: No action needed"""

        result = _parse_inference_response(output)

        assert result.step_id is None
        assert result.step_description is None
        assert result.phase_name is None

    def test_handles_complex_step_ids(self) -> None:
        """Parses step IDs with letters and periods."""
        output = """NEXT_STEP: yes
STEP_ID: 2A.1
DESCRIPTION: Test step
PHASE: Phase 2A
REASON: Complex ID"""

        result = _parse_inference_response(output)

        assert result.step_id == "2A.1"

    def test_handles_colons_in_values(self) -> None:
        """Preserves colons within field values."""
        output = """NEXT_STEP: yes
STEP_ID: 1.1
DESCRIPTION: Create types: NextStepResult and InferenceError
PHASE: Phase 1: Type definitions
REASON: First step: needs to be done"""

        result = _parse_inference_response(output)

        assert result.step_description == "Create types: NextStepResult and InferenceError"
        assert result.phase_name == "Phase 1: Type definitions"
        assert result.reason == "First step: needs to be done"


class TestExtractFields:
    """Tests for _extract_fields helper function."""

    def test_extracts_known_fields(self) -> None:
        """Extracts only known field names."""
        output = """NEXT_STEP: yes
STEP_ID: 1.1
UNKNOWN_FIELD: ignored
DESCRIPTION: Test
PHASE: Phase 1
REASON: Test reason"""

        fields = _extract_fields(output)

        assert fields == {
            "NEXT_STEP": "yes",
            "STEP_ID": "1.1",
            "DESCRIPTION": "Test",
            "PHASE": "Phase 1",
            "REASON": "Test reason",
        }
        assert "UNKNOWN_FIELD" not in fields

    def test_handles_lowercase_keys(self) -> None:
        """Normalizes field keys to uppercase."""
        output = """next_step: yes
step_id: 1.1"""

        fields = _extract_fields(output)

        assert fields.get("NEXT_STEP") == "yes"
        assert fields.get("STEP_ID") == "1.1"

    def test_handles_whitespace(self) -> None:
        """Strips whitespace from keys and values."""
        output = """  NEXT_STEP  :   yes
  STEP_ID:1.1"""

        fields = _extract_fields(output)

        assert fields.get("NEXT_STEP") == "yes"
        assert fields.get("STEP_ID") == "1.1"

    def test_handles_empty_output(self) -> None:
        """Returns empty dict for empty output."""
        fields = _extract_fields("")

        assert fields == {}

    def test_skips_lines_without_colons(self) -> None:
        """Ignores lines that don't contain colons."""
        output = """Some preamble text
NEXT_STEP: yes
Another line without colon
STEP_ID: 1.1"""

        fields = _extract_fields(output)

        assert fields.get("NEXT_STEP") == "yes"
        assert fields.get("STEP_ID") == "1.1"


class TestNormalizeOptional:
    """Tests for _normalize_optional helper function."""

    def test_returns_none_for_none_string(self) -> None:
        """Converts 'none' (case-insensitive) to None."""
        assert _normalize_optional("none") is None
        assert _normalize_optional("None") is None
        assert _normalize_optional("NONE") is None

    def test_returns_none_for_empty_string(self) -> None:
        """Converts empty string to None."""
        assert _normalize_optional("") is None

    def test_returns_value_for_real_content(self) -> None:
        """Returns the value unchanged for real content."""
        assert _normalize_optional("1.1") == "1.1"
        assert _normalize_optional("Create types") == "Create types"
        assert _normalize_optional("Phase 1: Foundation") == "Phase 1: Foundation"
