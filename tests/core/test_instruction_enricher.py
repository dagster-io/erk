"""Tests for InstructionEnricher."""

from erk.core.instruction_enricher import (
    EnrichmentRequest,
    InstructionEnricher,
)
from tests.fakes.prompt_executor import FakePromptExecutor


def test_enrich_success_parses_title_and_summary() -> None:
    """Messy input is enriched via inference into clean title and summary."""
    executor = FakePromptExecutor(
        simulated_prompt_output=(
            "TITLE: Fix tripwire validation in CI workflow\n"
            "SUMMARY: Update the tripwire validation step to handle missing docs gracefully."
        ),
    )
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(
        EnrichmentRequest(
            raw_instruction=(
                "fix this:\n\ngithub-actions\ngithub-actions\n2m ago\n\n"
                "Tripwires validation is broken when docs are missing"
            ),
        )
    )

    assert result.title == "Fix tripwire validation in CI workflow"
    expected_summary = "Update the tripwire validation step to handle missing docs gracefully."
    assert result.summary == expected_summary
    assert "github-actions" in result.raw_instruction


def test_enrich_short_circuit_skips_inference() -> None:
    """Short single-line input bypasses inference entirely."""
    executor = FakePromptExecutor()
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(EnrichmentRequest(raw_instruction="fix the import in config.py"))

    assert result.title == "fix the import in config.py"
    assert result.summary == "fix the import in config.py"
    assert result.raw_instruction == "fix the import in config.py"
    # No inference call should have been made
    assert len(executor.prompt_calls) == 0


def test_enrich_short_circuit_boundary_60_chars() -> None:
    """Exactly 60 chars, single-line: still short-circuits."""
    instruction = "x" * 60
    executor = FakePromptExecutor()
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(EnrichmentRequest(raw_instruction=instruction))

    assert result.title == instruction
    assert len(executor.prompt_calls) == 0


def test_enrich_multiline_short_does_not_short_circuit() -> None:
    """Short but multiline input triggers inference."""
    executor = FakePromptExecutor(
        simulated_prompt_output="TITLE: Fix bug\nSUMMARY: Fix the reported bug.",
    )
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(EnrichmentRequest(raw_instruction="fix\nbug"))

    assert result.title == "Fix bug"
    assert len(executor.prompt_calls) == 1


def test_enrich_fallback_on_inference_failure() -> None:
    """When inference fails, first-line truncation is used."""
    executor = FakePromptExecutor(simulated_prompt_error="model unavailable")
    enricher = InstructionEnricher(executor)

    raw = "Fix the broken authentication flow in the login page\nSome extra context here"
    result = enricher.enrich(EnrichmentRequest(raw_instruction=raw))

    assert result.title == "Fix the broken authentication flow in the login page"
    assert result.raw_instruction == raw


def test_enrich_fallback_on_unparseable_output() -> None:
    """When model returns no TITLE:/SUMMARY: markers, fallback is used."""
    executor = FakePromptExecutor(
        simulated_prompt_output="Here is a clean version of the task.",
    )
    enricher = InstructionEnricher(executor)

    raw = "messy input\nwith multiple lines\nand noise"
    result = enricher.enrich(EnrichmentRequest(raw_instruction=raw))

    # Fallback: first line as title
    assert result.title == "messy input"
    assert result.raw_instruction == raw


def test_enrich_title_truncation_when_model_returns_long_title() -> None:
    """Model returns >60 char title: truncated with ellipsis."""
    long_title = "A" * 80
    executor = FakePromptExecutor(
        simulated_prompt_output=f"TITLE: {long_title}\nSUMMARY: A summary.",
    )
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(
        EnrichmentRequest(raw_instruction="some long instruction\nwith context"),
    )

    assert len(result.title) == 60
    assert result.title.endswith("...")


def test_enrich_raw_instruction_always_preserved() -> None:
    """raw_instruction field always equals original input, regardless of path."""
    original = "fix this:\n\ngithub-actions\n2m ago\n\nTripwires broken"

    # Success path
    executor = FakePromptExecutor(
        simulated_prompt_output="TITLE: Fix tripwires\nSUMMARY: Fix the tripwires.",
    )
    enricher = InstructionEnricher(executor)
    result = enricher.enrich(EnrichmentRequest(raw_instruction=original))
    assert result.raw_instruction == original

    # Failure path
    executor_fail = FakePromptExecutor(simulated_prompt_error="fail")
    enricher_fail = InstructionEnricher(executor_fail)
    result_fail = enricher_fail.enrich(EnrichmentRequest(raw_instruction=original))
    assert result_fail.raw_instruction == original


def test_enrich_fallback_truncates_long_first_line() -> None:
    """Fallback with a long first line truncates to 60 chars."""
    long_first_line = "A" * 100
    raw = long_first_line + "\nsome context"
    executor = FakePromptExecutor(simulated_prompt_error="fail")
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(EnrichmentRequest(raw_instruction=raw))

    assert len(result.title) == 60
    assert result.title.endswith("...")


def test_enrich_fallback_summary_truncates_long_input() -> None:
    """Fallback summary is truncated to ~200 chars with ellipsis."""
    raw = "A" * 300 + "\nmore text"
    executor = FakePromptExecutor(simulated_prompt_error="fail")
    enricher = InstructionEnricher(executor)

    result = enricher.enrich(EnrichmentRequest(raw_instruction=raw))

    assert result.summary.endswith("...")
    assert len(result.summary) <= 204  # 200 + "..."
