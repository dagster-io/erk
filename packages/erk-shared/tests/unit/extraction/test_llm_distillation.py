"""Tests for LLM distillation module - Stage 2 semantic processing.

These tests mock the subprocess call to Claude Code since we can't
invoke it in unit tests.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from erk_shared.extraction.llm_distillation import (
    DISTILLATION_PROMPT,
    distill_with_haiku,
)


class TestDistillationPrompt:
    """Tests for the distillation prompt template."""

    def test_prompt_includes_instructions(self) -> None:
        """Prompt contains key instructions for Haiku."""
        assert "preprocessing" in DISTILLATION_PROMPT
        assert "documentation extraction" in DISTILLATION_PROMPT
        assert "conservative" in DISTILLATION_PROMPT.lower()

    def test_prompt_includes_preservation_rules(self) -> None:
        """Prompt explicitly preserves important content types."""
        assert "Error messages" in DISTILLATION_PROMPT
        assert "stack traces" in DISTILLATION_PROMPT
        assert "failures" in DISTILLATION_PROMPT

    def test_prompt_includes_filtering_rules(self) -> None:
        """Prompt specifies what to filter."""
        assert "duplicate" in DISTILLATION_PROMPT.lower()
        assert "noise" in DISTILLATION_PROMPT.lower()


class TestDistillWithHaiku:
    """Tests for distill_with_haiku function."""

    def test_calls_claude_with_haiku_model(self) -> None:
        """Claude Code is called with --model haiku."""
        mock_result = MagicMock()
        mock_result.stdout = "Distilled content"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            distill_with_haiku("<session>test</session>")

            # Verify subprocess call
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]

            assert "claude" in cmd
            assert "--model" in cmd
            assert "haiku" in cmd
            assert "--print" in cmd
            assert "-p" in cmd

    def test_returns_stdout_stripped(self) -> None:
        """Returns the stripped stdout from Claude Code."""
        mock_result = MagicMock()
        mock_result.stdout = "  Distilled output  \n"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = distill_with_haiku("<session>test</session>")

            assert result == "Distilled output"

    def test_raises_runtime_error_on_failure(self) -> None:
        """Raises RuntimeError when subprocess fails."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(
                returncode=1, cmd=["claude"], stderr="Auth failed"
            ),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                distill_with_haiku("<session>test</session>")

            assert "distillation failed" in str(exc_info.value).lower()

    def test_passes_full_prompt_with_content(self) -> None:
        """Full prompt includes distillation instructions and content."""
        mock_result = MagicMock()
        mock_result.stdout = "Distilled"
        mock_result.returncode = 0

        test_content = "<session>Test content here</session>"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            distill_with_haiku(test_content)

            call_args = mock_run.call_args
            cmd = call_args[0][0]

            # Find the prompt argument (after -p)
            prompt_idx = cmd.index("-p") + 1
            full_prompt = cmd[prompt_idx]

            # Prompt should contain both template and content
            assert "preprocessing" in full_prompt
            assert test_content in full_prompt
