"""Unit tests for PlanSummaryGenerator."""

from tests.fakes.prompt_executor import FakePromptExecutor

from erk.core.plan_summary_generator import (
    PlanSummaryGenerator,
    _postprocess_summary,
    generate_summary,
)

# =============================================================================
# PlanSummaryGenerator.generate
# =============================================================================


def test_generate_returns_summary_on_success() -> None:
    """Generator returns summary from LLM output."""
    executor = FakePromptExecutor(
        simulated_prompt_output="This plan adds caching to the API layer.",
    )
    generator = PlanSummaryGenerator(executor)

    result = generator.generate("# Add Caching\n\nStep 1: ...")

    assert result.success is True
    assert result.summary == "This plan adds caching to the API layer."
    assert result.error_message == ""


def test_generate_returns_failure_on_llm_error() -> None:
    """Generator returns failure when LLM execution fails."""
    executor = FakePromptExecutor(simulated_prompt_error="API error")
    generator = PlanSummaryGenerator(executor)

    result = generator.generate("# Plan")

    assert result.success is False
    assert result.summary == ""
    assert result.error_message == "API error"


def test_generate_returns_failure_on_empty_output() -> None:
    """Generator returns failure when LLM returns empty output."""
    executor = FakePromptExecutor(simulated_prompt_output="   ")
    generator = PlanSummaryGenerator(executor)

    result = generator.generate("# Plan")

    assert result.success is False
    assert result.summary == ""
    assert result.error_message != ""


def test_generate_uses_haiku_model() -> None:
    """Generator sends prompt to haiku model."""
    executor = FakePromptExecutor(simulated_prompt_output="Summary text.")
    generator = PlanSummaryGenerator(executor)

    generator.generate("# Plan\n\nContent")

    assert len(executor.prompt_calls) == 1
    prompt, system_prompt, dangerous = executor.prompt_calls[0]
    assert prompt == "# Plan\n\nContent"
    assert system_prompt is not None
    assert "summarizer" in system_prompt.lower()
    assert dangerous is False


# =============================================================================
# _postprocess_summary
# =============================================================================


def test_postprocess_strips_whitespace() -> None:
    """Post-processing strips leading/trailing whitespace."""
    assert _postprocess_summary("  summary text  ") == "summary text"


def test_postprocess_returns_empty_for_empty() -> None:
    """Post-processing returns empty string for empty/whitespace input."""
    assert _postprocess_summary("") == ""
    assert _postprocess_summary("   ") == ""


def test_postprocess_caps_at_max_length() -> None:
    """Post-processing truncates long summaries."""
    long_text = "word " * 200  # ~1000 chars
    result = _postprocess_summary(long_text)

    assert result != ""
    assert len(result) <= 503  # 500 + "..."
    assert result.endswith("...")


# =============================================================================
# generate_summary convenience function
# =============================================================================


def test_generate_summary_returns_summary_on_success() -> None:
    """Convenience function returns summary string on success."""
    executor = FakePromptExecutor(simulated_prompt_output="Good summary.")

    result = generate_summary(executor, "# Plan")

    assert result == "Good summary."


def test_generate_summary_returns_empty_on_failure() -> None:
    """Convenience function returns empty string on failure (graceful degradation)."""
    executor = FakePromptExecutor(simulated_prompt_error="LLM down")

    result = generate_summary(executor, "# Plan")

    assert result == ""
