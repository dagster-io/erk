"""Tests for get_artifact_health() function."""

from pathlib import Path

from erk.artifacts.artifact_health import (
    ArtifactHealthResult,
    ArtifactStatus,
    ArtifactStatusType,
    _get_bundled_by_type,
    get_artifact_health,
)
from erk.artifacts.models import ArtifactFileState
from erk.artifacts.paths import ErkPackageInfo
from erk.core.health_checks.managed_artifacts import (
    _build_managed_artifacts_result,
    _load_artifact_allowlist,
)


def test_get_artifact_health_tracks_nested_commands(tmp_path: Path) -> None:
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

    package = ErkPackageInfo(
        in_erk_repo=False,
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        bundled_erk_dir=tmp_path / "bundled" / ".erk",
        current_version="1.0.0",
    )

    # No saved state - all artifacts will show as changed-upstream
    saved_files: dict[str, ArtifactFileState] = {}

    # Pass installed_capabilities=None to check all artifacts
    result = get_artifact_health(
        tmp_path / "project",
        saved_files,
        installed_capabilities=None,
        package=package,
    )

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


# --- Tests for _load_artifact_allowlist ---


def test_load_artifact_allowlist_empty_when_no_config(tmp_path: Path) -> None:
    """Returns empty frozenset when no config files exist."""
    result = _load_artifact_allowlist(tmp_path)
    assert result == frozenset()


def test_load_artifact_allowlist_reads_config_toml(tmp_path: Path) -> None:
    """Reads allow_modified from .erk/config.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text(
        '[artifacts]\nallow_modified = ["actions/setup-claude-erk"]\n',
        encoding="utf-8",
    )
    result = _load_artifact_allowlist(tmp_path)
    assert result == frozenset({"actions/setup-claude-erk"})


def test_load_artifact_allowlist_merges_both_configs(tmp_path: Path) -> None:
    """Union of config.toml and config.local.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text(
        '[artifacts]\nallow_modified = ["actions/setup-claude-erk"]\n',
        encoding="utf-8",
    )
    (erk_dir / "config.local.toml").write_text(
        '[artifacts]\nallow_modified = ["skills/dignified-python"]\n',
        encoding="utf-8",
    )
    result = _load_artifact_allowlist(tmp_path)
    assert result == frozenset({"actions/setup-claude-erk", "skills/dignified-python"})


# --- Tests for _build_managed_artifacts_result with allowlist ---


def _make_artifact(*, name: str, status: ArtifactStatusType) -> ArtifactStatus:
    """Helper to create an ArtifactStatus for testing."""
    return ArtifactStatus(
        name=name,
        installed_version="1.0.0",
        current_version="1.0.0",
        installed_hash="abc123",
        current_hash="def456" if status != "up-to-date" else "abc123",
        status=status,
    )


def test_build_managed_artifacts_result_allows_locally_modified() -> None:
    """Allowed artifact produces no warning and no remediation."""
    health = ArtifactHealthResult(
        artifacts=[
            _make_artifact(name="skills/dignified-python", status="up-to-date"),
            _make_artifact(name="actions/setup-claude-erk", status="locally-modified"),
        ],
        skipped_reason=None,
    )
    result = _build_managed_artifacts_result(
        health, allow_modified=frozenset({"actions/setup-claude-erk"})
    )

    assert result.passed is True
    assert result.warning is False
    assert result.remediation is None


def test_build_managed_artifacts_result_verbose_shows_allowed_annotation() -> None:
    """Verbose output shows '(locally-modified, allowed by config)' for allowed artifacts."""
    health = ArtifactHealthResult(
        artifacts=[
            _make_artifact(name="actions/setup-claude-erk", status="locally-modified"),
        ],
        skipped_reason=None,
    )
    result = _build_managed_artifacts_result(
        health, allow_modified=frozenset({"actions/setup-claude-erk"})
    )

    assert result.verbose_details is not None
    assert "(locally-modified, allowed by config)" in result.verbose_details
