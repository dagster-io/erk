"""Tests for release-check command."""

from pathlib import Path

from click.testing import CliRunner

from erk_dev.commands.release_check.command import (
    release_check_command,
    validate_changelog,
)

VALID_CHANGELOG = """\
# Changelog

## [Unreleased]

## [0.2.1] - 2025-12-11

### Added
- Feature X
- Feature Y

### Fixed
- Bug fix Z

## [0.2.0] - 2025-12-01

- Initial release
"""

MISSING_UNRELEASED = """\
# Changelog

## [0.2.1] - 2025-12-11

- Feature X
"""

INVALID_VERSION_FORMAT = """\
# Changelog

## [Unreleased]

## [v0.2.1] - 2025-12-11

- Feature X
"""

NON_STANDARD_CATEGORY = """\
# Changelog

## [Unreleased]

## [0.2.1] - 2025-12-11

### Other
- Something else
"""

ODD_INDENTATION = """\
# Changelog

## [Unreleased]

## [0.2.1] - 2025-12-11

- Parent item
   - Nested with 3 spaces (wrong)
"""

INDENTATION_JUMP = """\
# Changelog

## [Unreleased]

## [0.2.1] - 2025-12-11

- Parent item
    - Nested level 2 (skipped level 1)
"""

VALID_NESTED = """\
# Changelog

## [Unreleased]

## [0.2.1] - 2025-12-11

- Parent item
  - Nested level 1
    - Nested level 2
  - Back to level 1
- Top level again
"""

MISSING_DATE = """\
# Changelog

## [Unreleased]

## [0.2.1]

- Feature X
"""


def test_validate_changelog_valid() -> None:
    """Valid changelog produces no errors."""
    issues = validate_changelog(VALID_CHANGELOG)

    errors = [i for i in issues if i.level == "error"]
    assert errors == []


def test_validate_changelog_missing_unreleased() -> None:
    """Missing [Unreleased] section is an error."""
    issues = validate_changelog(MISSING_UNRELEASED)

    errors = [i for i in issues if i.level == "error"]
    assert len(errors) == 1
    assert "Missing [Unreleased] section" in errors[0].message


def test_validate_changelog_invalid_version_format() -> None:
    """Malformed version header is an error."""
    issues = validate_changelog(INVALID_VERSION_FORMAT)

    errors = [i for i in issues if i.level == "error"]
    assert len(errors) == 1
    assert "Invalid version format" in errors[0].message
    assert "v0.2.1" in errors[0].message


def test_validate_changelog_non_standard_category() -> None:
    """Non-standard category is a warning (not error)."""
    issues = validate_changelog(NON_STANDARD_CATEGORY)

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    assert errors == []
    assert len(warnings) == 1
    assert "Non-standard category" in warnings[0].message
    assert "Other" in warnings[0].message


def test_validate_changelog_odd_indentation() -> None:
    """Odd indentation (not multiple of 2) is an error."""
    issues = validate_changelog(ODD_INDENTATION)

    errors = [i for i in issues if i.level == "error"]
    assert len(errors) == 1
    assert "Odd indentation" in errors[0].message


def test_validate_changelog_indentation_jump() -> None:
    """Indentation jumping levels is an error."""
    issues = validate_changelog(INDENTATION_JUMP)

    errors = [i for i in issues if i.level == "error"]
    assert len(errors) == 1
    assert "Indentation jumps" in errors[0].message


def test_validate_changelog_valid_nested() -> None:
    """Properly nested indentation passes validation."""
    issues = validate_changelog(VALID_NESTED)

    errors = [i for i in issues if i.level == "error"]
    assert errors == []


def test_validate_changelog_missing_date() -> None:
    """Version without date is a warning."""
    issues = validate_changelog(MISSING_DATE)

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    assert errors == []
    assert len(warnings) == 1
    assert "missing date" in warnings[0].message


def test_release_check_command_valid(tmp_path: Path) -> None:
    """Valid changelog passes all checks."""
    # Set up repo structure
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(VALID_CHANGELOG, encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(release_check_command, [])

    assert result.exit_code == 0
    assert "All checks passed" in result.output


def test_release_check_command_file_not_found(tmp_path: Path) -> None:
    """Missing CHANGELOG.md fails."""
    # Set up repo structure without changelog
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(release_check_command, [])

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_release_check_command_with_errors(tmp_path: Path) -> None:
    """Changelog with errors fails."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(MISSING_UNRELEASED, encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(release_check_command, [])

    assert result.exit_code == 1
    assert "Failed" in result.output


def test_release_check_command_with_warnings_only(tmp_path: Path) -> None:
    """Changelog with only warnings passes (exit code 0)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.uv.workspace]
members = []
""",
        encoding="utf-8",
    )

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(NON_STANDARD_CATEGORY, encoding="utf-8")

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(release_check_command, [])

    assert result.exit_code == 0
    assert "Passed with" in result.output
    assert "warning" in result.output
