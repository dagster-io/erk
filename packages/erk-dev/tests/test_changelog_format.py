"""Tests to validate CHANGELOG.md format.

These tests run against the actual CHANGELOG.md in the repo to catch
format drift and ensure release automation will work correctly.
"""

import re
from pathlib import Path


def _get_changelog_path() -> Path:
    """Get path to the repo's CHANGELOG.md."""
    # Walk up from this file to find repo root
    current = Path(__file__).resolve()
    while current != current.parent:
        changelog = current / "CHANGELOG.md"
        if changelog.exists():
            pyproject = current / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text(encoding="utf-8")
                if "[tool.uv.workspace]" in content:
                    return changelog
        current = current.parent
    raise FileNotFoundError("Could not find CHANGELOG.md in repo root")


def test_changelog_exists() -> None:
    """Test that CHANGELOG.md exists at repo root."""
    changelog = _get_changelog_path()
    assert changelog.exists(), "CHANGELOG.md should exist at repo root"


def test_changelog_has_header() -> None:
    """Test that changelog starts with expected header."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    assert content.startswith("# Changelog"), "CHANGELOG.md should start with '# Changelog'"


def test_changelog_has_unreleased_section() -> None:
    """Test that [Unreleased] section exists for ongoing development."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    assert "## [Unreleased]" in content, "CHANGELOG.md should have an [Unreleased] section"


def test_changelog_versions_are_semver() -> None:
    """Test that all version numbers follow semver format (if any exist)."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    # Find all version headers (excluding [Unreleased])
    version_pattern = r"## \[([^\]]+)\]"
    versions = re.findall(version_pattern, content)

    # Filter out "Unreleased"
    version_numbers = [v for v in versions if v != "Unreleased"]

    # It's valid to have no releases yet (only [Unreleased])
    if len(version_numbers) == 0:
        return

    semver_pattern = r"^\d+\.\d+\.\d+$"
    for version in version_numbers:
        assert re.match(semver_pattern, version), (
            f"Version '{version}' should follow semver format (X.Y.Z)"
        )


def test_changelog_dates_are_iso_format() -> None:
    """Test that all release dates follow ISO 8601 format (if any releases exist)."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    # Find all version headers with dates
    header_pattern = r"## \[(\d+\.\d+\.\d+)\] - (\S+)"
    matches = re.findall(header_pattern, content)

    # It's valid to have no releases yet (only [Unreleased])
    if len(matches) == 0:
        return

    iso_date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    for version, date in matches:
        assert re.match(iso_date_pattern, date), (
            f"Version {version} date '{date}' should be ISO 8601 format (YYYY-MM-DD)"
        )


def test_changelog_versions_in_descending_order() -> None:
    """Test that versions are listed in descending order (newest first)."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    # Find all version headers with positions
    version_pattern = r"## \[(\d+)\.(\d+)\.(\d+)\]"
    matches = list(re.finditer(version_pattern, content))

    if len(matches) < 2:
        return  # Not enough versions to check order

    versions = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in matches]

    for i in range(len(versions) - 1):
        current = versions[i]
        next_version = versions[i + 1]
        assert current >= next_version, (
            f"Version {'.'.join(map(str, current))} should come before "
            f"{'.'.join(map(str, next_version))} (descending order)"
        )


def test_changelog_unreleased_is_first_section() -> None:
    """Test that [Unreleased] comes before all versioned sections."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    unreleased_pos = content.find("## [Unreleased]")
    first_version_match = re.search(r"## \[\d+\.\d+\.\d+\]", content)

    assert unreleased_pos != -1, "CHANGELOG.md should have [Unreleased] section"

    if first_version_match:
        assert unreleased_pos < first_version_match.start(), (
            "[Unreleased] section should come before versioned releases"
        )


def test_changelog_has_keepachangelog_link() -> None:
    """Test that changelog references Keep a Changelog format."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    # Match the full markdown link to Keep a Changelog
    keepachangelog_pattern = r"\[Keep a Changelog\]\(https://keepachangelog\.com"
    assert re.search(keepachangelog_pattern, content), (
        "CHANGELOG.md should reference Keep a Changelog format"
    )


def test_changelog_has_semver_link() -> None:
    """Test that changelog references Semantic Versioning."""
    changelog = _get_changelog_path()
    content = changelog.read_text(encoding="utf-8")

    # Match the full markdown link to Semantic Versioning
    semver_pattern = r"\[Semantic Versioning\]\(https://semver\.org"
    assert re.search(semver_pattern, content), "CHANGELOG.md should reference Semantic Versioning"
