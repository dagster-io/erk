"""Tests for artifact sync."""

from pathlib import Path
from unittest.mock import patch

from erk.artifacts.sync import (
    _get_erk_package_dir,
    _is_editable_install,
    get_bundled_claude_dir,
    get_bundled_github_dir,
    sync_artifacts,
)


def test_sync_artifacts_skips_in_erk_repo(tmp_path: Path) -> None:
    """Skips sync when running in erk repo."""
    # Create pyproject.toml with erk name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    result = sync_artifacts(tmp_path, force=False)

    assert result.success is True
    assert result.artifacts_installed == 0
    assert "erk repo" in result.message


def test_sync_artifacts_fails_when_bundled_not_found(tmp_path: Path) -> None:
    """Fails when bundled .claude/ directory doesn't exist."""
    nonexistent = tmp_path / "nonexistent"
    with patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=nonexistent):
        result = sync_artifacts(tmp_path, force=False)

    assert result.success is False
    assert result.artifacts_installed == 0
    assert "not found" in result.message


def test_sync_artifacts_copies_files(tmp_path: Path) -> None:
    """Copies artifact files from bundled to target."""
    # Create bundled artifacts directory
    bundled_dir = tmp_path / "bundled"
    skill_dir = bundled_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

    # Create target directory (different from bundled)
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    # Mock both bundled dirs - github dir doesn't exist so no workflows synced
    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    assert result.artifacts_installed == 1

    # Verify file was copied
    copied_file = target_dir / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert copied_file.exists()
    assert copied_file.read_text(encoding="utf-8") == "# Test Skill"


def test_sync_artifacts_saves_state(tmp_path: Path) -> None:
    """Saves state with current version after sync."""
    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    target_dir = tmp_path / "project"
    target_dir.mkdir()

    nonexistent = tmp_path / "nonexistent"
    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_dir),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=nonexistent),
        patch("erk.artifacts.sync.get_current_version", return_value="2.0.0"),
    ):
        sync_artifacts(target_dir, force=False)

    # Verify state was saved
    state_file = target_dir / ".erk" / "state.toml"
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")
    assert 'version = "2.0.0"' in content


def test_is_editable_install_returns_true_for_src_layout() -> None:
    """Returns True when erk package is not in site-packages."""
    _get_erk_package_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/code/erk/src/erk"),
    ):
        assert _is_editable_install() is True
    _get_erk_package_dir.cache_clear()


def test_is_editable_install_returns_false_for_site_packages() -> None:
    """Returns False when erk package is in site-packages."""
    _get_erk_package_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/.venv/lib/python3.11/site-packages/erk"),
    ):
        assert _is_editable_install() is False
    _get_erk_package_dir.cache_clear()


def test_get_bundled_claude_dir_editable_install() -> None:
    """Returns .claude/ at repo root for editable installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/code/erk/src/erk"),
    ):
        result = get_bundled_claude_dir()
        assert result == Path("/home/user/code/erk/.claude")
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()


def test_get_bundled_claude_dir_wheel_install() -> None:
    """Returns erk/data/claude/ for wheel installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/.venv/lib/python3.11/site-packages/erk"),
    ):
        result = get_bundled_claude_dir()
        assert result == Path("/home/user/.venv/lib/python3.11/site-packages/erk/data/claude")
    _get_erk_package_dir.cache_clear()
    get_bundled_claude_dir.cache_clear()


def test_get_bundled_github_dir_editable_install() -> None:
    """Returns .github/ at repo root for editable installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/code/erk/src/erk"),
    ):
        result = get_bundled_github_dir()
        assert result == Path("/home/user/code/erk/.github")
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()


def test_get_bundled_github_dir_wheel_install() -> None:
    """Returns erk/data/github/ for wheel installs."""
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()
    with patch(
        "erk.artifacts.sync._get_erk_package_dir",
        return_value=Path("/home/user/.venv/lib/python3.11/site-packages/erk"),
    ):
        result = get_bundled_github_dir()
        assert result == Path("/home/user/.venv/lib/python3.11/site-packages/erk/data/github")
    _get_erk_package_dir.cache_clear()
    get_bundled_github_dir.cache_clear()


def test_sync_artifacts_copies_workflows(tmp_path: Path) -> None:
    """Syncs erk-managed workflow files from bundled to target."""
    # Create bundled .claude/ directory
    bundled_claude = tmp_path / "bundled"
    bundled_claude.mkdir()

    # Create bundled .github/ with workflows
    bundled_github = tmp_path / "bundled_github"
    bundled_workflows = bundled_github / "workflows"
    bundled_workflows.mkdir(parents=True)
    (bundled_workflows / "erk-impl.yml").write_text("name: Erk Impl", encoding="utf-8")
    (bundled_workflows / "other-workflow.yml").write_text("name: Other", encoding="utf-8")

    # Create target directory
    target_dir = tmp_path / "project"
    target_dir.mkdir()

    with (
        patch("erk.artifacts.sync.get_bundled_claude_dir", return_value=bundled_claude),
        patch("erk.artifacts.sync.get_bundled_github_dir", return_value=bundled_github),
        patch("erk.artifacts.sync.get_current_version", return_value="1.0.0"),
    ):
        result = sync_artifacts(target_dir, force=False)

    assert result.success is True
    # Only erk-impl.yml should be synced (it's in BUNDLED_WORKFLOWS)
    assert result.artifacts_installed == 1

    # Verify erk-impl.yml was copied
    copied_workflow = target_dir / ".github" / "workflows" / "erk-impl.yml"
    assert copied_workflow.exists()
    assert copied_workflow.read_text(encoding="utf-8") == "name: Erk Impl"

    # Verify other-workflow.yml was NOT copied (not in BUNDLED_WORKFLOWS)
    other_workflow = target_dir / ".github" / "workflows" / "other-workflow.yml"
    assert not other_workflow.exists()
