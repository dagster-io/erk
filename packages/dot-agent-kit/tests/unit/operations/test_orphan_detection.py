"""Tests for orphan detection operations."""

from pathlib import Path

from dot_agent_kit.models.config import InstalledKit, ProjectConfig
from dot_agent_kit.operations.orphan_detection import (
    OrphanDetectionResult,
    OrphanedArtifact,
    _extract_kit_prefix_from_skill,
    detect_orphaned_artifacts,
)

# --- Helper function tests ---


def test_extract_kit_prefix_simple_name() -> None:
    """Test extracting prefix from simple skill name without variant."""
    assert _extract_kit_prefix_from_skill("simple") == "simple"


def test_extract_kit_prefix_with_numeric_variant() -> None:
    """Test extracting prefix from skill with numeric variant."""
    assert _extract_kit_prefix_from_skill("dignified-python-313") == "dignified-python"
    assert _extract_kit_prefix_from_skill("dignified-python-310") == "dignified-python"


def test_extract_kit_prefix_with_non_numeric_suffix() -> None:
    """Test extracting prefix from skill with non-numeric suffix."""
    # Non-numeric suffixes are treated as part of the kit name
    assert _extract_kit_prefix_from_skill("gt-graphite") == "gt-graphite"


def test_extract_kit_prefix_hyphenated_kit_name() -> None:
    """Test extracting prefix preserves hyphenated kit names."""
    assert _extract_kit_prefix_from_skill("my-cool-kit-123") == "my-cool-kit"


# --- No .claude/ directory ---


def test_detect_no_claude_directory(tmp_project: Path) -> None:
    """Test detection when .claude/ doesn't exist."""
    result = detect_orphaned_artifacts(tmp_project, None)

    assert isinstance(result, OrphanDetectionResult)
    assert result.orphaned_directories == []


# --- Empty .claude/ directory ---


def test_detect_empty_claude_directory(tmp_project: Path) -> None:
    """Test detection with empty .claude/ directory."""
    (tmp_project / ".claude").mkdir()

    result = detect_orphaned_artifacts(tmp_project, None)

    assert result.orphaned_directories == []


# --- No config (all kit directories are orphaned) ---


def test_detect_all_orphaned_without_config(tmp_project: Path) -> None:
    """Test detection when no config exists - all kit directories are orphaned."""
    claude_dir = tmp_project / ".claude"
    commands_dir = claude_dir / "commands"
    (commands_dir / "old-kit").mkdir(parents=True)

    result = detect_orphaned_artifacts(tmp_project, None)

    assert len(result.orphaned_directories) == 1
    orphan = result.orphaned_directories[0]
    assert orphan.path == Path(".claude/commands/old-kit")
    assert orphan.kit_id == "old-kit"
    assert "old-kit" in orphan.reason


# --- local directory is reserved ---


def test_detect_local_directory_skipped(tmp_project: Path) -> None:
    """Test that .claude/commands/local/ is not considered orphaned."""
    claude_dir = tmp_project / ".claude"
    (claude_dir / "commands" / "local").mkdir(parents=True)

    result = detect_orphaned_artifacts(tmp_project, None)

    assert result.orphaned_directories == []


# --- Installed kit directories are not orphaned ---


def test_detect_installed_kit_not_orphaned(tmp_project: Path) -> None:
    """Test that directories for installed kits are not orphaned."""
    claude_dir = tmp_project / ".claude"
    (claude_dir / "commands" / "my-kit").mkdir(parents=True)

    config = ProjectConfig(
        version="1",
        kits={
            "my-kit": InstalledKit(
                kit_id="my-kit",
                source_type="bundled",
                version="1.0.0",
                artifacts=[".claude/commands/my-kit/cmd.md"],
            ),
        },
    )

    result = detect_orphaned_artifacts(tmp_project, config)

    assert result.orphaned_directories == []


# --- Multiple artifact directories ---


def test_detect_multiple_orphaned_directories(tmp_project: Path) -> None:
    """Test detection across commands, agents, and docs directories."""
    claude_dir = tmp_project / ".claude"
    (claude_dir / "commands" / "old-kit").mkdir(parents=True)
    (claude_dir / "agents" / "removed-kit").mkdir(parents=True)
    (claude_dir / "docs" / "stale-kit").mkdir(parents=True)

    result = detect_orphaned_artifacts(tmp_project, None)

    assert len(result.orphaned_directories) == 3
    kit_ids = {o.kit_id for o in result.orphaned_directories}
    assert kit_ids == {"old-kit", "removed-kit", "stale-kit"}


# --- Skills with prefix matching ---


def test_detect_orphaned_skill_by_prefix(tmp_project: Path) -> None:
    """Test detection of orphaned skill using kit prefix matching."""
    claude_dir = tmp_project / ".claude"
    (claude_dir / "skills" / "dignified-python-313").mkdir(parents=True)

    result = detect_orphaned_artifacts(tmp_project, None)

    assert len(result.orphaned_directories) == 1
    orphan = result.orphaned_directories[0]
    assert orphan.path == Path(".claude/skills/dignified-python-313")
    assert orphan.kit_id == "dignified-python"
    assert "dignified-python" in orphan.reason


def test_detect_skill_not_orphaned_when_kit_installed(tmp_project: Path) -> None:
    """Test that skill is not orphaned when its kit is installed."""
    claude_dir = tmp_project / ".claude"
    (claude_dir / "skills" / "dignified-python-313").mkdir(parents=True)

    config = ProjectConfig(
        version="1",
        kits={
            "dignified-python": InstalledKit(
                kit_id="dignified-python",
                source_type="bundled",
                version="1.0.0",
                artifacts=[".claude/skills/dignified-python-313/SKILL.md"],
            ),
        },
    )

    result = detect_orphaned_artifacts(tmp_project, config)

    assert result.orphaned_directories == []


# --- Mix of orphaned and valid directories ---


def test_detect_mixed_orphaned_and_valid(tmp_project: Path) -> None:
    """Test detection correctly identifies orphaned vs valid directories."""
    claude_dir = tmp_project / ".claude"
    (claude_dir / "commands" / "installed-kit").mkdir(parents=True)
    (claude_dir / "commands" / "orphaned-kit").mkdir(parents=True)
    (claude_dir / "agents" / "installed-kit").mkdir(parents=True)

    config = ProjectConfig(
        version="1",
        kits={
            "installed-kit": InstalledKit(
                kit_id="installed-kit",
                source_type="bundled",
                version="1.0.0",
                artifacts=[],
            ),
        },
    )

    result = detect_orphaned_artifacts(tmp_project, config)

    assert len(result.orphaned_directories) == 1
    assert result.orphaned_directories[0].kit_id == "orphaned-kit"


# --- Files (not directories) are ignored ---


def test_detect_ignores_files_in_artifact_dirs(tmp_project: Path) -> None:
    """Test that files in artifact directories are not treated as orphaned."""
    claude_dir = tmp_project / ".claude"
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    # Create a file, not a directory
    (commands_dir / "some-file.md").write_text("# Command", encoding="utf-8")

    result = detect_orphaned_artifacts(tmp_project, None)

    assert result.orphaned_directories == []


# --- Dataclass structure tests ---


def test_orphaned_artifact_dataclass() -> None:
    """Test OrphanedArtifact dataclass creation and access."""
    artifact = OrphanedArtifact(
        path=Path(".claude/commands/old-kit"),
        reason="kit 'old-kit' not installed",
        kit_id="old-kit",
    )

    assert artifact.path == Path(".claude/commands/old-kit")
    assert artifact.reason == "kit 'old-kit' not installed"
    assert artifact.kit_id == "old-kit"


def test_orphan_detection_result_dataclass() -> None:
    """Test OrphanDetectionResult dataclass creation and access."""
    result = OrphanDetectionResult(
        orphaned_directories=[
            OrphanedArtifact(
                path=Path(".claude/commands/old-kit"),
                reason="kit 'old-kit' not installed",
                kit_id="old-kit",
            )
        ]
    )

    assert len(result.orphaned_directories) == 1
    assert result.orphaned_directories[0].kit_id == "old-kit"
