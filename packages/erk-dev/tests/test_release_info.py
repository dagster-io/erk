"""Tests for release-info command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk_dev.commands.release_info.command import (
    parse_last_release,
    release_info_command,
)


def test_parse_last_release_extracts_version_and_date(tmp_path: Path) -> None:
    """Test that parse_last_release finds the first versioned release."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

## [0.2.1] - 2025-12-11

- Feature X

## [0.2.0] - 2025-12-01

- Initial release
""",
        encoding="utf-8",
    )

    result = parse_last_release(changelog)

    assert result is not None
    assert result[0] == "0.2.1"
    assert result[1] == "2025-12-11"


def test_parse_last_release_skips_unreleased(tmp_path: Path) -> None:
    """Test that [Unreleased] section is skipped."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

- In progress work

## [1.0.0] - 2025-01-15

- First stable release
""",
        encoding="utf-8",
    )

    result = parse_last_release(changelog)

    assert result is not None
    assert result[0] == "1.0.0"
    assert result[1] == "2025-01-15"


def test_parse_last_release_returns_none_when_no_versions(tmp_path: Path) -> None:
    """Test that None is returned when no versioned releases exist."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

- Work in progress
""",
        encoding="utf-8",
    )

    result = parse_last_release(changelog)

    assert result is None


def test_parse_last_release_returns_none_when_no_file(tmp_path: Path) -> None:
    """Test that None is returned when changelog doesn't exist."""
    changelog = tmp_path / "CHANGELOG.md"

    result = parse_last_release(changelog)

    assert result is None


def test_release_info_command_json_output(tmp_path: Path) -> None:
    """Test that --json-output produces valid JSON."""
    # Set up repo structure
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []

[project]
version = "0.2.1"
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

## [0.2.0] - 2025-12-01

- Previous release
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(release_info_command, ["--json-output"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["current_version"] == "0.2.1"
    assert data["last_version"] == "0.2.0"
    assert data["last_date"] == "2025-12-01"


def test_release_info_command_text_output(tmp_path: Path) -> None:
    """Test default text output format."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []

[project]
version = "1.0.0"
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """\
# Changelog

## [Unreleased]

## [0.9.0] - 2025-11-01

- Beta release
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(release_info_command, [])

    assert result.exit_code == 0
    assert "Current version: 1.0.0" in result.output
    assert "Last release: 0.9.0 (2025-11-01)" in result.output
