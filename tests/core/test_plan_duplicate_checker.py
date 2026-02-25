"""Tests for PlanDuplicateChecker."""

from datetime import datetime

from erk.core.plan_duplicate_checker import PlanDuplicateChecker
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.prompt_executor import FakePromptExecutor


def _make_plan(
    *,
    plan_identifier: str,
    title: str,
    body: str,
) -> Plan:
    """Create a minimal Plan for testing."""
    return Plan(
        plan_identifier=plan_identifier,
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/issues/{plan_identifier}",
        labels=["erk-planned-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
        metadata={},
        objective_id=None,
    )


def test_no_duplicates_found() -> None:
    """No duplicates returns has_duplicates=False."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd dark mode toggle",
        [_make_plan(plan_identifier="100", title="Refactor auth", body="Restructure auth flow")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is None


def test_duplicate_detected() -> None:
    """Detected duplicate returns correct match with plan_id and explanation."""
    llm_output = (
        '{"duplicates": [{"plan_id": "100", "explanation": "Both plans add dark mode support"}]}'
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd dark mode",
        [_make_plan(plan_identifier="100", title="Dark mode support", body="Add dark mode to app")],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 1
    assert result.matches[0].plan_id == "100"
    assert result.matches[0].title == "Dark mode support"
    assert result.matches[0].url == "https://github.com/owner/repo/issues/100"
    assert result.matches[0].explanation == "Both plans add dark mode support"
    assert result.error is None


def test_executor_failure_graceful_degradation() -> None:
    """Executor failure returns no duplicates with error message."""
    executor = FakePromptExecutor(
        simulated_prompt_error="LLM unavailable",
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is not None
    assert "LLM call failed" in result.error


def test_empty_existing_plans_no_llm_call() -> None:
    """Empty existing plans returns immediately without calling LLM."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check("# New Plan\n\nSome plan", [])

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is None
    # No LLM call should have been made
    assert len(executor.prompt_calls) == 0


def test_malformed_llm_response_graceful_degradation() -> None:
    """Malformed LLM response returns no duplicates with error."""
    executor = FakePromptExecutor(
        simulated_prompt_output="This is not JSON at all",
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is not None
    assert "Malformed LLM response" in result.error


def test_malformed_json_structure_graceful_degradation() -> None:
    """Valid JSON but wrong structure returns no duplicates with error."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"wrong_key": []}',
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is not None
    assert "missing 'duplicates' list" in result.error


def test_duplicate_referencing_unknown_plan_filtered_out() -> None:
    """Duplicates referencing plan IDs not in existing plans are filtered."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": [{"plan_id": "999", "explanation": "phantom"}]}',
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is None


def test_uses_haiku_model() -> None:
    """Checker uses the haiku model for LLM calls."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    checker = PlanDuplicateChecker(executor)
    checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert len(executor.prompt_calls) == 1
    _prompt, system_prompt, dangerous = executor.prompt_calls[0]
    assert system_prompt is not None
    assert "duplicate" in system_prompt.lower()
    assert dangerous is False


def test_json_wrapped_in_code_fence() -> None:
    """LLM response wrapped in markdown code fences is handled."""
    llm_output = '```json\n{"duplicates": [{"plan_id": "100", "explanation": "same"}]}\n```'
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 1
    assert result.matches[0].plan_id == "100"


def test_code_fence_with_trailing_text() -> None:
    """LLM response with explanation text after closing code fence is handled."""
    llm_output = (
        "```json\n"
        '{"duplicates": []}\n'
        "```\n"
        "\n"
        "None of the existing open plans are semantic duplicates. "
        "While #100 relates to auth, it addresses different concerns."
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_plan(plan_identifier="100", title="Existing plan", body="body")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is None


def test_code_fence_with_trailing_text_and_duplicate() -> None:
    """LLM response with duplicate match and trailing explanation is parsed."""
    llm_output = (
        "```json\n"
        '{"duplicates": [{"plan_id": "100", "explanation": "Both add auth"}]}\n'
        "```\n"
        "\n"
        "Plan #100 is a semantic duplicate because both aim to add authentication."
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd auth",
        [_make_plan(plan_identifier="100", title="Add authentication", body="Add auth flow")],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 1
    assert result.matches[0].plan_id == "100"
    assert result.error is None


def test_multiple_duplicates() -> None:
    """Multiple duplicates are all returned."""
    llm_output = (
        '{"duplicates": ['
        '{"plan_id": "100", "explanation": "same A"}, '
        '{"plan_id": "200", "explanation": "same B"}'
        "]}"
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [
            _make_plan(plan_identifier="100", title="Plan A", body="body A"),
            _make_plan(plan_identifier="200", title="Plan B", body="body B"),
        ],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 2
    assert result.matches[0].plan_id == "100"
    assert result.matches[1].plan_id == "200"
