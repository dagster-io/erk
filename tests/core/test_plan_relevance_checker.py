"""Tests for PlanRelevanceChecker."""

from erk.core.plan_relevance_checker import PlanRelevanceChecker
from tests.fakes.tests.prompt_executor import FakePromptExecutor


def _make_commits() -> list[dict[str, str]]:
    """Create sample commits for testing."""
    return [
        {
            "sha": "abc1234",
            "message": "Add dark mode toggle",
            "author": "dev",
            "date": "1 day ago",
        },
        {
            "sha": "def5678",
            "message": "Fix auth session timeout",
            "author": "dev",
            "date": "2 days ago",
        },
    ]


def test_no_relevant_commits_found() -> None:
    """No relevant commits returns already_implemented=False."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"already_implemented": false, "relevant_commits": []}',
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd user profile page",
        _make_commits(),
    )

    assert result.already_implemented is False
    assert result.relevant_commits == []
    assert result.error is None


def test_relevant_commit_detected() -> None:
    """Detected relevant commit returns correct result."""
    llm_output = (
        '{"already_implemented": true, "relevant_commits": '
        '[{"sha": "abc1234", "explanation": "This commit already adds dark mode"}]}'
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nAdd dark mode",
        _make_commits(),
    )

    assert result.already_implemented is True
    assert len(result.relevant_commits) == 1
    assert result.relevant_commits[0].sha == "abc1234"
    assert result.relevant_commits[0].message == "Add dark mode toggle"
    assert result.relevant_commits[0].explanation == "This commit already adds dark mode"
    assert result.error is None


def test_executor_failure_graceful_degradation() -> None:
    """Executor failure returns not implemented with error message."""
    executor = FakePromptExecutor(
        simulated_prompt_error="LLM unavailable",
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        _make_commits(),
    )

    assert result.already_implemented is False
    assert result.relevant_commits == []
    assert result.error is not None
    assert "LLM call failed" in result.error


def test_empty_commits_no_llm_call() -> None:
    """Empty commits list returns immediately without calling LLM."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"already_implemented": false, "relevant_commits": []}',
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check("# New Plan\n\nSome plan", [])

    assert result.already_implemented is False
    assert result.relevant_commits == []
    assert result.error is None
    # No LLM call should have been made
    assert len(executor.prompt_calls) == 0


def test_malformed_llm_response_graceful_degradation() -> None:
    """Malformed LLM response returns not implemented with error."""
    executor = FakePromptExecutor(
        simulated_prompt_output="This is not JSON at all",
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        _make_commits(),
    )

    assert result.already_implemented is False
    assert result.relevant_commits == []
    assert result.error is not None
    assert "Malformed LLM response" in result.error


def test_unknown_sha_filtered_out() -> None:
    """Commits referencing SHAs not in input are filtered out."""
    llm_output = (
        '{"already_implemented": true, "relevant_commits": '
        '[{"sha": "zzz9999", "explanation": "phantom commit"}]}'
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        _make_commits(),
    )

    # already_implemented should be False because all commits were filtered
    assert result.already_implemented is False
    assert result.relevant_commits == []
    assert result.error is None


def test_json_wrapped_in_code_fence() -> None:
    """LLM response wrapped in markdown code fences is handled."""
    llm_output = (
        '```json\n{"already_implemented": true, "relevant_commits": '
        '[{"sha": "abc1234", "explanation": "same work"}]}\n```'
    )
    executor = FakePromptExecutor(
        simulated_prompt_output=llm_output,
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        _make_commits(),
    )

    assert result.already_implemented is True
    assert len(result.relevant_commits) == 1
    assert result.relevant_commits[0].sha == "abc1234"


def test_missing_already_implemented_field() -> None:
    """Missing already_implemented field returns error."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"relevant_commits": []}',
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        _make_commits(),
    )

    assert result.already_implemented is False
    assert result.error is not None
    assert "missing 'already_implemented'" in result.error


def test_missing_relevant_commits_field() -> None:
    """Missing relevant_commits field returns error."""
    executor = FakePromptExecutor(
        simulated_prompt_output='{"already_implemented": true}',
    )
    checker = PlanRelevanceChecker(executor)
    result = checker.check(
        "# New Plan\n\nSome plan",
        _make_commits(),
    )

    assert result.already_implemented is False
    assert result.error is not None
    assert "missing 'relevant_commits'" in result.error
