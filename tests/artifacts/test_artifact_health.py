"""Tests for get_artifact_health() function."""

from pathlib import Path

from erk.artifacts.artifact_health import _get_bundled_by_type, get_artifact_health
from erk.artifacts.models import ArtifactFileState


def test_get_artifact_health_tracks_nested_commands(tmp_path: Path, monkeypatch) -> None:
    """get_artifact_health correctly enumerates nested command directories."""
    # Create bundled commands with nested structure
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_cmd = bundled_claude / "commands" / "erk"
    bundled_cmd.mkdir(parents=True)
    (bundled_cmd / "plan-save.md").write_text("# Flat Command", encoding="utf-8")

    # Create nested command (e.g., commands/erk/system/impl-execute.md)
    nested_cmd = bundled_cmd / "system"
    nested_cmd.mkdir(parents=True)
    (nested_cmd / "impl-execute.md").write_text("# Nested Command", encoding="utf-8")

    # Create project with matching structure
    project_claude = tmp_path / "project" / ".claude"
    project_cmd = project_claude / "commands" / "erk"
    project_cmd.mkdir(parents=True)
    (project_cmd / "plan-save.md").write_text("# Flat Command", encoding="utf-8")

    project_nested = project_cmd / "system"
    project_nested.mkdir(parents=True)
    (project_nested / "impl-execute.md").write_text("# Nested Command", encoding="utf-8")

    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_bundled_claude_dir",
        lambda: bundled_claude,
    )
    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_bundled_github_dir",
        lambda: tmp_path / "bundled" / ".github",
    )
    monkeypatch.setattr(
        "erk.artifacts.artifact_health.get_current_version",
        lambda: "1.0.0",
    )

    # No saved state - all artifacts will show as changed-upstream
    saved_files: dict[str, ArtifactFileState] = {}

    # Pass installed_capabilities=None to check all artifacts
    result = get_artifact_health(tmp_path / "project", saved_files, installed_capabilities=None)

    # Extract command artifact names
    cmd_artifacts = [a for a in result.artifacts if a.name.startswith("commands/erk/")]
    cmd_names = {a.name for a in cmd_artifacts}

    # Should include both flat and nested commands with correct relative paths
    assert "commands/erk/plan-save.md" in cmd_names
    assert "commands/erk/system/impl-execute.md" in cmd_names


def test_get_bundled_by_type_returns_all_when_no_filter() -> None:
    """When installed_capabilities is None, returns all managed artifacts."""
    # Hook artifacts come from HooksCapability which is required=True
    hooks = _get_bundled_by_type("hook", installed_capabilities=None)

    # Hooks should be included (they're from required capability)
    assert "user-prompt-hook" in hooks
    assert "exit-plan-mode-hook" in hooks


def test_get_bundled_by_type_returns_required_capabilities_when_empty_filter() -> None:
    """Required capabilities (like hooks) are always included even with empty filter."""
    # Empty frozenset means no capabilities are explicitly installed
    hooks = _get_bundled_by_type("hook", installed_capabilities=frozenset())

    # Hooks should still be included (from required HooksCapability)
    assert "user-prompt-hook" in hooks
    assert "exit-plan-mode-hook" in hooks


def test_get_bundled_by_type_excludes_optional_when_not_installed() -> None:
    """Optional capabilities are excluded when not in installed_capabilities."""
    # Empty frozenset means no optional capabilities installed
    skills = _get_bundled_by_type("skill", installed_capabilities=frozenset())

    # Skills are optional (not from required capability), should be excluded
    assert "dignified-python" not in skills
    assert "fake-driven-testing" not in skills


def test_get_bundled_by_type_includes_optional_when_installed() -> None:
    """Optional capabilities are included when in installed_capabilities."""
    # Include the skill capabilities
    installed = frozenset({"dignified-python", "fake-driven-testing"})
    skills = _get_bundled_by_type("skill", installed_capabilities=installed)

    # Skills should now be included
    assert "dignified-python" in skills
    assert "fake-driven-testing" in skills


def test_get_bundled_by_type_partial_installation() -> None:
    """Only installed optional capabilities are included."""
    # Only install one skill
    installed = frozenset({"dignified-python"})
    skills = _get_bundled_by_type("skill", installed_capabilities=installed)

    # Only dignified-python should be included
    assert "dignified-python" in skills
    assert "fake-driven-testing" not in skills
