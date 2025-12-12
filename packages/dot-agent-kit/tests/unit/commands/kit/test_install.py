"""Tests for kit install command functions."""

from pathlib import Path

from dot_agent_kit.commands.kit.install import _is_dev_mode_up_to_date
from dot_agent_kit.models.config import InstalledKit
from dot_agent_kit.sources.resolver import ResolvedKit


def _create_kit_manifest(kit_dir: Path, artifacts: dict[str, list[str]]) -> Path:
    """Create a kit.yaml manifest file with given artifacts."""
    import yaml

    manifest_path = kit_dir / "kit.yaml"
    manifest_data = {
        "name": "test-kit",
        "version": "1.0.0",
        "description": "Test kit",
        "artifacts": artifacts,
    }
    manifest_path.write_text(yaml.dump(manifest_data), encoding="utf-8")
    return manifest_path


def test_is_dev_mode_up_to_date_returns_false_when_manifest_has_new_artifacts(
    tmp_path: Path,
) -> None:
    """Test that dev mode is NOT up to date when kit.yaml has new artifacts."""
    # Setup: Create kit directory with manifest
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()

    # Create manifest with TWO artifacts
    manifest_path = _create_kit_manifest(
        kit_dir,
        {
            "agent": ["agents/helper.md"],
            "skill": ["skills/tool/SKILL.md"],  # New artifact in manifest
        },
    )

    # Create the actual artifact files
    (kit_dir / "agents").mkdir()
    (kit_dir / "agents" / "helper.md").write_text("# Helper", encoding="utf-8")
    (kit_dir / "skills" / "tool").mkdir(parents=True)
    (kit_dir / "skills" / "tool" / "SKILL.md").write_text("# Skill", encoding="utf-8")

    # Setup: Create project with only ONE artifact installed as symlink
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    agent_symlink = agents_dir / "helper.md"
    agent_symlink.symlink_to(kit_dir / "agents" / "helper.md")

    # Create installed kit record (tracking only one artifact)
    installed = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        artifacts=[".claude/agents/helper.md"],  # Only one artifact tracked
    )

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Act & Assert: Should return False because manifest has new artifact
    result = _is_dev_mode_up_to_date(installed, resolved, project_dir)
    assert result is False


def test_is_dev_mode_up_to_date_returns_true_when_artifacts_match(
    tmp_path: Path,
) -> None:
    """Test that dev mode IS up to date when tracked artifacts match manifest."""
    # Setup: Create kit directory with manifest
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()

    manifest_path = _create_kit_manifest(
        kit_dir,
        {
            "agent": ["agents/helper.md"],
        },
    )

    # Create the actual artifact file
    (kit_dir / "agents").mkdir()
    (kit_dir / "agents" / "helper.md").write_text("# Helper", encoding="utf-8")

    # Setup: Create project with artifact installed as symlink
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    agent_symlink = agents_dir / "helper.md"
    agent_symlink.symlink_to(kit_dir / "agents" / "helper.md")

    # Create installed kit record (artifacts match manifest)
    # Note: installed artifacts have .claude/ prefix
    installed = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        artifacts=[".claude/agents/helper.md"],  # With .claude/ prefix
    )

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Act & Assert: Should return True because artifacts match
    result = _is_dev_mode_up_to_date(installed, resolved, project_dir)
    assert result is True


def test_is_dev_mode_up_to_date_returns_false_when_artifact_not_symlink(
    tmp_path: Path,
) -> None:
    """Test that dev mode is NOT up to date when artifact is regular file, not symlink."""
    # Setup: Create kit directory with manifest
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()

    manifest_path = _create_kit_manifest(
        kit_dir,
        {
            "agent": ["agents/helper.md"],
        },
    )

    # Setup: Create project with artifact as regular file (not symlink)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    agent_file = agents_dir / "helper.md"
    agent_file.write_text("# Helper", encoding="utf-8")  # Regular file, not symlink

    installed = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        artifacts=[".claude/agents/helper.md"],  # With .claude/ prefix
    )

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Act & Assert: Should return False because artifact is not a symlink
    result = _is_dev_mode_up_to_date(installed, resolved, project_dir)
    assert result is False


def test_is_dev_mode_up_to_date_returns_false_when_artifact_missing(
    tmp_path: Path,
) -> None:
    """Test that dev mode is NOT up to date when tracked artifact doesn't exist."""
    # Setup: Create kit directory with manifest
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()

    manifest_path = _create_kit_manifest(
        kit_dir,
        {
            "agent": ["agents/helper.md"],
        },
    )

    # Setup: Create project WITHOUT the artifact
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    # Note: NOT creating agents/helper.md

    installed = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        artifacts=[".claude/agents/helper.md"],  # With .claude/ prefix, but doesn't exist
    )

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Act & Assert: Should return False because artifact doesn't exist
    result = _is_dev_mode_up_to_date(installed, resolved, project_dir)
    assert result is False


def test_is_dev_mode_up_to_date_returns_false_when_no_artifacts_tracked(
    tmp_path: Path,
) -> None:
    """Test that dev mode is NOT up to date when no artifacts are tracked."""
    # Setup: Create kit directory with manifest
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()

    manifest_path = _create_kit_manifest(
        kit_dir,
        {
            "agent": ["agents/helper.md"],
        },
    )

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    installed = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        artifacts=[],  # No artifacts tracked
    )

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Act & Assert: Should return False because no artifacts are tracked
    result = _is_dev_mode_up_to_date(installed, resolved, project_dir)
    assert result is False


def test_is_dev_mode_up_to_date_returns_false_when_manifest_has_removed_artifacts(
    tmp_path: Path,
) -> None:
    """Test that dev mode is NOT up to date when manifest has fewer artifacts than tracked."""
    # Setup: Create kit directory with manifest (only one artifact now)
    kit_dir = tmp_path / "kit"
    kit_dir.mkdir()

    manifest_path = _create_kit_manifest(
        kit_dir,
        {
            "agent": ["agents/helper.md"],
            # skill artifact was removed from manifest
        },
    )

    # Create the actual artifact file
    (kit_dir / "agents").mkdir()
    (kit_dir / "agents" / "helper.md").write_text("# Helper", encoding="utf-8")

    # Setup: Create project with TWO artifacts installed as symlinks
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()
    agent_symlink = agents_dir / "helper.md"
    agent_symlink.symlink_to(kit_dir / "agents" / "helper.md")

    skills_dir = claude_dir / "skills" / "tool"
    skills_dir.mkdir(parents=True)
    # Create a dummy target for the symlink
    dummy_skill_target = tmp_path / "old_skill.md"
    dummy_skill_target.write_text("# Old Skill", encoding="utf-8")
    skill_symlink = skills_dir / "SKILL.md"
    skill_symlink.symlink_to(dummy_skill_target)

    # Create installed kit record (tracking TWO artifacts, but manifest only has one)
    installed = InstalledKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        artifacts=[
            "agents/helper.md",
            "skills/tool/SKILL.md",  # This was removed from manifest
        ],
    )

    resolved = ResolvedKit(
        kit_id="test-kit",
        version="1.0.0",
        source_type="bundled",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Act & Assert: Should return False because tracked artifacts don't match manifest
    result = _is_dev_mode_up_to_date(installed, resolved, project_dir)
    assert result is False
