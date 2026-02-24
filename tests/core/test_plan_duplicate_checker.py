"""Tests for PlanDuplicateChecker."""

from datetime import datetime

from erk.core.plan_duplicate_checker import PlanDuplicateChecker
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.fakes.prompt_executor import FakePromptExecutor


def _make_issue(
    *,
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create a minimal IssueInfo for testing."""
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
        author="test",
    )


def test_no_duplicates_found() -> None:
    """No duplicates returns has_duplicates=False."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": []}',
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd dark mode toggle",
        [_make_issue(number=100, title="Refactor auth", body="Restructure auth flow")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is None


def test_duplicate_detected() -> None:
    """Detected duplicate returns correct match with issue number and explanation."""
    llm_output = (
        '{"duplicates": [{"issue_number": 100, "explanation": "Both plans add dark mode support"}]}'
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd dark mode",
        [_make_issue(number=100, title="Dark mode support", body="Add dark mode to app")],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 1
    assert result.matches[0].issue_number == 100
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
        [_make_issue(number=100, title="Existing plan", body="body")],
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
        [_make_issue(number=100, title="Existing plan", body="body")],
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
        [_make_issue(number=100, title="Existing plan", body="body")],
    )

    assert result.has_duplicates is False
    assert result.matches == []
    assert result.error is not None
    assert "missing 'duplicates' list" in result.error


def test_duplicate_referencing_unknown_issue_filtered_out() -> None:
    """Duplicates referencing issue numbers not in existing plans are filtered."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"duplicates": [{"issue_number": 999, "explanation": "phantom"}]}',
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_issue(number=100, title="Existing plan", body="body")],
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
        [_make_issue(number=100, title="Existing plan", body="body")],
    )

    assert len(executor.prompt_calls) == 1
    _prompt, system_prompt, dangerous = executor.prompt_calls[0]
    assert system_prompt is not None
    assert "duplicate" in system_prompt.lower()
    assert dangerous is False


def test_json_wrapped_in_code_fence() -> None:
    """LLM response wrapped in markdown code fences is handled."""
    llm_output = '```json\n{"duplicates": [{"issue_number": 100, "explanation": "same"}]}\n```'
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_issue(number=100, title="Existing plan", body="body")],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 1
    assert result.matches[0].issue_number == 100


def test_json_wrapped_in_code_fence_with_trailing_text() -> None:
    """LLM response with code fences AND trailing commentary is handled."""
    llm_output = (
        "```json\n"
        '{"duplicates": [{"issue_number": 100, "explanation": "same"}]}\n'
        "```\n"
        "\nThis JSON shows the duplicate found between the plans."
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [_make_issue(number=100, title="Existing plan", body="body")],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 1
    assert result.matches[0].issue_number == 100


def test_multiple_duplicates() -> None:
    """Multiple duplicates are all returned."""
    llm_output = (
        '{"duplicates": ['
        '{"issue_number": 100, "explanation": "same A"}, '
        '{"issue_number": 200, "explanation": "same B"}'
        "]}"
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanDuplicateChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        [
            _make_issue(number=100, title="Plan A", body="body A"),
            _make_issue(number=200, title="Plan B", body="body B"),
        ],
    )

    assert result.has_duplicates is True
    assert len(result.matches) == 2
    assert result.matches[0].issue_number == 100
    assert result.matches[1].issue_number == 200
