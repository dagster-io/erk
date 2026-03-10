"""Tests for erk json pr list machine command."""

import json

from click.testing import CliRunner

from erk.cli.cli import cli


def test_json_pr_list_schema() -> None:
    """--schema flag outputs valid schema document."""
    runner = CliRunner()
    result = runner.invoke(cli, ["json", "pr", "list", "--schema"])

    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["command"] == "pr_list"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert "error_schema" in doc
    # Verify key fields in input schema
    props = doc["input_schema"]["properties"]
    assert "state" in props
    assert "limit" in props
    assert "all_users" in props
