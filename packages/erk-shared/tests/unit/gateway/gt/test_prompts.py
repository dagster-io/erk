"""Tests for get_commit_message_prompt dynamic loader."""

from pathlib import Path

from erk_shared.gateway.gt.prompts import (
    COMMIT_MESSAGE_SYSTEM_PROMPT,
    get_commit_message_prompt,
)


class TestGetCommitMessagePrompt:
    """Tests for get_commit_message_prompt()."""

    def test_returns_default_when_no_custom_file(self, tmp_path: Path) -> None:
        """Returns built-in default when custom prompt file doesn't exist."""
        result = get_commit_message_prompt(tmp_path)

        assert result == COMMIT_MESSAGE_SYSTEM_PROMPT

    def test_returns_custom_prompt_when_file_exists(self, tmp_path: Path) -> None:
        """Returns custom prompt when .erk/prompt-hooks/commit-message-prompt.md exists."""
        custom_content = "# Custom Commit Message Prompt\n\nGenerate a commit message."
        prompt_hooks_dir = tmp_path / ".erk" / "prompt-hooks"
        prompt_hooks_dir.mkdir(parents=True)
        custom_prompt_file = prompt_hooks_dir / "commit-message-prompt.md"
        custom_prompt_file.write_text(custom_content, encoding="utf-8")

        result = get_commit_message_prompt(tmp_path)

        assert result == custom_content

    def test_returns_default_when_erk_dir_exists_but_no_prompt_file(self, tmp_path: Path) -> None:
        """Returns built-in default when .erk/ exists but prompt file doesn't."""
        erk_dir = tmp_path / ".erk"
        erk_dir.mkdir()

        result = get_commit_message_prompt(tmp_path)

        assert result == COMMIT_MESSAGE_SYSTEM_PROMPT

    def test_returns_default_when_prompt_hooks_dir_exists_but_no_prompt_file(
        self, tmp_path: Path
    ) -> None:
        """Returns built-in default when prompt-hooks/ dir exists but prompt file doesn't."""
        prompt_hooks_dir = tmp_path / ".erk" / "prompt-hooks"
        prompt_hooks_dir.mkdir(parents=True)

        result = get_commit_message_prompt(tmp_path)

        assert result == COMMIT_MESSAGE_SYSTEM_PROMPT
