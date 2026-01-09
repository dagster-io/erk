"""Tests for get_artifact_health() function."""

from pathlib import Path

from erk.artifacts.artifact_health import get_artifact_health
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

    result = get_artifact_health(tmp_path / "project", saved_files)

    # Extract command artifact names
    cmd_artifacts = [a for a in result.artifacts if a.name.startswith("commands/erk/")]
    cmd_names = {a.name for a in cmd_artifacts}

    # Should include both flat and nested commands with correct relative paths
    assert "commands/erk/plan-save.md" in cmd_names
    assert "commands/erk/system/impl-execute.md" in cmd_names
