"""Unit tests for issue-title-to-filename command."""

import json

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.issue_title_to_filename import issue_title_to_filename


@pytest.mark.parametrize(
    ("title", "expected_filename"),
    [
        ("My Feature", "my-feature-plan.md"),
        ("Fix CLI Parsing Bug", "fix-cli-parsing-bug-plan.md"),
        ("Add User Authentication", "add-user-authentication-plan.md"),
    ],
)
def test_valid_title_produces_filename(title: str, expected_filename: str) -> None:
    """Valid titles produce expected filename on stdout."""
    runner = CliRunner()
    result = runner.invoke(issue_title_to_filename, [title])
    assert result.exit_code == 0
    assert result.output.strip() == expected_filename


@pytest.mark.parametrize(
    "title",
    [
        "",
        "   ",
        "Untitled Plan",
        "Implementation Plan",
        "🚀🎉",
        "A",
    ],
)
def test_invalid_title_exits_with_code_2(title: str) -> None:
    """Invalid titles exit with code 2 and JSON error on stderr."""
    runner = CliRunner()
    result = runner.invoke(issue_title_to_filename, [title])
    assert result.exit_code == 2


def test_invalid_title_json_error_contains_guidance() -> None:
    """Invalid title outputs JSON with error_type and agent_guidance."""
    runner = CliRunner()
    result = runner.invoke(issue_title_to_filename, ["Untitled Plan"])
    assert result.exit_code == 2
    # CliRunner mixes stderr into output; parse the JSON from it
    error_output = json.loads(result.output.strip())
    assert error_output["error_type"] == "invalid_plan_title"
    assert "agent_guidance" in error_output
    assert "default fallback" in error_output["agent_guidance"].lower()
