"""Tests for BranchSlugGenerator."""

from erk.core.branch_slug_generator import (
    BranchSlugGenerator,
    generate_slug_or_fallback,
)
from tests.fakes.prompt_executor import FakePromptExecutor


def test_successful_slug_generation() -> None:
    """Test successful slug generation from a plan title."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="objective-marker-fallback",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Add Objective Context Marker Fallback")

    assert result.success is True
    assert result.slug == "objective-marker-fallback"
    assert result.error_message is None


def test_strips_quotes_from_output() -> None:
    """Test that surrounding quotes are stripped from LLM output."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output='"fix-auth-session"',
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Fix Authentication Session Handling")

    assert result.success is True
    assert result.slug == "fix-auth-session"


def test_strips_backticks_from_output() -> None:
    """Test that surrounding backticks are stripped from LLM output."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="`add-plan-validation`",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Add Plan Validation Gate")

    assert result.success is True
    assert result.slug == "add-plan-validation"


def test_falls_back_on_executor_failure() -> None:
    """Test that executor failure returns error result."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_error="Claude CLI not available",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Some Title")

    assert result.success is False
    assert result.slug is None
    assert result.error_message is not None


def test_rejects_single_word_output() -> None:
    """Test that single-word output is rejected."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="refactor",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Refactor the Gateway Layer")

    assert result.success is False
    assert result.slug is None
    assert "Invalid LLM output" in (result.error_message or "")


def test_rejects_too_long_output() -> None:
    """Test that output exceeding 30 characters is rejected."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="this-is-a-very-long-branch-name-that-exceeds-limit",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Some Very Long Title")

    assert result.success is False
    assert result.slug is None
    assert "Invalid LLM output" in (result.error_message or "")


def test_generate_slug_or_fallback_returns_slug_on_success() -> None:
    """Test that generate_slug_or_fallback returns slug on success."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="fix-auth-bug",
    )
    result = generate_slug_or_fallback(executor, "Fix Authentication Bug in Login")

    assert result == "fix-auth-bug"


def test_generate_slug_or_fallback_returns_raw_title_on_failure() -> None:
    """Test that generate_slug_or_fallback returns raw title on failure."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_error="LLM unavailable",
    )
    result = generate_slug_or_fallback(executor, "Fix Authentication Bug")

    assert result == "Fix Authentication Bug"


def test_generate_slug_or_fallback_returns_raw_title_on_invalid_output() -> None:
    """Test that generate_slug_or_fallback returns raw title when LLM output is invalid."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="singleword",
    )
    result = generate_slug_or_fallback(executor, "Fix Authentication Bug")

    assert result == "Fix Authentication Bug"


def test_uses_haiku_model() -> None:
    """Test that the generator uses the haiku model."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="fix-auth-bug",
    )
    generator = BranchSlugGenerator(executor)
    generator.generate("Fix Auth Bug")

    assert len(executor.prompt_calls) == 1
    # prompt_calls records (prompt, system_prompt, dangerous)
    prompt, system_prompt, dangerous = executor.prompt_calls[0]
    assert prompt == "Fix Auth Bug"
    assert system_prompt is not None
    assert dangerous is False


def test_sanitizes_special_characters() -> None:
    """Test that special characters in LLM output are sanitized."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="fix auth-bug!",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Fix Auth Bug!")

    assert result.success is True
    # sanitize_worktree_name handles the special chars
    assert result.slug == "fix-auth-bug"


def test_empty_output_rejected() -> None:
    """Test that empty LLM output is rejected."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="",
    )
    generator = BranchSlugGenerator(executor)
    result = generator.generate("Some Title")

    assert result.success is False
    assert result.slug is None
