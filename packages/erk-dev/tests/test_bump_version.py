"""Tests for bump-version command functions."""

from pathlib import Path

import pytest

from erk_dev.commands.bump_version.command import (
    find_repo_root,
    get_current_version,
    increment_patch,
    update_changelog_header,
    update_dot_agent_toml,
    update_kit_registry_md,
    update_toml_version,
    update_yaml_version,
)


class TestIncrementPatch:
    """Tests for increment_patch function."""

    def test_increments_patch_version(self) -> None:
        assert increment_patch("1.2.3") == "1.2.4"

    def test_increments_zero_patch(self) -> None:
        assert increment_patch("0.0.0") == "0.0.1"

    def test_increments_high_patch(self) -> None:
        assert increment_patch("1.0.99") == "1.0.100"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid semver"):
            increment_patch("1.2")


class TestGetCurrentVersion:
    """Tests for get_current_version function."""

    def test_reads_version_from_pyproject(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('version = "1.2.3"\n', encoding="utf-8")
        assert get_current_version(tmp_path) == "1.2.3"

    def test_returns_none_when_no_file(self, tmp_path: Path) -> None:
        assert get_current_version(tmp_path) is None

    def test_returns_none_when_no_version(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'foo'\n", encoding="utf-8")
        assert get_current_version(tmp_path) is None


class TestFindRepoRoot:
    """Tests for find_repo_root function."""

    def test_finds_root_with_workspace(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv.workspace]\nmembers = []\n", encoding="utf-8")
        subdir = tmp_path / "packages" / "foo"
        subdir.mkdir(parents=True)
        assert find_repo_root(subdir) == tmp_path

    def test_returns_none_without_workspace(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'foo'\n", encoding="utf-8")
        assert find_repo_root(tmp_path) is None


class TestUpdateTomlVersion:
    """Tests for update_toml_version function."""

    def test_updates_version_in_toml(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "pyproject.toml"
        toml_file.write_text('version = "1.0.0"\n', encoding="utf-8")
        ok, old = update_toml_version(toml_file, "2.0.0", dry_run=False)
        assert ok is True
        assert old == "1.0.0"
        assert toml_file.read_text(encoding="utf-8") == 'version = "2.0.0"\n'

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "pyproject.toml"
        toml_file.write_text('version = "1.0.0"\n', encoding="utf-8")
        ok, old = update_toml_version(toml_file, "2.0.0", dry_run=True)
        assert ok is True
        assert old == "1.0.0"
        assert toml_file.read_text(encoding="utf-8") == 'version = "1.0.0"\n'

    def test_returns_false_when_no_version(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "pyproject.toml"
        toml_file.write_text("[project]\nname = 'foo'\n", encoding="utf-8")
        ok, old = update_toml_version(toml_file, "2.0.0", dry_run=False)
        assert ok is False
        assert old is None


class TestUpdateYamlVersion:
    """Tests for update_yaml_version function."""

    def test_updates_version_in_yaml(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "kit.yaml"
        yaml_file.write_text("name: my-kit\nversion: 1.0.0\n", encoding="utf-8")
        ok, old = update_yaml_version(yaml_file, "2.0.0", dry_run=False)
        assert ok is True
        assert old == "1.0.0"
        assert "version: 2.0.0" in yaml_file.read_text(encoding="utf-8")

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "kit.yaml"
        yaml_file.write_text("version: 1.0.0\n", encoding="utf-8")
        ok, old = update_yaml_version(yaml_file, "2.0.0", dry_run=True)
        assert ok is True
        assert old == "1.0.0"
        assert yaml_file.read_text(encoding="utf-8") == "version: 1.0.0\n"


class TestUpdateDotAgentToml:
    """Tests for update_dot_agent_toml function."""

    def test_updates_multiple_versions(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "dot-agent.toml"
        toml_file.write_text(
            '[kits.foo]\nversion = "1.0.0"\n\n[kits.bar]\nversion = "1.0.0"\n',
            encoding="utf-8",
        )
        count = update_dot_agent_toml(toml_file, "2.0.0", dry_run=False)
        assert count == 2
        content = toml_file.read_text(encoding="utf-8")
        assert 'version = "2.0.0"' in content
        assert 'version = "1.0.0"' not in content

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "dot-agent.toml"
        toml_file.write_text('version = "1.0.0"\n', encoding="utf-8")
        count = update_dot_agent_toml(toml_file, "2.0.0", dry_run=True)
        assert count == 1
        assert toml_file.read_text(encoding="utf-8") == 'version = "1.0.0"\n'


class TestUpdateKitRegistryMd:
    """Tests for update_kit_registry_md function."""

    def test_updates_entry_versions(self, tmp_path: Path) -> None:
        md_file = tmp_path / "kit-registry.md"
        md_file.write_text(
            '<!-- ENTRY_START kit_id="foo" version="1.0.0" source="bundled" -->\n',
            encoding="utf-8",
        )
        count = update_kit_registry_md(md_file, "2.0.0", dry_run=False)
        assert count == 1
        assert 'version="2.0.0"' in md_file.read_text(encoding="utf-8")

    def test_returns_zero_when_no_entries(self, tmp_path: Path) -> None:
        md_file = tmp_path / "kit-registry.md"
        md_file.write_text("# Kit Registry\n\nNo entries.\n", encoding="utf-8")
        count = update_kit_registry_md(md_file, "2.0.0", dry_run=False)
        assert count == 0


class TestUpdateChangelogHeader:
    """Tests for update_changelog_header function."""

    def test_moves_unreleased_to_versioned(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        content = (
            "# Changelog\n\n## [Unreleased]\n\n"
            "### Added\n- New feature\n\n## [1.0.0] - 2025-01-01\n"
        )
        changelog.write_text(content, encoding="utf-8")
        result = update_changelog_header(changelog, "1.1.0", dry_run=False)
        assert result is True
        content = changelog.read_text(encoding="utf-8")
        # New version section should be added
        assert "## [1.1.0] -" in content
        # Content should be under new version
        assert "### Added\n- New feature" in content
        # Unreleased should now be empty (just header)
        assert "## [Unreleased]\n\n## [1.1.0]" in content

    def test_preserves_unreleased_header(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n## [Unreleased]\n\n- Feature X\n\n## [1.0.0] - 2025-01-01\n",
            encoding="utf-8",
        )
        update_changelog_header(changelog, "1.1.0", dry_run=False)
        content = changelog.read_text(encoding="utf-8")
        # [Unreleased] section should still exist
        assert "## [Unreleased]" in content

    def test_returns_false_when_no_unreleased(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## [1.0.0] - 2025-01-01\n", encoding="utf-8")
        result = update_changelog_header(changelog, "1.1.0", dry_run=False)
        assert result is False

    def test_returns_false_when_file_not_exists(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        result = update_changelog_header(changelog, "1.1.0", dry_run=False)
        assert result is False

    def test_dry_run_does_not_modify(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        original = "# Changelog\n\n## [Unreleased]\n\n- Feature X\n\n## [1.0.0] - 2025-01-01\n"
        changelog.write_text(original, encoding="utf-8")
        result = update_changelog_header(changelog, "1.1.0", dry_run=True)
        assert result is True
        assert changelog.read_text(encoding="utf-8") == original

    def test_handles_empty_unreleased_section(self, tmp_path: Path) -> None:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2025-01-01\n", encoding="utf-8"
        )
        result = update_changelog_header(changelog, "1.1.0", dry_run=False)
        assert result is True
        content = changelog.read_text(encoding="utf-8")
        # Empty unreleased should still create new version header
        assert "## [1.1.0] -" in content
