"""Tests for orphaned artifact cleanup during sync."""

from pathlib import Path

from erk.artifacts.models import ArtifactFileState, ArtifactState
from erk.artifacts.paths import ErkPackageInfo
from erk.artifacts.state import save_artifact_state
from erk.artifacts.sync import ArtifactSyncConfig, delete_orphaned_artifacts, sync_artifacts


def _make_config(
    tmp_path: Path,
    *,
    bundled_claude_dir: Path | None = None,
    bundled_github_dir: Path | None = None,
    bundled_erk_dir: Path | None = None,
) -> ArtifactSyncConfig:
    """Build a test ArtifactSyncConfig with sync_capabilities=False."""
    nonexistent = tmp_path / "nonexistent"
    claude = bundled_claude_dir if bundled_claude_dir is not None else nonexistent
    github = bundled_github_dir if bundled_github_dir is not None else nonexistent
    erk = bundled_erk_dir if bundled_erk_dir is not None else nonexistent
    return ArtifactSyncConfig(
        package=ErkPackageInfo(
            in_erk_repo=False,
            bundled_claude_dir=claude,
            bundled_github_dir=github,
            bundled_erk_dir=erk,
            current_version="2.0.0",
        ),
        installed_capabilities=frozenset(),
        sync_capabilities=False,
        backend="claude",
    )


def _save_old_state(project_dir: Path, keys: list[str]) -> None:
    """Save a state.toml with given keys as if they were previously synced."""
    files: dict[str, ArtifactFileState] = {}
    for key in keys:
        files[key] = ArtifactFileState(version="1.0.0", hash="oldhash")
    save_artifact_state(project_dir, ArtifactState(version="1.0.0", files=files))


def test_orphaned_skill_returned_but_not_deleted(tmp_path: Path) -> None:
    """Orphaned skill is returned in SyncResult but not deleted from disk."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    orphan_skill = project_dir / ".claude" / "skills" / "old-skill"
    orphan_skill.mkdir(parents=True)
    (orphan_skill / "SKILL.md").write_text("# Old", encoding="utf-8")

    _save_old_state(project_dir, ["skills/old-skill"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 1
    assert result.orphans[0].path == orphan_skill
    # File still exists — sync no longer auto-removes
    assert orphan_skill.exists()


def test_orphaned_command_returned_but_not_deleted(tmp_path: Path) -> None:
    """Orphaned command is returned in SyncResult but not deleted from disk."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    cmd_dir = project_dir / ".claude" / "commands" / "erk"
    cmd_dir.mkdir(parents=True)
    orphan_cmd = cmd_dir / "old-cmd.md"
    orphan_cmd.write_text("# Old", encoding="utf-8")

    _save_old_state(project_dir, ["commands/erk/old-cmd.md"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 1
    assert result.orphans[0].path == orphan_cmd
    assert orphan_cmd.exists()


def test_delete_orphaned_artifacts_removes_files(tmp_path: Path) -> None:
    """delete_orphaned_artifacts removes orphaned files and directories."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    # Create orphaned skill directory
    orphan_skill = project_dir / ".claude" / "skills" / "old-skill"
    orphan_skill.mkdir(parents=True)
    (orphan_skill / "SKILL.md").write_text("# Old", encoding="utf-8")

    # Create orphaned command file
    cmd_dir = project_dir / ".claude" / "commands" / "erk"
    cmd_dir.mkdir(parents=True)
    orphan_cmd = cmd_dir / "old-cmd.md"
    orphan_cmd.write_text("# Old", encoding="utf-8")

    _save_old_state(project_dir, ["skills/old-skill", "commands/erk/old-cmd.md"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert len(result.orphans) == 2
    assert orphan_skill.exists()
    assert orphan_cmd.exists()

    # Now delete them
    removed = delete_orphaned_artifacts(list(result.orphans))
    assert removed == 2
    assert not orphan_skill.exists()
    assert not orphan_cmd.exists()


def test_empty_parent_dir_removed_after_file_deletion(tmp_path: Path) -> None:
    """Empty parent directory is cleaned up after last file is removed."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    system_dir = project_dir / ".claude" / "commands" / "erk" / "system"
    system_dir.mkdir(parents=True)
    orphan_cmd = system_dir / "old.md"
    orphan_cmd.write_text("# Old", encoding="utf-8")

    _save_old_state(project_dir, ["commands/erk/system/old.md"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert len(result.orphans) == 1
    assert orphan_cmd.exists()

    removed = delete_orphaned_artifacts(list(result.orphans))
    assert removed == 1
    assert not orphan_cmd.exists()
    # Parent "system/" dir should also be gone since it's empty
    assert not system_dir.exists()


def test_first_sync_no_old_state_returns_no_orphans(tmp_path: Path) -> None:
    """First sync with no state.toml returns zero orphans."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 0


def test_hooks_never_returned_as_orphans(tmp_path: Path) -> None:
    """Hook keys in old state but not in new keys are not returned as orphans."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    _save_old_state(project_dir, ["hooks/user-prompt-hook"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 0


def test_orphaned_agent_returned_but_not_deleted(tmp_path: Path) -> None:
    """Orphaned agent directory is returned in SyncResult but not deleted."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    orphan_agent = project_dir / ".claude" / "agents" / "old-agent"
    orphan_agent.mkdir(parents=True)
    (orphan_agent / "agent.md").write_text("# Old", encoding="utf-8")

    _save_old_state(project_dir, ["agents/old-agent"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 1
    assert result.orphans[0].path == orphan_agent
    assert orphan_agent.exists()


def test_already_deleted_orphan_not_returned(tmp_path: Path) -> None:
    """Orphan in state but already deleted from disk is not returned."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    _save_old_state(project_dir, ["skills/gone"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 0


def test_orphaned_workflow_returned_but_not_deleted(tmp_path: Path) -> None:
    """Orphaned workflow file is returned in SyncResult but not deleted."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    workflows_dir = project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    orphan_wf = workflows_dir / "old.yml"
    orphan_wf.write_text("name: Old", encoding="utf-8")

    _save_old_state(project_dir, ["workflows/old.yml"])

    config = _make_config(tmp_path, bundled_claude_dir=bundled_dir)
    result = sync_artifacts(project_dir, force=False, config=config)

    assert result.success is True
    assert len(result.orphans) == 1
    assert result.orphans[0].path == orphan_wf
    assert orphan_wf.exists()
