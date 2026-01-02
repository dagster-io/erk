"""Tests for get-prompt exec command.

Tests retrieving prompt content from bundled prompts.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_prompt import get_prompt


def test_get_prompt_returns_content(tmp_path: Path) -> None:
    """Test get-prompt outputs prompt content when found."""
    # Create bundled prompts directory
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("# Dignified Python Review\n\nReview content here.", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(get_prompt, ["dignified-python-review"])

    assert result.exit_code == 0
    assert "# Dignified Python Review" in result.output
    assert "Review content here." in result.output


def test_get_prompt_unknown_prompt_fails() -> None:
    """Test get-prompt fails for unknown prompt names."""
    runner = CliRunner()
    result = runner.invoke(get_prompt, ["nonexistent-prompt"])

    assert result.exit_code == 1
    assert "Unknown prompt: nonexistent-prompt" in result.output


def test_get_prompt_lists_available_prompts_on_error() -> None:
    """Test get-prompt shows available prompts on error."""
    runner = CliRunner()
    result = runner.invoke(get_prompt, ["bad-name"])

    assert result.exit_code == 1
    assert "Available prompts:" in result.output
    assert "dignified-python-review" in result.output


def test_get_prompt_file_not_found(tmp_path: Path) -> None:
    """Test get-prompt fails when prompt file doesn't exist."""
    bundled_github = tmp_path / "bundled"
    bundled_github.mkdir()

    with patch(
        "erk.cli.commands.exec.scripts.get_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(get_prompt, ["dignified-python-review"])

    assert result.exit_code == 1
    assert "not found" in result.output
