"""Unit tests for synthesis module."""

from erk_shared.learn.synthesis import synthesize_session
from erk_shared.prompt_executor.fake import FakePromptExecutor


class TestSynthesizeSession:
    """Tests for synthesize_session function."""

    def test_returns_llm_output(self) -> None:
        """Returns LLM output on success."""
        fake_executor = FakePromptExecutor(output="- Doc gap 1\n- Doc gap 2")
        result = synthesize_session(
            session_xml="<session>test</session>",
            branch_name="feature-branch",
            pr_number=123,
            prompt_executor=fake_executor,
        )
        assert result == "- Doc gap 1\n- Doc gap 2"

    def test_returns_none_on_failure(self) -> None:
        """Returns None when LLM fails."""
        fake_executor = FakePromptExecutor(should_fail=True, error="API error")
        result = synthesize_session(
            session_xml="<session>test</session>",
            branch_name="feature-branch",
            pr_number=123,
            prompt_executor=fake_executor,
        )
        assert result is None

    def test_returns_none_on_empty_output(self) -> None:
        """Returns None when LLM returns empty output."""
        fake_executor = FakePromptExecutor(output="   ")
        result = synthesize_session(
            session_xml="<session>test</session>",
            branch_name="feature-branch",
            pr_number=123,
            prompt_executor=fake_executor,
        )
        assert result is None

    def test_prompt_includes_context(self) -> None:
        """Prompt includes branch name and PR number."""
        fake_executor = FakePromptExecutor(output="gaps")
        synthesize_session(
            session_xml="<session>content</session>",
            branch_name="my-feature",
            pr_number=456,
            prompt_executor=fake_executor,
        )

        assert len(fake_executor.prompt_calls) == 1
        prompt = fake_executor.prompt_calls[0].prompt
        assert "my-feature" in prompt
        assert "456" in prompt
        assert "<session>content</session>" in prompt

    def test_uses_haiku_model(self) -> None:
        """Uses haiku model for synthesis."""
        fake_executor = FakePromptExecutor(output="gaps")
        synthesize_session(
            session_xml="<session>test</session>",
            branch_name="branch",
            pr_number=1,
            prompt_executor=fake_executor,
        )

        assert fake_executor.prompt_calls[0].model == "haiku"
