"""Unit tests for the describe exec command."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.group import exec_group

# ============================================================================
# Success Cases
# ============================================================================


def test_describe_existing_command() -> None:
    """Describe an existing command and get parameter schema."""
    runner = CliRunner()
    result = runner.invoke(exec_group, ["describe", "get-pr-feedback"])
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["command"] == "get-pr-feedback"
    assert "params" in output
    assert "help" in output

    # Verify known params exist
    param_names = [p["name"] for p in output["params"]]
    assert "pr" in param_names
    assert "include_resolved" in param_names


def test_describe_shows_param_types() -> None:
    """Describe returns correct type information for params."""
    runner = CliRunner()
    result = runner.invoke(exec_group, ["describe", "get-pr-feedback"])
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    params_by_name = {p["name"]: p for p in output["params"]}

    pr_param = params_by_name["pr"]
    assert pr_param["type"] == "int"
    assert pr_param["kind"] == "option"

    resolved_param = params_by_name["include_resolved"]
    assert resolved_param["is_flag"] is True
    assert resolved_param["kind"] == "option"


def test_describe_shows_opts() -> None:
    """Describe returns CLI option names (e.g. --pr)."""
    runner = CliRunner()
    result = runner.invoke(exec_group, ["describe", "get-pr-feedback"])
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    params_by_name = {p["name"]: p for p in output["params"]}
    assert "--pr" in params_by_name["pr"]["opts"]
    assert "--include-resolved" in params_by_name["include_resolved"]["opts"]


def test_describe_shows_choices() -> None:
    """Describe returns choice values for Choice params."""
    runner = CliRunner()
    # impl-signal has a Choice argument for the event type
    result = runner.invoke(exec_group, ["describe", "impl-signal"])
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    # Find the param with choices
    choice_params = [p for p in output["params"] if "choices" in p]
    assert len(choice_params) >= 1
    assert isinstance(choice_params[0]["choices"], list)
    assert len(choice_params[0]["choices"]) > 0


def test_describe_shows_flags() -> None:
    """Describe marks boolean flags with is_flag=true."""
    runner = CliRunner()
    result = runner.invoke(exec_group, ["describe", "get-pr-feedback"])
    assert result.exit_code == 0, result.output
    output = json.loads(result.output)

    params_by_name = {p["name"]: p for p in output["params"]}
    assert params_by_name["include_resolved"]["is_flag"] is True
    assert params_by_name["pr"]["is_flag"] is False


# ============================================================================
# Error Cases
# ============================================================================


def test_describe_nonexistent_command() -> None:
    """Describe a nonexistent command returns error JSON."""
    runner = CliRunner()
    result = runner.invoke(exec_group, ["describe", "nonexistent-command-xyz"])
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "command-not-found"
    assert "nonexistent-command-xyz" in output["message"]
