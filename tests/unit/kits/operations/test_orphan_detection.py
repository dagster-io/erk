"""Tests for orphan detection operations."""

from pathlib import Path

from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.operations.orphan_detection import (
    OrphanDetectionResult,
    OrphanedArtifact,
    _build_declared_directories,
    detect_orphaned_artifacts,
)

# --- Helper function tests ---


def test_build_declared_directories_empty_config() -> None:
    """Test building declared directories with no config."""
    result = _build_declared_directories(None)
    assert result == set()


def test_build_declared_directories_no_kits() -> None:
    """Test building declared directories with empty kits."""
    config = ProjectConfig(version="1", kits={})
    result = _build_declared_directories(config)
    assert result == set()


def test_build_declared_directories_single_artifact() -> None:
    """Test building declared directories from single artifact."""
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
    result = _build_declared_directories(config)
    assert result == {Path(".claude/commands/my-kit")}


def test_build_declared_directories_multiple_artifacts() -> None:
    """Test building declared directories from multiple artifacts."""
    config = ProjectConfig(
        version="1",
        kits={
            "my-kit": InstalledKit(
                kit_id="my-kit",
                source_type="bundled",
                version="1.0.0",
                artifacts=[
                    ".claude/commands/my-kit/cmd1.md",
                    ".claude/commands/my-kit/cmd2.md",
                    ".claude/agents/my-kit/agent.md",
                ],
            ),
        },
    )
    result = _build_declared_directories(config)
    assert result == {
        Path(".claude/commands/my-kit"),
        Path(".claude/agents/my-kit"),
    }


def test_build_declared_directories_skill_with_different_name() -> None:
    """Test that skill directory name can differ from kit ID.

    This is the key case: gt kit declares .claude/skills/gt-graphite/SKILL.md,
    so .claude/skills/gt-graphite should be in the declared set.
    """
    config = ProjectConfig(
        version="1",
        kits={
            "gt": InstalledKit(
                kit_id="gt",
                source_type="bundled",
                version="1.0.0",
                artifacts=[".claude/skills/gt-graphite/SKILL.md"],
            ),
        },
    )
    result = _build_declared_directories(config)
    assert Path(".claude/skills/gt-graphite") in result


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
    assert "not declared" in orphan.reason


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
    paths = {str(o.path) for o in result.orphaned_directories}
    assert paths == {
        ".claude/commands/old-kit",
        ".claude/agents/removed-kit",
        ".claude/docs/stale-kit",
    }


# --- Skills directory is excluded from orphan detection ---
#
# Skills are intentionally excluded from orphan detection because Claude Code
# resolves skills by direct folder name. There's no way to distinguish
# "local skill I created" from "orphaned kit skill" in the flat namespace.


def test_detect_skills_directory_excluded(tmp_project: Path) -> None:
    """Test that skills/ directory is not checked for orphans.

    Skills use a flat namespace where Claude Code resolves by folder name directly.
    We can't distinguish local skills from orphaned kit skills, so we skip detection.
    """
    claude_dir = tmp_project / ".claude"
    (claude_dir / "skills" / "unknown-skill").mkdir(parents=True)
    (claude_dir / "skills" / "another-skill").mkdir(parents=True)

    result = detect_orphaned_artifacts(tmp_project, None)

    # No orphans reported for skills/
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
                artifacts=[
                    ".claude/commands/installed-kit/cmd.md",
                    ".claude/agents/installed-kit/agent.md",
                ],
            ),
        },
    )

    result = detect_orphaned_artifacts(tmp_project, config)

    assert len(result.orphaned_directories) == 1
    assert result.orphaned_directories[0].path == Path(".claude/commands/orphaned-kit")


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
        reason="not declared by any installed kit",
    )

    assert artifact.path == Path(".claude/commands/old-kit")
    assert artifact.reason == "not declared by any installed kit"


def test_orphan_detection_result_dataclass() -> None:
    """Test OrphanDetectionResult dataclass creation and access."""
    result = OrphanDetectionResult(
        orphaned_directories=[
            OrphanedArtifact(
                path=Path(".claude/commands/old-kit"),
                reason="not declared by any installed kit",
            )
        ]
    )

    assert len(result.orphaned_directories) == 1
    assert result.orphaned_directories[0].path == Path(".claude/commands/old-kit")


# --- Nested artifact directories ---


def test_detect_nested_artifact_paths(tmp_project: Path) -> None:
    """Test that nested artifact paths are handled correctly.

    Some kits declare artifacts in nested directories like:
    .claude/docs/erk/includes/file.md
    """
    claude_dir = tmp_project / ".claude"
    (claude_dir / "docs" / "erk").mkdir(parents=True)
    (claude_dir / "docs" / "erk" / "includes").mkdir(parents=True)

    config = ProjectConfig(
        version="1",
        kits={
            "erk": InstalledKit(
                kit_id="erk",
                source_type="bundled",
                version="1.0.0",
                artifacts=[
                    ".claude/docs/erk/README.md",
                    ".claude/docs/erk/includes/file.md",
                ],
            ),
        },
    )

    result = detect_orphaned_artifacts(tmp_project, config)

    # .claude/docs/erk is declared, so not orphaned
    assert result.orphaned_directories == []
