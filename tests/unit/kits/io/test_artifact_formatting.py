"""Tests for artifact formatting functions."""

from pathlib import Path

from erk.cli.commands.artifact.formatting import (
    format_artifact_header,
    format_bundled_kit_item,
    format_compact_artifact_line,
    format_compact_doc_line,
    format_compact_list,
    format_hook_metadata,
    format_level_indicator,
    format_source_indicator,
    format_verbose_list,
)
from erk.kits.models.artifact import ArtifactLevel, ArtifactSource, InstalledArtifact
from erk.kits.models.bundled_kit import BundledKitInfo


def test_format_level_indicator_user() -> None:
    """Test level indicator formatting for user level."""
    result = format_level_indicator(ArtifactLevel.USER)
    # Should contain [U] but may have ANSI codes
    assert "[U]" in result


def test_format_level_indicator_project() -> None:
    """Test level indicator formatting for project level."""
    result = format_level_indicator(ArtifactLevel.PROJECT)
    # Should contain [P] but may have ANSI codes
    assert "[P]" in result


def test_format_source_indicator_local() -> None:
    """Test source indicator for local artifacts."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="test-skill",
        file_path=Path("skills/test-skill/SKILL.md"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.USER,
    )

    result = format_source_indicator(artifact)
    assert "[local]" in result


def test_format_source_indicator_managed() -> None:
    """Test source indicator for managed artifacts."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="test-skill",
        file_path=Path("skills/test-skill/SKILL.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.USER,
        kit_id="my-kit",
        kit_version="1.0.0",
    )

    result = format_source_indicator(artifact)
    assert "my-kit@1.0.0" in result


def test_format_compact_artifact_line() -> None:
    """Test compact single-line artifact formatting."""
    artifact = InstalledArtifact(
        artifact_type="command",
        artifact_name="test-cmd",
        file_path=Path("commands/test-cmd.md"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
    )

    result = format_compact_artifact_line(artifact)
    assert "test-cmd" in result
    assert "[P]" in result
    assert "[local]" in result


def test_format_compact_doc_line() -> None:
    """Test compact single-line doc artifact formatting with full repo-relative path."""
    artifact = InstalledArtifact(
        artifact_type="doc",
        artifact_name="guide.md",
        file_path=Path("docs/test-kit/guide.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.PROJECT,
        kit_id="test-kit",
        kit_version="1.0.0",
    )

    result = format_compact_doc_line(artifact)
    # Should display full repo-relative path (.claude/ prepended)
    assert ".claude/docs/test-kit/guide.md" in result
    assert "[P]" in result
    assert "test-kit@1.0.0" in result


def test_format_artifact_header() -> None:
    """Test artifact header formatting without absolute path."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="my-skill",
        file_path=Path("skills/my-skill/SKILL.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.USER,
        kit_id="test-kit",
        kit_version="2.0.0",
    )

    result = format_artifact_header(artifact)
    assert "my-skill" in result
    assert "skill" in result
    assert "user" in result
    assert "managed" in result
    assert "test-kit" in result
    assert "2.0.0" in result
    assert str(artifact.file_path) in result


def test_format_artifact_header_with_absolute_path() -> None:
    """Test artifact header formatting with absolute path."""
    artifact = InstalledArtifact(
        artifact_type="skill",
        artifact_name="my-skill",
        file_path=Path("skills/my-skill/SKILL.md"),
        source=ArtifactSource.MANAGED,
        level=ArtifactLevel.USER,
        kit_id="test-kit",
        kit_version="2.0.0",
    )

    absolute_path = Path("/home/user/.claude/skills/my-skill/SKILL.md")
    result = format_artifact_header(artifact, absolute_path)
    assert "my-skill" in result
    assert str(absolute_path) in result
    # Should display absolute path, not the relative path as a separate item
    # The relative path may appear as part of the absolute path, but should not
    # be listed as the main Path value when absolute_path is provided
    assert f"Path: {artifact.file_path}" not in result
    assert f"Path: {absolute_path}" in result


def test_format_hook_metadata_with_settings_json() -> None:
    """Test hook metadata formatting with settings.json source."""
    artifact = InstalledArtifact(
        artifact_type="hook",
        artifact_name="test-hook",
        file_path=Path("hooks/test-hook.py"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
        settings_source="settings.json",
    )

    result = format_hook_metadata(artifact)
    assert "settings.json" in result
    # Should NOT have warning for settings.json
    assert "⚠️" not in result


def test_format_hook_metadata_with_settings_local() -> None:
    """Test hook metadata formatting with settings.local.json source."""
    artifact = InstalledArtifact(
        artifact_type="hook",
        artifact_name="test-hook",
        file_path=Path("hooks/test-hook.py"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
        settings_source="settings.local.json",
    )

    result = format_hook_metadata(artifact)
    assert "settings.local.json" in result
    # Should have warning for settings.local.json
    assert "⚠️" in result


def test_format_hook_metadata_non_hook() -> None:
    """Test hook metadata returns empty string for non-hook artifacts."""
    artifact = InstalledArtifact(
        artifact_type="command",
        artifact_name="test-cmd",
        file_path=Path("commands/test-cmd.md"),
        source=ArtifactSource.LOCAL,
        level=ArtifactLevel.PROJECT,
    )

    result = format_hook_metadata(artifact)
    assert result == ""


def test_format_compact_list_empty() -> None:
    """Test compact list formatting with empty list."""
    result = format_compact_list([])
    assert result == ""


def test_format_compact_list_grouped_by_type() -> None:
    """Test compact list groups artifacts by type."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="skill-a",
            file_path=Path("skills/skill-a/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.USER,
        ),
        InstalledArtifact(
            artifact_type="command",
            artifact_name="cmd-a",
            file_path=Path("commands/cmd-a.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
        ),
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="skill-b",
            file_path=Path("skills/skill-b/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.USER,
        ),
    ]

    result = format_compact_list(artifacts)

    # Should have type headers
    assert "Skills:" in result or "skills:" in result.lower()
    assert "Commands:" in result or "commands:" in result.lower()

    # Should have artifact names
    assert "skill-a" in result
    assert "skill-b" in result
    assert "cmd-a" in result


def test_format_verbose_list_empty() -> None:
    """Test verbose list formatting with empty list."""
    result = format_verbose_list([])
    assert result == ""


def test_format_verbose_list_with_metadata() -> None:
    """Test verbose list includes full metadata."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="test-skill",
            file_path=Path("skills/test-skill/SKILL.md"),
            source=ArtifactSource.MANAGED,
            level=ArtifactLevel.USER,
            kit_id="my-kit",
            kit_version="1.0.0",
        ),
        InstalledArtifact(
            artifact_type="command",
            artifact_name="test-cmd",
            file_path=Path("commands/test-cmd.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
        ),
    ]

    result = format_verbose_list(artifacts)

    # Should contain artifact names
    assert "test-skill" in result
    assert "test-cmd" in result

    # Should contain type groupings
    assert "Skills:" in result
    assert "Commands:" in result

    # Should contain level indicators
    assert "[U]" in result  # User level
    assert "[P]" in result  # Project level

    # Should contain source indicators
    assert "[local]" in result
    assert "my-kit@1.0.0" in result  # Kit info in both source and Kit: line

    # Should contain indented details
    assert "Path:" in result
    assert "Kit: my-kit@1.0.0" in result


def test_format_verbose_list_with_hooks() -> None:
    """Test verbose list includes hook-specific metadata."""
    artifacts = [
        InstalledArtifact(
            artifact_type="hook",
            artifact_name="test-hook",
            file_path=Path("hooks/test-hook.py"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
            settings_source="settings.local.json",
        ),
    ]

    result = format_verbose_list(artifacts)

    # Should contain hook metadata
    assert "test-hook" in result
    assert "settings.local.json" in result
    assert "⚠️" in result  # Warning for local settings


def test_format_bundled_kit_item_cli_command() -> None:
    """Test formatting of bundled kit CLI command."""
    kit_info = BundledKitInfo(
        kit_id="gt",
        version="0.1.0",
        cli_commands=["submit-branch", "update-pr"],
        available_docs=[],
        level="project",
    )

    result = format_bundled_kit_item("submit-branch", kit_info, "cli_command")

    # Should contain command name with kit prefix
    assert "gt:submit-branch" in result
    # Should contain level marker
    assert "[P]" in result
    # Should contain kit version
    assert "gt@0.1.0" in result


def test_format_bundled_kit_item_doc() -> None:
    """Test formatting of bundled kit doc."""
    kit_info = BundledKitInfo(
        kit_id="devrun",
        version="0.2.0",
        cli_commands=[],
        available_docs=["tools/gt.md"],
        level="user",
    )

    result = format_bundled_kit_item("tools/gt.md", kit_info, "doc")

    # Should contain doc path
    assert "tools/gt.md" in result
    # Should contain level marker for user
    assert "[U]" in result
    # Should contain kit version
    assert "devrun@0.2.0" in result


def test_format_compact_list_with_bundled_kits() -> None:
    """Test compact list with bundled kits shows two sections."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="dignified-python",
            file_path=Path("skills/dignified-python/SKILL.md"),
            source=ArtifactSource.MANAGED,
            level=ArtifactLevel.PROJECT,
            kit_id="dignified-python",
            kit_version="0.1.0",
        ),
    ]

    bundled_kits = {
        "gt": BundledKitInfo(
            kit_id="gt",
            version="0.1.0",
            cli_commands=["submit-branch", "update-pr"],
            available_docs=[],
            level="project",
        ),
    }

    result = format_compact_list(artifacts, bundled_kits)

    # Should have Claude Artifacts section
    assert "Claude Artifacts:" in result
    assert "dignified-python" in result

    # Should have Installed Items section
    assert "Installed Items:" in result
    assert "Kit CLI Commands:" in result
    assert "gt:submit-branch" in result
    assert "gt:update-pr" in result


def test_format_compact_list_with_empty_bundled_kits() -> None:
    """Test compact list with empty bundled kits dict."""
    artifacts = [
        InstalledArtifact(
            artifact_type="command",
            artifact_name="test-cmd",
            file_path=Path("commands/test-cmd.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
        ),
    ]

    result = format_compact_list(artifacts, {})

    # Should still work with empty bundled kits
    assert "test-cmd" in result


def test_format_compact_list_two_sections() -> None:
    """Test compact list properly separates artifacts and kit items."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="test-skill",
            file_path=Path("skills/test-skill/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.USER,
        ),
        InstalledArtifact(
            artifact_type="doc",
            artifact_name="guide.md",
            file_path=Path("docs/test-kit/guide.md"),
            source=ArtifactSource.MANAGED,
            level=ArtifactLevel.PROJECT,
            kit_id="test-kit",
            kit_version="1.0.0",
        ),
    ]

    bundled_kits = {
        "test-kit": BundledKitInfo(
            kit_id="test-kit",
            version="1.0.0",
            cli_commands=["run"],
            available_docs=["tools/ref.md"],
            level="project",
        ),
    }

    result = format_compact_list(artifacts, bundled_kits)

    # Claude Artifacts should contain skill but not doc
    claude_section = result.split("Installed Items:")[0]
    assert "test-skill" in claude_section
    assert "guide.md" not in claude_section

    # Installed Items should contain doc and kit CLI command
    installed_section = result.split("Claude Artifacts:")[1]
    assert "guide.md" in installed_section
    assert "test-kit:run" in installed_section


def test_format_verbose_list_with_bundled_kits() -> None:
    """Test verbose list with bundled kits shows full metadata."""
    artifacts = [
        InstalledArtifact(
            artifact_type="agent",
            artifact_name="devrun",
            file_path=Path("agents/devrun.md"),
            source=ArtifactSource.MANAGED,
            level=ArtifactLevel.PROJECT,
            kit_id="devrun",
            kit_version="0.1.0",
        ),
    ]

    bundled_kits = {
        "gt": BundledKitInfo(
            kit_id="gt",
            version="0.1.0",
            cli_commands=["submit-branch"],
            available_docs=[],
            level="project",
        ),
    }

    result = format_verbose_list(artifacts, bundled_kits)

    # Should have Claude Artifacts section with metadata
    assert "Claude Artifacts:" in result
    assert "devrun" in result
    assert "Agents:" in result

    # Should have Installed Items section with kit CLI command metadata
    assert "Installed Items:" in result
    assert "Kit CLI Commands:" in result
    assert "gt:submit-branch" in result
    assert "Kit: gt@0.1.0" in result


def test_format_compact_list_level_markers() -> None:
    """Test that level markers appear correctly for all items."""
    artifacts = [
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="user-skill",
            file_path=Path("skills/user-skill/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.USER,
        ),
        InstalledArtifact(
            artifact_type="skill",
            artifact_name="project-skill",
            file_path=Path("skills/project-skill/SKILL.md"),
            source=ArtifactSource.LOCAL,
            level=ArtifactLevel.PROJECT,
        ),
    ]

    bundled_kits = {
        "user-kit": BundledKitInfo(
            kit_id="user-kit",
            version="1.0.0",
            cli_commands=["user-cmd"],
            available_docs=[],
            level="user",
        ),
        "project-kit": BundledKitInfo(
            kit_id="project-kit",
            version="1.0.0",
            cli_commands=["proj-cmd"],
            available_docs=[],
            level="project",
        ),
    }

    result = format_compact_list(artifacts, bundled_kits)

    # Should contain both [U] and [P] markers
    assert "[U]" in result
    assert "[P]" in result
