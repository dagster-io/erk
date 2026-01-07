"""Tests for get-embedded-prompt exec command.

Tests retrieving prompt content from bundled prompts.
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_embedded_prompt import get_embedded_prompt


def test_get_embedded_prompt_returns_content(tmp_path: Path) -> None:
    """Test get-embedded-prompt outputs prompt content when found."""
    # Create bundled prompts directory
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("# Dignified Python Review\n\nReview content here.", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(get_embedded_prompt, ["dignified-python-review"])

    assert result.exit_code == 0
    assert "# Dignified Python Review" in result.output
    assert "Review content here." in result.output


def test_get_embedded_prompt_unknown_prompt_fails() -> None:
    """Test get-embedded-prompt fails for unknown prompt names."""
    runner = CliRunner()
    result = runner.invoke(get_embedded_prompt, ["nonexistent-prompt"])

    assert result.exit_code == 1
    assert "Unknown prompt: nonexistent-prompt" in result.output


def test_get_embedded_prompt_lists_available_prompts_on_error() -> None:
    """Test get-embedded-prompt shows available prompts on error."""
    runner = CliRunner()
    result = runner.invoke(get_embedded_prompt, ["bad-name"])

    assert result.exit_code == 1
    assert "Available prompts:" in result.output
    assert "dignified-python-review" in result.output


def test_get_embedded_prompt_file_not_found(tmp_path: Path) -> None:
    """Test get-embedded-prompt fails when prompt file doesn't exist."""
    bundled_github = tmp_path / "bundled"
    bundled_github.mkdir()

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(get_embedded_prompt, ["dignified-python-review"])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_var_substitution_single(tmp_path: Path) -> None:
    """Test --var substitutes a single placeholder."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("Status: {{ status }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var", "status=success"],
        )

    assert result.exit_code == 0
    assert "Status: success" in result.output


def test_var_substitution_multiple(tmp_path: Path) -> None:
    """Test multiple --var options work."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("A: {{ a }}, B: {{ b }}, C: {{ c }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            [
                "dignified-python-review",
                "--var",
                "a=alpha",
                "--var",
                "b=beta",
                "--var",
                "c=gamma",
            ],
        )

    assert result.exit_code == 0
    assert "A: alpha, B: beta, C: gamma" in result.output


def test_var_file_reads_content(tmp_path: Path) -> None:
    """Test --var-file reads file content for substitution."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("Errors:\n{{ ERRORS }}", encoding="utf-8")

    # Create a file with content to substitute
    errors_file = tmp_path / "errors.txt"
    errors_file.write_text("Error 1: Something failed\nError 2: Another failure", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var-file", f"ERRORS={errors_file}"],
        )

    assert result.exit_code == 0
    assert "Error 1: Something failed" in result.output
    assert "Error 2: Another failure" in result.output


def test_var_file_empty_file(tmp_path: Path) -> None:
    """Test --var-file with empty file substitutes empty string."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("Before{{ content }}After", encoding="utf-8")

    # Create an empty file
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var-file", f"content={empty_file}"],
        )

    assert result.exit_code == 0
    assert "BeforeAfter" in result.output


def test_missing_variable_fails(tmp_path: Path) -> None:
    """Test missing variable for placeholder raises error."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("{{ provided }} and {{ missing }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var", "provided=value"],
        )

    assert result.exit_code == 1
    assert "Missing variables" in result.output
    assert "missing" in result.output


def test_var_file_not_found(tmp_path: Path) -> None:
    """Test --var-file with nonexistent file fails."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("{{ content }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var-file", "content=/nonexistent/path.txt"],
        )

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_invalid_var_format(tmp_path: Path) -> None:
    """Test invalid --var format fails with helpful error."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("content", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var", "no-equals-sign"],
        )

    assert result.exit_code == 1
    assert "Invalid --var format" in result.output


def test_var_with_equals_in_value(tmp_path: Path) -> None:
    """Test --var handles values containing equals signs."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("{{ equation }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var", "equation=a=b+c"],
        )

    assert result.exit_code == 0
    assert "a=b+c" in result.output


def test_placeholder_with_whitespace(tmp_path: Path) -> None:
    """Test placeholders with whitespace around key are handled."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("{{  spaced  }} and {{ normal }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            [
                "dignified-python-review",
                "--var",
                "spaced=with-space",
                "--var",
                "normal=no-space",
            ],
        )

    assert result.exit_code == 0
    assert "with-space and no-space" in result.output


def test_hyphenated_placeholder_key(tmp_path: Path) -> None:
    """Test placeholders with hyphens in key names work."""
    bundled_github = tmp_path / "bundled"
    prompts_dir = bundled_github / "prompts"
    prompts_dir.mkdir(parents=True)
    prompt_file = prompts_dir / "dignified-python-review.md"
    prompt_file.write_text("{{ docs-check }}", encoding="utf-8")

    with patch(
        "erk.cli.commands.exec.scripts.get_embedded_prompt.get_bundled_github_dir",
        return_value=bundled_github,
    ):
        runner = CliRunner()
        result = runner.invoke(
            get_embedded_prompt,
            ["dignified-python-review", "--var", "docs-check=passed"],
        )

    assert result.exit_code == 0
    assert "passed" in result.output
