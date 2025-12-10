"""Unit tests for set_gha_output kit CLI command.

Tests setting GitHub Actions output variables from JSON input or direct values.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.scripts.erk.set_gha_output import (
    SetOutputError,
    SetOutputSuccess,
    _extract_value_from_json,
    _set_gha_output_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.set_gha_output import (
    set_gha_output as set_gha_output_command,
)

# ============================================================================
# 1. JSON Extraction Tests (6 tests)
# ============================================================================


def test_extract_simple_key() -> None:
    """Test extracting a simple top-level key."""
    data = {"trunk_branch": "main"}
    result = _extract_value_from_json(data, ".trunk_branch")
    assert result == "main"


def test_extract_nested_key() -> None:
    """Test extracting a nested key."""
    data = {"data": {"value": "nested"}}
    result = _extract_value_from_json(data, ".data.value")
    assert result == "nested"


def test_extract_array_index() -> None:
    """Test extracting array element by index."""
    data = {"items": ["first", "second", "third"]}
    result = _extract_value_from_json(data, ".items[1]")
    assert result == "second"


def test_extract_missing_key_returns_none() -> None:
    """Test that missing keys return None."""
    data = {"key": "value"}
    result = _extract_value_from_json(data, ".missing")
    assert result is None


def test_extract_boolean_value() -> None:
    """Test extracting boolean values as lowercase strings."""
    data = {"enabled": True, "disabled": False}
    assert _extract_value_from_json(data, ".enabled") == "true"
    assert _extract_value_from_json(data, ".disabled") == "false"


def test_extract_number_value() -> None:
    """Test extracting numeric values as strings."""
    data = {"count": 42, "ratio": 3.14}
    assert _extract_value_from_json(data, ".count") == "42"
    assert _extract_value_from_json(data, ".ratio") == "3.14"


# ============================================================================
# 2. Implementation Logic Tests (5 tests)
# ============================================================================


def test_impl_direct_value(tmp_path: Path) -> None:
    """Test setting output with direct value."""
    output_file = tmp_path / "github_output"
    output_file.touch()

    result = _set_gha_output_impl(
        key="my_key",
        value="my_value",
        jq_path=None,
        json_input=None,
        github_output_path=str(output_file),
    )

    assert isinstance(result, SetOutputSuccess)
    assert result.success is True
    assert result.key == "my_key"
    assert result.value == "my_value"
    assert output_file.read_text(encoding="utf-8") == "my_key=my_value\n"


def test_impl_json_extraction(tmp_path: Path) -> None:
    """Test setting output by extracting from JSON."""
    output_file = tmp_path / "github_output"
    output_file.touch()

    result = _set_gha_output_impl(
        key="trunk_branch",
        value=None,
        jq_path=".trunk_branch",
        json_input='{"trunk_branch": "main"}',
        github_output_path=str(output_file),
    )

    assert isinstance(result, SetOutputSuccess)
    assert result.success is True
    assert result.key == "trunk_branch"
    assert result.value == "main"
    assert output_file.read_text(encoding="utf-8") == "trunk_branch=main\n"


def test_impl_missing_github_output() -> None:
    """Test error when GITHUB_OUTPUT is not set."""
    result = _set_gha_output_impl(
        key="my_key",
        value="my_value",
        jq_path=None,
        json_input=None,
        github_output_path=None,
    )

    assert isinstance(result, SetOutputError)
    assert result.success is False
    assert result.error == "github_output_not_set"


def test_impl_invalid_json() -> None:
    """Test error with invalid JSON input."""
    result = _set_gha_output_impl(
        key="my_key",
        value=None,
        jq_path=".key",
        json_input="not valid json",
        github_output_path="/tmp/output",
    )

    assert isinstance(result, SetOutputError)
    assert result.success is False
    assert result.error == "json_parse_error"


def test_impl_key_not_found(tmp_path: Path) -> None:
    """Test error when JSON path not found."""
    output_file = tmp_path / "github_output"
    output_file.touch()

    result = _set_gha_output_impl(
        key="my_key",
        value=None,
        jq_path=".missing_key",
        json_input='{"other_key": "value"}',
        github_output_path=str(output_file),
    )

    assert isinstance(result, SetOutputError)
    assert result.success is False
    assert result.error == "key_not_found"


# ============================================================================
# 3. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_direct_value(tmp_path: Path, monkeypatch) -> None:
    """Test CLI with direct value."""
    output_file = tmp_path / "github_output"
    output_file.touch()
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    runner = CliRunner()
    result = runner.invoke(set_gha_output_command, ["--key", "my_key", "--value", "my_value"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["key"] == "my_key"
    assert output["value"] == "my_value"


def test_cli_json_extraction(tmp_path: Path, monkeypatch) -> None:
    """Test CLI with JSON extraction from stdin."""
    output_file = tmp_path / "github_output"
    output_file.touch()
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    runner = CliRunner()
    result = runner.invoke(
        set_gha_output_command,
        ["--key", "trunk", "--jq-path", ".trunk_branch"],
        input='{"trunk_branch": "main"}',
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["value"] == "main"


def test_cli_error_exit_code(tmp_path: Path, monkeypatch) -> None:
    """Test CLI exits with error code on failure."""
    # Don't set GITHUB_OUTPUT
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    runner = CliRunner()
    result = runner.invoke(set_gha_output_command, ["--key", "my_key", "--value", "my_value"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "github_output_not_set"


def test_cli_append_to_existing(tmp_path: Path, monkeypatch) -> None:
    """Test CLI appends to existing GITHUB_OUTPUT file."""
    output_file = tmp_path / "github_output"
    output_file.write_text("existing_key=existing_value\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    runner = CliRunner()
    result = runner.invoke(set_gha_output_command, ["--key", "new_key", "--value", "new_value"])

    assert result.exit_code == 0
    content = output_file.read_text(encoding="utf-8")
    assert "existing_key=existing_value" in content
    assert "new_key=new_value" in content
